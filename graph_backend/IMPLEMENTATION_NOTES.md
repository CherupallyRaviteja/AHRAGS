# GraphRAG Migration — Implementation Notes

This is the completed implementation of `GraphRAG_Migration_Blueprint.md`. All files
below are your existing project, upgraded in place — nothing was rewritten from
scratch, and every existing capability (PDF/DOCX ingestion with inline OCR, Postgres
vector+keyword retrieval, Ollama generation, the FastAPI endpoints, the CLI) is
preserved.

## What changed

### New files (blueprint Section 8)
| File | Implements |
|---|---|
| `graph_db.py` | Neo4j connection layer, fail-soft (§4.2) |
| `entity_extractor.py` | LLM-based entity/relationship extraction (§4.1) |
| `entity_linker.py` | Canonical entity resolution via embedding similarity (§4.5) |
| `graph_builder.py` | Knowledge graph construction + incremental removal (§4.1, §4.8, §4.10) |
| `query_planner.py` | Query intent classification (§4.11) |
| `graph_retriever.py` | Multi-hop traversal, relationship-aware retrieval, context expansion (§4.3, §4.4, §4.6, §4.7) |
| `hybrid_ranker.py` | Weighted merge of vector + graph signals, explainability (§4.12, §4.13) |
| `context_builder.py` | Final context/provenance assembly (§4.6, §4.7) |
| `graph_viz.py` | PyVis subgraph rendering for debugging (§4.9) |

### Modified files (blueprint Section 9)
| File | Change |
|---|---|
| `config.py` | Additive: Neo4j credentials, feature flags, thresholds, hybrid-ranking weights, centralized logging setup |
| `chunking.py` | Additive: `pairwise_chunk_similarity()` reusing `agentic_chunking`'s existing cosine-similarity primitive |
| `rag_index.py` | `add_pdf()` and `delete_document()` each gained one guarded, fail-soft call into the graph layer |
| `controller.py` | `main()` now optionally routes through query planning + graph retrieval + hybrid ranking; returns a 4th value (`provenance`) |
| `generator.py` | `generate_answer()` gained one optional `graph_context` parameter (default `None` — identical behavior to before when omitted) |
| `api.py` | `/chat` re-enables the `sources`/`score` fields it already computed but had commented out, adds `provenance`; new `/graph/visualize` and `/graph/status` debug endpoints |
| `chatbot.py` | Q&A branch now calls `controller.main()` instead of duplicating its logic inline, for CLI/API parity (optional, per blueprint Phase 5) |

### Unchanged, as specified by the blueprint
`document_loader.py`, `ocr_tables.py`, `ocr_utils.py`, `db_init.py`, `query_rewriter.py`, `main.py` (confirmed dead/unrelated scaffold, left untouched).

## Fail-soft design

Every graph-touching code path is wrapped so that a missing dependency, an
unreachable Neo4j instance, or a malformed LLM response degrades to the
existing vector+keyword behavior instead of raising:

- `graph_db.GraphStore` catches `ImportError` on the `neo4j` package and
  connection errors on startup; every query method becomes a no-op returning `[]`.
- `rag_index.RAGIndex.add_pdf` / `delete_document` wrap their new graph
  calls in `try/except`, logging and continuing — the Postgres/vector path
  always completes.
- `controller.main()` wraps query classification, graph retrieval, and
  hybrid ranking each in their own `try/except`, falling back to the
  original vector-only response shape at any failure point.
- `generator.generate_answer`'s new `graph_context` parameter defaults to
  `None`, so every pre-existing call site is byte-for-byte unaffected.

This was verified with the test project's own logic (`hybrid_ranker.merge`,
`context_builder.build_context`, `entity_extractor`'s JSON parsing,
`query_planner`'s classification parsing, and `graph_db.GraphStore`'s
no-driver-installed fallback) — see the session transcript for the actual
test runs. Full end-to-end testing requires your Postgres, Neo4j, and Ollama
instances, which aren't available in this environment.

## New configuration (environment variables, all optional — sensible defaults provided)

```
ENABLE_GRAPH_INDEXING=true      # default true — set false to disable graph writes on ingest
ENABLE_GRAPH_RETRIEVAL=true     # default true — set false to disable graph-aware retrieval
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=<your password>
NEO4J_DATABASE=neo4j
ENTITY_EXTRACTION_MODEL=phi3:mini   # defaults to config.MODEL if unset
```

## New dependencies

See `requirements-graphrag.txt`:
```
neo4j>=5.19,<6.0
pyvis>=0.3.2
```
Install alongside your existing requirements (fastapi, psycopg2, sentence-transformers,
nltk, PyPDF2, pymupdf, python-docx, paddleocr, opencv-python, tqdm, uvicorn, requests).

## Getting it running

1. `pip install -r requirements-graphrag.txt` (plus your existing project's requirements).
2. Start Neo4j (e.g. `docker run -p 7474:7474 -p 7687:7687 -e NEO4J_AUTH=neo4j/<password> neo4j:5`)
   and set `NEO4J_PASSWORD` to match.
3. Everything else starts exactly as before: `python -m uvicorn api:app --reload` or `python chatbot.py`.
4. Upload a document — it will be indexed into both Postgres (as before) and Neo4j (new).
5. Ask a relationship/comparison/multi-hop question and check the `/chat` response's
   new `provenance` field, or hit `GET /graph/visualize` to see the graph.
6. If you want to confirm graph features aren't required, set
   `ENABLE_GRAPH_INDEXING=false` and `ENABLE_GRAPH_RETRIEVAL=false` — the system
   returns to its exact pre-migration behavior.

## Requirement coverage

| Blueprint requirement | Status |
|---|---|
| 1. Knowledge Graph Creation | ✅ `graph_builder.py` + `entity_extractor.py` |
| 2. Graph Database | ✅ Neo4j via `graph_db.py` |
| 3. Hybrid Retrieval | ✅ `graph_retriever.py` + `hybrid_ranker.py` alongside unmodified `RAGIndex.retrieve` |
| 4. Multi-hop Reasoning | ✅ `GraphRetriever._expand_entities` (configurable hop depth) |
| 5. Entity Linking | ✅ `entity_linker.py` |
| 6. Context Expansion | ✅ `GraphRetriever._collect_chunks` (linked-chunk expansion) + `context_builder.py` |
| 7. Relationship-aware Retrieval | ✅ graph path rendering in `context_builder.py` / `generator.py`'s `graph_context` |
| 8. Better Chunk Connections | ✅ `chunking.pairwise_chunk_similarity` + `graph_builder._link_similar_chunks` |
| 9. Graph Visualization | ✅ `graph_viz.py` (PyVis) + Neo4j Browser + `GET /graph/visualize` |
| 10. Incremental Updates | ✅ per-document indexing in `add_pdf`, `graph_builder.remove_source` on delete |
| 11. Query Planning | ✅ `query_planner.py` |
| 12. Hybrid Ranking | ✅ `hybrid_ranker.py` (`config.HYBRID_WEIGHTS`) |
| 13. Explainability | ✅ `provenance` returned by `controller.main` and `/chat` |
| 14. Existing Features Preserved | ✅ feature flags + fail-soft design throughout |
