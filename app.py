"""Entry point for Hugging Face Spaces deployment."""
from src.ui import build_ui

demo = build_ui()

if __name__ == "__main__":
    demo.launch()
