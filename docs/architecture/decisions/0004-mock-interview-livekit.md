# ADR-0004: Mock Interview System — Self-hosted LiveKit + free local speech stack

**Status:** Accepted (design) — not yet implemented
**Date:** 2026-09-21

## Context

Applica needs a **video-based mock interview**: a candidate practices a role
interview against an AI interviewer, with realtime interaction, an on-screen
live transcript, a recording, and a post-interview feedback report.

Requirements agreed with product:

- **Good quality with zero/low cost** — the speech stack must be free (no
  per-minute SaaS speech charges). Self-host everything possible.
- AI interviewer presented as **voice + on-screen transcript** (no avatar).
- **Phased rollout** — text chat first, then voice, then video + recording.

Constraints from the existing codebase:

- docker-compose monorepo: `user_service`, `ai_service`, `notification_service`
  behind a Kong gateway (ADR-0003). No interview/media code exists — greenfield.
- Realtime push already works via **Redis pub/sub → WebSocket fan-out**
  (`notification_service` realtime module, `cv-status` pattern).
- All LLM calls go through **OpenRouter** via an OpenAI-compatible
  `ChatOpenAI` client (`ai_service/app/core/llm_client.py`) — no direct
  OpenAI streaming yet.
- Long-running work belongs in **Celery** (`ai_service`), question/answer
  orchestration uses **LangGraph** (tailoring agents are the reference pattern).
- The gateway (Kong) is **HTTP-only** — it cannot relay WebRTC (UDP) media.

## Decision

Separate the system into two independently scalable planes.

### Media plane — self-hosted LiveKit

- **LiveKit server** (Apache-2.0) runs as the WebRTC SFU in docker-compose. It
  ingresses/mixes participant audio/video. Suite of new docker services:
  `livekit`, `livekit-egress` (recording → S3), `interview-agent`.
- WebRTC media connects **directly** to the SFU over UDP (NOT through Kong).
  Kong only handles control-plane HTTP.
- **LiveKit Egress** records each session to S3, reusing the existing
  `AWS_*` / `S3_BUCKET_NAME` / `S3_ENDPOINT_URL` config in `ai_service`.

### Intelligence plane — ai_service + a dedicated agent worker

- New module `ai_service/app/modules/interviews/` owns the session lifecycle:
  create/list/get/cancel, LiveKit JWT token issuance, the interview LangGraph
  graph, and a Celery feedback task. New tables live in `ai_service`'s own
  PostgreSQL (ADR-0002 style: per-service DB, no cross-DB FKs).
- New docker service **`interview-agent`** (LiveKit Agents, Python) joins each
  session's room as the "AI interviewer" participant and runs the live pipeline:
  - **STT:** faster-whisper (Distil-Whisper, local, free, good quality)
  - **Interviewer LLM:** fast OpenRouter chat model via the existing
    `ChatOpenAI` client (new `INTERVIEW_MODEL` setting, no new provider)
  - **TTS:** Kokoro-82M (Apache-2.0/MIT, local, free)
  - The agent loads session config (role, job description, CV summary, question
    plan) from `ai_service` by `session_id`, and publishes transcript segments +
    status over Redis pub/sub.

### Realtime fan-out — extend notification_service

- The agent publishes to Redis pub/sub channel `interview:events:<session_id>`.
  `notification_service` pattern-subscribes `interview:*` and pushes over the
  existing `ws/notifications` socket, mirroring the `cv-status` pattern. New
  event types: `interview.session` and `interview.transcript`.

### Access — Kong

- Interview endpoints are new routes under the existing `ai-service` profile,
  protected by the existing `jwt` + `header_injector` plugins; ownership
  checks use the injected `X-User-Id`. Egress/webhook endpoints are protected
  by a shared signed header.

### Rollout order

1. **Text chat** — validate the interviewer graph, transcript, feedback, and
   notification flow with zero new infrastructure.
2. **Voice** — add LiveKit + `interview-agent` (STT/LLM/TTS).
3. **Video** — video tracks + Egress recording to S3.
4. **Hardening** — coturn (TURN) for NAT traversal, Egress lifecycle, notes on
   scaling and multi-region SFU deployment.

## Consequences

**Easier:**

- Media scale-out is independent of API scale-out: add LiveKit SFU nodes and
  `interview-agent` workers without touching the control plane.
- Control plane stays stateless and reuses existing patterns (LangGraph,
  Celery, Redis pub/sub, Kong auth) — low new-concept risk.
- Free, self-hosted speech stack keeps running cost near zero and data private.
- LiveKit's token/room model is provider-agnostic — migrating to LiveKit Cloud
  later is config-only.

**Harder / trade-offs (accepted):**

- `interview-agent` needs a model-loading setup and GPU-free or small-GPU
  inference tuning for acceptable voice latency. Text phase unblocks first.
- WebRTC requires direct UDP reachability to the LiveKit host (TURN for the
  long tail) — more moving parts than an HTTP-only feature.
- Local TTS quality is below top-tier SaaS TTS; accepted given the free +
  good-quality trade-off.
- New docker services increase compose footprint; recording adds S3 storage
  costs.

## Alternatives considered

- **Managed speech SaaS** (Deepgram STT / ElevenLabs TTS) — best quality and
  latency, but per-minute cost; rejected for the "free, good quality"
  requirement. Can be swapped in later behind the same agent interface.
- **Run the interviewer inside `ai_service`** — rejected: WebRTC/audio
  resources should not share the web/API process; the agent worker scales and
  restarts independently.
- **Managed LiveKit Cloud** — rejected for now (self-hosted is free); migration
  path is preserved by the token/room abstraction.
- **Animated avatar interviewer** — deferred; presenting as voice + transcript.

## Related

- [Mock interview design doc](../mock-interview.md)
- [System overview](../system-overview.md)
- [Service map](../service-map.md)
- [ADR-0003: API gateway — Kong](./0003-api-gateway-kong.md)
- [ai_service](../../services/ai-service/README.md)
- [notification_service realtime](../../services/notification-service/README.md)