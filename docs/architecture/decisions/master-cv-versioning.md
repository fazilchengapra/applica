# Master CV Versioning

**Status:** Proposed  
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

`master_cvs.current_version_id` will point to the currently active version.

Applications will reference the specific `master_cv_versions.id` used when
the application was created.

## Proposed Structure

### master_cvs

- id
- user_id
- current_version_id
- created_at
- updated_at

### master_cv_versions

- id
- master_cv_id
- version
- s3_key
- raw_text
- parsed_data
- embedding
- status
- created_at
- updated_at

## Update Flow

User updates CV
→ create new version
→ version = previous version + 1
→ process new CV
→ update `current_version_id`

## Implementation Status

Not implemented yet.