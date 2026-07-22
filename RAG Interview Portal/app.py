"""Gradio UI for the RAG Interview Portal."""

import shutil
from pathlib import Path

import gradio as gr

from rag import STUDY_MATERIALS_DIR, ask, get_collection_stats, index_files, index_folder, index_urls

STUDY_MATERIALS_DIR.mkdir(parents=True, exist_ok=True)


def _format_sources(sources: list[dict]) -> str:
    if not sources:
        return "_No sources retrieved._"
    lines = []
    for i, src in enumerate(sources, start=1):
        name = Path(src["source"]).name
        page = src.get("page")
        page_str = f" · page {page + 1}" if page is not None else ""
        lines.append(f"**{i}. {name}**{page_str}\n> {src['preview']}")
    return "\n\n".join(lines)


def chat_fn(message: str, history: list):
    """Gradio chat handler (Gradio 6 messages format)."""
    if not message.strip():
        return history, "", ""

    try:
        answer, sources = ask(message)
        history = history + [
            {"role": "user", "content": message},
            {"role": "assistant", "content": answer},
        ]
        return history, "", _format_sources(sources)
    except Exception as e:
        error = f"Error: {e}"
        history = history + [
            {"role": "user", "content": message},
            {"role": "assistant", "content": error},
        ]
        return history, "", ""


def upload_and_index(files):
    """Save uploaded files to study_materials/ and index them."""
    if not files:
        return "No files uploaded."

    saved_paths = []
    for file in files:
        src = file if isinstance(file, str) else getattr(file, "name", str(file))
        dest = STUDY_MATERIALS_DIR / Path(src).name
        shutil.copy(src, dest)
        saved_paths.append(str(dest))

    return index_files(saved_paths)


def index_existing_folder():
    return index_folder()


def get_stats():
    stats = get_collection_stats()
    return f"**Chunks indexed:** {stats['chunk_count']}  \n**Vector DB:** `{stats['persist_dir']}`"


SAMPLE_QUESTIONS = [
    "Explain time complexity of common sorting algorithms",
    "What is the CAP theorem?",
    "How does a B-tree index work in databases?",
    "Explain REST vs GraphQL",
    "What are the SOLID principles?",
]


with gr.Blocks(title="RAG Interview Portal") as app:
    gr.Markdown(
        """
        # RAG Interview Portal
        Upload your study material (PDF, TXT, MD, HTML, URLs), index it, then ask interview questions.
        Answers are grounded in **your documents** using Groq/Grok + local embeddings.
        """
    )

    with gr.Tab("Chat"):
        with gr.Row():
            with gr.Column(scale=2):
                chatbot = gr.Chatbot(label="Interview Q&A", height=480)
                with gr.Row():
                    msg = gr.Textbox(
                        placeholder="Ask an interview question…",
                        label="Your question",
                        scale=4,
                        lines=2,
                    )
                    send = gr.Button("Ask", variant="primary", scale=1)
                gr.Examples(examples=[[q] for q in SAMPLE_QUESTIONS], inputs=msg)
            with gr.Column(scale=1):
                gr.Markdown("### Retrieved sources")
                sources_box = gr.Markdown(value="_Ask a question to see sources._")

        send.click(chat_fn, [msg, chatbot], [chatbot, msg, sources_box])
        msg.submit(chat_fn, [msg, chatbot], [chatbot, msg, sources_box])

    with gr.Tab("Upload & Index"):
        gr.Markdown(
            f"""
            ### Add study material
            1. Upload files below (PDF, TXT, MD, HTML)
            2. Or paste URLs (one per line) and click **Index URLs**
            3. Or drop files into `{STUDY_MATERIALS_DIR.name}/` and click **Index folder**
               — also reads `urls.txt` and URLs inside `.md` files
            """
        )
        file_upload = gr.File(
            label="Study material files",
            file_count="multiple",
            file_types=[".pdf", ".txt", ".md", ".markdown", ".html", ".htm"],
        )
        url_input = gr.Textbox(
            label="Web URLs (one per line)",
            placeholder="https://scaler-content.github.io/class-3-AI-engg/",
            lines=3,
        )
        with gr.Row():
            index_btn = gr.Button("Index uploaded files", variant="primary")
            url_btn = gr.Button("Index URLs")
            folder_btn = gr.Button("Index study_materials/ folder")
        index_status = gr.Textbox(label="Status", interactive=False)

        index_btn.click(upload_and_index, file_upload, index_status)
        url_btn.click(index_urls, url_input, index_status)
        folder_btn.click(index_existing_folder, outputs=index_status)

    with gr.Tab("Status"):
        stats_md = gr.Markdown()
        refresh_btn = gr.Button("Refresh stats")
        refresh_btn.click(get_stats, outputs=stats_md)
        app.load(get_stats, outputs=stats_md)


if __name__ == "__main__":
    app.launch(theme=gr.themes.Soft())
