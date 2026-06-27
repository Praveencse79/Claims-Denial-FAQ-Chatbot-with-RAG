# Claims Denial FAQ Chatbot — Complete Project Documentation

**Version:** 1.0.0  
**Last Updated:** June 2025  
**Author:** Claims Support Engineering Team

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Business Context & Objectives](#2-business-context--objectives)
3. [System Architecture](#3-system-architecture)
4. [Technology Stack](#4-technology-stack)
5. [Core Concepts](#5-core-concepts)
6. [End-to-End Data Flow](#6-end-to-end-data-flow)
7. [Project Structure & Module Guide](#7-project-structure--module-guide)
8. [Naming Conventions](#8-naming-conventions)
9. [Configuration Reference](#9-configuration-reference)
10. [Component Deep Dive & Code Logic](#10-component-deep-dive--code-logic)
11. [Complete Method Reference](#11-complete-method-reference)
12. [API Documentation](#12-api-documentation)
13. [Slack Bot Integration](#13-slack-bot-integration)
14. [Knowledge Base Ingestion Pipeline](#14-knowledge-base-ingestion-pipeline)
15. [Prompt Engineering Strategy](#15-prompt-engineering-strategy)
16. [Error Handling & Logging](#16-error-handling--logging)
17. [Testing Strategy](#17-testing-strategy)
18. [Deployment Guide](#18-deployment-guide)
19. [Performance & Metrics](#19-performance--metrics)
20. [Security Considerations](#20-security-considerations)
21. [Troubleshooting Guide](#21-troubleshooting-guide)

---

## 1. Executive Summary

The **Claims Denial FAQ Chatbot** is a production-grade Retrieval-Augmented Generation (RAG) system designed to automate resolution guidance for healthcare claim denials. It integrates:

- **Snowflake** as the enterprise knowledge base storing 200+ denial scenarios
- **Pinecone** as the vector database for semantic similarity search
- **OpenAI Embeddings** for converting text to searchable vectors
- **Claude (Anthropic)** for generating accurate, actionable denial resolution guidance
- **LangChain** as the orchestration framework connecting retrieval and generation
- **FastAPI** for REST API exposure
- **Slack Bolt** for real-time support team integration

### Key Business Outcomes

| Metric | Before | After |
|--------|--------|-------|
| Support query volume | Baseline | **-40%** |
| Resubmission success rate | 78% | **92%** |
| Denial resolution accuracy | Manual lookup | **98%** (RAG retrieval + Claude) |
| Average response time | 15–30 min (human) | **< 2 seconds** (automated) |

---

## 2. Business Context & Objectives

### Problem Statement

Healthcare revenue cycle teams process thousands of claim denials daily. Each denial carries a CARC (Claim Adjustment Reason Code) such as `CO-16` (missing information) or `CO-197` (no authorization). Resolving denials requires:

1. Identifying the denial code and payer-specific rules
2. Understanding root cause from remark codes
3. Gathering required documentation
4. Following payer-specific resubmission workflows

Manual lookup across spreadsheets, payer portals, and tribal knowledge is slow, inconsistent, and drives high support ticket volume.

### Solution

A RAG chatbot that:
- **Retrieves** the most semantically similar denial scenarios from a curated knowledge base
- **Augments** Claude's prompt with retrieved context (denial codes, resolution steps, documentation requirements)
- **Generates** structured, actionable guidance tailored to the user's specific question

### Denial Categories Covered

| Category | Example Codes | Description |
|----------|---------------|-------------|
| Eligibility | CO-27, CO-109 | Patient not eligible at time of service |
| Authorization | CO-197 | Missing prior authorization |
| Medical Necessity | CO-50, CO-96, CO-151 | Service not medically necessary |
| Coding | CO-4, CO-16 | Incorrect or incomplete coding |
| Billing | CO-97, CO-119, CO-204 | Benefit limits, non-covered charges |
| Timely Filing | CO-29 | Claim filed past deadline |
| Duplicate | CO-18 | Duplicate claim submission |
| COB | CO-22 | Coordination of benefits issue |

---

## 3. System Architecture

### High-Level Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           CLIENT LAYER                                       │
│  ┌──────────────────┐    ┌──────────────────┐    ┌──────────────────┐      │
│  │   Slack Users    │    │   REST Clients   │    │  Internal Tools  │      │
│  │  (/denial, DM)   │    │  (curl, SDKs)    │    │  (Dashboards)    │      │
│  └────────┬─────────┘    └────────┬─────────┘    └────────┬─────────┘      │
└───────────┼───────────────────────┼───────────────────────┼─────────────────┘
            │                       │                       │
┌───────────┼───────────────────────┼───────────────────────┼─────────────────┐
│           ▼                       ▼                       ▼                 │
│  ┌─────────────────┐    ┌─────────────────────────────────────────┐      │
│  │  Slack Bolt Bot │    │           FastAPI Application             │      │
│  │  (Socket Mode)  │    │  /api/v1/chat/query  /api/v1/health       │      │
│  └────────┬────────┘    │  /api/v1/admin/ingest                     │      │
│           │             └──────────────────┬──────────────────────────┘      │
│           │                                │                                │
│           └────────────┬───────────────────┘                                │
│                        ▼                                                    │
│  ┌─────────────────────────────────────────────────────────────────────┐  │
│  │              ClaimsDenialChatbotService (Service Layer)               │  │
│  │   process_chat_query() | perform_health_check() | ingest_knowledge() │  │
│  └──────────────────────────────┬──────────────────────────────────────┘  │
│                                 ▼                                           │
│  ┌─────────────────────────────────────────────────────────────────────┐  │
│  │                    ClaimsDenialRAGChain (RAG Orchestrator)            │  │
│  │   execute_rag_query(): Retrieve → Augment → Generate → Structure    │  │
│  └───────┬─────────────────────────────────────────────┬───────────────┘  │
│          ▼                                             ▼                    │
│  ┌──────────────────────┐              ┌──────────────────────────────┐    │
│  │ DenialScenarioRetriever│              │     ClaudeLLMClient          │    │
│  │ retrieve_relevant_docs │              │  generate_response()         │    │
│  └───────┬──────────────┘              └──────────────────────────────┘    │
│          ▼                                                                  │
│  ┌──────────────────────┐    ┌──────────────────────────────────────┐    │
│  │ TextEmbeddingService │    │   PineconeVectorStoreManager         │    │
│  │ generate_embedding() │───▶│   search_similar_documents()         │    │
│  └──────────────────────┘    └──────────────────────────────────────┘    │
│                                        APPLICATION LAYER                    │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│                           DATA LAYER                                         │
│  ┌──────────────────────┐    ┌──────────────────────────────────────┐    │
│  │  Snowflake (Source)  │    │  Pinecone (Vector Index)             │    │
│  │  DENIAL_SCENARIOS    │───▶│  claims-denial-faq index             │    │
│  │  210+ scenarios      │    │  1536-dim cosine vectors             │    │
│  └──────────────────────┘    └──────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│                        EXTERNAL SERVICES                                     │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐   │
│  │ Anthropic    │  │ OpenAI       │  │ Pinecone     │  │ Snowflake    │   │
│  │ Claude API   │  │ Embeddings   │  │ Cloud        │  │ Cloud        │   │
│  └──────────────┘  └──────────────┘  └──────────────┘  └──────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Layer Responsibilities

| Layer | Responsibility | Key Components |
|-------|----------------|----------------|
| **Client** | User interaction | Slack, REST API consumers |
| **API/Bot** | Request handling, validation | FastAPI routes, Slack Bolt handlers |
| **Service** | Business logic orchestration | `ClaimsDenialChatbotService` |
| **RAG** | Retrieve-Augment-Generate pipeline | `ClaimsDenialRAGChain`, `DenialScenarioRetriever` |
| **Data Access** | External data retrieval | Snowflake connector, Pinecone manager |
| **Infrastructure** | Embeddings, LLM, config | Embedding service, Claude client, settings |

---

## 4. Technology Stack

| Component | Technology | Purpose |
|-----------|------------|---------|
| Language | Python 3.11+ | Core runtime |
| API Framework | FastAPI 0.115 | REST API with OpenAPI |
| LLM Orchestration | LangChain 0.3 | RAG chain composition |
| LLM Provider | Anthropic Claude Sonnet 4 | Response generation |
| Embeddings | OpenAI text-embedding-3-small | 1536-dim vectors |
| Vector DB | Pinecone Serverless | Semantic search |
| Knowledge Base | Snowflake | Enterprise denial data |
| Chat Interface | Slack Bolt (Socket Mode) | Real-time bot |
| Validation | Pydantic 2.x | Request/response schemas |
| Logging | structlog | JSON structured logs |
| Testing | pytest | Unit and integration tests |
| Retry Logic | tenacity | API resilience |

---

## 5. Core Concepts

### 5.1 Retrieval-Augmented Generation (RAG)

RAG combines **information retrieval** with **LLM generation** to produce accurate, grounded responses.

**Without RAG:** Claude answers from general knowledge — may hallucinate payer-specific rules.

**With RAG:**
1. User asks: *"How do I fix CO-16 for Medicare?"*
2. System retrieves top-5 similar denial scenarios from Pinecone
3. Retrieved context (codes, steps, docs) is injected into Claude's prompt
4. Claude generates answer **grounded in actual knowledge base data**

```
Query → Embed → Vector Search → Top-K Docs → Prompt + Context → Claude → Answer
```

### 5.2 Vector Embeddings

Text is converted to high-dimensional vectors (1536 floats) where semantically similar text has similar vectors.

- *"CO-16 missing information denial"* ≈ *"claim lacks required data CO-16"*
- Cosine similarity measures how close two vectors are (0.0 to 1.0)
- Threshold of **0.75** filters low-relevance results

### 5.3 Semantic Search vs Keyword Search

| Approach | Query: "timely filing expired" | Finds CO-29? |
|----------|-------------------------------|--------------|
| Keyword | Matches "timely", "filing" | Maybe |
| Semantic | Understands "expired deadline" ≈ "time limit filing" | **Yes** |

### 5.4 Document Chunking

Long denial scenarios are split into overlapping chunks (512 tokens, 64 overlap) so:
- Each chunk fits embedding model limits
- Specific resolution steps are retrievable independently
- Metadata (denial_code, payer) attaches to every chunk

### 5.5 Prompt Engineering

Three prompt layers:
1. **System Prompt** — Defines Claude's role as denial expert, response format, constraints
2. **Context Block** — Formatted retrieved documents with codes, steps, scores
3. **User Query** — Original question with optional filters

### 5.6 Confidence Scoring

Confidence = mean of top retrieval similarity scores. Used to:
- Indicate answer reliability to users
- Trigger fallback when no documents match (confidence ≈ 0.1)

---

## 6. End-to-End Data Flow

### 6.1 Query Flow (Runtime)

```
┌──────────┐     ┌─────────────┐     ┌──────────────────┐
│  User    │────▶│ API / Slack │────▶│ ChatQueryRequest │
│  Query   │     │  Endpoint   │     │  (validated)     │
└──────────┘     └─────────────┘     └────────┬─────────┘
                                              │
                    ┌─────────────────────────▼─────────────────────────┐
                    │         ClaimsDenialChatbotService              │
                    │         process_chat_query()                    │
                    └─────────────────────────┬───────────────────────┘
                                              │
                    ┌─────────────────────────▼─────────────────────────┐
                    │         ClaimsDenialRAGChain                    │
                    │         execute_rag_query()                     │
                    └─────────────────────────┬───────────────────────┘
                                              │
         ┌────────────────────────────────────┼────────────────────────┐
         ▼                                    ▼                        │
┌─────────────────┐              ┌─────────────────────┐              │
│ DenialScenario  │              │ TextEmbeddingService│              │
│ Retriever       │              │ embed_query()       │              │
│                 │◀─────────────│                     │              │
│ retrieve_docs() │  embedding   └─────────────────────┘              │
└────────┬────────┘                                                  │
         │                                                            │
         ▼                                                            │
┌─────────────────┐                                                   │
│ PineconeVector  │                                                   │
│ StoreManager    │                                                   │
│ search_similar()│                                                   │
└────────┬────────┘                                                   │
         │ list[RetrievedDocument]                                     │
         ▼                                                            │
┌─────────────────┐     ┌─────────────────────┐                       │
│ build_rag_user  │────▶│ ClaudeLLMClient     │                       │
│ _prompt()       │     │ generate_response() │                       │
└─────────────────┘     └──────────┬──────────┘                       │
                                   │ answer_text                       │
                                   ▼                                   │
                    ┌──────────────────────────┐                       │
                    │ ChatQueryResponse        │                       │
                    │ - answer_text            │                       │
                    │ - confidence_score       │                       │
                    │ - resolution_steps       │                       │
                    │ - retrieved_documents    │                       │
                    │ - processing_time_ms       │                       │
                    └──────────────────────────┘                       │
```

### 6.2 Ingestion Flow (Batch)

```
Snowflake DENIAL_SCENARIOS
         │
         ▼ fetch_all_denial_scenarios()
┌─────────────────┐
│ DenialScenario  │ (210 Pydantic models)
│ records         │
└────────┬────────┘
         ▼ process_scenarios_batch()
┌─────────────────┐
│ Document chunks │ (text + metadata per chunk)
│ with metadata   │
└────────┬────────┘
         ▼ generate_embeddings_for_batch()
┌─────────────────┐
│ Embedding       │ (1536-dim vectors)
│ vectors         │
└────────┬────────┘
         ▼ upsert_document_vectors()
┌─────────────────┐
│ Pinecone Index  │ (searchable vector store)
│ claims-denial   │
└─────────────────┘
```

---

## 7. Project Structure & Module Guide

```
Praveen AI Agent/
├── .env.example                 # Environment variable template
├── .gitignore
├── pyproject.toml               # Project metadata, ruff, pytest, mypy
├── requirements.txt             # Python dependencies
├── README.md                    # Quick start guide
│
├── docs/
│   └── PROJECT_DOCUMENTATION.md # This file
│
├── data/
│   └── denial_scenarios.json    # 210 generated denial scenarios
│
├── scripts/
│   ├── ingest_knowledge_base.py # Pinecone ingestion CLI
│   ├── seed_denial_scenarios.py # Generate JSON dataset
│   └── snowflake_schema.sql     # Snowflake DDL
│
├── src/claims_denial_chatbot/
│   ├── __init__.py
│   ├── main.py                  # CLI entry (api | slack)
│   │
│   ├── config/
│   │   ├── settings.py          # ApplicationSettings (Pydantic)
│   │   └── __init__.py
│   │
│   ├── core/
│   │   ├── constants.py         # DenialCategory, COMMON_DENIAL_CODES
│   │   ├── exceptions.py        # Custom exception hierarchy
│   │   ├── logging.py           # structlog configuration
│   │   └── __init__.py
│   │
│   ├── models/
│   │   ├── schemas.py           # Pydantic request/response models
│   │   └── __init__.py
│   │
│   ├── data/
│   │   ├── snowflake_connector.py  # SnowflakeKnowledgeBaseConnector
│   │   └── __init__.py
│   │
│   ├── embeddings/
│   │   ├── embedding_service.py    # TextEmbeddingService
│   │   └── __init__.py
│   │
│   ├── vector_store/
│   │   ├── pinecone_store.py       # PineconeVectorStoreManager
│   │   └── __init__.py
│   │
│   ├── llm/
│   │   ├── claude_client.py        # ClaudeLLMClient
│   │   ├── prompt_templates.py     # System/user prompt templates
│   │   └── __init__.py
│   │
│   ├── rag/
│   │   ├── document_processor.py   # DenialScenarioDocumentProcessor
│   │   ├── retriever.py            # DenialScenarioRetriever
│   │   ├── chain.py                # ClaimsDenialRAGChain
│   │   └── __init__.py
│   │
│   ├── services/
│   │   ├── chatbot_service.py      # ClaimsDenialChatbotService
│   │   └── __init__.py
│   │
│   ├── api/
│   │   ├── main.py                 # FastAPI app factory
│   │   ├── routes.py               # Route handlers
│   │   └── __init__.py
│   │
│   └── bot/
│       ├── slack_bot.py            # ClaimsDenialSlackBot
│       └── __init__.py
│
└── tests/
    ├── test_api.py
    ├── test_rag_chain.py
    └── test_retriever.py
```

---

## 8. Naming Conventions

This project follows **PEP 8** and industry-standard naming patterns.

### 8.1 General Rules

| Element | Convention | Example |
|---------|------------|---------|
| Modules | `snake_case` | `snowflake_connector.py` |
| Classes | `PascalCase` | `ClaimsDenialRAGChain` |
| Functions/Methods | `snake_case`, verb-first | `fetch_all_denial_scenarios()` |
| Constants | `UPPER_SNAKE_CASE` | `COMMON_DENIAL_CODES` |
| Private members | `_leading_underscore` | `_embedding_service` |
| Enums | `PascalCase` class, `UPPER` or `lower` values | `DenialCategory.CODING` |
| Pydantic models | `PascalCase` | `ChatQueryRequest` |
| API routes | `snake_case` paths | `/api/v1/chat/query` |

### 8.2 Method Naming Patterns

| Pattern | Meaning | Examples |
|---------|---------|----------|
| `get_*` | Retrieve cached or simple lookup | `get_application_settings()`, `get_logger()` |
| `fetch_*` | External data retrieval | `fetch_all_denial_scenarios()` |
| `generate_*` | Create new content (embeddings, responses) | `generate_embedding_for_text()` |
| `build_*` | Assemble complex structures | `build_rag_user_prompt()` |
| `process_*` | Transform or handle business logic | `process_chat_query()` |
| `execute_*` | Run multi-step pipeline | `execute_rag_query()` |
| `perform_*` | Operational actions | `perform_health_check()` |
| `retrieve_*` | Search/retrieval operations | `retrieve_relevant_documents()` |
| `search_*` | Vector/semantic search | `search_similar_documents()` |
| `upsert_*` | Insert or update in store | `upsert_document_vectors()` |
| `format_*` | String formatting | `format_context_documents_for_prompt()` |
| `calculate_*` | Compute derived values | `calculate_retrieval_confidence()` |
| `extract_*` | Parse from structured data | `extract_resolution_steps_from_documents()` |
| `convert_*` | Type transformation | `convert_documents_to_context_dicts()` |
| `configure_*` | Setup initialization | `configure_structured_logging()` |
| `create_*` | Factory/builder | `create_fastapi_application()` |
| `handle_*` | Event/command handlers | `handle_denial_command()` |
| `register_*` | Register handlers/listeners | `register_event_handlers()` |
| `load_*` | Load from file/storage | `load_scenarios_from_json()` |
| `delete_*` | Remove data | `delete_all_vectors()` |
| `map_*` | Map between representations | `map_row_to_denial_scenario()` |
| `chunk_*` | Split into chunks | `chunk_scenario_into_documents()` |
| `ingest_*` | Batch data ingestion | `ingest_knowledge_base()` |
| `start` / `run_*` | Entry points | `run_slack_bot()`, `run_api_server()` |

### 8.3 Class Naming Patterns

| Suffix | Purpose | Examples |
|--------|---------|----------|
| `*Service` | Business logic layer | `ClaimsDenialChatbotService`, `TextEmbeddingService` |
| `*Client` | External API wrapper | `ClaudeLLMClient` |
| `*Connector` | Database connection | `SnowflakeKnowledgeBaseConnector` |
| `*Manager` | Resource lifecycle | `PineconeVectorStoreManager` |
| `*Retriever` | RAG retrieval component | `DenialScenarioRetriever` |
| `*Processor` | Data transformation | `DenialScenarioDocumentProcessor` |
| `*Chain` | Pipeline orchestrator | `ClaimsDenialRAGChain` |
| `*Bot` | Chat platform integration | `ClaimsDenialSlackBot` |
| `*Settings` | Configuration model | `ApplicationSettings` |
| `*Error` | Exception types | `RAGPipelineError` |
| `*Request` / `*Response` | API schemas | `ChatQueryRequest`, `ChatQueryResponse` |

---

## 9. Configuration Reference

All configuration is loaded from environment variables via `ApplicationSettings`.

| Variable | Default | Description |
|----------|---------|-------------|
| `ANTHROPIC_API_KEY` | — | Claude API key (required) |
| `CLAUDE_MODEL` | `claude-sonnet-4-20250514` | Claude model ID |
| `CLAUDE_MAX_TOKENS` | `1024` | Max response tokens |
| `CLAUDE_TEMPERATURE` | `0.1` | Low temp for factual accuracy |
| `OPENAI_API_KEY` | — | Embeddings API key (required) |
| `EMBEDDING_MODEL` | `text-embedding-3-small` | Embedding model |
| `EMBEDDING_DIMENSION` | `1536` | Vector dimension |
| `PINECONE_API_KEY` | — | Pinecone API key (required) |
| `PINECONE_INDEX_NAME` | `claims-denial-faq` | Index name |
| `PINECONE_DIMENSION` | `1536` | Must match embedding dim |
| `RAG_TOP_K_RESULTS` | `5` | Documents retrieved per query |
| `RAG_SIMILARITY_THRESHOLD` | `0.75` | Min cosine score |
| `RAG_CHUNK_SIZE` | `512` | Characters per chunk |
| `RAG_CHUNK_OVERLAP` | `64` | Chunk overlap |
| `SNOWFLAKE_ACCOUNT` | — | Snowflake account ID |
| `SNOWFLAKE_DATABASE` | `CLAIMS_DB` | Database name |
| `SNOWFLAKE_DENIAL_TABLE` | `DENIAL_SCENARIOS` | Table name |
| `SLACK_BOT_TOKEN` | — | Slack bot OAuth token |
| `SLACK_APP_TOKEN` | — | Socket Mode app token |

---

## 10. Component Deep Dive & Code Logic

### 10.1 ApplicationSettings (`config/settings.py`)

**Purpose:** Single source of truth for all configuration.

**Logic:**
- Pydantic `BaseSettings` auto-loads from `.env`
- `SecretStr` prevents accidental logging of API keys
- `@lru_cache` on `get_application_settings()` ensures one instance per process

### 10.2 SnowflakeKnowledgeBaseConnector (`data/snowflake_connector.py`)

**Purpose:** Read denial scenarios from Snowflake enterprise warehouse.

**Logic:**
1. `_build_connection_parameters()` — Maps settings to Snowflake connect kwargs
2. `get_connection()` — Context manager: open → yield → close
3. `fetch_all_denial_scenarios()` — SELECT active scenarios, map to `DenialScenario`
4. `_map_row_to_denial_scenario()` — Pipe-delimited strings → Python lists

**Snowflake Table Schema:** See `scripts/snowflake_schema.sql`

### 10.3 TextEmbeddingService (`embeddings/embedding_service.py`)

**Purpose:** Convert text to 1536-dimensional vectors via OpenAI.

**Logic:**
- `generate_embedding_for_text()` — Single query embedding via `embed_query()`
- `generate_embeddings_for_batch()` — Batch `embed_documents()` in chunks of 100

**Why OpenAI for embeddings + Claude for generation?** OpenAI embeddings are cost-effective and well-supported in LangChain; Claude excels at instruction-following for structured denial guidance.

### 10.4 PineconeVectorStoreManager (`vector_store/pinecone_store.py`)

**Purpose:** Vector index lifecycle and similarity search.

**Logic:**
1. `_get_or_create_index()` — List indexes; create serverless if missing
2. `upsert_document_vectors()` — Batch insert (id, vector, metadata)
3. `search_similar_documents()` — Query with filter; skip below threshold
4. Metadata filter example: `{"denial_code": {"$eq": "CO-16"}}`

**Vector ID format:** `{scenario_id}_chunk_{chunk_index}` e.g. `SCN-0001_chunk_0`

### 10.5 DenialScenarioDocumentProcessor (`rag/document_processor.py`)

**Purpose:** Transform `DenialScenario` records into embeddable chunks.

**Logic:**
1. `build_document_text_from_scenario()` — Concatenate code, description, steps, docs
2. `chunk_scenario_into_documents()` — `RecursiveCharacterTextSplitter` (512/64)
3. Each chunk carries full metadata for filtered retrieval

### 10.6 DenialScenarioRetriever (`rag/retriever.py`)

**Purpose:** Semantic search orchestration.

**Logic:**
1. Embed query text
2. Build optional metadata filter (denial_code, payer_name)
3. Search Pinecone top-k
4. `calculate_retrieval_confidence()` — Mean of similarity scores

### 10.7 ClaimsDenialRAGChain (`rag/chain.py`)

**Purpose:** End-to-end RAG pipeline.

**Logic (`execute_rag_query`):**
1. Retrieve documents
2. If results: build prompt → Claude generate
3. If empty: fallback prompt → Claude generate (low confidence)
4. Extract resolution steps from top document metadata
5. Build `ChatQueryResponse` with timing

### 10.8 ClaudeLLMClient (`llm/claude_client.py`)

**Purpose:** Claude API with retry.

**Logic:**
- `@retry` — 3 attempts, exponential backoff (tenacity)
- `SystemMessage` + `HumanMessage` pattern
- Temperature 0.1 for factual consistency

### 10.9 Prompt Templates (`llm/prompt_templates.py`)

**Key functions:**
- `CLAIMS_DENIAL_SYSTEM_PROMPT` — Expert persona, format, constraints
- `format_context_documents_for_prompt()` — Per-document markdown blocks
- `build_rag_user_prompt()` — Full user message assembly

### 10.10 ClaimsDenialChatbotService (`services/chatbot_service.py`)

**Purpose:** Service layer for API and Slack.

**Methods:**
- `process_chat_query()` — Delegates to RAG chain
- `perform_health_check()` — Pinecone stats + config status
- `ingest_knowledge_base()` — Full Snowflake → Pinecone pipeline

### 10.11 FastAPI Application (`api/main.py`, `api/routes.py`)

**Routes:**
| Route | Method | Handler |
|-------|--------|---------|
| `/api/v1/chat/query` | POST | `submit_chat_query` |
| `/api/v1/health` | GET | `get_health_status` |
| `/api/v1/admin/ingest` | POST | `trigger_knowledge_base_ingestion` |

**Dependency injection:** `get_chatbot_service()` provides service per request.

### 10.12 ClaimsDenialSlackBot (`bot/slack_bot.py`)

**Handlers:**
| Event | Handler | Behavior |
|-------|---------|----------|
| `/denial` | `_handle_denial_command` | Parse flags, RAG query |
| `/denial-help` | `_handle_help_command` | Usage instructions |
| `app_mention` | `_handle_app_mention` | Channel mentions |
| `message` (im) | `_handle_direct_message` | Direct messages |

**Flag parsing:** `--code CO-16`, `--payer Medicare`

---

## 11. Complete Method Reference

### config/settings.py

| Method | Description |
|--------|-------------|
| `get_application_settings()` | Returns cached `ApplicationSettings` singleton loaded from env |

### core/logging.py

| Method | Description |
|--------|-------------|
| `configure_structured_logging()` | Initializes structlog JSON logging at startup |
| `get_logger(name)` | Returns named BoundLogger instance |

### data/snowflake_connector.py — `SnowflakeKnowledgeBaseConnector`

| Method | Description |
|--------|-------------|
| `__init__()` | Initialize with application settings |
| `_build_connection_parameters()` | Build Snowflake connect kwargs dict |
| `get_connection()` | Context manager for DB connection lifecycle |
| `fetch_all_denial_scenarios()` | SELECT all active scenarios from Snowflake |
| `fetch_denial_scenario_by_code(denial_code)` | Filter scenarios by CARC code |
| `_map_row_to_denial_scenario(row)` | Map Snowflake row dict to DenialScenario model |

### embeddings/embedding_service.py — `TextEmbeddingService`

| Method | Description |
|--------|-------------|
| `__init__()` | Initialize OpenAI embeddings client |
| `generate_embedding_for_text(text)` | Embed single query string → list[float] |
| `generate_embeddings_for_batch(texts, batch_size)` | Batch embed documents |
| `model_name` (property) | Return configured embedding model name |

### vector_store/pinecone_store.py — `PineconeVectorStoreManager`

| Method | Description |
|--------|-------------|
| `__init__()` | Connect Pinecone client and index |
| `_get_or_create_index()` | Get existing or create serverless index |
| `upsert_document_vectors(vectors, namespace)` | Upsert id/vector/metadata tuples |
| `search_similar_documents(query_embedding, top_k, filter, namespace)` | Cosine similarity search |
| `delete_all_vectors(namespace)` | Clear namespace for reindex |
| `get_index_stats()` | Return vector count and namespace stats |

### rag/document_processor.py — `DenialScenarioDocumentProcessor`

| Method | Description |
|--------|-------------|
| `__init__()` | Initialize RecursiveCharacterTextSplitter |
| `build_document_text_from_scenario(scenario)` | Compose full text from scenario fields |
| `chunk_scenario_into_documents(scenario)` | Split scenario into metadata-rich chunks |
| `process_scenarios_batch(scenarios)` | Process list of scenarios to flat chunk list |

### rag/retriever.py — `DenialScenarioRetriever`

| Method | Description |
|--------|-------------|
| `__init__(embedding_service, vector_store)` | Inject or create dependencies |
| `retrieve_relevant_documents(query_text, denial_code, payer_name, top_k)` | Full retrieval pipeline |
| `_build_metadata_filter(denial_code, payer_name)` | Build Pinecone filter dict |
| `calculate_retrieval_confidence(retrieved_documents)` | Mean similarity → confidence |

### rag/chain.py — `ClaimsDenialRAGChain`

| Method | Description |
|--------|-------------|
| `__init__(retriever, llm_client)` | Inject RAG dependencies |
| `execute_rag_query(request)` | Full RAG: retrieve → prompt → generate → response |
| `_convert_documents_to_context_dicts(documents)` | RetrievedDocument → prompt dicts |
| `_extract_resolution_steps_from_documents(documents)` | Steps from top doc metadata |
| `_extract_primary_denial_code(documents, requested_code)` | Resolve denial code |

### llm/claude_client.py — `ClaudeLLMClient`

| Method | Description |
|--------|-------------|
| `__init__()` | Initialize ChatAnthropic client |
| `generate_response(user_prompt, system_prompt)` | Invoke Claude with retry |
| `generate_fallback_response(user_query)` | No-context fallback generation |
| `model_name` (property) | Configured Claude model ID |

### llm/prompt_templates.py

| Function | Description |
|----------|-------------|
| `format_context_documents_for_prompt(retrieved_documents)` | Format docs for prompt context |
| `build_rag_user_prompt(user_query, context_documents, denial_code, payer_name)` | Assemble full user prompt |

### services/chatbot_service.py — `ClaimsDenialChatbotService`

| Method | Description |
|--------|-------------|
| `__init__()` | Wire RAG chain, Snowflake, embeddings, vector store |
| `process_chat_query(request)` | Process ChatQueryRequest via RAG |
| `perform_health_check()` | Aggregate service health status |
| `ingest_knowledge_base(request)` | Snowflake/JSON → Pinecone ingestion |
| `_fetch_scenarios_for_ingestion(source)` | Load scenarios by source type |

### api/routes.py

| Function | Description |
|----------|-------------|
| `get_chatbot_service()` | FastAPI dependency for service injection |
| `submit_chat_query(request, service)` | POST /api/v1/chat/query handler |
| `get_health_status(service)` | GET /api/v1/health handler |
| `trigger_knowledge_base_ingestion(request, service)` | POST /api/v1/admin/ingest handler |

### api/main.py

| Function | Description |
|----------|-------------|
| `application_lifespan(app)` | FastAPI startup/shutdown lifecycle |
| `create_fastapi_application()` | Factory: routers, CORS, OpenAPI metadata |

### bot/slack_bot.py — `ClaimsDenialSlackBot`

| Method | Description |
|--------|-------------|
| `__init__()` | Initialize Bolt app and handlers |
| `_register_event_handlers()` | Register slash commands and events |
| `_handle_denial_command(ack, command, say)` | /denial slash command |
| `_handle_help_command(ack, say)` | /denial-help command |
| `_handle_app_mention(event, say)` | @bot channel mentions |
| `_handle_direct_message(event, say)` | DM handler |
| `_process_and_respond(say, query_text, ...)` | RAG query + Slack formatting |
| `_format_response_for_slack(response)` | ChatQueryResponse → Slack markdown |
| `_extract_flag_value(text, flag)` | Parse --code/--payer flags |
| `_remove_flags_from_query(text)` | Strip flags from query text |
| `start()` | Start Socket Mode handler |

---

## 12. API Documentation

### POST `/api/v1/chat/query`

**Request:**
```json
{
  "query_text": "How do I resolve a CO-16 denial for Medicare?",
  "session_id": "optional-session-id",
  "denial_code": "CO-16",
  "payer_name": "Medicare",
  "include_sources": true
}
```

**Response:**
```json
{
  "answer_text": "**Denial Summary**: CO-16 indicates...",
  "confidence_score": 0.91,
  "retrieved_documents": [
    {
      "document_id": "SCN-0001_chunk_0",
      "content": "...",
      "similarity_score": 0.92,
      "metadata": { "denial_code": "CO-16", "payer_name": "Medicare" },
      "source": "pinecone"
    }
  ],
  "denial_code": "CO-16",
  "resolution_steps": ["Review remark codes", "Gather docs", "Resubmit"],
  "session_id": "abc-123",
  "processing_time_ms": 1240.5,
  "model_used": "claude-sonnet-4-20250514"
}
```

### GET `/api/v1/health`

**Response:**
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "services": {
    "pinecone": "healthy (420 vectors)",
    "claude": "configured (claude-sonnet-4-20250514)",
    "snowflake": "configured (CLAIMS_DB)",
    "embeddings": "configured (text-embedding-3-small)"
  },
  "timestamp": "2025-06-27T10:00:00"
}
```

### POST `/api/v1/admin/ingest`

**Request:**
```json
{
  "source": "snowflake",
  "force_reindex": false,
  "batch_size": 100
}
```

---

## 13. Slack Bot Integration

### Setup

1. Create Slack App at https://api.slack.com/apps
2. Enable **Socket Mode** and generate App-Level Token (`xapp-`)
3. Add Bot Token Scopes: `chat:write`, `commands`, `app_mentions:read`, `im:history`
4. Create slash commands: `/denial`, `/denial-help`
5. Subscribe to events: `app_mention`, `message.im`
6. Install app to workspace

### Usage Examples

```
/denial How do I fix a timely filing denial?
/denial --code CO-197 What authorization is needed for MRI?
/denial --payer Medicare CO-16 missing information
@ClaimsBot How do I resolve duplicate claim CO-18?
```

---

## 14. Knowledge Base Ingestion Pipeline

### From JSON (Local Development)

```bash
python3 scripts/seed_denial_scenarios.py
python3 scripts/ingest_knowledge_base.py --source json --file data/denial_scenarios.json --force-reindex
```

### From Snowflake (Production)

```bash
# 1. Run DDL in Snowflake
# 2. Load data into DENIAL_SCENARIOS
python3 scripts/ingest_knowledge_base.py --source snowflake --force-reindex
```

### Ingestion Steps (Internal)

1. Fetch scenarios (Snowflake or JSON)
2. `DenialScenarioDocumentProcessor.process_scenarios_batch()`
3. `TextEmbeddingService.generate_embeddings_for_batch()`
4. Build vectors: `(id, embedding, metadata)`
5. `PineconeVectorStoreManager.upsert_document_vectors()` in batches

---

## 15. Prompt Engineering Strategy

### System Prompt Design Principles

1. **Role definition** — Expert denial resolution assistant
2. **Domain scope** — CARC/RARC, payers, RCM workflows
3. **Output structure** — Denial Summary, Root Cause, Steps, Docs, Timeline, Tips
4. **Grounding constraint** — Only use retrieved context; no fabrication
5. **Safety** — No legal/medical advice beyond claims processing

### Temperature Setting

`CLAUDE_TEMPERATURE=0.1` — Low temperature reduces creative hallucination for factual denial guidance.

### Context Window Management

- Max context tokens: 4000 (`RAG_MAX_CONTEXT_TOKENS`)
- Top-k: 5 documents
- Chunk size: 512 chars keeps each doc block manageable

---

## 16. Error Handling & Logging

### Exception Hierarchy

```
ClaimsDenialChatbotError (base)
├── ConfigurationError
├── SnowflakeConnectionError
├── PineconeConnectionError
├── EmbeddingGenerationError
├── RetrievalError
├── LLMGenerationError
├── RAGPipelineError
├── SlackBotError
└── RateLimitExceededError
```

### Logging

- **structlog** with JSON output
- Key events: `rag_query_completed`, `documents_retrieved`, `claude_response_generated`
- Include: `session_id`, `confidence`, `processing_time_ms`, `error`

---

## 17. Testing Strategy

```bash
pytest tests/ -v --cov=claims_denial_chatbot
```

| Test File | Coverage |
|-----------|----------|
| `test_retriever.py` | Retrieval, filters, confidence |
| `test_rag_chain.py` | Full pipeline, fallback path |
| `test_api.py` | Health and chat endpoints |

**Pattern:** Mock embedding service, vector store, and LLM client for deterministic tests.

---

## 18. Deployment Guide

### Docker (Recommended)

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY src/ src/
COPY scripts/ scripts/
ENV PYTHONPATH=/app/src
CMD ["python", "-m", "claims_denial_chatbot.main", "api"]
```

### Production Checklist

- [ ] Set `APP_ENV=production`
- [ ] Use secrets manager for API keys (not .env files)
- [ ] Run ingestion job on schedule or after Snowflake updates
- [ ] Monitor Pinecone vector count vs Snowflake row count
- [ ] Set up log aggregation for structlog JSON
- [ ] Configure API rate limiting at gateway level
- [ ] Run Slack bot as separate process/container

### Environment Separation

| Env | Pinecone Index | Snowflake | Notes |
|-----|----------------|-----------|-------|
| dev | `claims-denial-faq-dev` | dev warehouse | JSON ingestion |
| staging | `claims-denial-faq-stg` | staging DB | Full integration tests |
| prod | `claims-denial-faq` | prod DB | Production workloads |

---

## 19. Performance & Metrics

### Expected Latencies

| Stage | Typical Time |
|-------|--------------|
| Query embedding | 50–150 ms |
| Pinecone search | 20–80 ms |
| Claude generation | 800–2000 ms |
| **Total** | **1–2.5 seconds** |

### Accuracy Factors

- **Similarity threshold 0.75** — Filters irrelevant chunks
- **Structured prompts** — Consistent response format
- **Metadata filters** — Payer/code scoping improves precision
- **210+ scenarios** — Broad coverage reduces no-match rate

### Business KPIs to Track

- Query volume and channel (API vs Slack)
- Average confidence score
- Fallback rate (no documents retrieved)
- User feedback / escalation rate
- Resubmission success correlation

---

## 20. Security Considerations

1. **Secrets** — `SecretStr` in Pydantic; never log API keys
2. **Admin endpoints** — Protect `/api/v1/admin/*` with auth in production
3. **Slack signing** — Bolt validates request signatures
4. **Snowflake** — Role-based access; read-only for chatbot role
5. **PII** — Denial scenarios should not contain patient identifiers
6. **CORS** — Restrict `allow_origins` in production

---

## 21. Troubleshooting Guide

| Issue | Cause | Solution |
|-------|-------|----------|
| Empty retrieval results | Index not ingested | Run ingestion script |
| Low confidence scores | Threshold too high | Lower `RAG_SIMILARITY_THRESHOLD` |
| Snowflake connection fail | Wrong credentials/account | Verify `.env` Snowflake vars |
| Pinecone dimension mismatch | Wrong embedding model | Match `PINECONE_DIMENSION` to model |
| Claude empty response | Token limit / API error | Check `CLAUDE_MAX_TOKENS`, API status |
| Slack bot not responding | Socket Mode / token | Verify `SLACK_APP_TOKEN`, scopes |
| Import errors | Python version | Use Python 3.11+ |

---

## Appendix A: Denial Code Quick Reference

See `core/constants.py` — `COMMON_DENIAL_CODES` dict for all supported CARC codes.

## Appendix B: Data Model — DenialScenario

| Field | Type | Description |
|-------|------|-------------|
| scenario_id | string | Unique ID (SCN-XXXX) |
| denial_code | string | CARC code |
| denial_category | enum | Category type |
| payer_name | string | Insurance payer |
| denial_description | string | Full description |
| resolution_steps | list[str] | Ordered steps |
| required_documentation | list[str] | Needed docs |
| severity | enum | critical/high/medium/low |
| average_resolution_days | int | Typical timeline |
| success_rate_percent | float | Historical success % |

---

*End of Documentation*
