from __future__ import annotations
import hashlib
import logging
from typing import Dict, List, Optional, Tuple
import numpy as np
import config
from graph_db import GraphStore, graph_store as default_graph_store

logger = logging.getLogger(__name__)


def _cosine_sim(a: np.ndarray, b: np.ndarray) -> float:
    denom = (np.linalg.norm(a) * np.linalg.norm(b))
    if denom == 0:
        return 0.0
    return float(np.dot(a, b) / denom)


def _canonical_id(name: str, entity_type: str) -> str:
    key = f"{entity_type.upper()}::{name.strip().lower()}"
    return hashlib.sha1(key.encode("utf-8")).hexdigest()[:16]


class EntityLinker:
    """
    Canonicalizes raw entity mentions extracted by entity_extractor.py into
    stable canonical entities, deduplicating near-identical surface forms.
    """

    def __init__(self, store: Optional[GraphStore] = None) -> None:
        self.store = store or default_graph_store
        # entity_type -> list of (canonical_id, canonical_name, embedding)
        self._cache: Dict[str, List[Tuple[str, str, np.ndarray]]] = {}
        self._loaded_types: set = set()

    def _load_type(self, entity_type: str) -> None:
        if entity_type in self._loaded_types or not self.store.available:
            return
        rows = self.store.run_read(
            "MATCH (e:Entity {type: $type}) RETURN e.id AS id, e.name AS name",
            {"type": entity_type},
        )
        entries = []
        if rows:
            names = [r["name"] for r in rows]
            try:
                embeddings = config.embed_model.encode(names, convert_to_numpy=True)
            except Exception as exc:  # noqa: BLE001
                logger.error("Failed to embed existing entities for linking: %s", exc)
                embeddings = []
            for row, emb in zip(rows, embeddings):
                entries.append((row["id"], row["name"], emb))
        self._cache[entity_type] = entries
        self._loaded_types.add(entity_type)
        logger.debug("Loaded %d canonical entities of type %s", len(entries), entity_type)

    def canonicalize(self, name: str, entity_type: str) -> Dict[str, str]:
        """
        Resolve a raw entity mention to a canonical entity.

        Returns {"id": canonical_id, "name": canonical_name, "type": entity_type}.
        If a sufficiently similar canonical entity already exists
        (cosine similarity >= config.ENTITY_LINK_THRESHOLD), it is reused and
        the mention is recorded as an alias. Otherwise a new canonical entity
        is created.
        """
        name = name.strip()
        entity_type = (entity_type or "CONCEPT").strip().upper()
        if not name:
            raise ValueError("entity name must not be empty")

        self._load_type(entity_type)

        try:
            mention_embedding = config.embed_model.encode(name, convert_to_numpy=True)
        except Exception as exc:  # noqa: BLE001
            logger.error("Failed to embed entity mention '%s': %s", name, exc)
            mention_embedding = None

        best_match: Optional[Tuple[str, str, float]] = None
        if mention_embedding is not None:
            for canon_id, canon_name, emb in self._cache.get(entity_type, []):
                sim = _cosine_sim(mention_embedding, emb)
                if sim >= config.ENTITY_LINK_THRESHOLD and (best_match is None or sim > best_match[2]):
                    best_match = (canon_id, canon_name, sim)

        if best_match is not None:
            canon_id, canon_name, sim = best_match
            logger.debug("Linked mention '%s' -> canonical '%s' (sim=%.3f)", name, canon_name, sim)
            self._record_alias(canon_id, name)
            return {"id": canon_id, "name": canon_name, "type": entity_type}

        # No match — create a new canonical entity.
        canon_id = _canonical_id(name, entity_type)
        self.store.run_write(
            """
            MERGE (e:Entity {id: $id})
            ON CREATE SET e.name = $name, e.type = $type, e.aliases = [$name]
            """,
            {"id": canon_id, "name": name, "type": entity_type},
        )
        if mention_embedding is not None:
            self._cache.setdefault(entity_type, []).append((canon_id, name, mention_embedding))
        logger.debug("Created new canonical entity '%s' (%s)", name, entity_type)
        return {"id": canon_id, "name": name, "type": entity_type}

    def _record_alias(self, canonical_id: str, alias: str) -> None:
        self.store.run_write(
            """
            MATCH (e:Entity {id: $id})
            SET e.aliases = CASE
                WHEN e.aliases IS NULL THEN [$alias]
                WHEN NOT $alias IN e.aliases THEN e.aliases + $alias
                ELSE e.aliases
            END
            """,
            {"id": canonical_id, "alias": alias},
        )


# Module-level singleton for reuse across graph_builder calls within a
# process, analogous to graph_db.graph_store.
entity_linker = EntityLinker()


if __name__ == "__main__":
    print(entity_linker.canonicalize("Artificial Intelligence", "TECHNOLOGY"))
    print(entity_linker.canonicalize("AI", "TECHNOLOGY"))
