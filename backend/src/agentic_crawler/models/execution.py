"""Execution tracking models."""

from datetime import datetime
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class ToolCall(BaseModel):
    """Model for tracking individual tool calls."""

    tool: str = Field(description="Name of the tool called")
    args: Dict[str, Any] = Field(default_factory=dict, description="Arguments passed to the tool")
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())
    duration: Optional[float] = Field(None, description="Execution duration in seconds")
    output_length: Optional[int] = Field(None, description="Length of tool output")
    saved_to: Optional[str] = Field(None, description="Path where output was saved")
    cached: bool = Field(False, description="Whether result was cached")

    class Config:
        json_schema_extra = {
            "example": {
                "tool": "firecrawl_scrape",
                "args": {"url": "https://example.com", "formats": ["markdown"]},
                "timestamp": "2024-01-15T10:30:00",
                "duration": 2.5,
                "output_length": 5000,
                "cached": False,
            }
        }


class ExecutionStats(BaseModel):
    """Statistics for an execution session."""

    total_calls: int = Field(0, description="Total number of tool calls")
    input_tokens: int = Field(0, description="Total input tokens used")
    output_tokens: int = Field(0, description="Total output tokens generated")
    total_tokens: int = Field(0, description="Total tokens (input + output)")
    estimated_cost: float = Field(0.0, description="Estimated cost in USD")
    actions_used: int = Field(0, description="Number of actions executed")
    outputs_saved: int = Field(0, description="Number of outputs saved to disk")

    def format_cost(self) -> str:
        """Format cost as currency string."""
        return f"${self.estimated_cost:.4f}"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for display."""
        return {
            "total_calls": self.total_calls,
            "input_tokens": f"{self.input_tokens:,}",
            "output_tokens": f"{self.output_tokens:,}",
            "total_tokens": f"{self.total_tokens:,}",
            "estimated_cost": self.format_cost(),
            "actions_used": self.actions_used,
            "outputs_saved": self.outputs_saved,
        }


class CacheStats(BaseModel):
    """Statistics for the cache service."""

    hits: int = Field(0, description="Number of cache hits")
    misses: int = Field(0, description="Number of cache misses")
    entries: int = Field(0, description="Number of cache entries")
    size_mb: float = Field(0.0, description="Cache size in MB")

    @property
    def hit_rate(self) -> float:
        """Calculate cache hit rate as percentage."""
        total = self.hits + self.misses
        return (self.hits / total * 100) if total > 0 else 0.0

    def format_hit_rate(self) -> str:
        """Format hit rate as percentage string."""
        return f"{self.hit_rate:.1f}%"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for display."""
        return {
            "hits": self.hits,
            "misses": self.misses,
            "hit_rate": self.format_hit_rate(),
            "size_mb": f"{self.size_mb:.2f}",
            "entries": self.entries,
        }
