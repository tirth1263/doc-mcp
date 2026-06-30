---
title: Doc-MCP Documentation RAG System
emoji: 📚
colorFrom: indigo
colorTo: purple
sdk: gradio
sdk_version: "5.34.2"
app_file: app.py
pinned: true
license: mit
short_description: GitHub docs into queryable RAG knowledge bases
---

# Doc-MCP — Documentation RAG System

<div align="center">

![Doc-MCP Banner](https://img.shields.io/badge/Doc--MCP-Documentation%20RAG%20System-6366f1?style=for-the-badge&logo=bookstack&logoColor=white)

[![Python](https://img.shields.io/badge/Python-3.13+-3776AB?style=flat-square&logo=python&logoColor=white)](https://python.org)
[![Gradio](https://img.shields.io/badge/Gradio-5.0+-FF7C00?style=flat-square&logo=gradio&logoColor=white)](https://gradio.app)
[![MongoDB Atlas](https://img.shields.io/badge/MongoDB%20Atlas-Vector%20Search-00ED64?style=flat-square&logo=mongodb&logoColor=white)](https://www.mongodb.com/atlas)
[![Nebius AI](https://img.shields.io/badge/Nebius%20AI-Embeddings%20%26%20LLM-7C3AED?style=flat-square)](https://nebius.com)
[![MCP](https://img.shields.io/badge/MCP-Compatible-0EA5E9?style=flat-square)](https://modelcontextprotocol.io)
[![License](https://img.shields.io/badge/License-MIT-green?style=flat-square)](LICENSE)

**Transform any GitHub documentation repository into an intelligent, queryable knowledge base — in minutes.**

[Live Demo](https://huggingface.co/spaces/tirth2101/doc-mcp) · [Report Bug](https://github.com/tirth1263/doc-mcp/issues) · [Request Feature](https://github.com/tirth1263/doc-mcp/issues)

</div>

---

## What is Doc-MCP?

Doc-MCP is an open-source **Retrieval-Augmented Generation (RAG)** system purpose-built for software documentation. Point it at any public GitHub repository, and within minutes you can ask natural language questions and receive precise, cited answers — all powered by state-of-the-art vector embeddings and large language models.

It also exposes its search capabilities as **MCP (Model Context Protocol)** tools, meaning any MCP-compatible AI assistant (like Claude Desktop) can query your documentation knowledge base directly, without manual copy-paste.

---

## Features

| Feature | Description |
|---------|-------------|
| **Semantic Search** | Find answers across thousands of docs using natural language — no keyword matching required |
| **AI-Powered Q&A** | Get intelligent, contextual responses with exact source file citations |
| **Batch Processing** | Ingest entire repositories with real-time progress tracking |
| **Incremental Updates** | SHA-based change detection — only re-embeds files that actually changed |
| **Repository Management** | Full CRUD: view stats, delete repositories, manage ingested content |
| **MCP Integration** | Expose documentation search as tools for any MCP-compatible AI agent |
| **Gradio Web UI** | Clean, intuitive browser interface — no CLI knowledge required |

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        Gradio Web UI                        │
│   (Ingestion Tab | Q&A Tab | Management Tab | MCP Info)     │
└─────────────────┬───────────────────────────────────────────┘
                  │
         ┌────────▼────────┐
         │  GitHub Loader  │  ← Async file fetching with rate-limit handling
         └────────┬────────┘
                  │ Markdown files
         ┌────────▼────────┐
         │  Text Chunker   │  ← Header-aware recursive splitting (CHUNK_SIZE=3072)
         └────────┬────────┘
                  │ Text chunks
         ┌────────▼────────┐
         │   Nebius AI     │  ← BAAI/bge-en-icl embeddings (4096 dims)
         │   Embeddings    │
         └────────┬────────┘
                  │ Vectors
         ┌────────▼────────┐
         │  MongoDB Atlas  │  ← Vector Search index (cosine similarity)
         │  Vector Store   │
         └────────┬────────┘
                  │ Top-K results
         ┌────────▼────────┐
         │   Nebius LLM    │  ← Meta-Llama-3.1-70B-Instruct
         │  (Answer Gen)   │
         └─────────────────┘
```

---

## Quick Start

### Prerequisites

- Python 3.13+
- [MongoDB Atlas](https://www.mongodb.com/atlas) account with **Vector Search** enabled
- [Nebius AI](https://nebius.com) API key (for embeddings + LLM)
- GitHub Personal Access Token (optional — increases rate limit from 60 to 5,000 req/hr)

### Installation

```bash
# Clone the repository
git clone https://github.com/tirth1263/doc-mcp.git
cd doc-mcp

# Create virtual environment
python -m venv .venv
source .venv/bin/activate      # Linux/Mac
# .venv\Scripts\activate       # Windows

# Install dependencies
pip install -r requirements.txt
```

### Configuration

```bash
# Copy environment template
cp .env.example .env
```

Edit `.env` with your credentials:

```env
# Required
NEBIUS_API_KEY=your_nebius_api_key_here
MONGODB_URI=mongodb+srv://username:password@cluster.mongodb.net/

# Optional
GITHUB_API_KEY=your_github_token_here
CHUNK_SIZE=3072
SIMILARITY_TOP_K=5
GITHUB_CONCURRENT_REQUESTS=10
```

### MongoDB Atlas Setup

1. Create a free cluster at [cloud.mongodb.com](https://cloud.mongodb.com)
2. Enable **Vector Search** in your cluster
3. Run the database setup script:

```bash
python scripts/db_setup.py setup
```

This automatically creates:
- `doc_rag` — document chunks with embeddings
- `ingested_repos` — repository metadata
- Vector search index on the `embedding` field

### Launch

```bash
python main.py
```

Visit **http://localhost:7860** to access the web interface.

MCP SSE endpoint: **http://127.0.0.1:7860/gradio_api/mcp/sse**

---

## Usage Guide

### 1. Ingest Documentation

1. Navigate to the **📥 Documentation Ingestion** tab
2. Enter a GitHub repository URL:
   - `langchain-ai/langchain`
   - `https://github.com/facebook/react`
   - `owner/repo`
3. Click **Load Files** — the system fetches the full file tree
4. Select which markdown files to include
5. Click **Ingest Selected Files** — watch the progress bar as files are chunked and embedded

### 2. Ask Questions

1. Go to the **🤖 AI Documentation Assistant** tab
2. Select your ingested repository from the dropdown
3. Type any natural language question
4. Get an AI-generated answer with source file citations

**Example questions:**
- *"How do I set up authentication?"*
- *"What are the available configuration options?"*
- *"Show me an example of streaming responses"*
- *"What's the difference between X and Y?"*

### 3. Manage Repositories

Use the **🗂️ Repository Management** tab to:
- View statistics (file count, chunk count, last ingested date)
- Delete repositories to free up storage
- Refresh the repository list

---

## MCP Integration

Connect any MCP-compatible AI assistant to query your documentation:

### Claude Desktop Configuration

Add to your `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "doc-mcp": {
      "url": "http://127.0.0.1:7860/gradio_api/mcp/sse"
    }
  }
}
```

### Available MCP Tools

#### `search_documentation`
Semantic similarity search across ingested documentation.

```json
{
  "repo": "langchain-ai/langchain",
  "query": "how to use memory in chains",
  "top_k": 5
}
```

#### `ask_documentation`
AI-powered Q&A with source citations.

```json
{
  "repo": "langchain-ai/langchain",
  "question": "What is the difference between LLMChain and ConversationChain?"
}
```

#### `list_available_repos`
List all ingested repositories.

```json
{}
```

---

## Configuration Reference

| Variable | Default | Description |
|----------|---------|-------------|
| `NEBIUS_API_KEY` | — | **Required.** Nebius AI API key |
| `MONGODB_URI` | — | **Required.** MongoDB Atlas connection string |
| `GITHUB_API_KEY` | — | Optional. GitHub token for higher rate limits |
| `CHUNK_SIZE` | `3072` | Maximum characters per text chunk |
| `SIMILARITY_TOP_K` | `5` | Number of chunks retrieved per query |
| `GITHUB_CONCURRENT_REQUESTS` | `10` | Parallel GitHub API requests |

---

## Project Structure

```
doc-mcp/
├── app.py                  # Hugging Face Spaces entry point
├── main.py                 # Local development entry point
├── requirements.txt
├── .env.example
├── scripts/
│   └── db_setup.py         # Database initialization & status utility
└── src/
    ├── config.py           # Environment & constants
    ├── github_loader.py    # Async GitHub file fetching
    ├── embeddings.py       # Nebius embeddings + LLM answer generation
    ├── vector_store.py     # MongoDB Atlas vector operations
    ├── mcp_server.py       # MCP tool definitions
    └── ui.py               # Gradio web interface
```

---

## Troubleshooting

**Rate limit errors from GitHub**
> Add a `GITHUB_API_KEY` to your `.env`. Authenticated requests get 5,000/hr vs 60/hr unauthenticated.

**No results returned from search**
> The MongoDB Atlas Vector Search index may still be building (can take 2-5 minutes after first setup). Check status with:
> ```bash
> python scripts/db_setup.py status
> ```

**Memory / OOM errors during ingestion**
> Reduce `CHUNK_SIZE` in your `.env` (e.g., `CHUNK_SIZE=1024`).

**MongoDB connection errors**
> 1. Verify your IP is whitelisted in Atlas Network Access
> 2. Confirm Vector Search is enabled on your cluster tier (M10+)
> 3. Double-check the connection string format in `.env`

**Embedding API errors**
> Verify your `NEBIUS_API_KEY` is valid and has sufficient credits.

---

## Tech Stack

| Component | Technology |
|-----------|-----------|
| Web UI | [Gradio 5](https://gradio.app) |
| Embeddings | [BAAI/bge-en-icl](https://huggingface.co/BAAI/bge-en-icl) via Nebius AI |
| LLM | [Meta-Llama-3.1-70B-Instruct](https://huggingface.co/meta-llama/Meta-Llama-3.1-70B-Instruct) via Nebius AI |
| Vector DB | [MongoDB Atlas Vector Search](https://www.mongodb.com/products/platform/atlas-vector-search) |
| GitHub API | [aiohttp](https://docs.aiohttp.org/) (async) |
| Protocol | [Model Context Protocol (MCP)](https://modelcontextprotocol.io) |

---

## Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## License

Distributed under the MIT License. See [`LICENSE`](LICENSE) for details.

---

<div align="center">

Built with Python, Gradio, MongoDB Atlas, and Nebius AI

[⬆ Back to top](#doc-mcp--documentation-rag-system)

</div>
