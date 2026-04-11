"""Display utilities for rich console output."""

from typing import Optional, Dict, Any
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.markdown import Markdown
from rich import box
console = Console()


def display_welcome() -> None:
    """Display welcome banner."""
    console.print("\n" + "=" * 100)
    console.print("[bold cyan]⚡ Website Evaluation Agent - Maximum Performance[/bold cyan]")
    console.print(
        "[dim]Fast execution • Website summaries • User flows • Sitemap diagrams[/dim]"
    )
    console.print("=" * 100 + "\n")


def display_tool_call_compact(tool_name: str, args: Dict[str, Any], cached: bool = False) -> None:
    """
    Display compact tool call information.

    Args:
        tool_name: Name of the tool
        args: Tool arguments
        cached: Whether result was cached
    """
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
) -> None:
    """
    Display compact tool output information.

    Args:
        output: Tool output
        tool_name: Name of the tool
        duration: Execution duration in seconds
        saved_path: Path where output was saved
    """
    output_len = len(str(output))
    console.print(
        f"[green]✓ {tool_name}[/green] [dim]({duration:.1f}s, {output_len:,} chars)[/dim]"
    )
    if saved_path:
        console.print(f"  [dim]→ {saved_path}[/dim]")


def display_response(response: str) -> None:
    """
    Display agent response with markdown formatting.

    Args:
        response: Agent response text
    """
    console.print("\n[bold cyan]💬 Agent Response:[/bold cyan]\n")

    # Handle list responses
    if isinstance(response, list):
        text = ""
        for block in response:
            if isinstance(block, dict) and block.get("type") == "text":
                text += block.get("text", "")
            elif isinstance(block, str):
                text += block
        response = text.strip()

    # Try to render as markdown
    try:
        md = Markdown(response)
        console.print(Panel(md, border_style="cyan", box=box.ROUNDED))
    except Exception:
        console.print(Panel(f"[white]{response}[/white]", border_style="cyan", box=box.ROUNDED))
    console.print()


def display_execution_summary(tracker: Any, cache: Any) -> None:
    """
    Display execution statistics summary.

    Args:
        tracker: Execution tracker instance (ExecutionTracker; Any avoids circular imports)
        cache: Cache service instance (CacheService)
    """
    console.print("\n[bold cyan]📊 Session Summary[/bold cyan]\n")

    stats = tracker.get_stats()
    cache_stats = cache.get_stats()

    # Create stats table
    stats_table = Table(box=box.SIMPLE, show_header=False)
    stats_table.add_column("Metric", style="cyan")
    stats_table.add_column("Value", style="yellow")

    stats_dict = stats.to_dict()
    stats_table.add_row("Tool Calls", str(stats_dict["total_calls"]))
    stats_table.add_row("With Actions", str(stats.actions_used))
    stats_table.add_row("Outputs Saved", str(stats.outputs_saved))
    stats_table.add_row("Total Tokens", stats_dict["total_tokens"])
    stats_table.add_row("Cost", stats_dict["estimated_cost"])
    stats_table.add_row("Cache Hit Rate", cache_stats.format_hit_rate())

    console.print(stats_table)
    console.print()


def display_error(message: str, details: Optional[str] = None) -> None:
    """
    Display error message.

    Args:
        message: Error message
        details: Optional error details
    """
    console.print(f"\n[red]❌ Error: {message}[/red]")
    if details:
        console.print(f"[dim]{details}[/dim]")
    console.print()


def display_success(message: str) -> None:
    """
    Display success message.

    Args:
        message: Success message
    """
    console.print(f"\n[green]✅ {message}[/green]\n")


def display_info(message: str) -> None:
    """
    Display info message.

    Args:
        message: Info message
    """
    console.print(f"\n[blue]ℹ️  {message}[/blue]\n")


def display_reports_list(reports: list) -> None:
    """
    Display list of website analysis reports.

    Args:
        reports: List of report file paths
    """
    console.print(f"[cyan]Website Analysis Reports ({len(reports)}):[/cyan]")
    for report in reports:
        console.print(f"  • {report.name}")


def display_outputs_list(outputs: list) -> None:
    """
    Display list of tool outputs.

    Args:
        outputs: List of output file paths
    """
    console.print(f"[cyan]Saved Outputs ({len(outputs)}):[/cyan]")
    for output in outputs:
        console.print(f"  • {output.name}")
