from openai import OpenAI
from dotenv import load_dotenv
from scraper import fetch_website_contents, extract_pdf_text
import os

load_dotenv()

MAX_CHARS = 50_000

WEBSITE_SYSTEM_PROMPT = """You analyze the contents of a website and
give a short, friendly summary. Ignore navigation menus.
Respond in markdown."""

PDF_SYSTEM_PROMPT = """You analyze the contents of a PDF document and
give a short, friendly summary. Highlight the main topics and key takeaways.
Respond in markdown."""

def _client():
    return OpenAI(
        api_key=os.getenv("GROQ_API_KEY"),
        base_url="https://api.groq.com/openai/v1",
    )

def _summarize(source_label, content, system_prompt):
    if content.startswith(("Could not", "No PDF")):
        return content

    if len(content) > MAX_CHARS:
        content = content[:MAX_CHARS] + "\n\n[Content truncated for length.]"

    response = _client().chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Summarize this {source_label}:\n\n{content}"},
        ],
    )
    return response.choices[0].message.content

def summarize(url):
    website = fetch_website_contents(url)
    return _summarize("website", website, WEBSITE_SYSTEM_PROMPT)

def summarize_pdf(file_path):
    pdf_text = extract_pdf_text(file_path)
    return _summarize("PDF", pdf_text, PDF_SYSTEM_PROMPT)
