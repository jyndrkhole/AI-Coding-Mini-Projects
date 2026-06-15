# pip install requests beautifulsoup4 pypdf
import os
import requests
from bs4 import BeautifulSoup
from pypdf import PdfReader

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/120.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}

IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg"}

def file_path(entry):
    if isinstance(entry, dict):
        return entry.get("path")
    return getattr(entry, "path", entry)

def file_extension(path):
    return os.path.splitext(path)[1].lower()

def looks_like_url(text):
    text = text.strip()
    if not text:
        return False
    if text.startswith(("http://", "https://")):
        return True
    return "." in text and " " not in text and not text.startswith(".")

def fetch_website_contents(url):
    if not url.startswith(("http://", "https://")):
        url = "https://" + url

    try:
        response = requests.get(url, headers=HEADERS, timeout=15)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        return f"Could not fetch the website. Error: {e}"

    soup = BeautifulSoup(response.text, "html.parser")
    title = soup.title.string if soup.title else "No title found"

    for tag in soup(["script", "style", "nav", "footer", "header", "img", "input"]):
        tag.decompose()

    text = soup.get_text(separator="\n", strip=True)
    return f"Title: {title}\n\nPage contents:\n{text}"

def extract_pdf_text(path):
    if not path:
        return "No PDF file provided."

    try:
        reader = PdfReader(path)
        pages = []
        for i, page in enumerate(reader.pages, start=1):
            text = page.extract_text()
            if text and text.strip():
                pages.append(f"--- Page {i} ---\n{text.strip()}")

        if not pages:
            return "Could not extract text from this PDF. It may be image-only or scanned."

        return "\n\n".join(pages)
    except Exception as e:
        return f"Could not read the PDF. Error: {e}"

def is_pdf(path):
    return file_extension(path) == ".pdf"

def is_image(path):
    return file_extension(path) in IMAGE_EXTENSIONS
