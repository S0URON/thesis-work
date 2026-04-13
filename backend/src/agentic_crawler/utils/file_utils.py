"""File operations utilities."""

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Any
from ..config import get_config


def save_tool_output(tool_name: str, args: Dict[str, Any], output: str) -> str:
    """
    Save tool output to file with timestamp.

    Args:
        tool_name: Name of the tool
        args: Tool arguments
        output: Tool output to save

    Returns:
        Path to saved file
    """
    config = get_config()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # Generate filename from URL if available
    url = args.get("url", "no_url")
    if url != "no_url":
        url_clean = url.replace("https://", "").replace("http://", "")
        url_clean = url_clean.replace("/", "_").replace(":", "_")[:50]
        filename = f"{timestamp}_{tool_name}_{url_clean}.json"
    else:
        filename = f"{timestamp}_{tool_name}.json"

    filepath = config.OUTPUTS_DIR / filename

    # Save as structured JSON for easy parsing
    data = {"tool": tool_name, "timestamp": timestamp, "arguments": args, "output": output}

    filepath.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    return str(filepath)


def save_qa_report(report_content: str, url: str, report_format: str = "markdown") -> str:
    """
    Save website analysis report to dedicated reports folder.
    (Kept function name for backward compatibility)

    Args:
        report_content: Content of the report
        url: URL of the analyzed website
        report_format: Format of the report (markdown or json)

    Returns:
        Path to saved report
    """
    return save_website_report(report_content, url, report_format)


def save_website_report(report_content: str, url: str, report_format: str = "markdown") -> str:
    """
    Save website analysis report to dedicated reports folder.

    Args:
        report_content: Content of the report
        url: URL of the analyzed website
        report_format: Format of the report (markdown or json)

    Returns:
        Path to saved report
    """
    config = get_config()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # Clean URL for filename
    url_clean = url.replace("https://", "").replace("http://", "")
    url_clean = url_clean.replace("/", "_").replace(":", "_")[:50]

    extension = "md" if report_format == "markdown" else "json"
    filename = f"Website_Analysis_{timestamp}_{url_clean}.{extension}"
    filepath = config.REPORTS_DIR / filename

    filepath.write_text(report_content, encoding="utf-8")
    return str(filepath)


def load_json_file(filepath: Path) -> Dict[str, Any]:
    """
    Load JSON file.

    Args:
        filepath: Path to JSON file

    Returns:
        Parsed JSON data
    """
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)


def list_files_in_directory(directory: Path, pattern: str = "*") -> list:
    """
    List files in directory matching pattern.

    Args:
        directory: Directory to search
        pattern: Glob pattern for matching files

    Returns:
        List of matching file paths
    """
    if not directory.exists():
        return []
    return list(directory.glob(pattern))


def get_recent_reports(limit: int = 10) -> list:
    """
    Get most recent website analysis reports.

    Args:
        limit: Maximum number of reports to return

    Returns:
        List of recent report paths
    """
    config = get_config()
    reports = list_files_in_directory(config.REPORTS_DIR, "*.md")
    reports += list_files_in_directory(config.REPORTS_DIR, "*.json")
    return sorted(reports, reverse=True)[:limit]


def resolve_safe_report_path(filename: str) -> Path:
    """
    Resolve a report file path under REPORTS_DIR only.

    Args:
        filename: Basename only (e.g. Website_Analysis_20250101_120000_example.com.md)

    Raises:
        ValueError: If the name is unsafe or not a supported extension.
        FileNotFoundError: If the file does not exist.
    """
    config = get_config()
    base = config.REPORTS_DIR.resolve()
    raw = filename.strip()
    if not raw or "/" in raw or "\\" in raw or ".." in raw:
        raise ValueError("Invalid filename")
    name = Path(raw).name
    if name != raw:
        raise ValueError("Invalid filename")
    if not name.endswith((".md", ".json")):
        raise ValueError("Report must be .md or .json")
    path = (base / name).resolve()
    try:
        path.relative_to(base)
    except ValueError as e:
        raise ValueError("Invalid path") from e
    if not path.is_file():
        raise FileNotFoundError(name)
    return path


def read_report_file(filename: str) -> tuple[str, str]:
    """
    Read a report file from REPORTS_DIR.

    Returns:
        Tuple of (file contents, format) where format is \"markdown\" or \"json\".
    """
    path = resolve_safe_report_path(filename)
    text = path.read_text(encoding="utf-8")
    kind = "json" if path.suffix.lower() == ".json" else "markdown"
    return text, kind


def get_recent_outputs(limit: int = 10) -> list:
    """
    Get most recent tool outputs.

    Args:
        limit: Maximum number of outputs to return

    Returns:
        List of recent output paths
    """
    config = get_config()
    outputs = list_files_in_directory(config.OUTPUTS_DIR, "*.json")
    return sorted(outputs, reverse=True)[:limit]
