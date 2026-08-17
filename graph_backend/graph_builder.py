from __future__ import annotations
import hashlib
import logging
import re
from typing import List, Optional
import config
from graph_db import GraphStore, graph_store as default_graph_store
from entity_extractor import extract_entities_relationships
from entity_linker import EntityLinker, entity_linker as default_entity_linker
from chunking import pairwise_chunk_similarity

logger = logging.getLogger(__name__)

_RELATION_SANITIZE_RE = re.compile(r"[^A-Z0-9_]")


def _sanitize_relation(relation: str) -> str:
    """Cypher relationship types can't be parameterized, so untrusted LLM
    output must be reduced to a safe identifier before string interpolation."""
    cleaned = _RELATION_SANITIZE_RE.sub("", relation.upper().replace(" ", "_"))
    return cleaned or "RELATED_TO"


def _chunk_id(source: str, page: int, index: int, content: str) -> str:
    key = f"{source}::{page}::{index}::{hashlib.sha1(content.encode('utf-8')).hexdigest()[:8]}"
    return hashlib.sha1(key.encode("utf-8")).hexdigest()[:24]


class KnowledgeGraphBuilder:
    """Builds and incrementally maintains the knowledge graph."""

    def __init__(
        self,
        store: Optional[GraphStore] = None,
        linker: Optional[EntityLinker] = None,
    ) -> None:
        self.store = store or default_graph_store
        self.linker = linker or default_entity_linker

    # ------------------------------------------------------------------
    # Ingestion (blueprint 4.1 Knowledge Graph Creation)
    # ------------------------------------------------------------------
    def index_chunks(self,chunks: List[str],embeddings,source: str,page: int,) -> None:
        """
        Index a page's chunks into the knowledge graph: create Chunk nodes,
        extract + link entities, create relationship edges between entities,
        and create similarity edges between chunks.

        Safe to call even if the graph store is unavailable (no-op, logged).
        Never raises — a failure here must not block the existing vector
        ingestion path in RAGIndex.add_pdf().
        """
        if not self.store.available:
            logger.debug("Graph store unavailable — skipping graph indexing for %s p.%s", source, page)
            return
        if not chunks:
            return

        chunk_ids: List[str] = []
        total_entities = 0
        total_relationships = 0

        for index, content in enumerate(chunks):
            chunk_id = _chunk_id(source, page, index, content)
            chunk_ids.append(chunk_id)
            try:
                self._write_chunk_node(chunk_id,source,page,index,content,embeddings[index],)
                extraction = extract_entities_relationships(content)
                self._write_entities_and_relationships(chunk_id, extraction)
                total_entities += len(extraction["entities"])
                total_relationships += len(extraction["relationships"])
            except Exception as exc:  # noqa: BLE001 - one bad chunk must not stop ingestion
                logger.error("Graph indexing failed for chunk %d of %s p.%s: %s", index, source, page, exc)

        try:
            self._link_similar_chunks(chunk_ids, chunks)
        except Exception as exc:  # noqa: BLE001
            logger.error("Chunk-similarity linking failed for %s p.%s: %s", source, page, exc)

        logger.info(
            "Graph-indexed %s p.%s: %d chunks, %d entities, %d relationships",
            source, page, len(chunks), total_entities, total_relationships,
        )

    def _write_chunk_node(
    self,
    chunk_id: str,
    source: str,
    page: int,
    index: int,
    content: str,
    embedding,
) -> None:
        self.store.run_write(
            """
            MERGE (c:Chunk {id: $id})
            SET c.source = $source,
                c.page = $page,
                c.index = $index,
                c.content = $content,
                c.embedding = $embedding
            """,
            {
                "id": chunk_id,
                "source": source,
                "page": page,
                "index": index,
                "content": content,
                "embedding": embedding.tolist(),
            }
        )

    def _write_entities_and_relationships(self, chunk_id: str, extraction: dict) -> None:
        canonical_by_raw = {}

        for entity in extraction["entities"]:
            canonical = self.linker.canonicalize(entity["name"], entity["type"])
            canonical_by_raw[entity["name"].strip().lower()] = canonical
            self.store.run_write(
                """
                MATCH (c:Chunk {id: $chunk_id})
                MATCH (e:Entity {id: $entity_id})
                MERGE (c)-[:MENTIONS]->(e)
                """,
                {"chunk_id": chunk_id, "entity_id": canonical["id"]},
            )

        for rel in extraction["relationships"]:
            src_key = rel["source"].strip().lower()
            tgt_key = rel["target"].strip().lower()
            src = canonical_by_raw.get(src_key) or self.linker.canonicalize(rel["source"], "CONCEPT")
            tgt = canonical_by_raw.get(tgt_key) or self.linker.canonicalize(rel["target"], "CONCEPT")
            if src["id"] == tgt["id"]:
                continue
            relation_type = _sanitize_relation(rel["relation"])
            # Relationship type cannot be parameterized in Cypher; it has
            # already been sanitized to [A-Z0-9_] by _sanitize_relation().
            cypher = (
                "MATCH (a:Entity {id: $src_id}) MATCH (b:Entity {id: $tgt_id}) "
                f"MERGE (a)-[:{relation_type}]->(b)"
            )
            self.store.run_write(cypher, {"src_id": src["id"], "tgt_id": tgt["id"]})

    # ------------------------------------------------------------------
    # Better Chunk Connections (blueprint 4.8)
    # ------------------------------------------------------------------
    def _link_similar_chunks(self, chunk_ids: List[str], chunks: List[str]) -> None:
        """
        Reuses chunking.pairwise_chunk_similarity() (added additively to
        chunking.py) to connect semantically related chunks. Pairs above the
        EXTENDS threshold (very high similarity, likely continuation/repeat)
        get an EXTENDS edge; pairs above the base threshold get a lower-
        confidence REFERENCES edge.
        """
        pairs = pairwise_chunk_similarity(chunks, threshold=config.CHUNK_LINK_SIM_THRESHOLD)
        extends_threshold = min(0.95, config.CHUNK_LINK_SIM_THRESHOLD + 0.1)

        for i, j, sim in pairs:
            relation = "EXTENDS" if sim >= extends_threshold else "REFERENCES"
            self.store.run_write(
                f"""
                MATCH (a:Chunk {{id: $id_a}})
                MATCH (b:Chunk {{id: $id_b}})
                MERGE (a)-[r:{relation}]->(b)
                SET r.weight = $weight
                """,
                {"id_a": chunk_ids[i], "id_b": chunk_ids[j], "weight": sim},
            )

    # ------------------------------------------------------------------
    # Incremental Updates (blueprint 4.10)
    # ------------------------------------------------------------------
    def remove_source(self, source: str) -> None:
        """
        Removes all Chunk nodes (and their edges) belonging to `source`, then
        prunes any Entity nodes left with no remaining MENTIONS from any
        other chunk. Called additively from RAGIndex.delete_document().
        """
        if not self.store.available:
            logger.debug("Graph store unavailable — skipping graph deletion for %s", source)
            return

        self.store.run_write(
            "MATCH (c:Chunk {source: $source}) DETACH DELETE c",
            {"source": source},
        )
        self.store.run_write(
            "MATCH (e:Entity) WHERE NOT (e)<-[:MENTIONS]-(:Chunk) DETACH DELETE e"
        )
        logger.info("Removed graph data for source '%s' (and orphaned entities)", source)


# Module-level singleton used by rag_index.py, consistent with the
# graph_store / entity_linker singleton pattern.
graph_builder = KnowledgeGraphBuilder()


if __name__ == "__main__":
    print("Graph builder ready. Store available:", graph_builder.store.available)
