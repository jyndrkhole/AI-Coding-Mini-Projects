# pip install gradio pypdf
import gradio as gr
from summarizer import summarize, summarize_pdf

with gr.Blocks(title="AI PDF Summarizer") as demo:
    gr.Markdown("# 📄 AI PDF Summarizer")

    with gr.Tab("PDF"):
        pdf_input = gr.File(
            label="Upload PDF",
            file_types=[".pdf"],
            type="filepath",
        )
        pdf_output = gr.Markdown(label="Summary")
        gr.Button("Summarize PDF", variant="primary").click(
            summarize_pdf, inputs=pdf_input, outputs=pdf_output
        )

    with gr.Tab("Website"):
        url_input = gr.Textbox(label="Website URL", placeholder="https://example.com")
        url_output = gr.Markdown(label="Summary")
        gr.Button("Summarize Website", variant="primary").click(
            summarize, inputs=url_input, outputs=url_output
        )

demo.launch()
