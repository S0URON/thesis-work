"""
Legacy standalone CLI entry (optional). System prompt: src/agentic_crawler/agents/prompts.py (get_system_prompt).
Prefer: python main.py or agentic-crawler-web from the packaged app.
"""

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from langchain_mcp_adapters.tools import load_mcp_tools
from langchain.agents import create_agent
from langchain_groq import ChatGroq
from langchain_google_genai import ChatGoogleGenerativeAI
from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.tree import Tree
from rich import box
from rich.markdown import Markdown
from datetime import datetime, timedelta
from collections import OrderedDict
import asyncio
import sys
import os
import json
import hashlib
from pathlib import Path
from typing import Optional, Dict, Any, List
import warnings

# Prefer src/ package on import path so `agentic_crawler` resolves to the package, not this file.
_SRC_DIR = Path(__file__).resolve().parent / "src"
if _SRC_DIR.is_dir():
    sys.path.insert(0, str(_SRC_DIR))

from agentic_crawler.agents.prompts import get_system_prompt

# Suppress warnings for clean output
warnings.filterwarnings("ignore")
os.environ["PYTHONWARNINGS"] = "ignore"

# Suppress specific pydantic warnings
import logging

logging.getLogger("pydantic").setLevel(logging.ERROR)
logging.getLogger("langchain").setLevel(logging.ERROR)

load_dotenv()

console = Console()


class Config:
    CACHE_DIR = Path("cache")
    SESSIONS_DIR = Path("sessions")
    OUTPUTS_DIR = Path("tool_outputs")
    REPORTS_DIR = Path("reports")
    TOOLS_SCHEMA_FILE = Path("tools_schema.json")
    CACHE_TTL_HOURS = 24
    MAX_CACHE_SIZE = 100
    ENABLE_CACHING = True
    ENABLE_STREAMING = True
    DEBUG_MODE = False  # Set to False for cleaner output
    AUTO_SAVE_OUTPUTS = True

    COST_PER_1K_INPUT_TOKENS = 0.00025
    COST_PER_1K_OUTPUT_TOKENS = 0.001

    def __init__(self):
        self.CACHE_DIR.mkdir(exist_ok=True)
        self.SESSIONS_DIR.mkdir(exist_ok=True)
        self.OUTPUTS_DIR.mkdir(exist_ok=True)
        self.REPORTS_DIR.mkdir(exist_ok=True)


config = Config()

# Use fastest models
model_groq = ChatGroq(
    model="llama-3.3-70b-versatile",
    temperature=0.3,  # Lower for more focused responses
    streaming=config.ENABLE_STREAMING,
)

model_google = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash-lite",  # Fastest Gemini model
    temperature=0.3,
    streaming=config.ENABLE_STREAMING,
)

server_params = StdioServerParameters(
    command="npx",
    env={"FIRECRAWL_API_KEY": os.getenv("FIRECRAWL_API_KEY")},
    args=["-y", "firecrawl-mcp"],
)


class ToolCache:
    def __init__(self, max_size_mb: int = 100, ttl_hours: int = 24):
        self.cache: OrderedDict[str, Dict[str, Any]] = OrderedDict()
        self.max_size_bytes = max_size_mb * 1024 * 1024
        self.ttl = timedelta(hours=ttl_hours)
        self.current_size = 0
        self.hits = 0
        self.misses = 0

    def _get_key(self, tool_name: str, args: dict) -> str:
        args_str = json.dumps(args, sort_keys=True)
        return hashlib.md5(f"{tool_name}:{args_str}".encode()).hexdigest()

    def get(self, tool_name: str, args: dict) -> Optional[str]:
        key = self._get_key(tool_name, args)

        if key in self.cache:
            entry = self.cache[key]
            if datetime.now() - entry["timestamp"] < self.ttl:
                self.hits += 1
                self.cache.move_to_end(key)
                return entry["result"]
            else:
                self._remove(key)

        self.misses += 1
        return None

    def put(self, tool_name: str, args: dict, result: str):
        key = self._get_key(tool_name, args)
        result_size = len(result.encode("utf-8"))

        while self.current_size + result_size > self.max_size_bytes and self.cache:
            oldest_key = next(iter(self.cache))
            self._remove(oldest_key)

        self.cache[key] = {"result": result, "timestamp": datetime.now(), "size": result_size}
        self.current_size += result_size

    def _remove(self, key: str):
        if key in self.cache:
            self.current_size -= self.cache[key]["size"]
            del self.cache[key]

    def stats(self) -> dict:
        total_requests = self.hits + self.misses
        hit_rate = (self.hits / total_requests * 100) if total_requests > 0 else 0
        return {
            "hits": self.hits,
            "misses": self.misses,
            "hit_rate": f"{hit_rate:.1f}%",
            "size_mb": f"{self.current_size / 1024 / 1024:.2f}",
            "entries": len(self.cache),
        }


class ExecutionTracker:
    def __init__(self):
        self.tool_calls = []
        self.current_call = None
        self.total_input_tokens = 0
        self.total_output_tokens = 0
        self.total_cost = 0.0
        self.actions_used = 0
        self.outputs_saved = 0

    def start_tool(self, name: str, args: dict):
        self.current_call = {
            "tool": name,
            "args": args,
            "timestamp": datetime.now().isoformat(),
            "start_time": datetime.now(),
            "has_actions": "scrapeOptions" in args and "actions" in args.get("scrapeOptions", {}),
        }

    def end_tool(self, output: str, saved_path: Optional[str] = None):
        if self.current_call:
            self.current_call["output_length"] = len(str(output))
            self.current_call["duration"] = (
                datetime.now() - self.current_call["start_time"]
            ).total_seconds()
            self.current_call["saved_to"] = saved_path

            if self.current_call.get("has_actions"):
                self.actions_used += 1

            if saved_path:
                self.outputs_saved += 1

            del self.current_call["start_time"]
            del self.current_call["has_actions"]
            self.tool_calls.append(self.current_call)
            self.current_call = None

    def add_tokens(self, input_tokens: int, output_tokens: int):
        self.total_input_tokens += input_tokens
        self.total_output_tokens += output_tokens

        input_cost = (input_tokens / 1000) * config.COST_PER_1K_INPUT_TOKENS
        output_cost = (output_tokens / 1000) * config.COST_PER_1K_OUTPUT_TOKENS
        self.total_cost += input_cost + output_cost

    def get_stats(self) -> dict:
        return {
            "total_calls": len(self.tool_calls),
            "input_tokens": self.total_input_tokens,
            "output_tokens": self.total_output_tokens,
            "total_tokens": self.total_input_tokens + self.total_output_tokens,
            "estimated_cost": f"${self.total_cost:.4f}",
            "actions_used": self.actions_used,
            "outputs_saved": self.outputs_saved,
        }


def save_tool_output(tool_name: str, args: dict, output: str) -> str:
    """Save tool output to file with timestamp"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    url = args.get("url", "no_url")
    if url != "no_url":
        url_clean = (
            url.replace("https://", "")
            .replace("http://", "")
            .replace("/", "_")
            .replace(":", "_")[:50]
        )
        filename = f"{timestamp}_{tool_name}_{url_clean}.json"
    else:
        filename = f"{timestamp}_{tool_name}.json"

    filepath = config.OUTPUTS_DIR / filename

    # Save as structured JSON for easy parsing
    data = {"tool": tool_name, "timestamp": timestamp, "arguments": args, "output": output}

    filepath.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    return str(filepath)


def save_qa_report(report_content: str, url: str) -> str:
    """Save website analysis report to dedicated reports folder"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    url_clean = (
        url.replace("https://", "").replace("http://", "").replace("/", "_").replace(":", "_")[:50]
    )
    filename = f"Website_Analysis_{timestamp}_{url_clean}.md"  # Save as markdown
    filepath = config.REPORTS_DIR / filename

    filepath.write_text(report_content, encoding="utf-8")
    console.print(f"\n[bold green]📄 Website Analysis Report saved to: {filepath}[/bold green]\n")
    return str(filepath)


def display_welcome():
    console.print("\n" + "=" * 100)
    console.print("[bold cyan]⚡ Website Evaluation Agent - Maximum Performance[/bold cyan]")
    console.print(
        "[dim]Fast execution • Website summaries • User flows • Sitemap diagrams[/dim]"
    )
    console.print("=" * 100 + "\n")


def display_tool_call_compact(tool_name: str, args: dict, cached: bool = False):
    """Compact tool call display"""
    cache_indicator = "⚡" if cached else ""
    has_actions = "scrapeOptions" in args and "actions" in args.get("scrapeOptions", {})
    actions_indicator = "🎬" if has_actions else ""

    url = args.get("url", args.get("query", "N/A"))
    console.print(f"\n[yellow]🔧 {tool_name}[/yellow] {cache_indicator}{actions_indicator}")
    console.print(f"   [dim]{url}[/dim]")

    if has_actions:
        actions = args.get("scrapeOptions", {}).get("actions", [])
        console.print(f"   [green]Actions: {len(actions)}[/green]")


def display_tool_output_compact(
    output: str, tool_name: str, duration: float, saved_path: Optional[str] = None
):
    """Compact output display"""
    output_len = len(str(output))
    console.print(
        f"[green]✓ {tool_name}[/green] [dim]({duration:.1f}s, {output_len:,} chars)[/dim]"
    )
    if saved_path:
        console.print(f"  [dim]→ {saved_path}[/dim]")


def display_response(response: str):
    console.print("\n[bold cyan]💬 Agent Response:[/bold cyan]\n")

    if isinstance(response, list):
        text = ""
        for block in response:
            if isinstance(block, dict) and block.get("type") == "text":
                text += block.get("text", "")
            elif isinstance(block, str):
                text += block
        response = text.strip()

    try:
        md = Markdown(response)
        console.print(Panel(md, border_style="cyan", box=box.ROUNDED))
    except:
        console.print(Panel(f"[white]{response}[/white]", border_style="cyan", box=box.ROUNDED))
    console.print()


def display_execution_summary(tracker: ExecutionTracker, cache: ToolCache):
    console.print("\n[bold cyan]📊 Session Summary[/bold cyan]\n")

    stats = tracker.get_stats()
    cache_stats = cache.stats()

    stats_table = Table(box=box.SIMPLE, show_header=False)
    stats_table.add_column("Metric", style="cyan")
    stats_table.add_column("Value", style="yellow")

    stats_table.add_row("Tool Calls", str(stats["total_calls"]))
    stats_table.add_row("With Actions", str(stats["actions_used"]))
    stats_table.add_row("Outputs Saved", str(stats["outputs_saved"]))
    stats_table.add_row("Total Tokens", f"{stats['total_tokens']:,}")
    stats_table.add_row("Cost", stats["estimated_cost"])
    stats_table.add_row("Cache Hit Rate", cache_stats["hit_rate"])

    console.print(stats_table)
    console.print()


async def main():
    """Main chat loop"""

    display_welcome()
    cache = ToolCache(max_size_mb=config.MAX_CACHE_SIZE, ttl_hours=config.CACHE_TTL_HOURS)
    tracker = ExecutionTracker()

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            all_tools = await load_mcp_tools(session)
            tools = all_tools

            console.print(f"[green]✅ Loaded {len(tools)} tools[/green]\n")

            system_prompt = get_system_prompt()

            agent = create_agent(model_google, tools, system_prompt=system_prompt)

            messages = []

            console.print(
                "[dim]💡 Example: 'Analyze https://example.com' or 'Generate website analysis for https://site.com'[/dim]"
            )
            console.print("[dim]Commands: /stats | /clear | /reports | quit[/dim]\n")

            while True:
                try:
                    console.print("\n[cyan]You:[/cyan] ", end="")
                    user_input = input().strip()

                    if user_input.lower() in ["quit", "exit", "q"]:
                        console.print("\n[yellow]👋 Goodbye![/yellow]\n")
                        break

                    if user_input.lower() == "/stats":
                        display_execution_summary(tracker, cache)
                        continue

                    if user_input.lower() == "/clear":
                        messages = []
                        console.print("[green]✅ Conversation cleared[/green]")
                        continue

                    if user_input.lower() == "/reports":
                        reports = list(config.REPORTS_DIR.glob("*.md"))
                        reports += list(config.REPORTS_DIR.glob("*.json"))
                        console.print(f"[cyan]Website Analysis Reports ({len(reports)}):[/cyan]")
                        for report in sorted(reports)[-10:]:
                            console.print(f"  • {report.name}")
                        continue

                    if user_input.lower() == "/outputs":
                        outputs = list(config.OUTPUTS_DIR.glob("*.json"))
                        console.print(f"[cyan]Saved outputs ({len(outputs)}):[/cyan]")
                        for output in sorted(outputs)[-10:]:
                            console.print(f"  • {output.name}")
                        continue

                    if not user_input:
                        continue

                    messages.append({"role": "user", "content": user_input})

                    console.print("[blue]⏳ Processing...[/blue]")

                    agent_response = await agent.ainvoke({"messages": messages})

                    response_messages = agent_response["messages"]

                    # Track tool calls with compact display
                    tool_outputs = {}
                    for msg in response_messages[:-1]:
                        if hasattr(msg, "tool_calls") and msg.tool_calls:
                            for tool_call in msg.tool_calls:
                                tool_name = tool_call.get("name", "unknown")
                                tool_args = tool_call.get("args", {})
                                tool_id = tool_call.get("id", "")

                                cached_result = (
                                    cache.get(tool_name, tool_args)
                                    if config.ENABLE_CACHING
                                    else None
                                )

                                display_tool_call_compact(
                                    tool_name, tool_args, cached=bool(cached_result)
                                )

                                tracker.start_tool(tool_name, tool_args)
                                tool_outputs[tool_id] = {
                                    "name": tool_name,
                                    "args": tool_args,
                                    "start": datetime.now(),
                                }

                        if msg.__class__.__name__ == "ToolMessage":
                            tool_id = getattr(msg, "tool_call_id", "")
                            output = msg.content

                            if tool_id in tool_outputs:
                                tool_info = tool_outputs[tool_id]
                                duration = (datetime.now() - tool_info["start"]).total_seconds()

                                saved_path = None
                                if config.AUTO_SAVE_OUTPUTS:
                                    saved_path = save_tool_output(
                                        tool_info["name"], tool_info["args"], output
                                    )

                                tracker.end_tool(output, saved_path)
                                display_tool_output_compact(
                                    output, tool_info["name"], duration, saved_path
                                )

                    final_response = response_messages[-1].content

                    # Check if response contains website analysis report and save it
                    if (
                        "# Website Analysis Report" in final_response
                        or "## 🗺️ Sitemap Diagram" in final_response
                        or "## 🔄 User Flow Diagrams" in final_response
                        or "## 🎯 Website Summary" in final_response
                    ):
                        # Extract markdown report from response
                        try:
                            # Get URL from user input
                            url_match = [word for word in user_input.split() if "http" in word]
                            url = url_match[0] if url_match else "unknown"
                            save_qa_report(final_response, url)
                        except:
                            pass

                    input_tokens = len(json.dumps(messages)) // 4
                    output_tokens = len(str(final_response)) // 4
                    tracker.add_tokens(input_tokens, output_tokens)

                    display_response(final_response)

                    messages.append({"role": "assistant", "content": str(final_response)})

                except KeyboardInterrupt:
                    console.print("\n[yellow]👋 Interrupted. Goodbye![/yellow]\n")
                    break
                except Exception as e:
                    error_msg = str(e)
                    console.print(f"\n[red]❌ Error: {error_msg[:200]}[/red]")

                    if "Element not found" in error_msg or "Action(s) failed" in error_msg:
                        if tracker.tool_calls:
                            last_call = tracker.tool_calls[-1]
                            console.print(
                                f"\n[yellow]⚠️ Action failed in {last_call['tool']}[/yellow]"
                            )

                            args = last_call.get("args", {})
                            actions = args.get("scrapeOptions", {}).get("actions", [])

                            if actions:
                                console.print(f"   Actions attempted: {len(actions)}")
                                for i, action in enumerate(actions, 1):
                                    console.print(
                                        f"   {i}. {action.get('type')}: {action.get('selector', 'N/A')[:50]}"
                                    )

                    if config.DEBUG_MODE:
                        import traceback

                        console.print(f"\n[dim]{traceback.format_exc()[:300]}[/dim]")

                    console.print()


if __name__ == "__main__":
    asyncio.run(main())
