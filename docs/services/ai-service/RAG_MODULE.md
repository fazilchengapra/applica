# RAG Module

This module handles the **Retrieval-Augmented Generation (RAG)** functionality inside the FastAPI application.

The module is designed to support:

- Document ingestion
- Incremental document updates
- Section/chunk-level change detection
- Chunking with overlap
- Embedding generation
- Vector database updates
- Document and chunk metadata management
- Retrieval from the vector database

## Folder Structure

```text
rag/
│
├── __init__.py
├── schemas.py
├── constants.py
│
├── services/
│   ├── ingestion.py
│   ├── chunking.py
│   ├── change_detection.py
│   └── embedding.py
│
├── repositories/
│   ├── document.py
│   ├── chunk.py
│   └── vector.py
│
├── models/
│   ├── document.py
│   └── chunk.py
│
├── loaders/
│   ├── base.py
│   ├── pdf.py
│   ├── docx.py
│   ├── html.py
│   ├── txt.py
│   └── factory.py
│
└── utils/
    └── hashing.py
```

---

## 1. `__init__.py`

Marks the `rag` directory as a Python package.

It can also be used to expose important objects from the module.

Example:

```python
from .schemas import LoadedDocument
```

Usually, this file can remain empty.

---

## 2. `api/v1/rag.py`

### Responsibility

Contains the **FastAPI API endpoints** related to RAG.

The router file lives in `app/api/v1/` (not inside the module) because
routers are registered centrally there and mounted under
`/api/ai/v1/<prefix>` — this module is served at `/api/ai/v1/rag`.

The router should handle HTTP requests and responses.

It should **not contain the actual ingestion or chunking logic**.

Example endpoints:

```text
GET    /rag/document-types   (list the doc-type catalog)
POST   /rag/document-types   (create a doc type)
PUT    /rag/document-types/{document_type_id} (rename / re-describe a type)
POST   /rag/load         (parse an upload into the common document format)
POST   /rag/ingest
POST   /rag/documents/{document_id}/update
DELETE /rag/documents/{document_id}
POST   /rag/search
```

Doc types are a **catalog table** (`document_types`), not code, so a business
can add categories like `shareholder-agreement` without a deploy. The five
built-ins (`financial`, `employee`, `investor`, `policy`, `other`) are seeded
by migration `eabb2273e3b3` and managed through the CRUD routes above.

Example:

```python
@router.post("/ingest")
async def ingest_document(request: IngestRequest):
    return await ingestion_service.ingest(request)
```

### Think of it as

```text
HTTP request
     ↓
api/v1/rag.py
     ↓
service
```

---

## 3. `schemas.py`

### Responsibility

Contains **Pydantic request and response schemas**.

It defines what data the API accepts and returns.

Example:

```python
class IngestRequest(BaseModel):
    document_id: str
    source: str
    content: str
```

Response:

```python
class IngestResponse(BaseModel):
    document_id: str
    status: str
    chunks_processed: int
```

### Think of it as

```text
API data contract
```

It tells the frontend/API consumer:

> "This is the data you need to send and this is what you will receive."

---

## 4. `services/ingestion.py`

### Responsibility

This is the **main ingestion orchestrator**.

It coordinates the complete ingestion workflow.

```text
Document
   ↓
Parse
   ↓
Detect changes
   ↓
Chunk
   ↓
Compare chunks
   ↓
Generate embeddings
   ↓
Update vector DB
   ↓
Save metadata
```

Example:

```python
async def ingest_document(document):

    sections = parse_document(document)

    changes = detect_changes(sections)

    for section in changes:
        chunks = chunk_section(section)

        changed_chunks = compare_chunks(chunks)

        embeddings = generate_embeddings(changed_chunks)

        update_vectors(embeddings)
```

### Important

This file **coordinates** the process.

It should not contain:

- SQL queries
- Hashing implementation
- Chunking algorithm
- Vector DB implementation

Those responsibilities belong to other files.

---

## 5. `services/chunking.py`

### Responsibility

Responsible for converting document content into chunks.

For example:

```text
Document
   ↓
Section
   ↓
Chunk 1
Chunk 2
Chunk 3
```

It also manages **chunk overlap**.

Example:

```python
chunk_size = 500
chunk_overlap = 100
```

Conceptually:

```text
Chunk 1
[------------------------------------]
                    100 tokens overlap
                    ↓
             Chunk 2
             [------------------------------------]
```

If a section changes, this service creates the new chunks using the same chunking configuration.

### Think of it as

> "How should a large document be divided into smaller pieces?"

---

## 6. `services/change_detection.py`

### Responsibility

Determines what changed between the old and new version of a document.

Possible states:

```text
NEW
UNCHANGED
MODIFIED
DELETED
```

For example:

```text
Old:

Introduction → A123
Payment      → B456
Refund       → C789


New:

Introduction → A123
Payment      → B456
Refund       → XYZ999
```

Result:

```text
Introduction → UNCHANGED
Payment      → UNCHANGED
Refund       → MODIFIED
```

This prevents unnecessary re-processing.

### Why is this important?

Without change detection:

```text
1000 chunks
    ↓
1000 embeddings
```

With change detection:

```text
1000 chunks
    ↓
990 unchanged → SKIP
10 changed    → EMBED
```

This reduces processing time and embedding cost.

---

## 7. `services/embedding.py`

### Responsibility

Responsible for converting text chunks into vectors.

Example:

```text
"Employees can work remotely..."
              ↓
         Embedding Model
              ↓
[0.021, -0.183, 0.442, ...]
```

It should contain functionality such as:

```python
generate_embedding(text)
```

and preferably batch processing:

```python
generate_embeddings(chunks)
```

Example:

```python
embeddings = embedding_service.generate_embeddings(
    chunks
)
```

The rest of the RAG module should not need to know which embedding model is being used.

---

## 8. `repositories/document.py`

### Responsibility

Handles database operations related to documents.

For example:

```python
get_document(document_id)

create_document(document)

update_document(document)

get_document_version(document_id)

delete_document(document_id)
```

This file contains **database access logic**.

For example:

```text
services/ingestion.py
        ↓
repositories/document.py
        ↓
PostgreSQL
```

The service decides **what should happen**.

The repository decides **how to access the database**.

---

## 9. `repositories/chunk.py`

### Responsibility

Handles database operations related to chunks.

Examples:

```python
get_chunks(document_id)

get_chunk(chunk_id)

save_chunk(chunk)

update_chunk(chunk)

delete_chunks(chunk_ids)

find_changed_chunks(...)
```

It stores metadata about chunks such as:

```text
chunk_id
document_id
section_id
content_hash
chunk_index
version
vector_id
```

---

## 10. `repositories/vector.py`

### Responsibility

Handles communication with the **vector database**.

The vector database could be:

```text
pgvector
Qdrant
Pinecone
Weaviate
Chroma
```

The rest of the RAG module shouldn't need to know which one you're using.

Example interface:

```python
upsert(vector_id, embedding, metadata)

delete(vector_ids)

search(query_embedding, limit)
```

For example:

```python
vector_repository.upsert(
    vector_id=chunk.id,
    embedding=embedding,
    metadata=metadata
)
```

### Why separate this?

If you later change:

```text
Qdrant
   ↓
pgvector
```

you should mainly change:

```text
repositories/vector.py
```

instead of changing the entire RAG module.

---

## 11. `models/document.py`

### Responsibility

Contains the **database model representing a document** (implemented, table `documents`):

```python
class Document(Base):
    id            # UUID, gen_random_uuid()
    doc_type      # "financial" | "employee" | "investor" | "policy" | "other"
    title
    version       # int, default 1
    content_hash  # String(64), SHA-256 of the ingested content
    access_level  # "public" | "internal" | "restricted"
    status        # "pending" | "processing" | "completed" | "failed"
    created_at
    updated_at
```

Enums (`DocType`, `AccessLevel`, `DocumentStatus`) live in `constants.py` as
`str(Enum)` and are backed by native Postgres enum types
(`document_doc_type`, `document_access_level`, `document_status`).

This represents information about the document itself.

Example:

```text
id: 4f7a...-9c2d
doc_type: policy
title: Parental Leave Policy
version: 5
content_hash: abc123
access_level: internal
status: completed
```

---

## 12. `models/chunk.py`

### Responsibility

Contains the **database model representing an individual chunk** (implemented, table `chunks`):

```python
class Chunk(Base):
    id            # UUID, gen_random_uuid()
    document_id   # FK -> documents.id, ON DELETE CASCADE
    doc_type      # denormalized from the document (row-level scoping)
    access_level  # denormalized (public | internal | restricted)
    section_id
    heading_path
    chunk_index
    content
    content_hash  # String(64), SHA-256 of the chunk text
    embedding     # pgvector Vector(1024), nullable until embedded
    created_at
    updated_at
```

Chunks are keyed by `(document_id, chunk_index)` (unique) and `doc_type` /
`access_level` are denormalized so retrieval can filter by type and privilege
without a join to `documents`.

Example:

```text
Document
   │
   ├── Chunk 1
   ├── Chunk 2
   ├── Chunk 3
   └── Chunk 4
```

This allows the system to know exactly which chunks belong to which document.

---

## 13. `utils/hashing.py`

### Responsibility

Contains hashing utilities.

The main purpose is to determine whether content has changed.

Example:

```python
import hashlib


def calculate_hash(content: str) -> str:
    return hashlib.sha256(
        content.encode("utf-8")
    ).hexdigest()
```

For example:

```text
Old content
    ↓
SHA256
    ↓
ABC123


New content
    ↓
SHA256
    ↓
ABC123
```

Same hash means:

```text
UNCHANGED
```

If:

```text
Old → ABC123
New → XYZ999
```

then:

```text
MODIFIED
```

Hashing is useful at different levels:

```text
Document hash
Section hash
Chunk hash
```

---

## 14. `constants.py`

### Responsibility

Contains **shared constant values** used across the module — for example
the DOCX XML namespace, HTML tag sets, skipped-element XPath and text
encoding fallbacks.

All literal values live in one place, so loaders stay focused on parsing
and a format detail can be adjusted in exactly one file.

---

## How the Files Work Together

The complete ingestion flow looks like this:

```text
                    API Request
                        │
                        ▼
                  api/v1/rag.py
                        │
                        ▼
                ingestion.py
                        │
             ┌──────────┴──────────┐
             ▼                     ▼
       change_detection.py     chunking.py
             │                     │
             └──────────┬──────────┘
                        ▼
                  embedding.py
                        │
             ┌──────────┴──────────┐
             ▼                     ▼
       repositories/chunk.py   repositories/vector.py
             │                     │
             ▼                     ▼
        PostgreSQL              Vector DB
```

---

## Example: Small Document Update

Suppose the original document contains:

```text
Section A
Section B
Section C
Section D
```

The user changes only Section C.

The system does:

```text
New document
     │
     ▼
change_detection.py
     │
     ├── Section A → unchanged
     ├── Section B → unchanged
     ├── Section C → modified
     └── Section D → unchanged
                  │
                  ▼
             chunking.py
                  │
                  ▼
       Re-create Section C chunks
                  │
                  ▼
             hashing.py
                  │
                  ▼
        Compare old/new chunks
                  │
             ┌────┴────┐
             ▼         ▼
          unchanged   changed
             │         │
           SKIP       embed
                       │
                       ▼
                 vector.py
                       │
                       ▼
                  Vector DB
```

Because chunking uses overlap, the system should regenerate the affected section's chunks rather than manually editing one vector.

---

## Responsibilities Summary

| File | Responsibility |
|---|---|
| `api/v1/rag.py` | API endpoints |
| `schemas.py` | Request/response validation |
| `ingestion.py` | Orchestrates ingestion |
| `chunking.py` | Splits content + manages overlap |
| `change_detection.py` | Finds new/modified/deleted content |
| `embedding.py` | Generates embeddings |
| `document.py` repository | Document DB operations |
| `chunk.py` repository | Chunk DB operations |
| `vector.py` repository | Vector DB operations |
| `document.py` model | Document database model |
| `chunk.py` model | Chunk database model |
| `hashing.py` | Content hashing |
| `constants.py` | Shared constant values |

---

## Main Design Principle

Each file should have **one clear responsibility**.

For example, avoid putting this inside `ingestion.py`:

```python
# SQL query
# chunking algorithm
# SHA256 implementation
# embedding API call
# vector DB query
# FastAPI endpoint
```

Instead:

```text
router
   ↓
service
   ↓
repository / utility
   ↓
external system
```

This makes the RAG module easier to:

- Test
- Maintain
- Scale
- Replace components
- Add Celery workers later
- Change embedding models
- Change vector databases
- Implement incremental ingestion
- Debug failed ingestion jobs
