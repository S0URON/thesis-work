# Thesis Title: Leveraging Agentic AI for Contextual User Flow Discovery and Heuristic Evaluation
## Project Report

---

## Executive Summary

This project presents an **Agentic Crawler**, an autonomous AI-powered system designed for comprehensive website analysis and documentation. The system leverages modern artificial intelligence technologies, specifically Large Language Models (LLMs), combined with web crawling capabilities to automatically analyze websites and generate detailed website summaries, content overviews, user flow diagrams, and sitemap diagrams.

The system demonstrates practical application of AI agents in website analysis, showcasing how autonomous systems can assist in understanding website architecture, user journeys, and content organization by intelligently exploring websites, mapping their structure, and generating visual diagrams and comprehensive documentation.

The same agent is also exposed as a **REST JSON API** (FastAPI), so custom clients (e.g. a React frontend) can integrate without using the terminal. The research focus remains on **agentic analysis**, **diagram generation**, and **efficient tool use**—not on a particular UI technology.

---

## 1. Project Objectives

### Primary Goals

1. **Automated Website Analysis**: Develop a system capable of autonomously exploring and understanding website structure without manual intervention.

2. **Intelligent Website Analysis Report Generation**: Create comprehensive, structured website analysis reports that include:
   - Website summaries and content overviews
   - Visual sitemap diagrams (Mermaid format)
   - User flow diagrams for key journeys
   - Navigation patterns and content organization
   - Design and UX observations
   - Technical observations

3. **Performance Optimization**: Implement efficient caching mechanisms to reduce API costs and improve response times.

4. **Accessible interfaces**: Provide an interactive **CLI** (Rich terminal) and an **HTTP API** (OpenAPI at `/docs`) so users or external applications can request analysis and consume structured JSON responses. A separate web frontend is not bundled in the repository but can be built against the API.

### Learning Objectives

- Understanding of AI agent architecture and implementation
- Integration of multiple external services (APIs, MCP servers)
- Design and implementation of caching strategies
- Development of structured data models and type safety
- Best practices in software architecture and design patterns

---

## 2. System Architecture

### 2.1 High-Level Architecture

The system follows a **layered architecture** with **two entry points** sharing one orchestration path:

```
┌──────────────────────┐     ┌──────────────────────┐
│  CLI (cli.py)        │     │  HTTP API (web/)     │
│  Rich, slash cmds    │     │  FastAPI + JSON      │
└──────────┬───────────┘     └──────────┬───────────┘
           │                            │
           └────────────┬───────────────┘
                        ▼
           ┌────────────────────────────┐
           │  ChatSessionService        │
           │  SessionStore (per id)     │
           │  process_turn → TurnResult │
           └────────────┬───────────────┘
                        ▼
           ┌────────────────────────────┐
           │  EvaluationAgent (LangChain + MCP) │
           └────────────┬───────────────┘
                        ▼
           ┌────────────────────────────┐
           │  Cache + ExecutionTracker  │
           └────────────┬───────────────┘
                        ▼
           ┌────────────────────────────┐
           │  Firecrawl MCP, Gemini/Groq  │
           └────────────────────────────┘
```

MCP and API keys run **only on the server process**. See `project_architecture.md` for diagrams, route list, and session semantics.

### 2.2 Component Responsibilities

#### **CLI** (`cli.py`)
- Thin adapter: starts MCP stdio client, builds `EvaluationAgent` and `ChatSessionService`, uses fixed `session_id="cli"`.
- Slash commands (`/stats`, `/clear`, `/reports`, `/outputs`, `/help`) and Rich rendering; delegates natural-language turns to `ChatSessionService.process_turn`.

#### **HTTP API** (`web/app.py`, `web/routes.py`, `web/main.py`)
- FastAPI application with **lifespan** that mirrors the CLI’s MCP connection lifecycle.
- JSON endpoints including `POST /api/chat` (optional `session_id`, returns `session_id` + `TurnResult` fields), `POST /api/session/clear`, listing reports/outputs, `GET /api/stats`, `GET /api/health`.
- **OpenAPI** documentation is served at `/docs` when the server runs (no separate SPA in-repo).

#### **ChatSessionService** (`services/chat_service.py`)
- Central **orchestration** for one user turn: append message, `ainvoke`, cache/tool tracking, optional file saves, `TurnResult` / `ToolEvent` DTOs.
- **SessionStore**: in-memory map `session_id → message list`; **asyncio.Lock** per session.
- **Content normalization** (`services/content_normalize.py`): LangChain may return list-shaped message content; normalized to string before cache and disk.

#### **Agent Layer** (`agents/evaluation_agent.py`, `prompts.py`)
- LangChain `create_agent` with Google or Groq chat model and MCP-loaded tools.

#### **Service helpers** (`services/`)
- **CacheService**, **ExecutionTracker** as before.

#### **Data models** (`models/` + Pydantic DTOs in `chat_service.py`)
- Execution/report models; `TurnResult` and `ToolEvent` for API responses.

#### **Utilities** (`utils/`)
- **File utils**: saves under `tool_outputs/`, `reports/`; **display utils**: terminal only.

---

## 3. Key Features and Capabilities

### 3.1 Intelligent Web Analysis

The system can automatically:
- **Discover website structure**: Maps out pages, links, and navigation patterns
- **Extract content**: Retrieves text, images, and metadata from web pages
- **Understand context**: Uses AI to comprehend the purpose and functionality of different sections

### 3.2 Comprehensive Website Analysis Report Generation

Generated reports include:

1. **Executive Summary**
   - Overall website assessment
   - Key metrics and statistics
   - High-level findings

2. **Website Summary**
   - Comprehensive description of website purpose
   - Target audience and business model
   - Value proposition

3. **Content Overview**
   - Content types and categories
   - Content themes and topics
   - Content organization structure
   - Media types used

4. **Sitemap Diagram**
   - Visual Mermaid diagram showing complete site structure
   - Hierarchical relationships between pages
   - All pages and their connections

5. **User Flow Diagrams**
   - Visual Mermaid diagrams for each key user journey
   - Decision points and actions
   - Entry and conversion points
   - Multiple user flows documented

6. **Site Structure Details**
   - Complete list of all pages with purposes
   - URL structure and relationships
   - Content descriptions

7. **Navigation Patterns**
   - Primary, secondary, and footer navigation
   - Breadcrumbs and search functionality

8. **Design & UX Observations**
   - Design style and patterns
   - Color scheme and typography
   - Interactive elements
   - Mobile responsiveness

9. **Technical Observations**
   - Technology stack detection
   - Performance observations
   - SEO elements
   - Accessibility features

### 3.3 Performance Optimization

#### Caching Strategy
- **LRU Cache**: Reduces redundant tool/API work when the same tool+arguments repeat (impact depends on workload)
- **TTL Support**: Cache entries expire after 24 hours (configurable)
- **Size Management**: Automatic eviction when cache exceeds 100MB limit
- **Cost Reduction**: Lowers repeated analysis cost when cache hits occur

#### Execution Tracking
- Real-time monitoring of:
  - Token usage (input/output)
  - API costs per operation
  - Tool call statistics
  - Performance metrics

### 3.4 Visual Diagram Generation

The system generates:
- **Sitemap Diagrams**: Complete site structure visualization using Mermaid syntax
- **User Flow Diagrams**: Step-by-step journey visualization with decision points
- **Markdown Compatible**: Diagrams render in GitHub, documentation tools, and markdown viewers

### 3.5 Interactive CLI and HTTP API

**CLI**
- Rich terminal formatting; slash commands; local session id `cli`.

**HTTP API**
- `POST /api/chat` returns JSON (`assistant_text`, `tool_events`, optional `error`, `report_saved_path`); clients should persist `session_id` across turns.
- Long-running requests: the MVP returns when the **full** agent turn completes (no token streaming in the current API).
- `GET /docs` (Swagger UI) for machine-readable schemas.

---

## 4. Technical Implementation

### 4.1 Technologies Used

#### **Core Technologies**
- **Python 3.11+**: Primary programming language (see `pyproject.toml`)
- **LangChain**: Framework for building LLM applications
- **Pydantic**: Data validation and type safety
- **Rich**: Terminal formatting and display
- **FastAPI** / **uvicorn**: HTTP API and ASGI server

#### **AI/ML Services**
- **Google Gemini API**: Primary LLM provider (gemini-2.5-flash-lite)
- **Groq API**: Alternative LLM provider (llama-3.3-70b-versatile)
- **Model Context Protocol (MCP)**: Protocol for tool integration

#### **Web Crawling**
- **Firecrawl**: Web scraping and crawling service via MCP server
- **Node.js**: Required for Firecrawl MCP server

#### **Development Tools**
- **pytest**: Testing framework
- **uv**: Fast Python package manager
- **dotenv**: Environment variable management

### 4.2 Design Patterns Implemented

#### 1. **Singleton Pattern**
Used for configuration management to ensure a single source of truth for settings.

#### 2. **Service Layer Pattern**
Separates business logic from presentation and data access layers.

#### 3. **Repository Pattern**
Abstracts file operations, making the system more testable and maintainable.

#### 4. **Factory Pattern**
Used for creating different LLM model instances based on configuration.

#### 5. **Strategy Pattern**
Implemented in cache eviction policies and display formatting.

#### 6. **Dependency injection**
`ChatSessionService` receives the agent, cache, and tracker—shared by CLI and API.

#### 7. **Async lifespan (HTTP)**
FastAPI `lifespan` holds the MCP stdio connection for the API process, analogous to the CLI’s async context managers.

### 4.3 Data Flow

#### Request Processing Flow (CLI)

1. **User Input**: User enters a query or command in the terminal
2. **Command Parsing**: CLI handles slash commands or delegates to `ChatSessionService.process_turn` for natural language
3. **ChatSessionService**: Updates in-memory history for `session_id="cli"`, invokes `EvaluationAgent`
4. **Cache Check**: Per tool call, cache may return a prior result
5. **Tool Execution**: On miss, MCP tools call Firecrawl
6. **AI Processing**: LLM produces the next assistant message (markdown, often with Mermaid)
7. **Persistence**: Optional saves to `tool_outputs/` and `reports/`
8. **Display**: Rich UI; tool trace replay uses `agent_messages` + `tool_events` ordering

#### Request Processing Flow (HTTP API)

1. **Client** sends `POST /api/chat` with `message` and optional `session_id`
2. **Server** assigns or reuses `session_id`, runs the same `ChatSessionService` path as the CLI
3. **Response** JSON includes `session_id` and turn fields; **503** if the app is not ready (MCP not initialized)
4. **No streaming** in the current MVP: the client waits until the full turn completes

#### Caching Flow

1. **Cache Key Generation**: MD5 hash of tool name + arguments
2. **Cache Lookup**: Check if entry exists
3. **TTL Validation**: Verify entry hasn't expired
4. **Cache Hit**: Return cached result (skip API call)
5. **Cache Miss**: Execute tool, store result, return to caller

---

## 5. Project Structure

```
agentic_crawler/
├── src/
│   └── agentic_crawler/
│       ├── __init__.py
│       ├── cli.py                 # Command-line interface
│       ├── config/
│       │   ├── __init__.py
│       │   └── settings.py        # Configuration management
│       ├── models/
│       │   ├── __init__.py
│       │   ├── execution.py        # Execution tracking models
│       │   └── reports.py         # QA report data models
│       ├── services/
│       │   ├── __init__.py
│       │   ├── cache_service.py      # LRU cache implementation
│       │   ├── tracker_service.py    # Execution tracking
│       │   ├── chat_service.py       # Turn orchestration, SessionStore, TurnResult
│       │   └── content_normalize.py # Multimodal/list → string for cache/IO
│       ├── web/
│       │   ├── app.py                # FastAPI + MCP lifespan
│       │   ├── routes.py             # REST endpoints
│       │   └── main.py               # uvicorn entry (agentic-crawler-web)
│       ├── agents/
│       │   ├── __init__.py
│       │   ├── evaluation_agent.py # EvaluationAgent (LLM + tools)
│       │   └── prompts.py         # System prompts
│       └── utils/
│           ├── __init__.py
│           ├── file_utils.py      # File operations
│           ├── display_utils.py   # Display formatting
│           └── mcp_utils.py       # MCP integration
├── tests/                          # Test suite
├── cache/                          # Cache storage directory
├── sessions/                       # Session data
├── tool_outputs/                   # Tool output files
├── reports/                        # Generated website analysis reports
├── main.py                         # CLI entry (calls packaged cli)
├── pyproject.toml                  # Project configuration
├── requirements.txt                # Python dependencies
├── project_architecture.md         # Technical architecture (thesis KB)
├── PROJECT_REPORT.md               # This document
├── .env.example                    # Environment template
└── README.md                       # Project documentation
```

---

## 6. Performance and Optimization

### 6.1 Caching Performance

- **Cache hits**: Avoid repeating expensive tool work when arguments match prior calls
- **Response Time**: Cached tool results are faster than re-invoking crawlers
- **Cost Savings**: Lower LLM/tool usage when the cache applies

### 6.2 Optimization Strategies

1. **LRU Eviction**: Automatically removes least recently used entries when cache is full
2. **TTL Expiration**: Prevents stale data while allowing reuse of recent analyses
3. **Size Limits**: Prevents unbounded memory growth
4. **Async Operations**: Non-blocking I/O for better concurrency

### 6.3 Token Management

- **Token Tracking**: Real-time monitoring of input/output tokens
- **Cost Calculation**: Automatic cost estimation per operation
- **Context Optimization**: Efficient prompt design to minimize token usage

---

## 7. Security Considerations

### 7.1 API Key Management

- **Environment Variables**: All API keys stored in `.env` file (never committed)
- **Validation**: Configuration validation ensures required keys are present
- **No Hardcoding**: No sensitive data in source code

### 7.2 Input Validation

- **Pydantic Models**: All data validated using Pydantic models
- **Type Safety**: Runtime type checking prevents invalid data
- **Sanitization**: User input sanitized before processing

### 7.3 Output Security

- **Safe File Naming**: Prevents path traversal attacks
- **Logging**: No sensitive data in logs (when DEBUG_MODE=False)
- **Data Isolation**: Each session maintains separate data

### 7.4 Network exposure (HTTP API)

- **API keys** remain server-side only; browsers or React apps must not embed Firecrawl/Gemini keys.
- **CORS** is configurable via `CORS_ORIGINS` (tighten beyond `*` for production).
- Treat the API as **trusted-network / localhost** unless HTTPS and authentication are added.

---

## 8. Testing Strategy

### 8.1 Current Testing

- **Unit Tests**: Tests for individual components (cache service, tracker service, file utils)
- **Test Coverage**: Aiming for comprehensive coverage of core functionality

### 8.2 Future Testing Plans

- **API tests**: FastAPI `TestClient` (or httpx) for `/api/health`, `/api/chat` with MCP mocked where needed
- **Integration Tests**: Testing component interactions
- **End-to-End Tests**: Full workflow testing
- **Performance Tests**: Load and stress testing

---

## 9. Use Cases and Applications

### 9.1 Primary Use Cases

1. **Website Analysts**: Generate comprehensive website documentation and analysis
2. **Developers**: Quick understanding of website structure, user flows, and content organization
3. **Project Managers**: High-level overview of website architecture and user journeys
4. **UX Designers**: Visual user flow diagrams and navigation patterns
5. **Content Strategists**: Content overview and organization analysis
6. **Technical Writers**: Complete site structure documentation

### 9.2 Example Scenarios

- **E-commerce Websites**: Map shopping flows, checkout processes, product hierarchies
- **SaaS Applications**: Document user registration flows, dashboard navigation, feature access
- **Content Websites**: Analyze content organization, navigation patterns, information architecture
- **Corporate Websites**: Map service pages, contact flows, about sections
- **Documentation Sites**: Understand documentation structure and navigation

---

## 10. Challenges and Solutions

### 10.1 Technical Challenges

**Challenge**: Managing API costs for repeated analyses
- **Solution**: Implemented LRU cache with TTL to reuse previous analyses

**Challenge**: Handling large websites with many pages
- **Solution**: Intelligent crawling strategies and pagination support

**Challenge**: Ensuring type safety and data validation
- **Solution**: Comprehensive use of Pydantic models throughout the system

**Challenge**: LLM/tool messages sometimes arrive as **list-shaped** multimodal content instead of plain strings
- **Solution**: `content_normalize.py` and defensive cache writes so string operations (e.g. encoding for cache size) never receive raw lists

### 10.2 Design Challenges

**Challenge**: Balancing flexibility and structure
- **Solution**: Layered architecture with clear separation of concerns

**Challenge**: User experience in CLI
- **Solution**: Rich formatting and helpful commands; HTTP API enables separate UX (e.g. React) for the same backend

---

## 11. Future Enhancements

### 11.1 Planned Features

1. **Dedicated web frontend**: e.g. React SPA consuming the existing REST API (the HTTP layer is already present; bundling a UI remains optional)
2. **Streaming responses**: SSE or WebSocket for partial agent output (requires API and LangChain streaming support)
3. **Report Export**: Additional export formats (PDF, HTML, JSON, SVG for diagrams)
4. **Scheduled Analysis**: Automated periodic website analysis
5. **Comparison Reports**: Compare different versions of websites
6. **Interactive Diagrams**: Clickable diagrams with drill-down capabilities
7. **Diagram Export**: Export Mermaid diagrams as images (PNG, SVG)

### 11.2 Technical Improvements

1. **Distributed Caching**: Redis integration for multi-instance deployments
2. **Enhanced AI Models**: Support for additional LLM providers
3. **Advanced Analytics**: More detailed performance and cost analytics
4. **Plugin System**: Extensible architecture for custom tools

---

## 12. Learning Outcomes

### 12.1 Technical Skills Developed

- **AI Agent Development**: Understanding of autonomous agent architecture
- **API Integration**: External LLM and Firecrawl services; **FastAPI** JSON API for clients
- **Caching Strategies**: Implementation of efficient caching mechanisms
- **Software Architecture**: Application of design patterns and best practices
- **Type Safety**: Use of modern Python type hints and validation

### 12.2 Problem-Solving Skills

- **System Design**: Designing scalable and maintainable systems
- **Performance Optimization**: Identifying and solving performance bottlenecks
- **Cost Management**: Optimizing API usage to reduce costs
- **User Experience**: Creating intuitive interfaces

---

## 13. Conclusion

The **Agentic Crawler** project successfully demonstrates the practical application of AI agents in website analysis and documentation. By combining modern AI technologies with web crawling capabilities, the system provides a powerful tool for automated website analysis, generating comprehensive summaries, content overviews, and visual diagrams of site structure and user flows.

### Key Achievements

✅ **Functional System**: Fully operational AI-powered website analysis tool  
✅ **Visual Documentation**: Generates Mermaid diagrams for sitemaps and user flows  
✅ **Performance Optimized**: LRU+TTL caching reduces redundant tool/API work  
✅ **Well-Architected**: Shared `ChatSessionService`, CLI + HTTP entry points  
✅ **User-Friendly**: Interactive CLI; **REST API** for programmatic and future web clients  
✅ **Comprehensive Documentation**: README, `project_architecture.md`, OpenAPI `/docs`  

### Educational Value

This project showcases:
- Real-world application of AI/ML technologies
- Software engineering best practices
- System design and architecture principles
- Performance optimization techniques
- Integration of multiple complex systems
- Visual documentation generation

The system serves as a practical example of how AI can be leveraged to automate traditionally manual processes in website analysis and documentation, demonstrating both the capabilities and considerations necessary when building production-ready AI applications.

---

## 14. References and Documentation

- **Project Documentation**: See `README.md` for user guide (CLI and HTTP server commands)
- **Architecture Details**: See `project_architecture.md` for layered design, routes, sessions, MCP lifecycle, and extension points (primary technical KB for this repo)
- **API Contract**: OpenAPI/Swagger at `http://<host>:<port>/docs` when `agentic-crawler-web` (or uvicorn) is running
- **Quick Start Guide**: See `QUICKSTART.md` for setup instructions (if present)
- **Other**: `ARCHITECTURE.md` may exist as an alternate narrative; prefer `project_architecture.md` for alignment with the current code layout