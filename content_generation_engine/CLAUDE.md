# CLAUDE.md — content_generation_engine

## What Is This?

A local-first greeting card generation platform. It produces personalized eCards by combining AI-generated text and images, orchestrated through a Studio UI. Targets Indian cultural occasions (Diwali, Holi, Ramadan) as well as evergreen themes.

**End-to-end flow:**
```
Theme Selection → Text Generation → Text Shortlist/Select → Image Generation → Image Select → Final Compose & Export
```

## Services at a Glance

| Service | Path | Port (local) | Role |
|---|---|---|---|
| eCardFactory | `ecard-factory/` | 8080 | Orchestrator, UI, workflow state, final render |
| ContentForge | `contentforge/` | 8001 | Text generation, multi-model comparison, judging |
| ImageForge | `imageforge/` | 8090 | Image generation via ComfyUI, prompt building, asset storage |
| Studio UI | `content_engine_ui/` | served by eCardFactory | React operator console |

**External runtimes (not in this repo):**
- PostgreSQL — port 5432
- Ollama — port 11434 (local LLM: Qwen 2.5, Llama 3.1, Mistral)
- ComfyUI — port 8188 (Stable Diffusion XL)
- n8n — port 5678 Docker (optional automation)

## Stack

- **Backend:** Python 3.11+ / FastAPI / Uvicorn
- **Database:** PostgreSQL 16 / SQLAlchemy 2.0 async / Alembic migrations
- **Frontend:** React 18 / React Router / esbuild
- **AI text:** Ollama (local) · Groq API · OpenAI API (optional)
- **AI images:** ComfyUI (local) · DALL-E (optional)

## Starting & Stopping

```bash
./start-all.sh   # launches all services; logs → .ops/logs/
./stop-all.sh    # stops all services via .ops/pids/
```

See [PROJECT_BOOTSTRAP.md](PROJECT_BOOTSTRAP.md) for full startup order and failure-mode guidance.

## Ownership Rules (never violate)

- **eCardFactory is the only external API surface.** Automation (n8n, scripts) talks to eCardFactory only — never directly to ContentForge or ImageForge.
- **eCardFactory owns final composition.** ContentForge and ImageForge never write readable text into images.
- **eCardFactory owns job state.** ContentForge and ImageForge are stateless request-handlers with busy guards.
- **Services communicate via REST only.** No shared in-process calls, no shared modules across service boundaries.
- **Configs are DB-driven.** Theme catalog and operator config live in PostgreSQL, not hardcoded.

## Engineering Rules

- Log every stage of the pipeline — text generation, image generation, shortlisting, selection, render.
- Services expose `/health` or equivalent — always check before assuming a service is up.
- Both ContentForge and ImageForge return `429 Busy` when a long job is already running — callers must handle this.
- Image assets live on an external filesystem root (configurable per service via env). Never store binary blobs in the DB.
- All provider calls (Ollama, ComfyUI, Groq, OpenAI) must have explicit timeouts.

## Current Focus (as of 2026-03)

Stage 4 — deterministic quality and operator-config hardening:
- text shortlist → text select → image generate → image select → final preview → quality check → export

Known open items (see [CLAUDE_WORKFLOW_HANDOFF.md](CLAUDE_WORKFLOW_HANDOFF.md)):
- Stage 3 composition needs live Studio visual signoff
- Content quality needs improvement in downstream prompts/ranking
- Config catalog needs live UI verification
- Image generation latency is still high

## Key Docs

| Doc | Purpose |
|---|---|
| [PROJECT_BOOTSTRAP.md](PROJECT_BOOTSTRAP.md) | Complete startup guide, ports, env vars, failure points |
| [AGENTS.md](AGENTS.md) | High-level architecture for AI agents |
| [CLAUDE_WORKFLOW_HANDOFF.md](CLAUDE_WORKFLOW_HANDOFF.md) | Detailed API boundaries, shortcomings, upgrade suggestions |
