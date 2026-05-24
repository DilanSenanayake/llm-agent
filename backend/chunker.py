# Split document text into overlapping word-based chunks.

from typing import Iterator


def _words(text: str) -> list[str]:
    return text.split()


# Split text into chunks of `chunk_size_words` with `overlap_words` overlap.
#
# Args:
#     text: Full document text.
#     chunk_size_words: Target words per chunk.
#     overlap_words: Words repeated at the start of the next chunk.
#
# Returns:
#     List of chunk strings (non-empty).
def chunk_text(
    text: str,
    chunk_size_words: int = 500,
    overlap_words: int = 50,
) -> list[str]:
    words = _words(text.strip())
    if not words:
        return []

    if overlap_words >= chunk_size_words:
        overlap_words = max(0, chunk_size_words // 10)

    step = max(1, chunk_size_words - overlap_words)
    chunks: list[str] = []
    start = 0
    while start < len(words):
        end = min(start + chunk_size_words, len(words))
        piece = " ".join(words[start:end]).strip()
        if piece:
            chunks.append(piece)
        if end >= len(words):
            break
        start += step

    return chunks
