# RAG Ingestion & Change-Detection Workflow

Companion to [`RAG_MODULE.md`](./RAG_MODULE.md), which documents every file
in the module. This document focuses on **runtime behaviour**: how a document
moves through ingestion, how updates are applied incrementally, how change
detection decides what to re-embed, what arguments and prompts the pipeline
uses — and how all of that keeps the system **cheap to operate**.

## Implementation Status

| Stage | Status | Component |
|---|---|---|
| Load (parse any format → common format) | Implemented | `loaders/`, `services/ingestion.py` |
| Chunking (500 tokens, 100 overlap) | Implemented | `services/chunking.py` |
| Chunk hashing (for change detection) | Implemented | `utils/hashing.py`, `services/chunking.py` |
| Change detection | Designed | `services/change_detection.py` |
| Embedding + vector store | Designed | `services/embedding.py`, `repositories/vector.py` |
| Document persistence | Implemented | `models/document.py` (migration `61febb2769c5`) |
| Chunk persistence | Designed | `repositories/chunk.py` |

The designed stages are described here so the workflow is complete; the
"implemented" stages exist today.

---

## 1. Data Ingestion Workflow

### 1.1 The full pipeline

```text
                          file upload (bytes)
                                │
                                ▼
                POST /api/ai/v1/rag/ingest   (api/v1/rag.py)
                                │
                                ▼
                     services/ingestion.py   (orchestrator)
                                │
        ┌───────────────────────┼──────────────────────────┐
        ▼                       ▼                          ▼
   loaders/factory        change_detection.py         embedding.py
   pdf/docx/html/txt      hash old vs new,            chunk text →
   → plain text           classify NEW/UNCHANGED/     embedding vector
        │                 MODIFIED/DELETED                 │
        │                       │                          │
        ▼                       ▼                          ▼
   services/chunking.py   repositories/chunk.py     repositories/vector.py
   500 tokens, 100        chunk metadata (DB        upsert / delete /
   overlap                hash, index, version)     search (vector DB)
                                │                          │
                                ▼                          ▼
                           PostgreSQL                  Vector database
```

### 1.2 Orchestrator steps

`ingestion.py` decides **what should happen**; it never does the work itself.
It delegates to the loaders, chunking, change detection, embedding and
repositories.

```python
async def ingest_document(document):
    sections = parse_document(document)        # loaders → plain text
    changes  = detect_changes(sections)        # hash comparison → states

    for section in changes:                    # only changed sections
        chunks            = chunk_section(section)          # CHUNK_SIZE, CHUNK_OVERLAP
        changed_chunks    = compare_chunks(chunks)          # chunk-level hashing
        embeddings        = generate_embeddings(changed_chunks)
        update_vectors(embeddings)             # vector repo upsert
        save_chunk_metadata(changed_chunks)    # document/chunk repos
```

| # | Stage | What happens | Where |
|---|---|---|---|
| 1 | Parse | Bytes → plain text via the loader for the file type | `loaders/*`, factory |
| 2 | Change detection | Compare section hashes → `NEW / UNCHANGED / MODIFIED / DELETED` | `change_detection.py` |
| 3 | Chunk | Split a section into ≤500-token chunks, 100-token overlap | `chunking.py` |
| 4 | Compare chunks | Re-hash new chunks, diff against stored chunk hashes | `chunking.py` + `utils/hashing.py` |
| 5 | Embed | Vectorise only the changed chunks (`input_type="document"`) | `embedding.py` |
| 6 | Update vectors | Upsert new/changed vectors, delete removed ones | `repositories/vector.py` |
| 7 | Save metadata | Persist document + chunk rows (hash, index, version) | `repositories/document.py`, `repositories/chunk.py` |

### 1.3 Three workflows

**First-time ingestion** — every section is `NEW`, so every chunk is chunked,
embedded, upserted and stored. Cost is proportional to the whole document.

```text
upload → parse → all sections NEW → chunk all → embed all → vector DB + metadata
```

**Incremental update** (`POST /rag/documents/{id}/update`) — only the delta is
processed. Example from `RAG_MODULE.md`: the document has sections A–D and the
user edits only section C.

```text
new document
     │
change_detection.py
     │
     ├── Section A → unchanged
     ├── Section B → unchanged
     ├── Section C → MODIFIED
     └── Section D → unchanged
                  │
                  ▼
        chunking.py           re-chunk section C
                  │
                  ▼
        compare chunk hashes  per-chunk reuse of unchanged pieces
                  │
             ┌────┴────┐
             ▼         ▼
          unchanged  changed
             │         │
           SKIP      embed (input_type="document")
                        │
                        ▼
                  vector DB upsert
```

**Delete** (`DELETE /rag/documents/{id}`) — drop the vectors and chunk rows for
the document so dead chunks stop costing storage and scan time.

> **Correctness note:** because chunks overlap, a change anywhere in a section
> shifts its neighbours. The affected *section* is re-chunked wholesale rather
> than patching one stale vector.

---

## 2. Arguments and Prompts

### 2.1 HTTP API arguments

| Endpoint | Arguments | Meaning |
|---|---|---|
| `POST /rag/load` | `file` (multipart `UploadFile`) | Current dev entry point: load + chunk, returns the common format with chunks |
| `POST /rag/ingest` (designed) | `document_id`, `source`, `content` (or `file`) | Full pipeline incl. metadata persistence |
| `POST /rag/documents/{id}/update` | same as ingest | Incremental re-ingest of one document |
| `DELETE /rag/documents/{id}` | path `id` | Remove document, chunks and vectors |
| `POST /rag/search` | `query`, `top_k` | Retrieve matching chunks for a question |

Gateway/internal headers required by every `ai_service` route (see
`app/core/dependencies.py`):

- `X-Gateway-Secret` — proves the request came through Kong; missing → `403`.
- `X-User-Id` — the authenticated user id; missing → `422`.

Example request/response contract (ingest, designed shape from `RAG_MODULE.md`):

```jsonc
POST /rag/ingest
{
  "document_id": "policy-001",
  "source": "s3://documents/policy.pdf",
  "content": "<raw bytes>"          // or a multipart file upload
}

// 201 Created
{
  "document_id": "policy-001",
  "status": "completed",            // processing | completed | failed
  "chunks_processed": 42            // number actually embedded this run
}
```

The load endpoint (implemented) returns the common format plus chunks:

```jsonc
{
  "filename": "policy.pdf",
  "content_type": "application/pdf",
  "loader": "PdfLoader",
  "text": "<full extracted text>",
  "characters": 12345,
  "lines": 300,
  "chunk_count": 24,
  "chunks": [
    { "index": 0, "text": "...", "characters": 1800, "tokens": 490,
      "content_hash": "9b74c989..." }
  ]
}
```

### 2.2 Internal pipeline arguments

What each step receives and what it drives:

| Call | Arguments | Controls |
|---|---|---|
| `get_loader(filename, content_type)` | file name + MIME | Which loader parses the file |
| `parse_document(source)` | raw file | Plain text for the pipeline |
| `detect_changes(old_sections, new_sections)` | old/new section maps | What gets re-processed |
| `chunk_section(section)` | the section text | Chunk boundaries |
| `compare_chunks(old, new)` | old/new chunk hashes | Which chunks get embedded |
| `generate_embeddings(chunks)` | chunk texts | Vectors for the vector DB |
| `calculate_hash(content)` | text | `content_hash` comparisons |

### 2.3 Chunking configuration

Defined once in `app/modules/rag/constants.py`:

```python
CHUNK_SIZE         = 500   # target tokens per chunk
CHUNK_OVERLAP      = 100   # tokens shared between neighbouring chunks
CHUNK_TOKEN_ENCODING = "o200k_base"
```

Overlap is deliberately bounded (100 of 500 tokens = 20%). That redundancy is
the price of not losing context at boundaries; it is a *constant* overhead, it
never grows with document size.

### 2.4 Embedding arguments / prompts (input types)

Per ADR `0002-cv-chunking-and-embeddings`, the Voyage embedding model is
**direction-sensitive**, and the `input_type` argument must match:

```python
generate_embeddings(chunks, input_type="document")   # index time
generate_embeddings([query], input_type="query")     # search time
```

Using the wrong `input_type` silently degrades retrieval quality, so the
embedding service owns the mapping and no other component needs to know who
the model is.

### 2.5 Retrieval prompt (designed)

At search time the flow is: query → `input_type="query"` embedding → vector
search → top-k chunks → prompt for an LLM.

```text
SYSTEM:    "Answer only from the provided context. If the context does not
            contain the answer, say you do not know."

CONTEXT:   [{source, section, chunk_index, text} for the top-k chunks]

QUESTION:  <user query>
```

The cost levers at generation time are exactly the prompt **context size**
(`top_k` × chunk tokens) and the model's input billing — which is why small,
bounded chunks matter for cost as much as for semantics.

---

## 3. Change-Detection Workflow

### 3.1 Purpose

Avoid re-processing work that is unchanged. Every document, section and chunk
stores a `content_hash`; comparing hashes is what decides `NEW / UNCHANGED /
MODIFIED / DELETED`, and only `MODIFIED`/`NEW` work is paid for.

### 3.2 Hash levels

Hashing runs at three granularities (`utils/hashing.py`, SHA-256):

```text
document hash   → same document → skip the entire document
section hash    → diff sections → only modified sections are re-chunked
chunk hash      → diff chunks   → only changed chunks are re-embedded
```

Same hash means `UNCHANGED`; different hash means `MODIFIED`.

```text
Old content --SHA256--> ABC123      New section --SHA256--> XYZ999
                │                                    │
           UNCHANGED?  no (ABC123 != XYZ999) → MODIFIED
```

### 3.3 The algorithm: three gates, cheapest first

| Gate | Comparison | Result | Paid work |
|---|---|---|---|
| 1 | whole-document hash | equal → nothing to do | **0 embeddings** |
| 2 | per-section hashes | classify sections `NEW/UNCHANGED/MODIFIED/DELETED` | only MODIFIED/NEW sections proceed |
| 3 | per-chunk hashes (within modified sections) | identify changed chunks | only changed chunks are embedded |

Gates run in increasing cost order, so the cheapest test (a CPU hash, ~free)
decides whether any expensive work (chunking → embedding → vector writes)
happens at all.

### 3.4 Worked example

```text
Old:   Introduction → A123 | Payment → B456 | Refund → C789
New:   Introduction → A123 | Payment → B456 | Refund → XYZ999

Result:  Introduction → UNCHANGED   (skip)
         Payment      → UNCHANGED   (skip)
         Refund       → MODIFIED    (re-chunk → re-embed changed chunks)
```

### 3.5 Overlap handling

Because chunks overlap, a one-line fix in section C can shift the tail of a
neighbouring chunk. The pipeline therefore **regenerates all chunks of the
affected section** and lets chunk hashing re-use the identical ones — it never
hand-edits a single vector.

---

## 4. How the System Reduces Cost

### 4.1 Where the cost actually is

| Cost source | Billed per | Notes |
|---|---|---|
| Embedding API | token embedded, per call | dominant ingest cost, scales with chunk count |
| Vector storage | stored vector | grows with documents retained |
| Vector search scans | queried/served vectors | grows with index size |
| LLM generation | prompt + completion tokens | context = top_k × chunk tokens |

Hashing and comparison are local CPU work — essentially **free** — and they
sit in front of every paid step.

### 4.2 Cost-avoidance mechanisms

| Mechanism | Avoids | Where | Example saving |
|---|---|---|---|
| Document-hash gate | *any* work on a re-uploaded identical file | `hashing.py` + `ingestion.py` | same file → 0 embeddings |
| Section-level diffing | re-chunking/re-embedding untouched sections | `change_detection.py` | edit 1 of 4 sections → 25% of hits |
| Chunk-level diffing | re-embedding identical chunks within a changed section | chunk hashes | unchanged chunks in a re-chunked section → SKIP |
| Incremental ingestion | rebuilding the whole index on every edit | orchestrator + repositories | update = delta only |
| Batch embeddings | per-call request overhead and throttling | `embedding.generate_embeddings(chunks)` | 1 API call per batch, not 1 per chunk |
| Bounded overlap | runaway redundant tokens | `CHUNK_OVERLAP` (100/500 = 20%) | constant overhead, never grows |
| Delete/orphan cleanup | wasted storage and scan cost | `repositories/vector.py` | removed chunks stop being stored/scanned |

### 4.3 The headline numbers

From `RAG_MODULE.md` — a 1000-chunk document updated once:

```text
WITHOUT change detection           WITH change detection
1000 chunks                        1000 chunks
   ↓                                  ↓
1000 embeddings                     990 unchanged → SKIP (free)
                                    10 changed    → EMBED
                                   ----------
                                   only 10 embeddings
```

That is a **99% reduction** in embedding spend on a typical update, and the
saving is bigger on update-heavy documents (policies, knowledge bases, CVs
edited often). Because embeddings are billed per token, a 10-instead-of-1000
run also cuts an update's latency and its API-quota pressure by the same
factor — this is what makes frequent incremental re-ingestion affordable.

### 4.4 When cost is *not* reduced

- **First ingestion** still embeds every chunk — unavoidable.
- **Whole-file replacements** with a genuinely new hash still re-embed the
  changed sections.
- A change in one sentence re-chunks its *section* (correctness over
  micro-optimisation), so neighbouring chunks are re-created — but their
  unchanged hashes are still skipped before any embedding call.

---

## 5. Where the knobs live

| Knob | Effect on cost | Location |
|---|---|---|
| `CHUNK_SIZE` / `CHUNK_OVERLAP` | tokens embedded per chunk, redundancy | `app/modules/rag/constants.py` |
| change-detection gates | how much of an update is skipped | `services/change_detection.py` |
| batch size | API calls per re-ingest | `services/embedding.py` |
| `top_k` (search) | prompt context tokens per query | `api/v1/rag.py` / retrieval |
| retention / cleanup | vectors kept in the index | `repositories/vector.py` |