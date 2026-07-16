import logging
import re
from typing import Any

import tiktoken

logger = logging.getLogger(__name__)
_encoder = tiktoken.get_encoding("cl100k_base")


def count_tokens(text: str) -> int:
    return len(_encoder.encode(text))


def chunk_text(text: str, max_tokens: int = 500, overlap: int = 50) -> list[str]:
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    if not paragraphs:
        return []

    chunks: list[str] = []
    current = ""

    for para in paragraphs:
        candidate = f"{current}\n\n{para}".strip() if current else para
        if count_tokens(candidate) <= max_tokens:
            current = candidate
        else:
            if current:
                chunks.append(current)
            if count_tokens(para) <= max_tokens:
                current = para
            else:
                sentences = re.split(r"(?<=[.!?])\s+", para)
                current = ""
                for sentence in sentences:
                    candidate = f"{current} {sentence}".strip() if current else sentence
                    if count_tokens(candidate) <= max_tokens:
                        current = candidate
                    else:
                        if current:
                            chunks.append(current)
                        current = sentence
    if current:
        chunks.append(current)

    if overlap > 0 and len(chunks) > 1:
        overlapped = [chunks[0]]
        for i in range(1, len(chunks)):
            prev_words = chunks[i - 1].split()[-overlap:]
            overlapped.append(" ".join(prev_words) + " " + chunks[i])
        return overlapped

    return chunks


def clean_text(text: str) -> str:
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"\[.*?\]", "", text)
    return text.strip()
