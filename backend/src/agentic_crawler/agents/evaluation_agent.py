"""Evaluation agent implementation (LangChain + MCP tools)."""

from typing import List, Dict, Any, Optional
from langchain.agents import create_agent
from langchain_groq import ChatGroq
from langchain_google_genai import ChatGoogleGenerativeAI

from ..config import get_config
from .prompts import get_system_prompt


class EvaluationAgent:
    """Agent that orchestrates LLM and crawling tools for website evaluation and analysis."""

    def __init__(
        self, tools: List[Any], model_type: str = "google", custom_prompt: Optional[str] = None
    ):
        """
        Initialize the evaluation agent.

        Args:
            tools: List of MCP tools to use
            model_type: "google" or "groq"
            custom_prompt: Optional custom system prompt
        """
        self.config = get_config()
        self.tools = tools
        self.model_type = model_type
        self.system_prompt = custom_prompt or get_system_prompt()

        # Initialize model
        self.model = self._create_model()

        # Create agent
        self.agent = create_agent(self.model, self.tools, system_prompt=self.system_prompt)

    def _create_model(self):
        """Create the appropriate LLM model."""
        if self.model_type == "groq":
            return ChatGroq(
                model=self.config.GROQ_MODEL,
                temperature=self.config.MODEL_TEMPERATURE,
                streaming=self.config.ENABLE_STREAMING,
            )
        else:  # google
            return ChatGoogleGenerativeAI(
                model=self.config.GOOGLE_MODEL,
                temperature=self.config.MODEL_TEMPERATURE,
                streaming=self.config.ENABLE_STREAMING,
            )

    async def ainvoke(self, messages: List[Dict[str, str]]) -> Dict[str, Any]:
        """
        Invoke agent asynchronously.

        Args:
            messages: List of message dictionaries with role and content

        Returns:
            Agent response
        """
        return await self.agent.ainvoke({"messages": messages})

    def invoke(self, messages: List[Dict[str, str]]) -> Dict[str, Any]:
        """
        Invoke agent synchronously.

        Args:
            messages: List of message dictionaries with role and content

        Returns:
            Agent response
        """
        return self.agent.invoke({"messages": messages})

    def update_system_prompt(self, new_prompt: str) -> None:
        """
        Update system prompt and recreate agent.

        Args:
            new_prompt: New system prompt
        """
        self.system_prompt = new_prompt
        self.agent = create_agent(self.model, self.tools, system_prompt=self.system_prompt)
