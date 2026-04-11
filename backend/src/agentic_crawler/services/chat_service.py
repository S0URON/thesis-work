"""Chat session orchestration (agent turns, cache, tracker) — shared by CLI and HTTP API."""

from __future__ import annotations

import asyncio
import json
import uuid
from collections import defaultdict
from datetime import datetime
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from ..agents import EvaluationAgent
from ..config import Config, get_config
from .cache_service import CacheService
from .tracker_service import ExecutionTracker
from .content_normalize import normalize_langchain_content
from ..utils.file_utils import save_tool_output, save_website_report


class ToolEvent(BaseModel):
    """One tool invocation and its result (if any)."""

    name: str
    args: Dict[str, Any] = Field(default_factory=dict)
    cached: bool = False
    duration_seconds: Optional[float] = None
    output: Optional[str] = None
    saved_path: Optional[str] = None


class TurnResult(BaseModel):
    """Structured result of a single user turn."""

    assistant_text: str = ""
    tool_events: List[ToolEvent] = Field(default_factory=list)
    error: Optional[str] = None
    report_saved_path: Optional[str] = None


@dataclass
class ProcessTurnOutcome:
    """Result of process_turn; agent_messages supports CLI interleaved tool display."""

    result: TurnResult
    agent_messages: Optional[List[Any]] = None


class SessionStore:
    """In-memory chat history keyed by session id."""

    def __init__(self) -> None:
        self._messages: Dict[str, List[Dict[str, str]]] = {}

    def get_messages(self, session_id: str) -> List[Dict[str, str]]:
        return self._messages.get(session_id, [])

    def set_messages(self, session_id: str, messages: List[Dict[str, str]]) -> None:
        self._messages[session_id] = messages

    def clear(self, session_id: str) -> None:
        self._messages.pop(session_id, None)

    def ensure_session(self, session_id: Optional[str]) -> str:
        """Return a valid session id (generate UUID if missing)."""
        if session_id and session_id.strip():
            return session_id.strip()
        return str(uuid.uuid4())


class ChatSessionService:
    """Runs agent turns with shared cache, tracker, and per-session message history."""

    def __init__(
        self,
        agent: EvaluationAgent,
        cache: CacheService,
        tracker: ExecutionTracker,
        config: Optional[Config] = None,
        store: Optional[SessionStore] = None,
    ) -> None:
        self.agent = agent
        self.cache = cache
        self.tracker = tracker
        self.config = config or get_config()
        self.store = store or SessionStore()
        self._locks: Dict[str, asyncio.Lock] = defaultdict(lambda: asyncio.Lock())

    async def process_turn(self, session_id: str, user_text: str) -> ProcessTurnOutcome:
        """
        Append user message, invoke agent, update history on success.

        On failure, keeps the user message without an assistant reply (matches CLI).

        Args:
            session_id: Conversation session key
            user_text: User message content

        Returns:
            ProcessTurnOutcome with TurnResult; agent_messages set on success for CLI tracing
        """
        lock = self._locks[session_id]
        async with lock:
            messages = list(self.store.get_messages(session_id))
            messages.append({"role": "user", "content": user_text})

            try:
                agent_response = await self.agent.ainvoke(messages)
                response_messages: List[Any] = agent_response["messages"]
                tool_events: List[ToolEvent] = []

                tool_outputs: Dict[str, Dict[str, Any]] = {}
                for msg in response_messages[:-1]:
                    if hasattr(msg, "tool_calls") and msg.tool_calls:
                        for tool_call in msg.tool_calls:
                            tool_name = tool_call.get("name", "unknown")
                            tool_args = tool_call.get("args", {})
                            tool_id = tool_call.get("id", "")

                            cached_result = None
                            if self.config.ENABLE_CACHING:
                                cached_result = self.cache.get(tool_name, tool_args)

                            self.tracker.start_tool(
                                tool_name, tool_args, cached=bool(cached_result)
                            )
                            tool_outputs[tool_id] = {
                                "name": tool_name,
                                "args": tool_args,
                                "start": datetime.now(),
                                "cached": bool(cached_result),
                            }

                    if msg.__class__.__name__ == "ToolMessage":
                        tool_id = getattr(msg, "tool_call_id", "")
                        output = normalize_langchain_content(msg.content)

                        if tool_id in tool_outputs:
                            tool_info = tool_outputs[tool_id]
                            duration = (datetime.now() - tool_info["start"]).total_seconds()

                            saved_path = None
                            if self.config.AUTO_SAVE_OUTPUTS:
                                saved_path = save_tool_output(
                                    tool_info["name"], tool_info["args"], output
                                )

                            if self.config.ENABLE_CACHING:
                                self.cache.put(tool_info["name"], tool_info["args"], output)

                            self.tracker.end_tool(output, saved_path)

                            tool_events.append(
                                ToolEvent(
                                    name=tool_info["name"],
                                    args=tool_info["args"],
                                    cached=tool_info["cached"],
                                    duration_seconds=duration,
                                    output=str(output),
                                    saved_path=saved_path,
                                )
                            )

                final_response = normalize_langchain_content(response_messages[-1].content)
                report_saved_path: Optional[str] = None

                if (
                    "# Website Analysis Report" in final_response
                    or "## 🗺️ Sitemap Diagram" in final_response
                    or "## 🔄 User Flow Diagrams" in final_response
                    or "## 🎯 Website Summary" in final_response
                ):
                    try:
                        url_match = [word for word in user_text.split() if "http" in word]
                        url = url_match[0] if url_match else "unknown"
                        report_saved_path = save_website_report(final_response, url)
                    except Exception:
                        if self.config.DEBUG_MODE:
                            raise
                        report_saved_path = None

                input_tokens = len(json.dumps(messages)) // 4
                output_tokens = len(str(final_response)) // 4
                self.tracker.add_tokens(input_tokens, output_tokens)

                messages.append({"role": "assistant", "content": final_response})
                self.store.set_messages(session_id, messages)

                return ProcessTurnOutcome(
                    result=TurnResult(
                        assistant_text=final_response,
                        tool_events=tool_events,
                        report_saved_path=report_saved_path,
                    ),
                    agent_messages=response_messages,
                )

            except Exception as e:
                self.store.set_messages(session_id, messages)
                err = str(e)
                return ProcessTurnOutcome(
                    result=TurnResult(error=err[:2000] if err else "Unknown error")
                )

    def clear_session(self, session_id: str) -> None:
        """Drop conversation history for a session."""
        self.store.clear(session_id)
