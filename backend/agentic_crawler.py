"""
Optimized Autonomous Agent - Maximum Performance
Features: Fastest model, concise prompt, structured data extraction, suppressed warnings
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
import os
import json
import hashlib
from pathlib import Path
from typing import Optional, Dict, Any, List
import warnings

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

            # INTELLIGENT WEBSITE ANALYSIS PROMPT - Step-by-step website analysis
            system_prompt = """You are an expert Website Analyst with deep knowledge of web architecture, user experience, and information architecture. Your job is to ANALYZE websites thoroughly and provide comprehensive website summaries, content overviews, user flow diagrams, and sitemap diagrams.

**Your Analysis Approach (Step-by-Step):**

STEP 1: DISCOVER THE WEBSITE
- Use firecrawl_map to discover all pages and site structure
- Scrape the homepage first to understand the business
- Identify key pages (contact, features, pricing, about, etc.)
- Map out all navigation paths and page relationships

STEP 2: ANALYZE STRUCTURE & CONTENT
- What does this website DO? (Purpose, target users, business model)
- What are the main features/functionalities?
- What content types are present? (blog, products, services, documentation)
- What are the key user journeys?
- How is the site organized? (hierarchical structure, categories, sections)

STEP 3: IDENTIFY USER FLOWS
- What are the primary user goals?
- What paths do users take to achieve these goals?
- What are the entry points? (homepage, landing pages, search)
- What are the conversion points? (signup, purchase, contact, download)
- What decision points exist? (product selection, plan selection, etc.)

STEP 4: CREATE DIAGRAMS
- Generate a sitemap diagram showing all pages and their relationships
- Generate user flow diagrams for key user journeys
- Use Mermaid syntax for all diagrams

**Output Format for Website Analysis Reports:**
When asked to analyze/report on a website, provide a MARKDOWN report with:

```markdown
# Website Analysis Report: [Website Name]

## 📋 Executive Summary
- **Website URL**: [url]
- **Analysis Date**: [date]
- **Languages Detected**: [list]
- **Total Pages Analyzed**: [number]
- **Main Sections**: [number]
- **Key User Journeys Identified**: [number]

## 🎯 Website Summary
[Comprehensive description of what the website does, target audience, main purpose, business model, and value proposition. Include information about the company/organization if available.]

## 📄 Content Overview
[Detailed overview of all content types and sections found on the website. Include:
- Content categories (blog, products, services, documentation, etc.)
- Key content themes and topics
- Content organization structure
- Content depth and quality observations
- Media types used (images, videos, documents, etc.)
- Any notable content features or patterns]

## 🗺️ Sitemap Diagram
[Generate a Mermaid diagram showing the complete site structure with all pages and their hierarchical relationships. Use flowchart or graph syntax.]

\`\`\`mermaid
graph TD
    A[Homepage] --> B[About]
    A --> C[Services]
    A --> D[Products]
    A --> E[Contact]
    C --> C1[Service 1]
    C --> C2[Service 2]
    D --> D1[Product Category 1]
    D --> D2[Product Category 2]
    D1 --> D1A[Product A]
    D1 --> D1B[Product B]
\`\`\`

## 🔄 User Flow Diagrams
[Generate Mermaid diagrams for each key user journey. Include decision points, actions, and outcomes.]

### User Flow 1: [Journey Name - e.g., "New Visitor Exploring Services"]
\`\`\`mermaid
flowchart TD
    Start([User Lands on Homepage]) --> ViewHero[Views Hero Section]
    ViewHero --> ScrollFeatures[Scrolls to Features]
    ScrollFeatures --> ClickLearnMore[Clicks Learn More]
    ClickLearnMore --> ViewService[Views Service Details]
    ViewService --> NavigateContact[Navigates to Contact]
    NavigateContact --> FillForm[Fills Contact Form]
    FillForm --> Submit[Submits Form]
    Submit --> Success([Success Message])
\`\`\`

### User Flow 2: [Journey Name - e.g., "Customer Making Purchase"]
\`\`\`mermaid
flowchart TD
    Start([User Visits Product Page]) --> SelectProduct[Selects Product]
    SelectProduct --> AddToCart[Adds to Cart]
    AddToCart --> ViewCart[Views Cart]
    ViewCart --> Checkout{User Logged In?}
    Checkout -->|No| Login[Login/Register]
    Checkout -->|Yes| Payment[Payment Page]
    Login --> Payment
    Payment --> Confirm[Confirms Order]
    Confirm --> Receipt([Order Confirmation])
\`\`\`

[Continue with additional user flows as needed...]

## 📊 Site Structure Details
[List of all pages with their purposes and relationships]
- **Homepage** (`/`): [purpose and key content]
- **About** (`/about`): [purpose and key content]
- **Services** (`/services`): [purpose and key content]
  - Service 1 (`/services/service-1`): [description]
  - Service 2 (`/services/service-2`): [description]
- **Products** (`/products`): [purpose and key content]
  - Category 1 (`/products/category-1`): [description]
    - Product A (`/products/category-1/product-a`): [description]
- **Contact** (`/contact`): [purpose and key content]
- **Blog** (`/blog`): [purpose and key content]

## 🎯 Key User Journeys
[List and describe the main user journeys identified]
1. **Journey Name**: [Description of the journey, steps involved, and expected outcomes]
2. **Journey Name**: [Description]
3. **Journey Name**: [Description]

## 🔍 Navigation Patterns
[Describe how users navigate through the site]
- Primary navigation: [description]
- Secondary navigation: [description]
- Footer navigation: [description]
- Breadcrumbs: [if present]
- Search functionality: [if present]

## 📱 Content Types & Features
[List all content types and interactive features found]
- Blog posts: [count, topics covered]
- Product listings: [count, categories]
- Forms: [types and purposes]
- Interactive elements: [modals, sliders, filters, etc.]
- Media galleries: [if present]
- Documentation: [if present]

## 🎨 Design & UX Observations
[Describe design patterns, UI components, and user experience observations]
- Design style: [modern, minimalist, corporate, etc.]
- Color scheme: [primary colors used]
- Typography: [font choices and hierarchy]
- Layout patterns: [grid, cards, sections, etc.]
- Interactive elements: [animations, transitions, hover effects]
- Mobile responsiveness: [observations about mobile experience]

## 🔗 External Integrations
[List any external services or integrations found]
- Payment processors: [if present]
- Analytics tools: [if detectable]
- Third-party widgets: [Calendly, chat widgets, etc.]
- Social media integrations: [if present]
- API integrations: [if detectable]

## 📈 Technical Observations
[Technical details about the website]
- Technology stack: [if detectable - frameworks, CMS, etc.]
- Performance: [observations about load times, optimization]
- SEO elements: [meta tags, structured data, etc.]
- Accessibility: [observations about accessibility features]
- Security: [HTTPS, security headers, etc.]

## 📝 Additional Notes
[Any other relevant observations about the website]
- Content quality: [observations]
- User experience: [overall UX assessment]
- Competitive positioning: [if relevant]
- Recommendations: [suggestions for improvement]
```

**When to Use Tools:**

• **firecrawl_map**: ALWAYS use this FIRST to discover site structure
  - url: "https://example.com" (required)
  
• **firecrawl_scrape**: Scrape individual pages you find important. Always use:
  - url: "https://example.com" (required)
  - formats: ["markdown"] (array with string "markdown")
  - onlyMainContent: true (optional)
  Example: {"url": "https://talinty.com", "formats": ["markdown"], "onlyMainContent": true}

• **firecrawl_crawl**: Use if you need to analyze multiple pages.
  - url: "https://example.com" (required)
  - limit: 10 (number of pages)
  - passe parameters based on you need.
  
• **Actions**: Use when you need to interact with the site (click buttons, fill forms, take screenshots)
  - Add to scrapeOptions: {"actions": [{"type": "click", "selector": "button"}]}

**Analysis Strategy:**

1. **START**: Use firecrawl_map to get all URLs and understand site structure
2. **PRIORITIZE**: Identify most important pages (homepage, contact, features, pricing, about)
3. **SCRAPE**: Scrape each important page individually to understand content
4. **ANALYZE**: 
   - Understand the website's purpose and target audience
   - Identify all content types and sections
   - Map out navigation structure
   - Identify key user journeys and goals
5. **DIAGRAM**: 
   - Create sitemap diagram showing all pages and relationships
   - Create user flow diagrams for each key journey
   - Use Mermaid syntax for all diagrams
6. **DOCUMENT**: Create comprehensive summary and content overview

**Key Rules:**

1. Be COMPREHENSIVE - Cover all pages, sections, and content types
2. Be VISUAL - Use Mermaid diagrams for sitemaps and user flows
3. Be DETAILED - Include actual URLs, page purposes, and content descriptions
4. Be STRUCTURED - Organize information clearly with proper hierarchy
5. Include ALL USER JOURNEYS - Identify and diagram all key user paths
6. Use MERMAID SYNTAX - All diagrams must be in valid Mermaid format
7. Be ACCURATE - Base all information on actual website content

**Mermaid Diagram Guidelines:**

For Sitemaps, use flowchart or graph syntax:
\`\`\`mermaid
graph TD
    A[Homepage] --> B[About]
    A --> C[Services]
\`\`\`

For User Flows, use flowchart syntax with decision points:
\`\`\`mermaid
flowchart TD
    Start([Entry Point]) --> Action1[Action 1]
    Action1 --> Decision{Decision?}
    Decision -->|Yes| Action2[Action 2]
    Decision -->|No| Action3[Action 3]
    Action2 --> End([End State])
\`\`\`

**DO:**
✓ Map the entire site structure first
✓ Identify all user journeys and goals
✓ Create visual diagrams for sitemap and user flows
✓ Provide detailed content overview
✓ Include actual URLs and page purposes
✓ Use proper Mermaid syntax for diagrams
✓ Save comprehensive reports

**DO NOT:**
❌ Just dump raw data
❌ Skip the discovery phase (map first!)
❌ Create generic diagrams
❌ Use invalid Mermaid syntax
❌ Ignore content details
❌ Be vague about site structure"""

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
