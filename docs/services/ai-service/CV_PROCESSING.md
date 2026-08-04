# CV Processing Pipeline

## Upload constraints
- Max file size: 5MB
- Allowed types: PDF only (magic-byte verified, not just content-type header)
- Max CVs per user: 5 (enforced at service layer)

## Pipeline stages
1. Text extraction — PyMuPDF (fitz)
   - Fallback: Claude API vision-based extraction for garbled/complex layouts
2. Section parsing — Claude API, structured JSON output
   - Schema: contact, summary, experience[], education[], skills[], projects[]
3. Chunking — one chunk per semantic unit (per experience entry, one for skills, etc.)
   - Rationale: avoids splitting bullets mid-sentence, avoids diluted whole-doc embeddings
4. Embedding — Voyage AI `voyage-3.5`, 1024 dims, stored in pgvector

## Storage
- raw_text: kept indefinitely (source of truth for reprocessing)
- structured_data: JSONB, derived, can be regenerated from raw_text
- CVChunk rows: derived from structured_data, regenerated on any CV update (not patched)

## Why not embed raw_text directly
[your reasoning about semantic boundaries, dilution, etc.]