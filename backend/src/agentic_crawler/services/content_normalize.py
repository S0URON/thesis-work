"""Normalize LangChain message content (str vs multimodal list) to plain text."""

from __future__ import annotations

import json
from typing import Any


def normalize_langchain_content(content: Any) -> str:
    """
    Coerce AIMessage / ToolMessage content to a string.

    Models may return a list of blocks (e.g. ``[{"type": "text", "text": "..."}]``).
    """
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for block in content:
            if isinstance(block, dict):
                if block.get("type") == "text" and "text" in block:
                    parts.append(str(block.get("text", "")))
                elif "text" in block:
                    parts.append(str(block.get("text", "")))
                else:
                    parts.append(json.dumps(block, ensure_ascii=False))
            elif isinstance(block, str):
                parts.append(block)
            else:
                parts.append(str(block))
        return "\n".join(parts)
    return str(content)
