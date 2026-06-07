import re
import spacy
from dataclasses import dataclass, field
from typing import Optional
import asyncio

nlp = spacy.load("en_core_web_sm", disable=["ner", "parser"])
nlp.enable_pipe("senter")
nlp.max_length = 2_000_000

@dataclass
class Chunk:
    text: str
    source: str
    page_number: int
    section_heading: Optional[str]
    chunk_index: int
    char_start: int
    char_end: int

MAX_TOKENS = 512
OVERLAP_TOKENS = 64
AVG_CHARS_PER_TOKEN = 4

MAX_CHARS = MAX_TOKENS * AVG_CHARS_PER_TOKEN
OVERLAP_CHARS = OVERLAP_TOKENS * AVG_CHARS_PER_TOKEN

def _is_heading(line: str) -> bool:
    if line.startswith("#"):
        return True
    if line.isupper() and len(line) < 80:
        return True
    result = re.match(r'^\d+(\.\d+)*\s+\S', line)
    if result:
        return True
    
    if line.istitle() and len(line) < 60 and not line.endswith("."):
        return True
    
    return False

def _split_into_sections(text: str) -> list[dict]:
    blocks = text.split("\n\n")
    sections = []
    current_heading = None
    for block in blocks:
        block = block.strip()
        if not block:
            continue

        lines = block.split("\n")
        first_line = lines[0]

        if _is_heading(first_line):
            current_heading = first_line
            block_text = "\n".join(lines[1:]).strip()

            if not block_text:
                continue

        else:
            block_text = block

        sections.append({
            "heading": current_heading,
            "text": block_text
        })

    return sections

def _split_section_into_chunks(text: str, heading: Optional[str], source: str, page_number: int, start_chunk_index: int) -> list[Chunk]:
    doc = nlp(text)
    sentences = [sent.text for sent in doc.sents]

    chunks = []
    current_sentences = []
    current_chars = 0
    char_cursor = 0

    for sentence in sentences:
        sentence_len = len(sentence) + (1 if current_sentences else 0)

        if current_chars + sentence_len > MAX_CHARS:
            if current_sentences:
                chunk_text = " ".join(current_sentences)
                char_end = char_cursor + len(chunk_text)

                chunks.append(Chunk(
                    text=chunk_text,
                    source=source,
                    page_number=page_number,
                    section_heading=heading,
                    chunk_index=start_chunk_index,
                    char_start=char_cursor,
                    char_end=char_end
                ))
                start_chunk_index += 1

                overlap_sentences = []
                overlap_chars = 0
                for s in reversed(current_sentences):
                    s_len = len(s) + (1 if overlap_sentences else 0)
                    if overlap_chars + s_len <= OVERLAP_CHARS:
                        overlap_sentences.insert(0, s)
                        overlap_chars += s_len
                    else:
                        break

                overlap_text = " ".join(overlap_sentences)
                char_cursor += len(chunk_text) - len(overlap_text)

                current_sentences = overlap_sentences
                current_chars = len(overlap_text)

        current_sentences.append(sentence)
        current_chars += sentence_len

    if current_sentences:
        chunk_text = " ".join(current_sentences)
        char_end = char_cursor + len(chunk_text)

        chunks.append(Chunk(
            text=chunk_text,
            source=source,
            page_number=page_number,
            section_heading=heading,
            chunk_index=start_chunk_index,
            char_start=char_cursor,
            char_end=char_end
        ))

    return chunks

def chunk_pages(pages: list[dict]) -> list[Chunk]:
    all_chunks = []
    chunk_index = 0

    for page in pages:
        sections = _split_into_sections(page["text"])
        for section in sections:
            chunks = _split_section_into_chunks(
                text=section["text"],
                heading=section["heading"],
                source=page["source"],
                page_number=page["page_number"],
                start_chunk_index=chunk_index
            )
            all_chunks.extend(chunks)

            chunk_index += len(chunks)
    return all_chunks

async def chunk_pages_large(pages: list[dict]) -> list[Chunk]:
    LARGE_DOC_PAGE_THRESHOLD = 50
    loop = asyncio.get_event_loop()
    if len(pages) <= LARGE_DOC_PAGE_THRESHOLD:
        return await loop.run_in_executor(None, chunk_pages, pages)
    
    batch_size = 20
    batches = [pages[i:i + batch_size] for i in range(0, len(pages), batch_size)]

    tasks = [
        loop.run_in_executor(None, chunk_pages, batch) for batch in batches
    ]

    batch_results = await asyncio.gather(*tasks)

    flattened_chunks = [chunk for batch in batch_results for chunk in batch]

    for i, chunk in enumerate(flattened_chunks):
        chunk.chunk_index = i

    return flattened_chunks
