"""Application configuration and settings."""

import os
from pathlib import Path
from typing import Optional
from dataclasses import dataclass
import warnings
import logging


@dataclass
class Config:
    """Application configuration with environment-based settings."""

    # Directory paths
    CACHE_DIR: Path = Path("cache")
    SESSIONS_DIR: Path = Path("sessions")
    OUTPUTS_DIR: Path = Path("tool_outputs")
    REPORTS_DIR: Path = Path("reports")
    TOOLS_SCHEMA_FILE: Path = Path("tools_schema.json")

    # Cache settings
    CACHE_TTL_HOURS: int = 24
    MAX_CACHE_SIZE: int = 100  # MB
    ENABLE_CACHING: bool = True

    # Application settings
    ENABLE_STREAMING: bool = True
    DEBUG_MODE: bool = False
    AUTO_SAVE_OUTPUTS: bool = True
    # Comma-separated origins for FastAPI CORS, or "*" for any (dev only)
    CORS_ORIGINS: str = "*"

    # Cost calculation (per 1K tokens)
    COST_PER_1K_INPUT_TOKENS: float = 0.00025
    COST_PER_1K_OUTPUT_TOKENS: float = 0.001

    # Model settings — set LLM_PROVIDER to google | groq | openai (see .env)
    LLM_PROVIDER: str = "google"
    GROQ_MODEL: str = "llama-3.3-70b-versatile"
    GOOGLE_MODEL: str = "gemini-2.5-flash-lite"
    OPENAI_MODEL: str = "gpt-4o-mini"
    # Optional: custom API base (OpenAI-compatible proxies, Azure OpenAI resource URL, etc.)
    OPENAI_BASE_URL: Optional[str] = None
    MODEL_TEMPERATURE: float = 0.3

    # MCP Server settings
    MCP_COMMAND: str = "npx"
    MCP_ARGS: list = None

    # API Keys (loaded from environment)
    FIRECRAWL_API_KEY: Optional[str] = None
    GROQ_API_KEY: Optional[str] = None
    GOOGLE_API_KEY: Optional[str] = None
    OPENAI_API_KEY: Optional[str] = None

    def __post_init__(self):
        """Initialize directories and load environment variables."""
        self._create_directories()
        self._load_environment()
        self._configure_logging()
        self._suppress_warnings()

        # Set default MCP args
        if self.MCP_ARGS is None:
            self.MCP_ARGS = ["-y", "firecrawl-mcp"]

    def _create_directories(self):
        """Create necessary directories if they don't exist."""
        self.CACHE_DIR.mkdir(exist_ok=True)
        self.SESSIONS_DIR.mkdir(exist_ok=True)
        self.OUTPUTS_DIR.mkdir(exist_ok=True)
        self.REPORTS_DIR.mkdir(exist_ok=True)

    def _load_environment(self):
        """Load configuration from environment variables."""
        self.FIRECRAWL_API_KEY = os.getenv("FIRECRAWL_API_KEY")
        self.GROQ_API_KEY = os.getenv("GROQ_API_KEY")
        self.GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
        self.OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

        # Override settings from environment if present
        if os.getenv("DEBUG_MODE"):
            self.DEBUG_MODE = os.getenv("DEBUG_MODE").lower() == "true"

        if os.getenv("ENABLE_CACHING"):
            self.ENABLE_CACHING = os.getenv("ENABLE_CACHING").lower() == "true"

        if os.getenv("CORS_ORIGINS") is not None:
            self.CORS_ORIGINS = os.getenv("CORS_ORIGINS", "*")

        if os.getenv("MODEL_TEMPERATURE"):
            self.MODEL_TEMPERATURE = float(os.getenv("MODEL_TEMPERATURE"))

        if os.getenv("LLM_PROVIDER"):
            self.LLM_PROVIDER = os.getenv("LLM_PROVIDER", "google").strip().lower()
        if os.getenv("OPENAI_MODEL"):
            self.OPENAI_MODEL = os.getenv("OPENAI_MODEL", self.OPENAI_MODEL).strip()
        if os.getenv("OPENAI_BASE_URL"):
            self.OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "").strip() or None

    def _configure_logging(self):
        """Configure logging based on debug mode."""
        level = logging.DEBUG if self.DEBUG_MODE else logging.INFO
        logging.basicConfig(
            level=level, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )

        # Suppress verbose library logs
        if not self.DEBUG_MODE:
            logging.getLogger("pydantic").setLevel(logging.ERROR)
            logging.getLogger("langchain").setLevel(logging.ERROR)
            logging.getLogger("httpx").setLevel(logging.WARNING)

    def _suppress_warnings(self):
        """Suppress unnecessary warnings."""
        if not self.DEBUG_MODE:
            warnings.filterwarnings("ignore")
            os.environ["PYTHONWARNINGS"] = "ignore"

    def validate(self) -> bool:
        """Validate required configuration."""
        errors = []

        if not self.FIRECRAWL_API_KEY:
            errors.append("FIRECRAWL_API_KEY is not set")

        valid_providers = ("google", "groq", "openai")
        provider = (self.LLM_PROVIDER or "google").strip().lower()
        if provider not in valid_providers:
            errors.append(
                f"LLM_PROVIDER must be one of: {', '.join(valid_providers)} (got {provider!r})"
            )
        elif provider == "google" and not self.GOOGLE_API_KEY:
            errors.append("GOOGLE_API_KEY is required when LLM_PROVIDER=google")
        elif provider == "groq" and not self.GROQ_API_KEY:
            errors.append("GROQ_API_KEY is required when LLM_PROVIDER=groq")
        elif provider == "openai" and not self.OPENAI_API_KEY:
            errors.append("OPENAI_API_KEY is required when LLM_PROVIDER=openai")

        if errors:
            for error in errors:
                logging.error(f"Configuration error: {error}")
            return False

        return True


# Global config instance
_config: Optional[Config] = None


def get_config() -> Config:
    """Get or create global config instance."""
    global _config
    if _config is None:
        _config = Config()
    return _config


def reset_config():
    """Reset global config (mainly for testing)."""
    global _config
    _config = None
