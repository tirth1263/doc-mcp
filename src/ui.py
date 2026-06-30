import gradio as gr
from src.github_loader import GitHubLoader, parse_repo_url
from src.embeddings import embed_texts, generate_answer, chunk_text
from src.vector_store import (
    get_db, ensure_vector_index, upsert_chunks, upsert_repo_meta,
    list_repos, delete_repo, vector_search, get_file_shas, get_repo_stats,
    delete_file_chunks,
)

loader = GitHubLoader()


# ── Ingestion helpers ──────────────────────────────────────────────────────────

def load_repo_files(repo_url: str):
    """Step 1: List markdown files from a GitHub repo."""
    if not repo_url.strip():
        return gr.update(choices=[], value=[]), "Please enter a repository URL."
    try:
        owner, repo = parse_repo_url(repo_url)
        files = loader.list_markdown_files_sync(owner, repo)
        if not files:
            return gr.update(choices=[], value=[]), f"No markdown files found in {owner}/{repo}."
        choices = [f["path"] for f in files]
        msg = f"Found **{len(choices)}** markdown files in `{owner}/{repo}`. Select files to ingest."
        return gr.update(choices=choices, value=choices), msg
    except Exception as e:
        return gr.update(choices=[], value=[]), f"Error: {e}"


def ingest_files(repo_url: str, selected_files: list[str], progress=gr.Progress()):
    """Step 2: Fetch, chunk, embed and store selected files."""
    if not repo_url.strip():
        return "Please enter a repository URL."
    if not selected_files:
        return "Please select at least one file."
    try:
        owner, repo = parse_repo_url(repo_url)
        repo_id = f"{owner}/{repo}"
        db = get_db()
        ensure_vector_index(db)

        existing_shas = get_file_shas(db, repo_id)
        all_file_infos = loader.list_markdown_files_sync(owner, repo)
        to_fetch = [fi for fi in all_file_infos if fi["path"] in selected_files]

        # Filter unchanged files
        changed = [fi for fi in to_fetch if existing_shas.get(fi["path"]) != fi.get("sha", "")]
        skipped = len(to_fetch) - len(changed)

        if not changed:
            return f"All {skipped} selected files are already up-to-date. Nothing to ingest."

        progress(0, desc="Fetching files from GitHub...")
        fetched = loader.fetch_files_sync(owner, repo, changed)

        total = len(fetched)
        ingested = 0
        for i, file in enumerate(fetched):
            progress((i + 1) / total, desc=f"Embedding {file.path}...")
            chunks = chunk_text(file.content)
            if not chunks:
                continue
            embeddings = embed_texts(chunks)
            delete_file_chunks(db, repo_id, file.path)
            upsert_chunks(db, repo_id, file.path, chunks, embeddings, file.sha, file.url)
            ingested += 1

        upsert_repo_meta(db, repo_id, owner, len(selected_files))
        return (
            f"Ingestion complete for `{repo_id}`.\n\n"
            f"- Files ingested: **{ingested}**\n"
            f"- Files skipped (unchanged): **{skipped}**\n"
            f"- Total selected: **{len(selected_files)}**"
        )
    except Exception as e:
        return f"Ingestion error: {e}"


# ── Q&A helpers ───────────────────────────────────────────────────────────────

def get_repo_choices():
    try:
        db = get_db()
        repos = list_repos(db)
        return [r["repo"] for r in repos]
    except Exception:
        return []


def answer_question(repo: str, question: str, progress=gr.Progress()):
    if not repo:
        return "Please select a repository.", ""
    if not question.strip():
        return "Please enter a question.", ""
    try:
        progress(0.2, desc="Generating query embedding...")
        db = get_db()
        embeddings = embed_texts([question])
        if not embeddings:
            return "Failed to generate embedding.", ""

        progress(0.5, desc="Searching documentation...")
        results = vector_search(db, repo, embeddings[0])
        if not results:
            return "No relevant documentation found. Try rephrasing or ingesting more files.", ""

        progress(0.8, desc="Generating answer...")
        answer = generate_answer(question, results)

        sources_md = "\n".join(
            f"- [{r['path']}]({r['url']}) — score: {r['score']:.3f}"
            for r in results if r.get("url")
        )
        return answer, sources_md
    except Exception as e:
        return f"Error: {e}", ""


# ── Repo management ───────────────────────────────────────────────────────────

def refresh_repo_list():
    choices = get_repo_choices()
    return gr.update(choices=choices, value=choices[0] if choices else None)


def show_repo_stats(repo: str):
    if not repo:
        return "Select a repository."
    try:
        db = get_db()
        stats = get_repo_stats(db, repo)
        last = stats["last_ingested"].strftime("%Y-%m-%d %H:%M UTC") if stats.get("last_ingested") else "Unknown"
        return (
            f"**Repository:** `{repo}`\n\n"
            f"- Files indexed: **{stats['file_count']}**\n"
            f"- Total chunks: **{stats['total_chunks']}**\n"
            f"- Last ingested: **{last}**"
        )
    except Exception as e:
        return f"Error: {e}"


def delete_repo_action(repo: str):
    if not repo:
        return "Select a repository to delete.", gr.update()
    try:
        db = get_db()
        delete_repo(db, repo)
        choices = get_repo_choices()
        return f"Repository `{repo}` deleted successfully.", gr.update(choices=choices, value=None)
    except Exception as e:
        return f"Error deleting repo: {e}", gr.update()


# ── Gradio UI ─────────────────────────────────────────────────────────────────

def build_ui():
    with gr.Blocks(
        title="Doc-MCP: Documentation RAG System",
        theme=gr.themes.Soft(primary_hue="indigo", secondary_hue="slate"),
        css="""
        .header-text { text-align: center; margin-bottom: 1rem; }
        .status-box { background: #f0f4ff; border-radius: 8px; padding: 12px; }
        footer { display: none !important; }
        """,
    ) as demo:
        gr.Markdown(
            """
# Doc-MCP: Documentation RAG System
**Transform GitHub documentation repositories into intelligent, queryable knowledge bases.**

> Powered by **Nebius AI** embeddings · **MongoDB Atlas** vector search · **MCP**-compatible tools
""",
            elem_classes="header-text",
        )

        with gr.Tabs():
            # ── Tab 1: Ingestion ────────────────────────────────────────────
            with gr.TabItem("📥 Documentation Ingestion"):
                gr.Markdown("### Step 1 — Load repository files")
                with gr.Row():
                    repo_url_input = gr.Textbox(
                        label="GitHub Repository",
                        placeholder="e.g. langchain-ai/langchain  or  https://github.com/owner/repo",
                        scale=4,
                    )
                    load_btn = gr.Button("Load Files", variant="primary", scale=1)

                load_status = gr.Markdown()
                file_selector = gr.CheckboxGroup(label="Select files to ingest", choices=[], interactive=True)

                gr.Markdown("### Step 2 — Generate embeddings & store")
                ingest_btn = gr.Button("Ingest Selected Files", variant="primary")
                ingest_status = gr.Markdown()

                load_btn.click(load_repo_files, inputs=repo_url_input, outputs=[file_selector, load_status])
                ingest_btn.click(ingest_files, inputs=[repo_url_input, file_selector], outputs=ingest_status)

            # ── Tab 2: Q&A ──────────────────────────────────────────────────
            with gr.TabItem("🤖 AI Documentation Assistant"):
                with gr.Row():
                    repo_select = gr.Dropdown(
                        label="Repository",
                        choices=get_repo_choices(),
                        interactive=True,
                        scale=3,
                    )
                    refresh_btn = gr.Button("🔄 Refresh", scale=1)

                question_input = gr.Textbox(
                    label="Ask a question",
                    placeholder="How do I configure authentication?",
                    lines=3,
                )
                ask_btn = gr.Button("Ask", variant="primary")

                with gr.Row():
                    with gr.Column(scale=2):
                        answer_output = gr.Markdown(label="Answer")
                    with gr.Column(scale=1):
                        sources_output = gr.Markdown(label="Sources")

                refresh_btn.click(refresh_repo_list, outputs=repo_select)
                ask_btn.click(answer_question, inputs=[repo_select, question_input], outputs=[answer_output, sources_output])
                question_input.submit(answer_question, inputs=[repo_select, question_input], outputs=[answer_output, sources_output])

            # ── Tab 3: Repository Management ────────────────────────────────
            with gr.TabItem("🗂️ Repository Management"):
                with gr.Row():
                    mgmt_repo_select = gr.Dropdown(
                        label="Select Repository",
                        choices=get_repo_choices(),
                        interactive=True,
                        scale=3,
                    )
                    mgmt_refresh_btn = gr.Button("🔄 Refresh", scale=1)

                with gr.Row():
                    stats_btn = gr.Button("View Stats", variant="secondary")
                    delete_btn = gr.Button("Delete Repository", variant="stop")

                mgmt_output = gr.Markdown()

                mgmt_refresh_btn.click(refresh_repo_list, outputs=mgmt_repo_select)
                stats_btn.click(show_repo_stats, inputs=mgmt_repo_select, outputs=mgmt_output)
                delete_btn.click(delete_repo_action, inputs=mgmt_repo_select, outputs=[mgmt_output, mgmt_repo_select])

            # ── Tab 4: MCP Info ─────────────────────────────────────────────
            with gr.TabItem("🔌 MCP Integration"):
                gr.Markdown("""
### MCP (Model Context Protocol) Integration

This application exposes documentation search as MCP-compatible tools that any AI assistant can use.

#### Available MCP Tools

| Tool | Description |
|------|-------------|
| `search_documentation` | Semantic search across ingested documentation |
| `ask_documentation` | AI-powered Q&A with source citations |
| `list_available_repos` | List all ingested repositories |

#### Connect via MCP SSE

```
http://127.0.0.1:7860/gradio_api/mcp/sse
```

#### Example Usage (Claude Desktop)

```json
{
  "mcpServers": {
    "doc-mcp": {
      "url": "http://127.0.0.1:7860/gradio_api/mcp/sse"
    }
  }
}
```

#### Tool Parameters

**search_documentation**
- `repo` — Repository name (e.g. `owner/repo`)
- `query` — Natural language search query
- `top_k` — Number of results (default: 5)

**ask_documentation**
- `repo` — Repository name
- `question` — Question to answer from documentation
""")

    return demo
