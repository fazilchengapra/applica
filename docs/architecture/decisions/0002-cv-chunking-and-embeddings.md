# CV Chunking and Embeddings

**Status:** Proposed
**Date:** 2026-08-10

## Context

For job matching, a CV needs to be searchable at a granular level (e.g.
"does this candidate have React experience" should match against a specific
experience entry, not the whole CV as one blob). This requires splitting a
parsed CV into chunks and embedding each one independently.

Chunks are tied to a specific `master_cv_versions` row, not directly to
`master_cvs`, so that re-parsing a CV (creating a new version) doesn't
require destroying and rebuilding chunks for the version still marked
`is_current`. Processing happens against the new version; chunks only
become "live" for matching once that version is promoted.

## Proposed Decision

Introduce a `cv_chunks` table. Each row represents one semantically
meaningful unit of a CV (an experience entry, an education entry, a
project, etc.) plus its embedding vector.

`source_id` uses a positional convention (e.g. `experience_0`,
`education_1`) to trace a chunk back to its position in
`master_cv_versions.parsed_data`, rather than a separate FK to a
sub-table per section type.

Voyage AI's embedding model requires different `input_type` values
depending on direction: `"document"` when embedding CV chunks at index
time, `"query"` when embedding a job description at search time. This
asymmetry is specific to Voyage and must be respected consistently, or
retrieval quality degrades.

## Proposed Structure

### cv_chunks

- id
- cv_version_id (FK → master_cv_versions.id, ON DELETE CASCADE)
- chunk_type (varchar — e.g. `experience`, `education`, `project`, `summary`)
- source_id (varchar — positional reference into parsed_data, e.g. `experience_0`)
- content (text — the chunked text that was embedded)
- embedding (vector(1024))
- created_at

Index: HNSW on `embedding` for cosine similarity search.

## Chunking Flow

New `master_cv_versions` row created, `status = processing`
→ parse CV into structured sections (`parsed_data`)
→ split sections into chunks per `chunk_type`
→ embed each chunk with Voyage AI (`input_type="document"`)
→ insert `cv_chunks` rows
→ on success: promote version (`is_current = true`), `status = completed`
→ on failure: `status = failed`, chunks for this version rolled back or left orphaned pending cleanup

## Open Questions

- Exact chunk boundaries: one chunk per experience/education/project entry,
  or finer-grained (e.g. per bullet point within an experience entry)?
- Retention: do chunks get deleted when their version is no longer current,
  or kept for historical search/comparison? Ties into the retention question
  in the versioning ADR.

## Implementation Status

Not implemented yet.