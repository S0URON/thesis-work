"""Execution tracking service."""

from datetime import datetime
from typing import Optional, Dict, Any, List
from ..models.execution import ToolCall, ExecutionStats
from ..config import get_config


class ExecutionTracker:
    """Service for tracking tool execution and statistics."""

    def __init__(self):
        """Initialize execution tracker."""
        self.config = get_config()
        self.tool_calls: List[ToolCall] = []
        self.current_call: Optional[Dict[str, Any]] = None
        self.total_input_tokens = 0
        self.total_output_tokens = 0
        self.total_cost = 0.0
        self.actions_used = 0
        self.outputs_saved = 0

    def start_tool(self, name: str, args: dict, cached: bool = False) -> None:
        """
        Start tracking a tool call.

        Args:
            name: Tool name
            args: Tool arguments
            cached: Whether result was retrieved from cache
        """
        self.current_call = {
            "tool": name,
            "args": args,
            "timestamp": datetime.now().isoformat(),
            "start_time": datetime.now(),
            "cached": cached,
            "has_actions": "scrapeOptions" in args and "actions" in args.get("scrapeOptions", {}),
        }

    def end_tool(self, output: str, saved_path: Optional[str] = None) -> None:
        """
        Complete tracking of current tool call.

        Args:
            output: Tool output
            saved_path: Path where output was saved (if applicable)
        """
        if self.current_call:
            duration = (datetime.now() - self.current_call["start_time"]).total_seconds()
            output_length = len(str(output))

            # Track actions usage
            if self.current_call.get("has_actions"):
                self.actions_used += 1

            # Track saved outputs
            if saved_path:
                self.outputs_saved += 1

            # Create ToolCall model
            tool_call = ToolCall(
                tool=self.current_call["tool"],
                args=self.current_call["args"],
                timestamp=self.current_call["timestamp"],
                duration=duration,
                output_length=output_length,
                saved_to=saved_path,
                cached=self.current_call["cached"],
            )

            self.tool_calls.append(tool_call)
            self.current_call = None

    def add_tokens(self, input_tokens: int, output_tokens: int) -> None:
        """
        Add token usage and calculate cost.

        Args:
            input_tokens: Number of input tokens used
            output_tokens: Number of output tokens generated
        """
        self.total_input_tokens += input_tokens
        self.total_output_tokens += output_tokens

        # Calculate cost
        input_cost = (input_tokens / 1000) * self.config.COST_PER_1K_INPUT_TOKENS
        output_cost = (output_tokens / 1000) * self.config.COST_PER_1K_OUTPUT_TOKENS
        self.total_cost += input_cost + output_cost

    def get_stats(self) -> ExecutionStats:
        """
        Get execution statistics.

        Returns:
            ExecutionStats model with current statistics
        """
        return ExecutionStats(
            total_calls=len(self.tool_calls),
            input_tokens=self.total_input_tokens,
            output_tokens=self.total_output_tokens,
            total_tokens=self.total_input_tokens + self.total_output_tokens,
            estimated_cost=self.total_cost,
            actions_used=self.actions_used,
            outputs_saved=self.outputs_saved,
        )

    def get_tool_calls(self) -> List[ToolCall]:
        """Get list of all tool calls."""
        return self.tool_calls

    def reset(self) -> None:
        """Reset all tracking data."""
        self.tool_calls.clear()
        self.current_call = None
        self.total_input_tokens = 0
        self.total_output_tokens = 0
        self.total_cost = 0.0
        self.actions_used = 0
        self.outputs_saved = 0
