"""Run the API server with uvicorn."""

import os

import uvicorn


def main() -> None:
    host = os.getenv("AGENTIC_CRAWLER_HOST", "127.0.0.1")
    port = int(os.getenv("AGENTIC_CRAWLER_PORT", "8000"))
    uvicorn.run(
        "agentic_crawler.web.app:app",
        host=host,
        port=port,
        reload=os.getenv("AGENTIC_CRAWLER_RELOAD", "").lower() == "true",
    )


if __name__ == "__main__":
    main()
