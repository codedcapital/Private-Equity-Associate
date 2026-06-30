"""Embedding pipeline: chunk filings, generate embeddings, store in pgvector."""

import tiktoken
from sqlalchemy import select

from core.config import settings
from core.embeddings import generate_embedding
from db.models import Filing, FilingChunk
from db.session import async_session_factory


def _get_encoding() -> "tiktoken.Encoding":
    """tiktoken encoding for the configured embedding model, with a safe fallback."""
    try:
        return tiktoken.encoding_for_model(settings.openai_embedding_model)
    except KeyError:
        return tiktoken.get_encoding("cl100k_base")


def chunk_text(text: str, chunk_size: int = 512, overlap: int = 50) -> list[str]:
    """Split text into overlapping token chunks using tiktoken.

    Args:
        text: The raw text to chunk.
        chunk_size: Target number of tokens per chunk (default 512).
        overlap: Number of overlapping tokens between chunks (default 50).

    Returns:
        A list of text chunks. For text with <= chunk_size tokens, returns
        a single-element list. Returns an empty list for empty/whitespace text.
    """
    if not text or not text.strip():
        return []

    encoding = _get_encoding()
    tokens = encoding.encode(text)

    if len(tokens) <= chunk_size:
        return [text.strip()]

    chunks: list[str] = []
    start = 0
    step = chunk_size - overlap

    while start < len(tokens):
        end = min(start + chunk_size, len(tokens))
        chunk_tokens = tokens[start:end]
        chunk_str = encoding.decode(chunk_tokens).strip()
        if chunk_str:
            chunks.append(chunk_str)

        if end == len(tokens):
            break
        start += step

    return chunks


async def run_embedding_pipeline(batch_size: int = 10) -> dict:
    """Process all un-embedded filings: chunk, embed, and store.

    Reads all filings where `embedding IS NULL`, chunks the raw text into
    ~512-token windows with 50-token overlap, generates embeddings per chunk
    via OpenAI, and persists them in the `filing_chunks` table. Also updates
    the parent `filings` row with the first chunk's embedding.

    Args:
        batch_size: Number of filings to process before committing to the DB.

    Returns:
        A dict with:
            - filings_processed: number of filings that had embeddings generated
            - chunks_created: total number of chunks stored
    """
    async with async_session_factory() as session:
        stmt = select(Filing).where(Filing.embedding.is_(None))
        result = await session.execute(stmt)
        filings = result.scalars().all()

        filings_processed = 0
        chunks_created = 0

        for filing in filings:
            if not filing.raw_text or not filing.raw_text.strip():
                continue

            chunks = chunk_text(filing.raw_text)
            if not chunks:
                continue

            chunk_embeddings: list[list[float]] = []

            for idx, chunk_text_str in enumerate(chunks):
                embedding = await generate_embedding(chunk_text_str)
                chunk_embeddings.append(embedding)

                chunk = FilingChunk(
                    filing_id=filing.id,
                    chunk_index=idx,
                    chunk_text=chunk_text_str,
                    embedding=embedding,
                )
                session.add(chunk)
                chunks_created += 1

            # Update the parent filing with the first chunk's embedding
            if chunk_embeddings:
                filing.embedding = chunk_embeddings[0]

            filings_processed += 1

            # Commit in batches to keep transactions bounded
            if filings_processed % batch_size == 0:
                await session.commit()

        # Final commit for any remaining filings
        if filings_processed > 0 and filings_processed % batch_size != 0:
            await session.commit()

        return {
            "filings_processed": filings_processed,
            "chunks_created": chunks_created,
        }
