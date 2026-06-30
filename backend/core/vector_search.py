"""Semantic search over filing chunks using pgvector cosine similarity."""

from dataclasses import dataclass

from sqlalchemy import select

from core.embeddings import generate_embedding
from db.models import FilingChunk
from db.session import async_session_factory


@dataclass
class ChunkResult:
    """Result of a semantic search over filing chunks."""

    chunk_id: int
    filing_id: int
    chunk_text: str
    similarity_score: float


async def semantic_search(query: str, top_k: int = 5) -> list[ChunkResult]:
    """Search filing_chunks by cosine similarity.

    Generates an embedding for the query, then uses pgvector's cosine
    distance operator (<=>) to find the most similar chunks. Similarity
    score is returned as 1 - cosine_distance (range: [-1, 1]).

    Args:
        query: The search query text.
        top_k: Maximum number of results to return.

    Returns:
        A list of ChunkResult objects ordered by similarity (highest first).
    """
    query_embedding = await generate_embedding(query)

    async with async_session_factory() as session:
        distance_expr = FilingChunk.embedding.cosine_distance(query_embedding)

        stmt = (
            select(
                FilingChunk.id,
                FilingChunk.filing_id,
                FilingChunk.chunk_text,
                (1 - distance_expr).label("similarity"),
            )
            .where(FilingChunk.embedding.is_not(None))
            .order_by(distance_expr)
            .limit(top_k)
        )

        result = await session.execute(stmt)
        rows = result.all()

        return [
            ChunkResult(
                chunk_id=row.id,
                filing_id=row.filing_id,
                chunk_text=row.chunk_text,
                similarity_score=float(row.similarity),
            )
            for row in rows
        ]
