# Claude Handoff: Current Workflow And App Boundaries

Updated: 2026-03-18

## Purpose

This document is a repo-level handoff for reviewing the current greeting-card generation system. It explains:

- what each of the three apps does
- how they connect
- what the current 1-job workflow actually looks like
- where the architecture is clean
- where the current implementation is split or inconsistent
- what Claude should focus on for the next upgrade plan

Current repo focus:

`text shortlist -> text select -> image generate -> image select -> final preview/final export`

## System Summary

The repository has three main apps:

| App | Path | Primary role |
| --- | --- | --- |
| eCardFactory | `ecard-factory/` | Main orchestrator, UI, workflow state, final render |
| ContentForge | `contentforge/` | Text generation, model comparison, judging |
| ImageForge | `imageforge/` | Image asset generation, prompt building, ComfyUI execution |

Supporting runtimes:

- PostgreSQL
- Ollama
- ComfyUI
- n8n (optional orchestration layer, not a repo app folder)

## What Each App Owns

### 1. eCardFactory

eCardFactory is the control tower of the system.

It owns:

- job creation and lifecycle state
- theme resolution and operator-facing workflow
- ContentForge request shaping
- shortlist persistence and text selection
- ImageForge request shaping
- local mirroring of image candidate metadata
- final card composition
- final PNG/PDF export
- UI pages and Studio actions
- audit events and workflow visibility

It should be treated as the only app that external automation or operators talk to directly.

It should not delegate final text layout to ImageForge.

### 2. ContentForge

ContentForge is the text engine.

It owns:

- text candidate generation
- multi-model comparison
- baseline quality scoring
- optional judge-based winner selection
- optional quality-memory feedback loop
- busy handling for long model calls

It does not own:

- jobs
- approvals
- shortlist UI
- final selected card state

### 3. ImageForge

ImageForge is the image asset engine.

It owns:

- structured image request intake
- positive and negative prompt construction
- provider execution against ComfyUI
- provider run persistence
- candidate persistence
- candidate selection
- filesystem storage for generated image assets

It does not own:

- theme business rules
- final greeting-card layout
- readable text overlay
- final card export

## Connection Between The Apps

The intended service chain is:

`Operator or n8n -> eCardFactory -> ContentForge -> eCardFactory -> ImageForge -> eCardFactory`

The important boundary rules are:

- n8n should call only eCardFactory
- eCardFactory calls ContentForge for text work
- eCardFactory calls ImageForge for image asset work
- ImageForge calls ComfyUI
- eCardFactory performs final composition itself
- ImageForge must not generate readable greeting text inside the image

## Current End-To-End Workflow

## Canonical Flow To Review

For the current upgrade discussion, the cleanest target flow is:

1. eCardFactory starts a job.
2. eCardFactory resolves theme and output settings.
3. eCardFactory calls ContentForge for a candidate pool.
4. eCardFactory persists all candidates and creates a shortlist.
5. Operator selects one text option.
6. eCardFactory builds a structured ImageForge request from theme + selected text.
7. ImageForge generates image asset candidates through ComfyUI.
8. eCardFactory mirrors ImageForge candidate metadata locally.
9. Operator selects one image.
10. eCardFactory renders the final card by overlaying readable text on the selected image.
11. eCardFactory exports final assets.

## What Happens In Practice Today

### A. Text stage

The text stage is mostly aligned with the intended architecture.

- `POST /api/jobs/start` or theme-based start endpoints create a job in eCardFactory.
- eCardFactory calls ContentForge through `ContentForgeWorkflowClient`.
- If ContentForge is unavailable, eCardFactory falls back to a local stub generator inside `WorkflowV1Service`.
- eCardFactory persists:
  - the full candidate pool
  - shortlist entries
  - judge metadata
  - audit events

### B. Image stage

There are currently two image paths in the codebase.

#### Path 1: ImageForge-backed asset flow

This is the cleaner direction and should likely become canonical.

- eCardFactory builds a structured ImageForge payload.
- ImageForge generates reusable asset candidates.
- eCardFactory exposes:
  - `POST /api/jobs/{job_id}/image-assets/generate`
  - `POST /api/jobs/{job_id}/image-assets/regenerate`
  - `POST /api/jobs/{job_id}/image-assets/{candidate_id}/select`
  - `GET /api/jobs/{job_id}/image-assets`
- After image selection, eCardFactory keeps the chosen image URL/path and uses it in final render.

#### Path 2: Internal eCardFactory image preview flow

This older flow still exists and uses eCardFactory’s own local image provider abstraction plus the local card renderer.

- `generate-image`
- `generate-more-images`
- `approve-image`
- some rerun paths

This path generates card-style visuals directly inside eCardFactory and does not go through ImageForge.

### C. Final render stage

The final render stays inside eCardFactory, which is the correct boundary.

- eCardFactory uses `WorkflowCardRenderer`
- it optionally uses the selected image as a background
- it overlays readable text
- it writes preview/final PNG/PDF assets to eCardFactory storage

## Current API-Level Responsibility Split

| Caller | Callee | Current purpose |
| --- | --- | --- |
| Operator/UI | eCardFactory | Start jobs, shortlist/select text, trigger image generation, select image, render final card |
| n8n | eCardFactory | Workflow automation only |
| eCardFactory | ContentForge | Generate and compare text candidates |
| eCardFactory | ImageForge | Generate and select image asset candidates |
| ImageForge | ComfyUI | Run actual image generation workflow |

## Data Ownership And Persistence

### eCardFactory

Persistence pattern:

- PostgreSQL for workflow/job data
- filesystem for generated previews and final card assets

Important stored concepts:

- card jobs
- text candidates
- shortlist rows
- approval records
- audit events
- mirrored image candidate records
- final asset records

### ContentForge

Persistence pattern:

- mostly stateless request/response service
- optional PostgreSQL-backed quality memory

Important stored concepts when enabled:

- previous quality runs
- repeated openings / cliche patterns
- avoid-phrase feedback for future generations

### ImageForge

Persistence pattern:

- PostgreSQL for request/provider/candidate metadata
- filesystem for image bytes

Important stored concepts:

- image requests
- provider runs
- image candidates
- prompt history
- selection state

## Important Reality Checks For Review

These are the most important things Claude should understand before suggesting an upgrade.

### 1. The architecture is conceptually clean, but the implementation still has overlap

The intended split is:

- ContentForge = text
- ImageForge = image assets
- eCardFactory = orchestration + final composition

But the actual code still contains overlap, especially in image generation.

### 2. eCardFactory can silently fall back to stub text generation

If ContentForge is unavailable, eCardFactory can still generate candidates via `StubContentForgeClient`.

That is useful for local development, but it can hide real integration problems and distort quality evaluation.

### 3. Shortlist ranking is not owned by a single source of truth

ContentForge produces scored outputs, but eCardFactory also applies its own shortlist and de-duplication logic.

That means:

- ranking logic is split
- quality problems can be hard to attribute
- upgrade work may accidentally improve one layer while the other still degrades output

### 4. Image state is duplicated across eCardFactory and ImageForge

ImageForge persists its own request/candidate data.

eCardFactory also mirrors image candidate metadata locally so the Studio and final render stay job-centric.

That is practical, but it increases sync and consistency risk.

### 5. The workflow has multiple “official” paths in code

There is:

- the older approval-gated workflow
- the Studio-first workflow
- the ImageForge-backed asset flow
- the older internal eCardFactory image-preview flow

This is currently the biggest source of conceptual drift.

## Main Shortcomings

These are the most likely upgrade pain points.

### 1. Split image-generation responsibility

Problem:

- some flows use ImageForge
- some flows still generate visuals inside eCardFactory

Impact:

- confusing source of truth
- duplicated logic
- harder testing and debugging
- unclear future boundary

### 2. Content quality ownership is split

Problem:

- ContentForge scores quality
- eCardFactory re-shortlists locally
- eCardFactory can fall back to stub outputs

Impact:

- poor ranking can come from multiple places
- duplicate content can survive if the two scoring layers disagree
- production quality is hard to reason about

### 3. Workflow mode drift

Problem:

- docs and code describe both approval-first and Studio-first behavior

Impact:

- hard to know which path is canonical
- API contracts and n8n flow can drift away from the UI workflow

### 4. State duplication across services

Problem:

- image metadata lives in both ImageForge and eCardFactory

Impact:

- selection sync bugs
- stale previews
- extra migration cost when contracts change

### 5. No strong asynchronous workflow engine inside the services

Problem:

- long-running operations rely on busy guards and synchronous request-response patterns

Impact:

- poor scalability
- limited retry semantics
- operator-visible delays

### 6. Final rendering is correct architecturally, but still relatively local/simple

Problem:

- final card composition is currently tied to local renderer/templates in eCardFactory

Impact:

- easy to keep boundaries clean
- but limited if the next upgrade expects richer templates, layout systems, or external design tooling

## Suggested Upgrade Direction

If the goal is to stabilize the 1-job flow first, the likely best sequence is:

1. Choose one canonical workflow.
2. Make one canonical image path.
3. Make one canonical text ranking path.
4. Reduce duplicated persistence where possible.
5. Improve observability around each stage.

A pragmatic next-upgrade direction would be:

### Priority 1

Make the Studio-first flow the only primary workflow:

`start job -> shortlist -> select text -> generate ImageForge assets -> select image -> render final -> approve/export`

### Priority 2

Remove or isolate the legacy internal image-generation path inside eCardFactory.

Keep eCardFactory focused on:

- orchestration
- selection state
- final composition

Keep ImageForge focused on:

- image asset generation only

### Priority 3

Decide where ranking truth lives.

Best likely option:

- ContentForge owns candidate scoring and primary ranking
- eCardFactory only applies UI-safe filtering and persistence

### Priority 4

Make ContentForge fallback behavior explicit.

The stub should be:

- disabled in production-like runs, or
- visibly flagged in job state and UI

### Priority 5

Formalize the ImageForge mirror contract in eCardFactory.

Decide whether eCardFactory should:

- keep full mirrored candidate state, or
- store only request ID + selected candidate + selected asset path

## Recommended Source Files For Claude To Read

If Claude needs to inspect the implementation, these are the most important files:

### Repo-level

- `PROJECT_BOOTSTRAP.md`
- `AGENTS.md`

### eCardFactory

- `ecard-factory/docs/ECARDFACTORY_WORKFLOW.md`
- `ecard-factory/workflows/n8n/ecardfactory_workflow_v2_notes.md`
- `ecard-factory/app/services/workflow_v1_service.py`
- `ecard-factory/app/services/image_generation_service.py`
- `ecard-factory/app/repositories/workflow_repository.py`
- `ecard-factory/app/integrations/contentforge/client.py`
- `ecard-factory/app/integrations/imageforge/mapper.py`
- `ecard-factory/app/services/workflow_card_renderer.py`

### ContentForge

- `contentforge/README.md`
- `contentforge/app/routers/generate.py`
- `contentforge/app/routers/judge.py`
- `contentforge/app/quality_memory.py`

### ImageForge

- `imageforge/README.md`
- `imageforge/app/services/generation/service.py`
- `imageforge/app/services/prompts/image_prompt_builder.py`
- `imageforge/app/services/persistence/repository.py`
- `imageforge/db/schema.sql`

## Suggested Prompt For Claude

Use this as the starting prompt:

```text
Review the attached repo handoff and the referenced source files.

My goal is to stabilize and simplify the current 1-job greeting-card flow:
text shortlist -> text select -> image generate -> image select -> final preview/final export.

Please do the following:

1. Identify the biggest architectural inconsistencies in the current three-app design.
2. Tell me which workflow should become canonical and why.
3. Recommend how responsibilities should be split between eCardFactory, ContentForge, and ImageForge.
4. Propose a concrete upgrade plan in phases, with low-risk first steps.
5. Call out any data-model, API-contract, or orchestration changes that would be required.
6. Highlight where the current design is good and should be preserved.

Important context:
- eCardFactory should remain the orchestration and final composition layer.
- ContentForge should remain the text engine.
- ImageForge should remain the image asset engine.
- ImageForge must not generate readable text inside images.
- Final card composition should remain outside ImageForge.

Also tell me what to remove, what to keep, and what to refactor first.
```

## Bottom Line

The repo already has the right high-level separation:

- eCardFactory as orchestrator
- ContentForge as text engine
- ImageForge as image engine

The next upgrade should focus less on adding new capability and more on removing overlap, choosing one canonical workflow, and enforcing a single clear boundary for text, image, and final render stages.
