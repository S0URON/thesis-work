# Agentic Crawler - Professional Website Analysis Tool

A sophisticated autonomous agent for comprehensive website analysis and documentation using AI-powered web crawling.

## 🚀 Features

- **Intelligent Web Analysis**: Automatically discovers and analyzes website structure
- **Website Summaries**: Comprehensive overviews of website purpose, target audience, and business model
- **Content Overview**: Detailed analysis of content types, themes, and organization
- **Visual Sitemap Diagrams**: Mermaid diagrams showing complete site structure and page relationships
- **User Flow Diagrams**: Visual Mermaid diagrams for key user journeys with decision points
- **Smart Caching**: LRU cache system reduces API calls and improves performance
- **Execution Tracking**: Detailed statistics on token usage, costs, and performance
- **Professional Output**: Structured markdown reports with visual diagrams
- **Interactive CLI**: User-friendly command-line interface with rich formatting

## 📋 Requirements

- Python 3.11+
- Node.js (for Firecrawl MCP server)
- API Keys:
  - Firecrawl API Key
  - Google AI API Key (Gemini) or Groq API Key

## 🔧 Installation

1. **Clone the repository**:
```bash
git clone <your-repo-url>
cd agentic_crawler
```

2. **Install dependencies**:
```bash
pip install -e .
```

Or using uv:
```bash
uv pip install -e .
```

3. **Set up environment variables**:
```bash
copy .env.example .env
```

Edit `.env` and add your API keys:
```
FIRECRAWL_API_KEY=your_firecrawl_key
GOOGLE_API_KEY=your_google_key
GROQ_API_KEY=your_groq_key  # Optional
```

## 🎯 Usage

### Basic Usage

Run the CLI:
```bash
python main.py
```

### Example Queries

```
Analyze https://example.com
Generate website analysis for https://mywebsite.com
Create a comprehensive website analysis report for https://app.example.com
```

### Available Commands

- `/stats` - Show execution statistics
- `/clear` - Clear conversation history
- `/reports` - List recent website analysis reports
- `/outputs` - List recent tool outputs
- `/help` - Show help message
- `quit` or `exit` - Exit the application

### HTTP API (JSON)

The same agent logic is exposed over HTTP (no bundled frontend). The FastAPI app runs the Firecrawl MCP **on the server machine**; clients only send JSON.

Start the server (defaults to `http://127.0.0.1:8000`):

```bash
agentic-crawler-web
```

Or:

```bash
uvicorn agentic_crawler.web.app:app --host 127.0.0.1 --port 8000
```

Optional environment variables: `AGENTIC_CRAWLER_HOST`, `AGENTIC_CRAWLER_PORT`, `CORS_ORIGINS` (comma-separated origins, or `*` for development), `AGENTIC_CRAWLER_RELOAD=true` for auto-reload (not recommended with MCP in production).

Interactive OpenAPI docs: open `http://127.0.0.1:8000/docs` after the server has started.

Example chat request:

```bash
curl -s -X POST "http://127.0.0.1:8000/api/chat" \
  -H "Content-Type: application/json" \
  -d '{"message": "Hello"}'
```

The response includes `session_id` (use the same value on later turns). Clear history: `POST /api/session/clear` with `{"session_id": "<id>"}`. Other routes: `GET /api/reports`, `GET /api/outputs`, `GET /api/stats`, `GET /api/health`.

## 📁 Project Structure

```
agentic_crawler/
├── src/
│   └── agentic_crawler/
│       ├── __init__.py
│       ├── cli.py              # Command-line interface
│       ├── config/
│       │   ├── __init__.py
│       │   └── settings.py     # Configuration management
│       ├── models/
│       │   ├── __init__.py
│       │   ├── execution.py    # Execution tracking models
│       │   └── reports.py      # Website analysis report models
│       ├── services/
│       │   ├── __init__.py
│       │   ├── cache_service.py     # Caching logic
│       │   ├── chat_service.py      # Agent turns (CLI + API)
│       │   └── tracker_service.py   # Execution tracking
│       ├── web/
│       │   ├── app.py               # FastAPI app + MCP lifespan
│       │   ├── routes.py            # REST endpoints
│       │   └── main.py              # uvicorn entry
│       ├── agents/
│       │   ├── __init__.py
│       │   ├── evaluation_agent.py  # EvaluationAgent (LLM + MCP tools)
│       │   └── prompts.py      # System prompts
│       └── utils/
│           ├── __init__.py
│           ├── file_utils.py   # File operations
│           └── display_utils.py # Display formatting
├── tests/                      # Test suite
├── cache/                      # Cache storage
├── sessions/                   # Session data
├── tool_outputs/               # Tool output files
├── reports/                    # Generated website analysis reports
├── main.py                     # Entry point
├── pyproject.toml             # Project configuration
├── .env.example               # Environment template
└── README.md                  # This file
```

## 🛠️ Configuration

Edit `src/agentic_crawler/config/settings.py` or set environment variables:

```python
# Cache settings
CACHE_TTL_HOURS = 24
MAX_CACHE_SIZE = 100  # MB
ENABLE_CACHING = True

# Application settings
ENABLE_STREAMING = True
DEBUG_MODE = False
AUTO_SAVE_OUTPUTS = True
# CORS for HTTP API (comma-separated origins, or * )
CORS_ORIGINS = "*"

# Model settings
GROQ_MODEL = "llama-3.3-70b-versatile"
GOOGLE_MODEL = "gemini-2.5-flash-lite"
MODEL_TEMPERATURE = 0.3
```

## 📊 Output Examples

### Website Analysis Reports
Generated reports include:
- Executive summary with metrics
- Website summary (purpose, audience, business model)
- Content overview (types, themes, organization)
- Sitemap diagram (Mermaid format)
- User flow diagrams (Mermaid format) for key journeys
- Site structure details (all pages with purposes)
- Navigation patterns
- Design & UX observations
- Technical observations
- Additional notes and recommendations

Reports are saved to `reports/` in markdown format with embedded Mermaid diagrams that render in GitHub, documentation tools, and markdown viewers.

### Tool Outputs
All tool outputs are saved to `tool_outputs/` as JSON files with:
- Tool name and arguments
- Timestamp
- Output data
- Metadata

## 🧪 Testing

Run tests:
```bash
pytest tests/
```

With coverage:
```bash
pytest tests/ --cov=src/agentic_crawler --cov-report=html
```

## 🔒 Security

- Never commit `.env` file with real API keys
- Use `.env.example` as template
- API keys are loaded from environment only
- No sensitive data in logs (when DEBUG_MODE=False)

## 📈 Performance

- **Caching**: Reduces redundant API calls by ~40-60%
- **Streaming**: Real-time response display
- **LRU Eviction**: Automatic cache size management
- **Token Tracking**: Detailed cost analysis