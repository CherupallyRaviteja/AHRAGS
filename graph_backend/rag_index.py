import os
import logging
from config import embed_model
import config
from chunking import watson_chunking
from document_loader import test_ocr

logger = logging.getLogger(__name__)

class RAGIndex:

    def add_pdf(self, path):
        pages = test_ocr(path)
        total_chunks = 0
        source_name = os.path.basename(path)

        for page_num, page_text in pages:

            chunks = watson_chunking(page_text)
            total_chunks += len(chunks)
            vectors = embed_model.encode(chunks, convert_to_numpy=True)

            for c, v in zip(chunks, vectors):
                self.buffer.append({
                    "source": source_name,
                    "page": page_num,
                    "content": c,
                    "embedding": v
                })

            # --- GraphRAG addition (blueprint Section 4.1 / 4.14) ---------
            # Additive, non-blocking: builds/extends the knowledge graph for
            # this page's chunks. Guarded by the feature flag and internally
            # fail-soft (graph_builder / graph_db never raise), so the
            # existing vector ingestion above is unaffected if this fails or
            # is disabled.
            if config.ENABLE_GRAPH_INDEXING:
                try:
                    from graph_builder import graph_builder
                    graph_builder.index_chunks(chunks, vectors, source_name, page_num)
                except Exception as exc:  # noqa: BLE001
                    logger.error(
                        "Graph indexing failed for %s p.%s (vector ingestion unaffected): %s",
                        source_name, page_num, exc,
                    )
            # Update PageRank once after the complete document
            # has been added to the graph.
            if config.ENABLE_GRAPH_INDEXING:
                try:
                    from graph_db import graph_store

                    if graph_store.update_pagerank():
                        logger.info(
                            "PageRank updated successfully after "
                            "ingesting %s",
                            source_name,
                        )
                    else:
                        logger.warning(
                            "PageRank update failed for %s",
                            source_name,
                        )

                except Exception as exc:
                    logger.error(
                        "PageRank update failed for %s: %s",
                        source_name,
                        exc,
                    )       
            # ----------------------------------------------------------------

        logger.info("PDF ADDED (%s): %d chunks", source_name, total_chunks)
        print(f"PDF ADDED ✅ (Total chunks: {total_chunks})")
    
    def get_documents(self):
        """Return documents currently indexed in the Neo4j graph."""

        if not config.ENABLE_GRAPH_INDEXING:
            return []

        try:
            from graph_db import graph_store

            rows = graph_store.run_read(
                """
                MATCH (c:Chunk)
                RETURN DISTINCT c.source AS name
                ORDER BY name
                """
            )

            return [
                {"name": row["name"]}
                for row in rows
                if row.get("name")
            ]

        except Exception as exc:
            logger.error(
                "Failed to fetch documents from Neo4j: %s",
                exc,
            )
            return []
    
    def delete_document(self, doc_name):
        """Delete a document and its graph data from Neo4j."""

        if not config.ENABLE_GRAPH_INDEXING:
            logger.warning(
                "Graph indexing is disabled — cannot delete graph document: %s",
                doc_name,
            )
            return False

        try:
            from graph_builder import graph_builder
            from graph_db import graph_store

            # Check that the document exists.
            rows = graph_store.run_read(
                """
                MATCH (c:Chunk {source: $source})
                RETURN count(c) AS count
                """,
                {"source": doc_name},
            )

            if not rows or rows[0]["count"] == 0:
                logger.warning(
                    "Document not found in Neo4j: %s",
                    doc_name,
                )
                return False

            # Remove chunks, relationships and orphaned entities.
            graph_builder.remove_source(doc_name)

            # Graph changed, so PageRank must be recalculated.
            graph_store.update_pagerank()

            logger.info(
                "Document deleted from Neo4j: %s",
                doc_name,
            )

            print(f"{doc_name} deleted ✅")

            return True

        except Exception as exc:
            logger.error(
                "Graph document deletion failed for %s: %s",
                doc_name,
                exc,
            )
            return False
    
if __name__ == "__main__":
    print("✅ RAG index ready")
