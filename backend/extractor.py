import asyncio
import re
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import pdfplumber
from docx import Document
from collections import Counter

_executor = ThreadPoolExecutor(max_workers=4)

ALLOWED_EXTENSIONS = {
    ".pdf",
    ".docx",
    ".txt",
    ".md"
}

def _extract_pdf(file_path: str) -> list[dict]:
    all_pages = []
    with pdfplumber.open(file_path) as pdf:
        for i, page in enumerate(pdf.pages, start=1):
            text = page.extract_text()
            if text is None or text == "":
                continue
            
            result = {
                "text": text,
                "page_number": i
            }

            all_pages.append(result)

    return all_pages


def _extract_docx(file_path: str) -> list[dict]:
    all_paragraphs = ""
    doc = Document(file_path)
    for paragraph in doc.paragraphs:
        if paragraph.text.strip() == "":
            continue
        all_paragraphs += paragraph.text + "\n"

    return [
        {
            "text": all_paragraphs,
            "page_number": 1
        }
    ]

def _extract_txt(file_path: str) -> list[dict]:
    all_text = ""
    with open(file_path, "r", encoding="utf-8", errors="replace") as f:
        all_text = f.read()

    return [
        {
            "text": all_text,
            "page_number": 1
        }
    ]

def _clean_text(text: str) -> str:
    text = text.replace("\x00", "")
    text = re.sub(r'\n{3,}', '\n\n', text)
    text = re.sub(r'[\t]+', ' ', text)
    text = text.strip()

    return text

def _remove_repeated_lines(pages: list[dict]) -> list[dict]:
    first_lines = Counter()
    last_lines = Counter()

    # Steps 1 & 2: Split lines and collect the first and last lines
    for page in pages:
        lines = page["text"].split('\n')
        first_lines[lines[0]] += 1
        last_lines[lines[-1]] += 1

    # Step 3: Find lines appearing on more than 40% of pages
    threshold = len(pages) * 0.4
    headers_footers = {
        line for counts in (first_lines, last_lines)
        for line, count in counts.items() if count > threshold
    }

    # Steps 4 & 5: Rebuild the text and return a new list of dicts
    cleaned_pages = []
    for page in pages:
        new_page = page.copy()  # Shallow copy keeps the function pure
        lines = new_page["text"].split('\n')
        new_page["text"] = '\n'.join(line for line in lines if line not in headers_footers)
        cleaned_pages.append(new_page)

    return cleaned_pages

async def extract_text(file_path: str, filename: str) -> list[dict]:
    path = Path(filename).suffix.lower()
    if path == ".pdf":
        func = _extract_pdf
    elif path == ".docx":
        func = _extract_docx
    elif path == ".txt" or path == ".md":
        func = _extract_txt
    else:
        raise ValueError(f"Unsupported file type: {path}")

    loop = asyncio.get_event_loop()
    pages = await loop.run_in_executor(_executor, func, file_path)

    if path == ".pdf":
        pages = _remove_repeated_lines(pages)

    final_pages = []
    for page in pages:
        page["text"] = _clean_text(page["text"])

        if page["text"]:
            page["source"] = filename
            final_pages.append(page)

    return final_pages