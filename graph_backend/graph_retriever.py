from __future__ import annotations
import logging
from typing import Any, Dict, List, Optional
import numpy as np
import config
from graph_db import GraphStore, graph_store as default_graph_store

logger = logging.getLogger(__name__)


def _cosine_sim(a: np.ndarray, b: np.ndarray) -> float:
    denom = np.linalg.norm(a) * np.linalg.norm(b)
    return float(np.dot(a, b) / denom) if denom else 0.0


class GraphRetriever:
    """Graph-based retrieval: entity matching, multi-hop traversal, and
    relationship-aware chunk collection."""

    def __init__(self, store: Optional[GraphStore] = None) -> None:
        self.store = store or default_graph_store

    # ------------------------------------------------------------------
    def search(self, query: str, top_k: int = None) -> List[Dict[str, Any]]:
        """
        GraphRAG retrieval:

            Query
            ↓
            Vector search in Neo4j
            ↓
            Initial chunks
            ↓
            Graph expansion
            ↓
            Related chunks
            ↓
            Combined graph results

        Returns graph-retrieved chunks with provenance.
        """

        top_k = top_k or config.GRAPH_TOP_K_CHUNKS

        if not self.store.available:
            return []

        try:
            # ---------------------------------------------------------
            # 1. Vector search
            # ---------------------------------------------------------
            vector_chunks = self._vector_search_chunks(query, top_k)

            if not vector_chunks:
                logger.debug(
                    "No vector-matched chunks for query: %s",
                    query,
                )
                return []

            chunk_ids = [
                row["chunk_id"]
                for row in vector_chunks
                if row.get("chunk_id")
            ]

            logger.info(
                "Neo4j vector search returned %d candidate chunks: %s",
                len(chunk_ids),
                chunk_ids,
            )

            # ---------------------------------------------------------
            # 2. Graph expansion
            # ---------------------------------------------------------
            graph_chunks = self._expand_from_chunks(
                chunk_ids,
                top_k,
            )

            logger.info(
                "Graph expansion: %d vector candidates → %d graph candidates",
                len(vector_chunks),
                len(graph_chunks),
            )

            # ---------------------------------------------------------
            # 3. Convert initial vector results
            # ---------------------------------------------------------
            results = []

            for row in vector_chunks:
                results.append({
                    "chunk_id": row.get("chunk_id"),
                    "source": row.get("source"),
                    "page": row.get("page"),
                    "content": row.get("content"),
                    "score": row.get("score", 0.0),
                    "hop_distance": 0,
                    "matched_entity": None,
                    "starting_chunk_id": row.get("chunk_id"),
                    "retrieval_type": "vector",
                })

            # ---------------------------------------------------------
            # 4. Add graph-expanded results
            # ---------------------------------------------------------
            existing_ids = {
                result["chunk_id"]
                for result in results
            }

            for row in graph_chunks:

                chunk_id = row.get("chunk_id")

                if not chunk_id:
                    continue

                if chunk_id in existing_ids:
                    continue

                results.append({
                    "chunk_id": chunk_id,
                    "source": row.get("source"),
                    "page": row.get("page"),
                    "content": row.get("content"),
                    "score": 0.0,
                    "hop_distance": row.get("hop_distance", 1),
                    "matched_entity": row.get("matched_entity"),
                    "starting_chunk_id": row.get("starting_chunk_id"),
                    "relationship_types": row.get("relationship_types", []),
                    "graph_path": row.get("graph_path", []),
                    "node_importance": row.get("node_importance", 0.0),
                    "retrieval_type": "graph",
                })
                existing_ids.add(chunk_id)
            # ---------------------------------------------------------
            # 5. Return the combined candidates
            # ---------------------------------------------------------
            logger.info(
                "Graph retrieval total: %d chunks "
                "(%d vector + %d graph)",
                len(results),
                len(vector_chunks),
                len(results) - len(vector_chunks),
            )

            return results

        except Exception as exc:
            logger.error(
                "Graph retrieval failed, falling back to vector-only: %s",
                exc,
            )
            return []
        
    def _vector_search_chunks(self,query: str,top_k: int,) -> List[Dict[str, Any]]:
        """Find the most semantically similar Chunk nodes using Neo4j vector search."""

        try:
            query_embedding = config.embed_model.encode(
                query,
                convert_to_numpy=True,
            ).tolist()

            rows = self.store.run_read(
                """
                CALL db.index.vector.queryNodes(
                    'chunk_embedding_index',
                    $top_k,
                    $query_embedding
                )
                YIELD node, score

                RETURN
                    node.id AS chunk_id,
                    node.source AS source,
                    node.page AS page,
                    node.content AS content,
                    score
                ORDER BY score DESC
                """,
                {
                    "top_k": top_k,
                    "query_embedding": query_embedding,
                },
            )

            return rows

        except Exception as exc:
            logger.error(
                "Neo4j chunk vector search failed: %s",
                exc,
            )
            return []

    def _expand_from_chunks(
    self,
    chunk_ids: List[str],
    top_k: int,
) -> List[Dict[str, Any]]:
        """
        Expand vector-matched chunks through the knowledge graph.

        Flow:

            Starting Chunk
                ↓
            Entity
                ↓
        Related Entity
                ↓
        Related Chunk

        The starting chunks themselves are excluded from the returned
        graph-expanded candidates because they already came from vector search.

        hop_distance:
            0 = entity directly mentioned by the starting chunk
            1 = entity reached through one Entity -> Entity relationship
            2 = two Entity -> Entity relationships
            ...
        """

        if not chunk_ids:
            return []

        rows = list(self.store.run_read(
            f"""
            MATCH (start:Chunk)
            WHERE start.id IN $chunk_ids

            MATCH (start)-[:MENTIONS]->(direct:Entity)

            OPTIONAL MATCH path =
                (direct)-[*0..{config.GRAPH_MAX_HOPS}]-(related:Entity)

            WITH
                start,
                related,
                path,
                CASE
                    WHEN path IS NULL THEN 0
                    ELSE length(path)
                END AS hop_distance

            WHERE related IS NOT NULL

            MATCH (candidate:Chunk)-[:MENTIONS]->(related)

            WHERE NOT candidate.id IN $chunk_ids

            RETURN
                candidate.id AS chunk_id,
                candidate.source AS source,
                candidate.page AS page,
                candidate.content AS content,
                start.id AS starting_chunk_id,
                related.name AS matched_entity,
                hop_distance,
                CASE
                    WHEN path IS NULL THEN []
                    ELSE [rel IN relationships(path) | type(rel)]
                END AS relationship_types,
                CASE
                    WHEN path IS NULL THEN []
                    ELSE [node IN nodes(path) | node.name]
                END AS graph_path,
                related.pagerank AS pagerank
            ORDER BY hop_distance ASC

            LIMIT $limit
            """,
            {
                "chunk_ids": chunk_ids,
                "limit": top_k * 5,
            },
        ))

        results = []
        seen = set()

        for row in rows:
            chunk_id = row.get("chunk_id")

            if not chunk_id:
                continue

            if chunk_id in seen:
                continue

            seen.add(chunk_id)

            pagerank = float(row.get("pagerank") or 0.0)

            results.append({
                "chunk_id": chunk_id,
                "source": row.get("source"),
                "page": row.get("page"),
                "content": row.get("content"),
                "starting_chunk_id": row.get("starting_chunk_id"),
                "matched_entity": row.get("matched_entity"),
                "hop_distance": row.get("hop_distance", 0),
                "relationship_types": row.get("relationship_types", []),
                "graph_path": row.get("graph_path", []),
                "node_importance": pagerank / (1.0 + pagerank),
            })

        return results[:top_k]
    # ------------------------------------------------------------------
    # Entity matching
    # ------------------------------------------------------------------
    def _match_entities(self, query: str) -> List[Dict[str, Any]]:
        """Find entities whose name appears in the query (substring match),
        falling back to embedding similarity against all known entities for
        paraphrased mentions."""
        tokens = [t for t in query.lower().replace("?", "").split() if len(t) > 2]
        candidates: Dict[str, Dict[str, Any]] = {}

        if tokens:
            rows = self.store.run_read(
                """
                MATCH (e:Entity)
                WHERE any(t IN $tokens WHERE toLower(e.name) CONTAINS t)
                   OR any(t IN $tokens WHERE toLower($query) CONTAINS toLower(e.name))
                RETURN e.id AS id, e.name AS name, e.type AS type
                LIMIT $limit
                """,
                {"tokens": tokens, "query": query, "limit": config.GRAPH_TOP_K_ENTITIES * 3},
            )
            for row in rows:
                candidates[row["id"]] = {"id": row["id"], "name": row["name"], "type": row["type"], "score": 1.0}

        if len(candidates) < config.GRAPH_TOP_K_ENTITIES:
            candidates.update(self._embedding_match_entities(query, exclude=set(candidates.keys())))

        ranked = sorted(candidates.values(), key=lambda c: c["score"], reverse=True)
        return ranked[: config.GRAPH_TOP_K_ENTITIES]

    def _embedding_match_entities(self, query: str, exclude: set) -> Dict[str, Dict[str, Any]]:
        rows = self.store.run_read(
            "MATCH (e:Entity) RETURN e.id AS id, e.name AS name, e.type AS type LIMIT 500"
        )
        rows = [r for r in rows if r["id"] not in exclude]
        if not rows:
            return {}

        try:
            query_vec = config.embed_model.encode(query, convert_to_numpy=True)
            names = [r["name"] for r in rows]
            name_vecs = config.embed_model.encode(names, convert_to_numpy=True)
        except Exception as exc:  # noqa: BLE001
            logger.error("Embedding-based entity matching failed: %s", exc)
            return {}

        scored = []
        for row, vec in zip(rows, name_vecs):
            sim = _cosine_sim(query_vec, vec)
            if sim >= config.ENTITY_LINK_THRESHOLD - 0.15:  # slightly looser than exact-entity linking
                scored.append({"id": row["id"], "name": row["name"], "type": row["type"], "score": sim})

        scored.sort(key=lambda c: c["score"], reverse=True)
        return {c["id"]: c for c in scored[: config.GRAPH_TOP_K_ENTITIES]}

    # ------------------------------------------------------------------
    # Multi-hop expansion (blueprint 4.4, 4.6)
    # ------------------------------------------------------------------
    def _expand_entities(self, matched_entities: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
        expanded: Dict[str, Dict[str, Any]] = {
            e["id"]: {**e, "hop_distance": 0, "path": [e["name"]]} for e in matched_entities
        }

        ids = [e["id"] for e in matched_entities]
        if not ids:
            return expanded

        rows = self.store.run_read(
            f"""
            MATCH (start:Entity) WHERE start.id IN $ids
            MATCH path = (start)-[*1..{config.GRAPH_MAX_HOPS}]-(related:Entity)
            RETURN start.name AS start_name, related.id AS id, related.name AS name,
                   related.type AS type, length(path) AS hops,
                   [n IN nodes(path) | coalesce(n.name, '')] AS path_names
            """,
            {"ids": ids},
        )
        for row in rows:
            existing = expanded.get(row["id"])
            if existing is None or row["hops"] < existing["hop_distance"]:
                expanded[row["id"]] = {
                    "id": row["id"],
                    "name": row["name"],
                    "type": row["type"],
                    "score": 1.0 / (1 + row["hops"]),
                    "hop_distance": row["hops"],
                    "path": row["path_names"],
                }
        return expanded

    # ------------------------------------------------------------------
    # Chunk collection (blueprint 4.7 relationship-aware retrieval)
    # ------------------------------------------------------------------
    def _collect_chunks(self, expanded_entities: Dict[str, Dict[str, Any]], top_k: int) -> List[Dict[str, Any]]:
        if not expanded_entities:
            return []

        entity_ids = list(expanded_entities.keys())
        rows = self.store.run_read(
            """
            MATCH (c:Chunk)-[:MENTIONS]->(e:Entity)
            WHERE e.id IN $entity_ids

            OPTIONAL MATCH (c)-[:REFERENCES|EXTENDS]-(linked:Chunk)

            OPTIONAL MATCH (e)-[r]-()
            WITH
                c,
                e,
                count(DISTINCT r) AS entity_degree,
                collect(DISTINCT linked) AS linked_chunks

            WITH
                c,
                collect(DISTINCT e.id) AS mentioned_ids,
                collect(DISTINCT linked_chunks) AS linked_groups,
                max(entity_degree) AS max_entity_degree

            RETURN
                c.id AS chunk_id,
                c.source AS source,
                c.page AS page,
                c.content AS content,
                mentioned_ids,
                reduce(
                    all_links = [],
                    links IN linked_groups |
                    all_links + links
                ) AS linked_chunks,
                e.pagerank AS pagerank
                max_entity_degree AS node_importance

            LIMIT $limit
            """,
            {"entity_ids": entity_ids, "limit": top_k * 3},
        )

        results: List[Dict[str, Any]] = []
        seen_chunk_ids = set()

        def _score_for(entity_ids_for_chunk: List[str]) -> Dict[str, Any]:
            best_hop = min(
                (expanded_entities[eid]["hop_distance"] for eid in entity_ids_for_chunk if eid in expanded_entities),
                default=config.GRAPH_MAX_HOPS + 1,
            )
            names = [expanded_entities[eid]["name"] for eid in entity_ids_for_chunk if eid in expanded_entities]
            path = []
            for eid in entity_ids_for_chunk:
                if eid in expanded_entities:
                    path = expanded_entities[eid]["path"]
                    break
            return {"hop_distance": best_hop, "matched_entities": names, "path": path}

        for row in rows:
            if row["chunk_id"] in seen_chunk_ids:
                continue
            seen_chunk_ids.add(row["chunk_id"])
            pagerank = float(row.get("pagerank") or 0.0)
            meta = _score_for(row["mentioned_ids"])
            results.append({
                "chunk_id": row["chunk_id"],
                "source": row["source"],
                "page": row["page"],
                "content": row["content"],
                **meta,
                "node_importance": pagerank / (1.0 + pagerank),
            })

            # Context expansion: pull in directly linked chunks too, one hop
            # further out at a lower confidence (blueprint 4.6).
            for linked in row["linked_chunks"] or []:
                if not linked or linked.get("id") in seen_chunk_ids:
                    continue
                seen_chunk_ids.add(linked["id"])
                results.append({
                    "chunk_id": linked["id"],
                    "source": linked.get("source"),
                    "page": linked.get("page"),
                    "content": linked.get("content"),
                    "hop_distance": meta["hop_distance"] + 1,
                    "matched_entities": meta["matched_entities"],
                    "path": meta["path"] + ["(linked chunk)"],
                    "node_importance": 0.5 * row.get("node_importance", 0.0),
                })

        results.sort(key=lambda r: (r["hop_distance"], -r["node_importance"]))
        return results[:top_k]


# Module-level singleton, consistent with graph_store / graph_builder pattern.
graph_retriever = GraphRetriever()


if __name__ == "__main__":
    print("Graph retriever ready. Store available:", graph_retriever.store.available)
