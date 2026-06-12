# pip install openai gradio python-dotenv
import os
import gradio as gr
from openai import OpenAI
from dotenv import load_dotenv
load_dotenv()

# openai_client = OpenAI()                                  # uses OPENAI_API_KEY
groq_client       = OpenAI(api_key=os.getenv("GROQ_API_KEY"),
                            base_url="https://api.groq.com/openai/v1")
openrouter_client = OpenAI(api_key=os.getenv("OPENROUTER_API_KEY"),
                            base_url="https://openrouter.ai/api/v1")

def ask(client, model, prompt):
    r = client.chat.completions.create(
        model=model, messages=[{"role": "user", "content": prompt}])
    return r.choices[0].message.content

def battle(value):
    prompt = prompt_text(value)
    a = ask(openrouter_client, "gpt-4o-mini", prompt)
    b = ask(groq_client, "llama-3.3-70b-versatile", prompt)
    return a, b

def vote(label):
    return f"🗳️ Thanks! You voted: **{label}**"   # in real apps, save this to a file/DB

def _audio_path(file_entry):
    if isinstance(file_entry, dict):
        return file_entry.get("path")
    return getattr(file_entry, "path", file_entry)

def prompt_text(value):
    if not value:
        return ""
    return (value.get("text") or "").strip()

def transcribe_prompt(value):
    if not value:
        return {"text": "", "files": []}

    text = prompt_text(value)
    files = value.get("files") or []
    if not files:
        return value

    audio_path = _audio_path(files[0])
    if not audio_path:
        return value

    with open(audio_path, "rb") as f:
        r = groq_client.audio.transcriptions.create(
            model="whisper-large-v3-turbo",
            file=f,
        )
    transcribed = r.text.strip()
    if text and transcribed:
        text = f"{text} {transcribed}"
    elif transcribed:
        text = transcribed

    return {"text": text, "files": []}

with gr.Blocks(title="LLM Arena") as demo:
    gr.Markdown("# 🥊 LLM Arena — one prompt, two models")
    prompt = gr.MultimodalTextbox(
        label="Ask both models the same thing",
        placeholder="Type here or click the mic to speak…",
        sources=["microphone"],
        file_types=["audio"],
        submit_btn=False,
        lines=2,
    )
    go = gr.Button("⚔️ Battle!", variant="primary")

    with gr.Row():
        with gr.Column():
            gr.Markdown("### 🤖 Model: gpt-4o-mini")
            out_a = gr.Markdown()
            with gr.Row():
                up_a   = gr.Button("👍");  down_a = gr.Button("👎")
        with gr.Column():
            gr.Markdown("### 🤖 Model: llama-3.3-70b-versatile")
            out_b = gr.Markdown()
            with gr.Row():
                up_b   = gr.Button("👍");  down_b = gr.Button("👎")

    verdict = gr.Markdown()

    prompt.change(transcribe_prompt, inputs=prompt, outputs=prompt)
    go.click(battle, inputs=prompt, outputs=[out_a, out_b])
    up_a.click(lambda: vote("👍 Model A"), outputs=verdict)
    down_a.click(lambda: vote("👎 Model A"), outputs=verdict)
    up_b.click(lambda: vote("👍 Model B"), outputs=verdict)
    down_b.click(lambda: vote("👎 Model B"), outputs=verdict)

demo.launch()