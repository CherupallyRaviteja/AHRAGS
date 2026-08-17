import logging

from generator import generate_answer
from query_rewriter import rewrite_query
from config import SIM_THRESHOLD

logger = logging.getLogger(__name__)


def main(question):
    """
    GraphRAG-only question -> answer pipeline.

    Flow:
        Question
        -> Query Rewriting
        -> Graph Retrieval
        -> Graph Ranking
        -> Context Building
        -> Gemma 2B
        -> Grounded Answer

    Returns:
        answer, sources, score, provenance
    """

    # ---------------------------------------------------------
    # 1. Rewrite query
    # ---------------------------------------------------------
    q = rewrite_query(question)

    # ---------------------------------------------------------
    # 2. Graph retrieval
    # ---------------------------------------------------------
    try:
        from graph_retriever import graph_retriever

        graph_results = graph_retriever.search(q)

    except Exception as exc:
        logger.exception("Graph retrieval failed: %s", exc)
        return (
            "I don't know.",
            {},
            0.0,
            [],
        )

    # ---------------------------------------------------------
    # 3. No graph results
    # ---------------------------------------------------------
    if not graph_results:
        logger.info("No graph results found for query: %s", q)

        return (
            "I don't know.",
            {},
            0.0,
            [],
        )

    # ---------------------------------------------------------
    # 4. Graph ranking + context building
    # ---------------------------------------------------------
    try:
        from hybrid_ranker import merge
        from context_builder import build_context

        # Graph-only ranking.
        #
        # We pass an empty vector-result list because this
        # controller no longer performs vector retrieval.
        ranked = merge([], graph_results)

        contexts, graph_context_text, sources, provenance = (
            build_context(ranked)
        )

    except Exception as exc:
        logger.exception(
            "Graph ranking/context building failed: %s",
            exc,
        )

        return (
            "I don't know.",
            {},
            0.0,
            [],
        )

    # ---------------------------------------------------------
    # 5. No usable context
    # ---------------------------------------------------------
    if not contexts:
        return (
            "I don't know.",
            {},
            0.0,
            provenance,
        )

    # ---------------------------------------------------------
    # 6. Extract final graph-ranking scores
    # ---------------------------------------------------------
    scores = [
        float(item.get("score", 0.0))
        for item in ranked[:len(contexts)]
        if isinstance(item, dict)
    ]

    final_score = scores[0] if scores else 0.0

    # ---------------------------------------------------------
    # 7. Generate grounded answer
    # ---------------------------------------------------------
    answer = generate_answer(
        q,
        contexts,
        scores=scores,
        sim_threshold=SIM_THRESHOLD,
        graph_context=graph_context_text or None,
    )

    # ---------------------------------------------------------
    # 8. Logging
    # ---------------------------------------------------------
    logger.info(
        "GraphRAG query completed | "
        "query=%s | graph_results=%d | contexts=%d | "
        "final_score=%.4f",
        q,
        len(graph_results),
        len(contexts),
        final_score,
    )

    return (
        answer,
        sources,
        final_score,
        provenance,
    )