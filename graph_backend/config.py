import os
import logging
import nltk
from sentence_transformers import SentenceTransformer

nltk.download('punkt', quiet=True)

# ---------------------------------------------------------------------------
# Centralized logging configuration.
# config.py is the first internal module imported by every entry point
# (api.py, chatbot.py, controller.py, rag_index.py, ...), so this is the
# single place logging is initialized for the whole project. Modules obtain
# their logger with `logging.getLogger(__name__)` and inherit this config.
# ---------------------------------------------------------------------------
from neo4j_manager import ensure_neo4j_running

ensure_neo4j_running()


LOG_LEVEL = os.environ.get("AHRAGS_LOG_LEVEL", "INFO").upper()

if not logging.getLogger().handlers:
    logging.basicConfig(
        level=LOG_LEVEL,
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

logger = logging.getLogger("ahrags")

OLLAMA_URL = 'http://localhost:11434'
MODEL = 'gemma:2b'
EMBED_MODEL = 'all-MiniLM-L6-v2'
EMBED_DIM = 384
SIM_THRESHOLD = 0.3
FAISS_TOP_K = 4
SENT_SIM_THRESHOLD = 0.7

POPPLER_BIN = r"C:\poppler\Library\bin"
if POPPLER_BIN not in os.environ["PATH"]:
    os.environ["PATH"] = POPPLER_BIN + os.pathsep + os.environ["PATH"]

embed_model = SentenceTransformer(EMBED_MODEL)

# ---------------------------------------------------------------------------
# GraphRAG configuration
# Added per GraphRAG_Migration_Blueprint.md, Section 5 ("Feature-Flag
# Rollout") and Section 2 ("Graph Database"). All existing configuration
# above this block is unchanged.
# ---------------------------------------------------------------------------

# Feature flags. With both False, the system behaves exactly as the
# pre-GraphRAG implementation (blueprint Section 4.14 / Section 5).
# Defaulted to True here for the completed migration (blueprint Phase 5 —
# cutover); every graph-touching code path is fail-soft (see graph_db.py,
# rag_index.py, controller.py) so a missing/unreachable Neo4j instance
# degrades to vector-only behavior instead of breaking the API.
ENABLE_GRAPH_INDEXING = os.environ.get("ENABLE_GRAPH_INDEXING", "true").lower() == "true"
ENABLE_GRAPH_RETRIEVAL = os.environ.get("ENABLE_GRAPH_RETRIEVAL", "true").lower() == "true"

# Neo4j connection (blueprint Section 4.2 — Neo4j recommended as primary
# graph store; falls back gracefully if unreachable).
NEO4J_URI = os.environ.get("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.environ.get("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.environ.get("NEO4J_PASSWORD", os.environ.get("Neo4j_Password", ""))
NEO4J_DATABASE = os.environ.get("NEO4J_DATABASE", "neo4j")

# Entity extraction (blueprint Section 4.1). Reuses the same Ollama model
# used elsewhere (query_rewriter.py, generator.py) unless overridden.
ENTITY_EXTRACTION_MODEL = os.environ.get("ENTITY_EXTRACTION_MODEL", "gemma:2b")
ENTITY_EXTRACTION_TIMEOUT = 90

# Entity linking (blueprint Section 4.5). Same style of threshold constant
# as the existing SIM_THRESHOLD / SENT_SIM_THRESHOLD above.
ENTITY_LINK_THRESHOLD = 0.85

# Chunk-connection edges (blueprint Section 4.8). Reuses the similarity
# style already used by chunking.agentic_chunking / SENT_SIM_THRESHOLD.
CHUNK_LINK_SIM_THRESHOLD = 0.8

# Multi-hop reasoning (blueprint Section 4.4).
GRAPH_MAX_HOPS = 2
GRAPH_TOP_K_ENTITIES = 5
GRAPH_TOP_K_CHUNKS = 5

# Hybrid ranking weights (blueprint Section 4.12). Mirrors the existing
# 0.6 / 0.4 vector+keyword weighting already used in rag_index.RAGIndex.retrieve.
HYBRID_WEIGHTS = {
    "vector": 0.45,
    "keyword": 0.15,
    "graph_distance": 0.15,
    "relationship_relevance": 0.10,
    "node_importance": 0.10,
    "entity_frequency": 0.05,
}

# Query planner (blueprint Section 4.11).
QUERY_TYPES = (
    "fact_lookup",
    "relationship_lookup",
    "multi_hop",
    "comparison",
    "summary",
    "recommendation",
)
GRAPH_ROUTED_QUERY_TYPES = {"relationship_lookup", "multi_hop", "comparison"}

if __name__ == "__main__":
    print("✅ Config loaded")
    print("Model:", MODEL)
    print("Embedding dim:", EMBED_DIM)
    print("Graph indexing enabled:", ENABLE_GRAPH_INDEXING)
    print("Graph retrieval enabled:", ENABLE_GRAPH_RETRIEVAL)
