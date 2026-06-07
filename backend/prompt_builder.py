import os
import inspect

def build_prompt(query: str, chunks: list[dict]) -> str:
    system_str = """<system>
        You are a document analysis assistant. You answer questions strictly and only
        based on the provided document excerpts. You never use outside knowledge.
        If the answer is not present in the excerpts, say exactly:
        'I could not find this information in the provided documents.'
        Never speculate. Never say "I think" or "probably." Cite the source filename
        and section for every claim you make.
        </system>"""

    excerpt_parts = []
    for chunk in chunks:
        source = chunk.get("source")
        chunk_id = chunk.get("chunk_index")
        section = chunk.get("section_heading", "N/A")
        text = chunk.get("text")
        excerpt_parts.append(
            f'<excerpt source="{source}" section="{section}" chunk_id="{chunk_id}">\n{text}\n</excerpt>'
        )

    context_str = "<context>\n" + "\n\n".join(excerpt_parts) + "\n</context>"

    question_str = f"""<question>
        {query}
        </question>"""

    instruction_str = """<instructions>
    Answer only using the excerpts provided in <context>. 
    For every claim, cite the source filename and section.
    If the answer is not present, respond with exactly: 
    'I could not find this information in the provided documents.'
    Do not speculate or use outside knowledge.
    </instructions>"""      

    return system_str + "\n" + instruction_str + "\n" + context_str + "\n" + question_str

