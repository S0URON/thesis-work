"""Command-line interface for Agentic Crawler."""

import asyncio
from datetime import datetime
from typing import Any, List

from dotenv import load_dotenv

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from langchain_mcp_adapters.tools import load_mcp_tools

from agentic_crawler.config import get_config
from agentic_crawler.agents import EvaluationAgent

from agentic_crawler.services import CacheService, ChatSessionService, ExecutionTracker
from agentic_crawler.utils import (
    display_welcome,
    display_tool_call_compact,
    display_tool_output_compact,
    display_response,
    display_execution_summary,
    display_error,
    display_success,
    display_reports_list,
    display_outputs_list,
    get_recent_reports,
    get_recent_outputs,
)
from agentic_crawler.utils.display_utils import console

# Load environment variables
load_dotenv()

CLI_SESSION_ID = "cli"


class AgenticCrawlerCLI:
    """Command-line interface for the Agentic Crawler."""

    def __init__(self):
        """Initialize CLI."""
        self.config = get_config()
        self.cache = CacheService(
            max_size_mb=self.config.MAX_CACHE_SIZE, ttl_hours=self.config.CACHE_TTL_HOURS
        )
        self.tracker = ExecutionTracker()
        self.agent = None
        self.chat_service: ChatSessionService | None = None

    async def initialize(self, session: ClientSession):
        """
        Initialize agent with MCP tools.

        Args:
            session: MCP client session
        """
        # Load MCP tools
        all_tools = await load_mcp_tools(session)

        # Initialize agent
        self.agent = EvaluationAgent(
            tools=all_tools,
            model_type=(self.config.LLM_PROVIDER or "google").strip().lower(),
        )

        self.chat_service = ChatSessionService(
            agent=self.agent,
            cache=self.cache,
            tracker=self.tracker,
            config=self.config,
        )

        console.print(f"[green]✅ Loaded {len(all_tools)} tools[/green]\n")

    def display_help(self):
        """Display help information."""
        console.print("\n[cyan]Available Commands:[/cyan]")
        console.print("  [bold]/stats[/bold]    - Show execution statistics")
        console.print("  [bold]/clear[/bold]    - Clear conversation history")
        console.print("  [bold]/reports[/bold]  - List recent website analysis reports")
        console.print("  [bold]/outputs[/bold]  - List recent tool outputs")
        console.print("  [bold]/help[/bold]     - Show this help message")
        console.print("  [bold]quit/exit[/bold] - Exit the application\n")

    async def handle_user_input(self, user_input: str) -> bool:
        """
        Handle user input and commands.

        Args:
            user_input: User's input string

        Returns:
            False if should quit, True otherwise
        """
        # Handle quit command
        if user_input.lower() in ["quit", "exit", "q"]:
            console.print("\n[yellow]👋 Goodbye![/yellow]\n")
            return False

        # Handle stats command
        if user_input.lower() == "/stats":
            display_execution_summary(self.tracker, self.cache)
            return True

        # Handle clear command
        if user_input.lower() == "/clear":
            if self.chat_service:
                self.chat_service.clear_session(CLI_SESSION_ID)
            display_success("Conversation cleared")
            return True

        # Handle reports command
        if user_input.lower() == "/reports":
            reports = get_recent_reports()
            display_reports_list(reports)
            return True

        # Handle outputs command
        if user_input.lower() == "/outputs":
            outputs = get_recent_outputs()
            display_outputs_list(outputs)
            return True

        # Handle help command
        if user_input.lower() == "/help":
            self.display_help()
            return True

        # Process as normal query
        await self.process_query(user_input)
        return True

    def _display_interleaved_trace(
        self, response_messages: List[Any], tool_events_iter: List[Any]
    ) -> None:
        """Replay tool call / tool output display (matches original ordering)."""
        tool_outputs: dict = {}
        te_iter = iter(tool_events_iter)

        for msg in response_messages[:-1]:
            if hasattr(msg, "tool_calls") and msg.tool_calls:
                for tool_call in msg.tool_calls:
                    tool_name = tool_call.get("name", "unknown")
                    tool_args = tool_call.get("args", {})
                    tool_id = tool_call.get("id", "")

                    cached_result = None
                    if self.config.ENABLE_CACHING:
                        cached_result = self.cache.get(tool_name, tool_args)

                    display_tool_call_compact(tool_name, tool_args, cached=bool(cached_result))

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
                    ev = next(te_iter, None)
                    if ev is not None:
                        display_tool_output_compact(
                            output,
                            ev.name,
                            ev.duration_seconds if ev.duration_seconds is not None else duration,
                            ev.saved_path,
                        )
                    else:
                        display_tool_output_compact(output, tool_info["name"], duration, None)

    async def process_query(self, user_input: str):
        """
        Process user query through agent.

        Args:
            user_input: User's query
        """
        if not self.chat_service:
            display_error("Agent not initialized", "")
            return

        console.print("[blue]⏳ Processing...[/blue]")

        outcome = await self.chat_service.process_turn(CLI_SESSION_ID, user_input)
        result = outcome.result

        if result.error:
            display_error("Query processing failed", result.error[:200])

            if self.config.DEBUG_MODE:
                import traceback

                console.print(f"\n[dim]{traceback.format_exc()[:300]}[/dim]")
            return

        if outcome.agent_messages:
            self._display_interleaved_trace(outcome.agent_messages, result.tool_events)

        if result.report_saved_path:
            console.print(
                f"\n[bold green]📄 Website Analysis Report saved to: {result.report_saved_path}[/bold green]\n"
            )

        display_response(result.assistant_text)

    async def run(self):
        """Main CLI loop."""
        display_welcome()

        # Validate configuration
        if not self.config.validate():
            display_error("Configuration validation failed. Please check your .env file.")
            return

        # Set up MCP server parameters
        server_params = StdioServerParameters(
            command=self.config.MCP_COMMAND,
            env={"FIRECRAWL_API_KEY": self.config.FIRECRAWL_API_KEY},
            args=self.config.MCP_ARGS,
        )

        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                await self.initialize(session)

                console.print(
                    "[dim]💡 Example: 'Analyze https://example.com' or 'Generate website analysis for https://site.com'[/dim]"
                )
                console.print("[dim]Type /help for available commands[/dim]\n")

                # Main loop
                while True:
                    try:
                        console.print("\n[cyan]You:[/cyan] ", end="")
                        user_input = input().strip()

                        if not user_input:
                            continue

                        should_continue = await self.handle_user_input(user_input)
                        if not should_continue:
                            break

                    except KeyboardInterrupt:
                        console.print("\n[yellow]👋 Interrupted. Goodbye![/yellow]\n")
                        break
                    except Exception as e:
                        display_error("Unexpected error", str(e))
                        if self.config.DEBUG_MODE:
                            import traceback

                            console.print(f"\n[dim]{traceback.format_exc()}[/dim]")


async def main():
    """Main entry point."""
    cli = AgenticCrawlerCLI()
    await cli.run()


if __name__ == "__main__":
    asyncio.run(main())
