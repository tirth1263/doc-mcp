from src.ui import build_ui
from src.mcp_server import search_documentation, ask_documentation, list_available_repos

if __name__ == "__main__":
    demo = build_ui()
    demo.launch(
        server_name="0.0.0.0",
        server_port=7860,
        mcp_server=True,
    )
