from __future__ import annotations
import logging
from typing import Any, Dict, List, Optional

try:
    from neo4j import GraphDatabase, Driver
    from neo4j.exceptions import Neo4jError, ServiceUnavailable
    _NEO4J_DRIVER_AVAILABLE = True
except ImportError:  # neo4j driver not installed
    GraphDatabase = None  # type: ignore
    Driver = Any  # type: ignore
    Neo4jError = ServiceUnavailable = Exception  # type: ignore
    _NEO4J_DRIVER_AVAILABLE = False

import config

logger = logging.getLogger(__name__)


class GraphStore:
    """
    Connection + query wrapper for the Neo4j graph database.

    Usage:
        store = GraphStore()
        store.run_write("MERGE (e:Entity {id: $id}) SET e.name = $name", {...})
        rows = store.run_read("MATCH (e:Entity) RETURN e LIMIT 5")
    """

    def __init__(
        self,
        uri: Optional[str] = None,
        user: Optional[str] = None,
        password: Optional[str] = None,
        database: Optional[str] = None,
    ) -> None:
        self.uri = uri or config.NEO4J_URI
        self.user = user or config.NEO4J_USER
        self.password = password or config.NEO4J_PASSWORD
        self.database = database or config.NEO4J_DATABASE
        self._driver: Optional["Driver"] = None
        self.available = False

        if not _NEO4J_DRIVER_AVAILABLE:
            logger.warning(
                "neo4j driver package is not installed — graph features are "
                "disabled. Install with `pip install neo4j` to enable GraphRAG."
            )
            return

        self._connect()

    def _connect(self) -> None:
        try:
            self._driver = GraphDatabase.driver(self.uri, auth=(self.user, self.password))
            self._driver.verify_connectivity()
            self.available = True
            logger.info("Connected to Neo4j at %s", self.uri)
            self._ensure_constraints()
        except Exception as exc:  # noqa: BLE001 - any connectivity failure must fail soft
            self._driver = None
            self.available = False
            logger.warning(
                "Could not connect to Neo4j at %s (%s). Graph features will be "
                "skipped and the system will fall back to vector+keyword retrieval.",
                self.uri, exc,
            )

    def _ensure_constraints(self) -> None:
        """Idempotent schema setup — safe to call on every startup."""
        statements = [
            "CREATE CONSTRAINT entity_id IF NOT EXISTS FOR (e:Entity) REQUIRE e.id IS UNIQUE",
            "CREATE CONSTRAINT chunk_id IF NOT EXISTS FOR (c:Chunk) REQUIRE c.id IS UNIQUE",
        ]
        for stmt in statements:
            try:
                self.run_write(stmt)
            except Exception as exc:  # noqa: BLE001
                logger.warning("Could not apply graph constraint (%s): %s", stmt, exc)

    def close(self) -> None:
        if self._driver is not None:
            self._driver.close()
            logger.info("Neo4j connection closed")

    # ------------------------------------------------------------------
    # Query execution
    # ------------------------------------------------------------------
    def run_write(self, cypher: str, params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        return self._run(cypher, params, write=True)

    def run_read(self, cypher: str, params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        return self._run(cypher, params, write=False)

    def _run(
        self, cypher: str, params: Optional[Dict[str, Any]], write: bool
    ) -> List[Dict[str, Any]]:
        if not self.available or self._driver is None:
            logger.debug("GraphStore unavailable — skipping query: %s", cypher[:80])
            return []

        params = params or {}
        try:
            with self._driver.session(database=self.database) as session:
                if write:
                    result = session.execute_write(lambda tx: list(tx.run(cypher, params)))
                else:
                    result = session.execute_read(lambda tx: list(tx.run(cypher, params)))
                return [record.data() for record in result]
        except (Neo4jError, ServiceUnavailable) as exc:
            logger.error("Neo4j query failed (%s): %s", cypher[:120], exc)
            return []
        except Exception as exc:  # noqa: BLE001 - never let a graph failure break the caller
            logger.error("Unexpected graph error (%s): %s", cypher[:120], exc)
            return []

    def health_check(self) -> bool:
        if not self.available or self._driver is None:
            return False
        try:
            self._driver.verify_connectivity()
            return True
        except Exception:  # noqa: BLE001
            self.available = False
            return False
        
    def update_pagerank(self) -> bool:
        """
        Recalculate PageRank for all Entity nodes and store the
        result in Entity.pagerank.
        """

        if not self.available or self._driver is None:
            logger.warning("Neo4j unavailable — skipping PageRank update.")
            return False

        graph_name = "ahrags_pagerank"

        try:
            # Remove an old projection if it exists.
            self.run_write(
                """
                CALL gds.graph.drop($graph_name, false)
                YIELD graphName
                RETURN graphName
                """,
                {"graph_name": graph_name},
            )

            # Create a fresh projection from the current Neo4j graph.
            projection = self.run_read(
                """
                MATCH (source:Entity)-[r]->(target:Entity)
                RETURN gds.graph.project(
                    $graph_name,
                    source,
                    target,
                    {
                        relationshipType: type(r)
                    }
                ) AS graph
                """,
                {"graph_name": graph_name},
            )

            if not projection:
                logger.warning("Could not create PageRank graph projection.")
                return False

            # Calculate PageRank and write it directly to Neo4j.
            result = self.run_write(
                """
                CALL gds.pageRank.write(
                    $graph_name,
                    {
                        writeProperty: 'pagerank'
                    }
                )
                YIELD nodePropertiesWritten, ranIterations, didConverge
                RETURN nodePropertiesWritten, ranIterations, didConverge
                """,
                {"graph_name": graph_name},
            )

            if not result:
                logger.warning("PageRank calculation returned no result.")
                return False

            stats = result[0]

            logger.info(
                "PageRank updated: %s nodes, %s iterations, converged=%s",
                stats.get("nodePropertiesWritten"),
                stats.get("ranIterations"),
                stats.get("didConverge"),
            )

            return True

        except Exception as exc:
            logger.error("PageRank update failed: %s", exc)
            return False

        finally:
            # Remove the in-memory GDS projection.
            try:
                self.run_write(
                    """
                    CALL gds.graph.drop($graph_name, false)
                    YIELD graphName
                    RETURN graphName
                    """,
                    {"graph_name": graph_name},
                )
            except Exception as exc:
                logger.warning(
                    "Could not drop PageRank projection: %s",
                    exc,
                )

# Module-level singleton, analogous to config.embed_model being loaded once.
# Graph modules import `graph_store` from here rather than constructing their
# own GraphStore, so the connection (and its availability state) is shared.
graph_store = GraphStore()


if __name__ == "__main__":
    print("Graph store available:", graph_store.available)
