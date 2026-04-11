# 🏗️ Architecture Overview

## System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        User Interface (CLI)                      │
│                    src/agentic_crawler/cli.py                    │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                         Agent Layer                              │
│                   src/agentic_crawler/agents/                    │
│  ┌──────────────┐              ┌──────────────────────┐         │
│  │ EvaluationAgent │◄──────────│  System Prompts      │         │
│  │  evaluation_agent.py │      │  prompts.py          │         │
│  └──────┬───────┘              └──────────────────────┘         │
└─────────┼──────────────────────────────────────────────────────┘
          │
          ▼
┌─────────────────────────────────────────────────────────────────┐
│                        Service Layer                             │
│                  src/agentic_crawler/services/                   │
│  ┌──────────────────┐         ┌──────────────────────┐          │
│  │  Cache Service   │         │  Execution Tracker   │          │
│  │  cache_service.py│         │  tracker_service.py  │          │
│  │                  │         │                      │          │
│  │  • LRU Cache     │         │  • Token Tracking    │          │
│  │  • TTL Support   │         │  • Cost Calculation  │          │
│  │  • Size Limits   │         │  • Tool Call Stats   │          │
│  └──────────────────┘         └──────────────────────┘          │
└─────────────────────────────────────────────────────────────────┘
          │                              │
          ▼                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                         Data Models                              │
│                   src/agentic_crawler/models/                    │
│  ┌──────────────────┐         ┌──────────────────────┐          │
│  │  Execution       │         │  Reports             │          │
│  │  execution.py    │         │  reports.py          │          │
│  │                  │         │                      │          │
│  │  • ToolCall      │         │  • QAReport          │          │
│  │  • ExecutionStats│         │  • TestScenario      │          │
│  │  • CacheStats    │         │  • TestStep          │          │
│  └──────────────────┘         └──────────────────────┘          │
└─────────────────────────────────────────────────────────────────┘
          │
          ▼
┌─────────────────────────────────────────────────────────────────┐
│                         Utilities                                │
│                   src/agentic_crawler/utils/                     │
│  ┌────────────┐  ┌──────────────┐  ┌─────────────────┐         │
│  │  File      │  │  Display     │  │  MCP Utils      │         │
│  │  Utils     │  │  Utils       │  │                 │         │
│  └────────────┘  └──────────────┘  └─────────────────┘         │
└─────────────────────────────────────────────────────────────────┘
          │
          ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Configuration                               │
│                  src/agentic_crawler/config/                     │
│                                                                   │
│  • Environment Variables                                         │
│  • Directory Setup                                               │
│  • API Keys                                                      │
│  • Logging Configuration                                         │
└─────────────────────────────────────────────────────────────────┘
          │
          ▼
┌─────────────────────────────────────────────────────────────────┐
│                    External Services                             │
│                                                                   │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │  Firecrawl   │  │  Google AI   │  │  Groq        │          │
│  │  MCP Server  │  │  (Gemini)    │  │  (Llama)     │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
└─────────────────────────────────────────────────────────────────┘
```

## Data Flow

### 1. User Query Flow

```
User Input
    │
    ▼
CLI Handler
    │
    ├─► Command? (/stats, /clear, etc.)
    │       │
    │       └─► Execute Command ─► Display Result
    │
    └─► Query? (Analyze website)
            │
            ▼
        EvaluationAgent
            │
            ├─► Check Cache
            │       │
            │       ├─► Hit? ─► Return Cached Result
            │       └─► Miss? ─► Continue
            │
            ├─► Execute Tool Calls
            │       │
            │       └─► Firecrawl MCP Tools
            │               │
            │               ├─► firecrawl_map
            │               ├─► firecrawl_scrape
            │               └─► firecrawl_crawl
            │
            ├─► Track Execution
            │       │
            │       └─► ExecutionTracker
            │               │
            │               ├─► Token Usage
            │               ├─► Cost Calculation
            │               └─► Tool Call Stats
            │
            ├─► Save Outputs
            │       │
            │       └─► File Utils
            │               │
            │               ├─► tool_outputs/
            │               └─► qa_reports/
            │
            └─► Generate Response
                    │
                    └─► Display to User
```

### 2. Cache Flow

```
Tool Call Request
    │
    ▼
Cache Service
    │
    ├─► Generate Cache Key (MD5 hash of tool + args)
    │
    ├─► Check if exists
    │       │
    │       ├─► YES: Check TTL
    │       │       │
    │       │       ├─► Valid? ─► Return Cached Result
    │       │       └─► Expired? ─► Remove & Continue
    │       │
    │       └─► NO: Continue
    │
    ├─► Execute Tool Call
    │
    ├─► Store Result
    │       │
    │       ├─► Check Size Limits
    │       └─► Evict Old Entries (LRU)
    │
    └─► Return Result
```

## Component Responsibilities

### CLI (`cli.py`)
**Responsibilities:**
- User interaction
- Command parsing
- Session management
- Result display

**Dependencies:**
- Agent Layer
- Utils Layer
- Config

### Agent Layer (`agents/`)
**Responsibilities:**
- LLM interaction
- Tool orchestration
- Prompt management
- Response generation

**Dependencies:**
- Service Layer
- External APIs
- MCP Tools

### Service Layer (`services/`)
**Responsibilities:**
- Business logic
- Caching strategy
- Execution tracking
- State management

**Dependencies:**
- Data Models
- Config

### Data Models (`models/`)
**Responsibilities:**
- Type definitions
- Data validation
- Serialization
- Business rules

**Dependencies:**
- Pydantic

### Utilities (`utils/`)
**Responsibilities:**
- File I/O
- Display formatting
- Helper functions
- Common operations

**Dependencies:**
- Config
- Rich library

### Configuration (`config/`)
**Responsibilities:**
- Settings management
- Environment loading
- Directory setup
- Validation

**Dependencies:**
- OS environment
- dotenv

## Design Patterns Used

### 1. **Singleton Pattern**
Used in: `Config`
```python
_config: Optional[Config] = None

def get_config() -> Config:
    global _config
    if _config is None:
        _config = Config()
    return _config
```

### 2. **Service Layer Pattern**
Used throughout for separation of concerns
- CacheService
- ExecutionTracker

### 3. **Repository Pattern**
File operations abstracted in `file_utils.py`

### 4. **Factory Pattern**
Model creation in agents:
```python
def _create_model(self):
    if self.model_type == "groq":
        return ChatGroq(...)
    else:
        return ChatGoogleGenerativeAI(...)
```

### 5. **Strategy Pattern**
Cache eviction (LRU), display formatting

## Scalability Considerations

### Horizontal Scaling
```
┌──────────┐
│ Instance │───┐
└──────────┘   │
               │    ┌────────────┐
┌──────────┐   ├───►│   Redis    │
│ Instance │───┤    │   Cache    │
└──────────┘   │    └────────────┘
               │
┌──────────┐   │    ┌────────────┐
│ Instance │───┘    │  Shared    │
└──────────┘        │  Storage   │
                    └────────────┘
```

### Vertical Scaling
- Increase cache size
- More concurrent tool calls
- Larger batch sizes

## Extension Points

### Adding New Tools
```python
# In agents/evaluation_agent.py
def __init__(self, tools, custom_tools=None):
    all_tools = tools + (custom_tools or [])
    ...
```

### Adding New Services
```python
# services/my_service.py
class MyService:
    def __init__(self):
        self.config = get_config()
```

### Adding New Models
```python
# models/my_model.py
from pydantic import BaseModel

class MyModel(BaseModel):
    field: str
```

## Performance Optimization

### 1. Caching Strategy
- **LRU Eviction**: Remove least recently used entries
- **TTL**: Time-based expiration (24 hours default)
- **Size Limits**: Maximum 100MB cache

### 2. Async Operations
- All tool calls are async
- Non-blocking I/O operations
- Concurrent processing where possible

### 3. Token Optimization
- Compressed prompts
- Efficient context management
- Smart truncation

## Security Architecture

### 1. API Key Management
```
.env file (never committed)
    ↓
Environment Variables
    ↓
Config Validation
    ↓
Secure Usage
```

### 2. Input Validation
- Pydantic models validate all data
- Type checking at runtime
- Sanitization of user input

### 3. Output Sanitization
- No sensitive data in logs (when DEBUG=false)
- Safe file naming
- Path traversal prevention

## Testing Strategy

```
Unit Tests (tests/)
    ├── test_cache_service.py
    ├── test_tracker_service.py
    └── test_file_utils.py
          │
          ▼
    Integration Tests (future)
          │
          ▼
    End-to-End Tests (future)
```

## Deployment Architecture

```
Development
    ├── Local Python Environment
    └── Direct Execution

Production
    ├── Docker Container
    │   ├── Application
    │   ├── Node.js (for MCP)
    │   └── Dependencies
    │
    ├── Cloud VM (AWS/GCP/Azure)
    │   ├── Systemd Service
    │   └── Monitoring
    │
    └── Kubernetes (Optional)
        ├── Deployment
        ├── Service
        └── Persistent Volumes
```

---

**This architecture provides:**
- ✅ Clear separation of concerns
- ✅ Easy testing and maintenance
- ✅ Scalable design
- ✅ Professional structure
- ✅ Production-ready deployment
