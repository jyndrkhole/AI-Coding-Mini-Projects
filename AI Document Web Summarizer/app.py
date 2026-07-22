# pip install gradio pypdf
import os
import gradio as gr
from scraper import looks_like_url
from summarizer import summarize_input

URL_LABEL = "Website URL"
URL_PLACEHOLDER = "https://example.com"
INSTRUCTIONS_LABEL = "Extra instructions (optional)"
INSTRUCTIONS_PLACEHOLDER = (
    "e.g. Translate the summary to the document's original language"
)

def _upload_path(file):
    if file is None:
        return None
    if isinstance(file, str):
        return file
    return getattr(file, "name", file)

def _url_textbox():
    return gr.update(label=URL_LABEL, placeholder=URL_PLACEHOLDER)

def _instructions_textbox(value=""):
    return gr.update(
        value=value,
        label=INSTRUCTIONS_LABEL,
        placeholder=INSTRUCTIONS_PLACEHOLDER,
    )

def on_upload(file, current_text):
    path = _upload_path(file)
    if not path:
        return None, "", _url_textbox()

    text = current_text or ""
    if looks_like_url(text.strip()):
        text = ""

    return (
        path,
        f"📎 Uploaded: `{os.path.basename(path)}`",
        _instructions_textbox(text),
    )

def on_text_input(text, current_file):
    raw = text or ""

    if looks_like_url(raw.strip()):
        return None, ""

    if current_file:
        return current_file, f"📎 Uploaded: `{os.path.basename(current_file)}`"

    return None, ""

def summarize(text, file_path):
    text = (text or "").strip()

    if text and looks_like_url(text):
        return summarize_input({"text": text, "files": []})

    if file_path:
        return summarize_input({"text": text, "files": [{"path": file_path}]})

    if text:
        return "Enter a valid website URL or upload a PDF/image."

    return "Paste a website URL or upload a PDF/image."

def reset():
    return (
        None,
        "",
        gr.update(value="", label=URL_LABEL, placeholder=URL_PLACEHOLDER),
        "",
    )

with gr.Blocks(
    title="AI Document/Web Summarizer",
    css="""
    .input-group { align-items: flex-end; gap: 8px !important; }
    .input-group .upload-btn button {
        min-width: 48px;
        height: 48px;
        font-size: 1.5rem;
        line-height: 1;
        padding: 0;
    }
    """,
) as demo:
    gr.Markdown(
        "# 📑 AI Document/Web Summarizer\n"
        "Paste a **website URL** *or* upload a file with **＋**. "
        "After uploading, use the text box for optional instructions. "
        "Click **New summary** to clear everything and start over."
    )

    file_state = gr.State(value=None)

    with gr.Row(elem_classes="input-group"):
        text_input = gr.Textbox(
            label=URL_LABEL,
            placeholder=URL_PLACEHOLDER,
            lines=2,
            scale=5,
        )
        upload_btn = gr.UploadButton(
            "＋",
            file_types=[".pdf", ".png", ".jpg", ".jpeg"],
            elem_classes="upload-btn",
        )

    attachment = gr.Markdown()
    summary = gr.Markdown(label="Summary")

    with gr.Row():
        summarize_btn = gr.Button("Summarize", variant="primary")
        reset_btn = gr.Button("New summary")

    upload_btn.upload(
        on_upload,
        inputs=[upload_btn, text_input],
        outputs=[file_state, attachment, text_input],
    )
    text_input.input(
        on_text_input,
        inputs=[text_input, file_state],
        outputs=[file_state, attachment],
    )
    summarize_btn.click(
        summarize, inputs=[text_input, file_state], outputs=summary
    )
    reset_btn.click(
        reset,
        outputs=[file_state, attachment, text_input, summary],
    )

demo.launch()
