"""Main entry point for Agentic Crawler application."""

import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / "src"))

from agentic_crawler.cli import main as cli_main


def main():
    """Run the Agentic Crawler CLI."""
    try:
        cli_main()
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
