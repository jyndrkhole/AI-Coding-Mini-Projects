import base64
import os
from openai import OpenAI
from dotenv import load_dotenv
from scraper import (
    extract_pdf_text,
    fetch_website_contents,
    file_path,
    is_image,
    is_pdf,
    looks_like_url,
)

load_dotenv()

MAX_CHARS = 50_000
TEXT_MODEL = "llama-3.3-70b-versatile"
VISION_MODEL = "meta-llama/llama-4-scout-17b-16e-instruct"

WEBSITE_SYSTEM_PROMPT = """You analyze the contents of a website and
give a short, friendly summary. Ignore navigation menus.
Respond in markdown."""

DOCUMENT_SYSTEM_PROMPT = """You analyze the contents of a document and
give a short, friendly summary. Highlight the main topics and key takeaways.
Respond in markdown."""

IMAGE_SYSTEM_PROMPT = """You analyze an image and give a short, friendly summary.
Describe what you see, any visible text, and the main takeaways.
Respond in markdown."""

def _client():
    return OpenAI(
        api_key=os.getenv("GROQ_API_KEY"),
        base_url="https://api.groq.com/openai/v1",
    )

def _with_instructions(base_prompt, instructions):
    if not instructions:
        return base_prompt
    return f"{base_prompt}\n\nFollow these instructions:\n{instructions}"

def _summarize_text(source_label, content, system_prompt, instructions=""):
    if content.startswith(("Could not", "No PDF")):
        return content

    if len(content) > MAX_CHARS:
        content = content[:MAX_CHARS] + "\n\n[Content truncated for length.]"

    user_prompt = _with_instructions(
        f"Summarize this {source_label}:\n\n{content}",
        instructions,
    )

    response = _client().chat.completions.create(
        model=TEXT_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    )
    return response.choices[0].message.content

def _summarize_image(path, instructions=""):
    with open(path, "rb") as f:
        encoded = base64.b64encode(f.read()).decode("utf-8")

    ext = os.path.splitext(path)[1].lower().lstrip(".")
    mime = "jpeg" if ext in ("jpg", "jpeg") else ext

    prompt = _with_instructions(
        "Summarize this image. Describe key content and any text visible.",
        instructions,
    )

    try:
        response = _client().chat.completions.create(
            model=VISION_MODEL,
            messages=[
                {"role": "system", "content": IMAGE_SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:image/{mime};base64,{encoded}"},
                        },
                    ],
                },
            ],
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"Could not summarize the image. Error: {e}"

def summarize_input(value):
    if not value:
        return "Paste a website URL or upload a PDF/image."

    text = (value.get("text") or "").strip()
    files = value.get("files") or []

    if text and looks_like_url(text):
        return _summarize_text(
            "website",
            fetch_website_contents(text),
            WEBSITE_SYSTEM_PROMPT,
        )

    if files:
        path = file_path(files[0])
        if not path:
            return "Could not read the uploaded file."

        instructions = text

        if is_pdf(path):
            return _summarize_text(
                "PDF document",
                extract_pdf_text(path),
                DOCUMENT_SYSTEM_PROMPT,
                instructions,
            )
        if is_image(path):
            return _summarize_image(path, instructions)

        return "Unsupported file type. Upload a PDF, PNG, JPG, or JPEG."

    if text:
        return "Enter a valid website URL or upload a PDF/image."

    return "Paste a website URL or upload a PDF/image."
