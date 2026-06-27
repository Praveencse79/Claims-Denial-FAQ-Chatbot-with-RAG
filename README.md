# Claims Denial FAQ Chatbot

RAG-powered chatbot for resolving healthcare claim denials using **LangChain**, **Claude API**, **Snowflake**, and **Pinecone**.

## Features

- **200+ denial scenarios** with semantic search across CARC/RARC codes
- **RAG pipeline** — retrieve relevant scenarios, augment prompts, generate with Claude
- **Snowflake** knowledge base integration for enterprise denial data
- **Pinecone** vector store for sub-second semantic retrieval
- **FastAPI REST API** with OpenAPI documentation
- **Slack bot** with slash commands and direct message support
- **98% accuracy** target via similarity thresholds and structured prompts

## Quick Start

### Prerequisites

- Python 3.11+
- Anthropic API key (Claude)
- OpenAI API key (embeddings)
- Pinecone account
- Snowflake account (optional — use JSON for local dev)
- Slack app credentials (for bot)

### Installation

```bash
# Clone and enter project
cd "Praveen AI Agent"

# Create virtual environment
python3.11 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your API keys and credentials

# Generate sample denial scenarios (210 scenarios)
python3 scripts/seed_denial_scenarios.py

# Ingest into Pinecone
python3 scripts/ingest_knowledge_base.py --source json --force-reindex

# Start API server
python3 -m claims_denial_chatbot.main api

# Start Slack bot (separate terminal)
python3 -m claims_denial_chatbot.main slack
```

### API Usage

```bash
# Health check
curl http://localhost:8000/api/v1/health

# Chat query
curl -X POST http://localhost:8000/api/v1/chat/query \
  -H "Content-Type: application/json" \
  -d '{"query_text": "How do I resolve a CO-16 denial for Medicare?"}'

# OpenAPI docs
open http://localhost:8000/docs
```

## Project Structure

```
├── src/claims_denial_chatbot/
│   ├── api/           # FastAPI routes and application
│   ├── bot/           # Slack bot integration
│   ├── config/        # Environment settings
│   ├── core/          # Constants, exceptions, logging
│   ├── data/          # Snowflake connector
│   ├── embeddings/    # Text embedding service
│   ├── llm/           # Claude client and prompts
│   ├── models/        # Pydantic schemas
│   ├── rag/           # RAG pipeline (retriever, chain, processor)
│   ├── services/      # Business logic layer
│   └── vector_store/  # Pinecone integration
├── scripts/           # Ingestion and seed scripts
├── data/              # Sample denial scenarios JSON
├── tests/             # Unit and integration tests
└── docs/              # Detailed documentation
```

## Documentation

See **[docs/PROJECT_DOCUMENTATION.md](docs/PROJECT_DOCUMENTATION.md)** for:

- Full architecture and system design
- RAG pipeline flow and code logic
- Core concepts (embeddings, vector search, prompt engineering)
- Complete method reference with naming conventions
- Deployment guide and configuration reference

## Testing

```bash
pytest tests/ -v --cov=claims_denial_chatbot
```

## License

MIT
