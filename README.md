# AHRAGS --- Agentic Hybrid Retrieval-Augmented Generation System

AHRAGS is a document-based question-answering system that combines
**relational retrieval** and **GraphRAG-based retrieval** to provide
grounded answers from uploaded documents.

The project contains **two independent backends** behind a shared React
frontend:

-   **Relational Backend** --- PostgreSQL-based document storage and
    retrieval.
-   **Graph Backend** --- Neo4j-based knowledge graph, graph retrieval,
    hybrid ranking, PageRank, and grounded LLM generation.

The **Graph Backend** is the primary GraphRAG implementation.

------------------------------------------------------------------------

## Features

-   PDF document upload and ingestion
-   Document listing and deletion
-   PostgreSQL-based relational document storage
-   Neo4j knowledge graph construction
-   LLM-based entity and relationship extraction
-   Generic entity filtering and entity normalization
-   Direct, 1-hop, and multi-hop graph retrieval
-   Hybrid ranking using vector, keyword, graph, relationship, and node-importance signals
-   Neo4j GDS PageRank for entity importance
-   Automatic PageRank updates after graph changes
-   Source and retrieval provenance tracking
-   Local LLM generation using Ollama and Gemma 2B
-   Grounded answer generation
-   `"I don't know"` behavior for unsupported questions
-   React + FastAPI integration
-   Local/offline-first architecture

------------------------------------------------------------------------

## System Architecture

``` mermaid
flowchart TD
    U[User] --> F[React Frontend]
    F --> API[FastAPI API]

    API --> RB[Relational Backend]
    API --> GB[Graph Backend]

    subgraph RB[Relational Backend]
        PG[(PostgreSQL)]
        RR[Relational Retrieval]
        PG --> RR
    end

    subgraph GB[Graph Backend]
        ING[PDF Ingestion]
        EXT[Entity and Relationship Extraction]
        FIL[Entity Filtering and Normalization]
        NEO[(Neo4j)]
        PR[Neo4j GDS PageRank]
        GR[Graph Retriever]
        HR[Hybrid Ranker]
        CB[Context Builder]
        LLM[Ollama + Gemma 2B]

        ING --> EXT
        EXT --> FIL
        FIL --> NEO
        NEO --> PR
        NEO --> GR
        PR --> GR
        GR --> HR
        HR --> CB
        CB --> LLM
    end

    API --> GB
    LLM --> API
    API --> F
    F --> U
```

------------------------------------------------------------------------

## Two-Backend Architecture

### Relational Backend Workflow

The relational backend provides the conventional document retrieval
path:

``` text
PDF
 ↓
Document Processing
 ↓
PostgreSQL
 ↓
Vector / Text Retrieval
 ↓
Retrieved Context
 ↓
Answer Generation
```

### Graph Backend Workflow

The Graph backend provides relationship-aware GraphRAG:

``` text
PDF
 ↓
Chunking
 ↓
Entity & Relationship Extraction
 ↓
Entity Filtering & Normalization
 ↓
Neo4j Knowledge Graph
 ↓
PageRank
 ↓
Graph Retrieval
 ↓
Hybrid Ranking
 ↓
Context Builder
 ↓
Gemma 2B
 ↓
Grounded Answer
```

------------------------------------------------------------------------

## GraphRAG Pipeline

### 1. Document Ingestion

Uploaded PDF documents are processed into chunks. The chunks are used as
the source material for retrieval and graph construction.

### 2. Entity and Relationship Extraction

The local extraction model identifies meaningful entities and
relationships explicitly supported by the document.

Generic entities such as broad labels like `Country`, `Organization`,
and `Concept` are excluded to reduce graph noise.

### 3. Knowledge Graph Construction

Entities become nodes and extracted relationships become edges in Neo4j.

Example:

``` text
Energy
   │
   ├── USES ──> Biomass
   │
   └── REQUIRES ──> Industry
```

### 4. PageRank

Neo4j GDS PageRank calculates an importance score for graph entities.
The score is stored on entity nodes and can contribute to retrieval
ranking.

PageRank is refreshed when the graph is updated.

### 5. Graph Retrieval

The graph retriever searches the knowledge graph using entities
identified from the query.

It supports:

-   Direct entity retrieval
-   1-hop retrieval
-   Multi-hop retrieval

Graph results retain provenance such as:

-   matched entity
-   hop distance
-   relationship type
-   graph path
-   source chunk

### 6. Hybrid Ranking

Candidate results are ranked using multiple signals, including:

-   Vector relevance
-   Keyword relevance
-   Graph distance
-   Relationship strength
-   Node importance / PageRank
-   Entity frequency

### 7. Context Builder

The context builder converts ranked candidates into the final context
supplied to the language model while preserving source and provenance
information.

### 8. Grounded Generation

Gemma 2B runs locally through Ollama. The model is instructed to answer
from the supplied context and avoid unsupported information.

When sufficient evidence is unavailable:

``` text
I don't know.
```

------------------------------------------------------------------------

## Query Flow

``` mermaid
sequenceDiagram
    participant User
    participant Frontend
    participant API as FastAPI
    participant Graph as Graph Backend
    participant Ranker as Hybrid Ranker
    participant Context as Context Builder
    participant LLM as Gemma 2B

    User->>Frontend: Ask question
    Frontend->>API: POST /chat
    API->>Graph: Retrieve graph candidates
    Graph-->>API: Results + provenance
    API->>Ranker: Rank candidates
    Ranker-->>API: Ranked results
    API->>Context: Build grounded context
    Context-->>API: Final context
    API->>LLM: Generate answer
    LLM-->>API: Grounded response
    API-->>Frontend: Response + sources + provenance
    Frontend-->>User: Display answer
```

------------------------------------------------------------------------

## API Endpoints

### Health Check

``` http
GET /
```

### Chat

``` http
POST /chat
```

Example:

``` json
{
  "message": "What are the main energy resources in India?"
}
```

### Upload Document

``` http
POST /upload
```

Uploads and processes a PDF document.

### List Documents

``` http
GET /documents
```

Returns the documents currently available to the backend.

### Delete Document

``` http
DELETE /documents/{doc_name}
```

Deletes the document and synchronizes graph data when graph indexing is
enabled.

------------------------------------------------------------------------

## Project Structure

``` text
AHRAGS/
│
├── frontend/
│   ├── src/
│   ├── public/
│   ├── package.json
│   └── ...
│
├── graph_backend/
│   ├── main.py
│   ├── controller.py
│   ├── graph_db.py
│   ├── graph_builder.py
│   ├── graph_retriever.py
│   ├── entity_extractor.py
│   ├── entity_linker.py
│   ├── hybrid_ranker.py
│   ├── context_builder.py
│   ├── query_planner.py
│   ├── generator.py
│   └── ...
│
├── relational_backend/
│   └── ...
│
├── screenshots/
├── .gitignore
├── requirements.txt
├── package.json
├── package-lock.json
└── README.md
```

------------------------------------------------------------------------

## Technology Stack

### Frontend

-   React
-   Vite
-   JavaScript
-   Axios
-   Tailwind CSS

### Graph Backend

-   Python
-   FastAPI
-   Neo4j
-   Neo4j GDS
-   Ollama
-   Gemma 2B
-   Sentence Transformers
-   GraphRAG

### Relational Backend

-   Python
-   FastAPI
-   PostgreSQL
-   Vector / text retrieval

### Development

-   Git
-   GitHub
-   VS Code

------------------------------------------------------------------------

## Local / Offline Architecture

AHRAGS is designed around locally running components:

``` text
React
  ↓
FastAPI
  ↓
Local PostgreSQL / Local Neo4j
  ↓
Local Retrieval
  ↓
Local Ollama
  ↓
Gemma 2B
```

The GraphRAG generation pipeline does not require an external LLM API
when the required models and databases are installed locally.

------------------------------------------------------------------------

## Evaluation

The system is evaluated using:

1.  Direct factual questions
2.  Relationship questions
3.  Multi-context questions
4.  Unsupported questions
5.  Multi-hop graph questions
6.  Final ranking inspection
7.  Retrieval and generation latency

For unsupported questions, the expected behavior is:

``` text
I don't know.
```

------------------------------------------------------------------------

## Example Questions

``` text
What are the main energy resources mentioned in the document?

Why is India's energy demand increasing?

What industries require large amounts of energy?

What renewable energy resources are mentioned?

How can renewable energy help India meet its growing energy needs?

What is the average monthly electricity bill for a household in India?
```

The last question should produce `"I don't know"` when the document does
not contain that information.

------------------------------------------------------------------------

## Key Design Goals

-   Ground answers in retrieved document evidence
-   Use graph relationships for relationship-aware retrieval
-   Reduce generic and meaningless graph entities
-   Preserve retrieval provenance
-   Automatically maintain PageRank values
-   Keep relational and graph implementations separate
-   Provide a local-first architecture
-   Prevent unsupported answers and hallucinated information

------------------------------------------------------------------------

## Future Improvements

-   More advanced graph candidate filtering
-   Improved multi-hop retrieval
-   Larger evaluation datasets and quantitative retrieval metrics
-   Context compression
-   More advanced query planning
-   Retrieval and generation optimization
-   Additional graph-ranking signals
-   Improved graph provenance visualization

------------------------------------------------------------------------

## License

This project is intended for educational, research, and portfolio
purposes.
