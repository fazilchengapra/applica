# Master CV Versioning

**Status:** Implemented
**Date:** 2026-08-10

## Context

Currently, `master_cvs` stores the user's CV data directly.

When a user updates their CV, overwriting the existing data could cause
problems because existing job applications may have been created using the
previous CV.

## Proposed Decision

Introduce CV versioning.

A `master_cvs` record will represent the user's logical Master CV, while
`master_cv_versions` will store each uploaded version.

Rather than `master_cvs` pointing down to a current version (which creates a
circular FK dependency at insert time — the parent can't be created before
the child, and the child can't be created before the parent), each
`master_cv_versions` row carries an `is_current` flag. A partial unique index
enforces exactly one current version per master CV:

```sql
CREATE UNIQUE INDEX one_current_version_per_cv
  ON master_cv_versions (master_cv_id) WHERE is_current;
```

Promoting a version is a single transaction that unsets the old flag and sets
the new one — no write to `master_cvs` required.

Applications will reference the specific `master_cv_versions.id` used when
the application was created.

## Proposed Structure

### master_cvs

- id
- user_id (unique — one master CV per user)
- deleted_at
- created_at
- updated_at

### master_cv_versions

- id
- master_cv_id (FK → master_cvs.id)
- version (int)
- embedding (vector)
- is_current (bool, default false)
- s3_key
- raw_text
- parsed_data (jsonb)
- status (`processing` | `completed` | `failed`)
- created_at
- updated_at

Unique constraint on `(master_cv_id, version)`.

## Update Flow

User updates CV
→ create new `master_cv_versions` row, `version = previous version + 1`, `status = processing`
→ process new CV (parse, embed)
→ on success: transaction sets old version's `is_current = false`, new version's `is_current = true`, `status = completed`
→ on failure: new version's `status = failed`, old version remains current

## Open Question

Retention policy for old versions and their S3 objects — keep indefinitely,
or prune after N versions / a time window. Affects storage cost and whether
`master_cv_versions` needs its own `deleted_at`.

## Implementation Status

Implemented and need a test