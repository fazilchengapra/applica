# Database Schema — user-service

## Overview

One PostgreSQL database (RDS), owned exclusively by user-service.
No other service should read/write these tables directly — go through the API.

## Core tables

| Table | App | Notes |
|---|---|---|
| `auth_user` / custom user model | authentication/users | |
| `profile` | profile | 1:1 with user |
| `task` | task_monitoring | |
| `notification` | notification | |

## Diagram

Add an ER diagram here (dbdiagram.io export, or generated via
`django-extensions graph_models`).

## Conventions

- Naming conventions (snake_case, table prefixes)
- Soft delete pattern if used
- Indexing notes for high-traffic tables
