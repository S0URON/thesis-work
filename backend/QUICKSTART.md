# ⚡ Quick Start Guide

Get up and running with Agentic Crawler in 5 minutes!

## 🚀 Installation (2 minutes)

### Step 1: Install Dependencies
```bash
pip install -e .
```

Or if you're developing:
```bash
pip install -e ".[dev]"
```

### Step 3: Set Up Environment
```bash
# Copy the template
copy .env.example .env

# Edit with your API keys
notepad .env
```

Add your keys:
```env
FIRECRAWL_API_KEY=your_firecrawl_api_key_here
GOOGLE_API_KEY=your_google_api_key_here
```

## 🎯 First Run (1 minute)

```bash
python main.py
```

You'll see:
```
================================================================================
⚡ Optimized Evaluation Agent - Maximum Performance
Fast execution • Structured data extraction • Ready for test generation
================================================================================

✅ Loaded 6 tools

💡 Example: 'Analyze https://example.com for QA testing'
Type /help for available commands

You: 
```

## 💡 Try These Examples

### Example 1: Quick Website Analysis
```
You: Analyze https://example.com for QA testing
```

### Example 2: Comprehensive Report
```
You: Generate a comprehensive QA test report for https://your-website.com including test scenarios for forms, navigation, and localization
```

### Example 3: Specific Feature Testing
```
You: Create test scenarios for the contact form on https://your-site.com/contact
```

## 📋 Useful Commands

| Command | Description |
|---------|-------------|
| `/stats` | Show execution statistics (tokens, cost, cache) |
| `/reports` | List recent QA reports |
| `/outputs` | List saved tool outputs |
| `/clear` | Clear conversation history |
| `/help` | Show all commands |
| `quit` or `exit` | Exit the application |

## 📁 Where Are My Files?

After running queries, check these folders:

```
agentic_crawler/
├── qa_reports/          # ← Your QA reports are here (*.md files)
├── tool_outputs/        # ← Raw tool outputs here (*.json files)
├── cache/               # ← Cached results for faster queries
└── sessions/            # ← Session data
```

## 🎓 Understanding the Output

### During Analysis
You'll see tool calls like:
```
🔧 firecrawl_map ⚡
   https://example.com
   
✓ firecrawl_map (2.3s, 1,234 chars)
  → tool_outputs/20250115_123045_firecrawl_map_example_com.json
```

- `🔧` = Tool being called
- `⚡` = Result from cache (faster!)
- `🎬` = Interactive actions being performed
- `✓` = Tool completed successfully

### Final Response
You'll get a structured markdown report with:
- Executive summary
- Website structure
- Detailed test scenarios
- Test data requirements
- Automation recommendations

## 🧪 Running Tests

Verify everything works:

```bash
# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=src/agentic_crawler --cov-report=html

# View coverage report
start htmlcov\index.html
```

## 🐛 Troubleshooting

### Import Errors?
```bash
pip install -e .
```

### Missing API Key Error?
Make sure `.env` file has your keys:
```env
FIRECRAWL_API_KEY=fc-xxxxx
GOOGLE_API_KEY=AIzaSyxxxxx
```

### Tool Not Found?
Make sure Node.js is installed (needed for Firecrawl):
```bash
node --version  # Should show v18+ or higher
npm --version
```

## 📊 Performance Tips

1. **Enable Caching** (default: ON)
   - Speeds up repeated queries by 50-70%
   - Cached results show `⚡` indicator

2. **Use Specific URLs**
   - Better: `https://example.com/contact`
   - Instead of: "analyze example.com"

3. **Check Stats Regularly**
   ```
   /stats
   ```
   See your token usage and costs

## 🎯 What to Analyze?

### Good Candidates
- ✅ Marketing websites
- ✅ SaaS applications
- ✅ E-commerce sites
- ✅ Contact/booking forms
- ✅ Multi-language sites

### Not Ideal For
- ❌ Sites requiring login
- ❌ Heavy JavaScript SPAs (limited support)
- ❌ Sites with anti-bot protection

## 📖 Next Steps

1. **Read Full Documentation**
   - `README.md` - Complete feature guide
   - `CONTRIBUTING.md` - Development guide
   - `DEPLOYMENT.md` - Production deployment

2. **Explore the Code**
   ```
   src/agentic_crawler/
   ├── agents/        # Agent logic
   ├── config/        # Configuration
   ├── models/        # Data models
   ├── services/      # Business logic
   └── utils/         # Helpers
   ```

3. **Customize Prompts**
   Edit `src/agentic_crawler/agents/prompts.py` to adjust analysis style

4. **Add Features**
   Follow the modular structure to add new capabilities

## 🎉 You're Ready!

Start analyzing websites and generating QA reports:

```bash
python main.py
```

Type:
```
Analyze https://example.com for QA testing
```

Watch the magic happen! ✨

---

**Need Help?**
- Check `README.md` for detailed docs
- Review examples in `MIGRATION_GUIDE.md`
- Open an issue on GitHub

**Happy Testing!** 🚀
