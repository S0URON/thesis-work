"""FastAPI application with MCP lifespan."""

from contextlib import asynccontextmanager
from typing import AsyncIterator, List

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from langchain_mcp_adapters.tools import load_mcp_tools
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from ..agents import EvaluationAgent
from ..config import get_config
from ..services import CacheService, ChatSessionService, ExecutionTracker
from .routes import router

load_dotenv()


def _parse_cors_origins(raw: str) -> List[str]:
    raw = raw.strip()
    if raw == "*":
        return ["*"]
    parts = [o.strip() for o in raw.split(",") if o.strip()]
    return parts if parts else ["*"]


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    config = get_config()
    if not config.validate():
        raise RuntimeError("Configuration validation failed; check .env")

    server_params = StdioServerParameters(
        command=config.MCP_COMMAND,
        env={"FIRECRAWL_API_KEY": config.FIRECRAWL_API_KEY or ""},
        args=config.MCP_ARGS,
    )

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            all_tools = await load_mcp_tools(session)
            agent = EvaluationAgent(tools=all_tools, model_type="google")
            cache = CacheService(
                max_size_mb=config.MAX_CACHE_SIZE, ttl_hours=config.CACHE_TTL_HOURS
            )
            tracker = ExecutionTracker()
            chat_service = ChatSessionService(
                agent=agent,
                cache=cache,
                tracker=tracker,
                config=config,
            )

            app.state.config = config
            app.state.chat_service = chat_service
            app.state.cache = cache
            app.state.tracker = tracker

            yield


_cfg = get_config()
_origins = _parse_cors_origins(_cfg.CORS_ORIGINS)
app = FastAPI(title="Agentic Crawler API", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins,
    allow_credentials=_origins != ["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(router)
