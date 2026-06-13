# Project Bootstrap

## 1. Project Overview

This repository is a local multi-service workspace for generating greeting cards end to end:

1. `contentforge` generates text options.
2. `ecard-factory` shortlists and selects text, orchestrates image generation, and renders final cards.
3. `imageforge` generates image asset candidates through ComfyUI.
4. `n8n` optionally automates the orchestration flow against eCardFactory APIs.

Operationally, there is one additional required runtime outside the three Python services plus n8n:

- `ComfyUI`, used by ImageForge as the actual image generation backend

Current repo paths:

- `ecard-factory/`
- `contentforge/`
- `imageforge/`

There is no standalone top-level `n8n/` application folder in this repo. n8n is currently run via Docker, and the workflow JSON files live under `ecard-factory/workflows/n8n/`.

## 2. Service List And Responsibility

| Service | Path | Startup mechanism detected in repo | Responsibility |
| --- | --- | --- | --- |
| eCardFactory | `ecard-factory/` | FastAPI + `uvicorn`, wrapped by `scripts/run-ecard.sh` | Main orchestrator, UI, shortlist/selection flow, final composition/render |
| ContentForge | `contentforge/` | FastAPI + `uvicorn` from `startup.txt` | Text generation and judge/ranking endpoints |
| ImageForge | `imageforge/` | FastAPI + `uvicorn`, wrapped by `scripts/run_local.sh` | Image asset generation and candidate persistence |
| n8n | Docker container started from `ecard-factory/scripts/run-n8n.sh` | Docker `n8nio/n8n` | Optional workflow automation calling eCardFactory APIs |

External but operationally required runtime:

| Runtime | Source of startup command | Responsibility |
| --- | --- | --- |
| ComfyUI | `ecard-factory/startup.txt` | Local image generation engine called by ImageForge |

Important service boundary rules already reflected in code/docs:

- `imageforge` does not generate readable greeting text inside images.
- `ecard-factory` owns final card composition.
- n8n talks to eCardFactory, not directly to ContentForge.

## 3. Required Startup Order

Use this order for a reliable local bootstrap:

1. PostgreSQL
2. Ollama
3. ComfyUI
4. ContentForge
5. ImageForge
6. eCardFactory
7. n8n

Why this order:

- eCardFactory depends on its database and calls ContentForge/ImageForge.
- ContentForge depends on Ollama for local model access.
- ImageForge depends on PostgreSQL and ComfyUI.
- n8n is last because its workflows call back into eCardFactory at `http://host.docker.internal:8080`.

For the current 1-job manual flow, `n8n` is optional. The minimum interactive stack is:

1. PostgreSQL
2. Ollama
3. ComfyUI
4. ContentForge
5. ImageForge
6. eCardFactory

## 4. Port Mapping Table

| Component | Local URL / port | Source detected in repo | Notes |
| --- | --- | --- | --- |
| eCardFactory local run | `http://localhost:8080` | `ecard-factory/config/local.ports.env`, `ecard-factory/scripts/run-ecard.sh`, `ecard-factory/README.md` | This is the main local port for direct runs |
| eCardFactory app env default | `8000` | `ecard-factory/.env`, `ecard-factory/app/config.py`, `ecard-factory/docker-compose.yml` | Used by Docker/app config; differs from the local wrapper port |
| ContentForge | `http://localhost:8001` | `contentforge/startup.txt`, `ecard-factory/config/local.ports.env`, `ecard-factory/app/routers/generation.py` | eCardFactory hardcodes calls to `localhost:8001` |
| ImageForge | `http://127.0.0.1:8090` | `imageforge/.env`, `imageforge/scripts/run_local.sh`, `imageforge/app/config.py` | eCardFactory defaults `IMAGEFORGE_BASE_URL` to this URL |
| n8n | `http://localhost:5678` | `ecard-factory/config/local.ports.env`, `ecard-factory/scripts/run-n8n.sh` | Docker container maps host port to container port `5678` |
| PostgreSQL | `localhost:5432` | `ecard-factory/docker-compose.yml`, example DB URLs in `.env` files | Shared dependency for eCardFactory and ImageForge |
| Ollama | `http://127.0.0.1:11434` | `contentforge/.env` | Required by ContentForge |
| ComfyUI | `http://127.0.0.1:8188` | `imageforge/.env`, `imageforge/README.md` | Required by ImageForge |

## 5. Commands To Start Each Service Locally

### eCardFactory

Recommended local command:

```bash
cd ecard-factory
./scripts/run-ecard.sh
```

What it does:

- sources `config/local.ports.env` if present
- activates `venv/` if present
- builds the local console bundle with `npm run build:console`
- runs `uvicorn app.main:app` on `ECARD_PORT` (currently `8080`)

### ContentForge

Detected local command from `contentforge/startup.txt`:

```bash
cd contentforge
source venv/bin/activate
python -m uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload
```

Notes:

- ContentForge has its own `venv/`.
- It reads runtime settings from `contentforge/.env`.
- There is no separate port variable in `contentforge/.env`; the repo uses `8001` from startup docs and `ecard-factory/config/local.ports.env`.

### ImageForge

Recommended local commands:

```bash
cd imageforge
./scripts/setup_db.sh
./scripts/run_local.sh
```

What this does:

- sources `imageforge/.env`
- ensures the `imageforge` schema/tables exist
- runs `uvicorn app.main:create_app --factory --host 0.0.0.0 --port 8090 --reload`

### ComfyUI

Detected local startup command from [`ecard-factory/startup.txt`](/Users/aritrarpal/Documents/workspace_biz/content_generation_engine/ecard-factory/startup.txt):

```bash
cd /Volumes/Ari_SSD_01/AI_MODELS/comfyui
source .venv/bin/activate
python main.py --force-fp16
```

Notes:

- This path is outside the current repo.
- ImageForge expects ComfyUI at `COMFYUI_BASE_URL`, currently `http://127.0.0.1:8188`.
- The root `./start-all.sh` now attempts to start ComfyUI before ImageForge if it is not already responding.
- If the path has moved, set `COMFYUI_DIR` before running `./start-all.sh`.

### n8n

Existing repo startup command:

```bash
cd ecard-factory
./scripts/run-n8n.sh
```

What it does:

- reads `ecard-factory/config/local.ports.env`
- runs Docker image `n8nio/n8n`
- binds host port `5678`
- injects `ECARDFACTORY_BASE_URL=http://host.docker.internal:8080`

Note: `run-n8n.sh` is interactive (`docker run --rm -it`). The root `./start-all.sh` created for this repo runs the same container in detached mode so all services can come up from one command.

## 6. Commands To Verify Each Service Is Running

### eCardFactory

```bash
curl -s http://localhost:8080/health
curl -I http://localhost:8080/static/console/app.js
```

### ContentForge

```bash
curl -s http://localhost:8001/health
curl -s http://localhost:8001/models
```

Expected detail:

- `/health` should return JSON with `ok: true`
- `ollama_reachable` may be `false` if Ollama is down even though the API process is up

### ImageForge

```bash
curl -s http://127.0.0.1:8090/health
curl -i http://127.0.0.1:8090/ready
```

Expected detail:

- `/health` checks service/database/storage/provider health
- `/ready` is the stronger check and returns `503` if DB schema, ComfyUI, storage, or workflow file are not ready

### ComfyUI

```bash
curl -s -o /dev/null -w '%{http_code}\n' http://127.0.0.1:8188
```

Any non-`000` HTTP status confirms that the ComfyUI process is reachable on the configured port.

### n8n

```bash
curl -I http://localhost:5678
docker ps --filter name=^/n8n$
```

## 7. Environment Variables

### Primary Env Files

These are the files currently driving local startup:

- `ecard-factory/.env`
- `ecard-factory/config/local.ports.env`
- `contentforge/.env`
- `imageforge/.env`

### eCardFactory

Important keys in `ecard-factory/.env`:

- `DATABASE_URL`
- `OPENAI_API_KEY`
- `GROQ_API_KEY`
- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHAT_ID`
- `CANVA_CLIENT_ID`
- `CANVA_CLIENT_SECRET`
- `APP_ENV`
- `APP_PORT`
- `LOG_LEVEL`
- `DB_SCHEMA`
- `ASSET_STORAGE_BACKEND`
- `ASSET_STORAGE_ROOT`
- `ASSET_PUBLIC_BASE_URL`
- `IMAGE_PROVIDER`
- `IMAGE_CANDIDATES_PER_RUN`
- `WORKFLOW_MEMORY_FALLBACK_ENABLED`

Important keys in `ecard-factory/config/local.ports.env`:

- `ECARD_HOST_BIND=0.0.0.0`
- `ECARD_PORT=8080`
- `ECARD_RELOAD=false`
- `CONTENTFORGE_HOST_BIND=0.0.0.0`
- `CONTENTFORGE_PORT=8001`
- `CONTENTFORGE_RELOAD=false`
- `N8N_PORT=5678`
- `N8N_TIMEZONE=Asia/Kolkata`
- `N8N_DATA_DIR=$HOME/.n8n`
- `ECARD_BASE_URL=http://host.docker.internal:8080`

ImageForge integration in eCardFactory:

- `IMAGEFORGE_ENABLED` defaults to `true` in code
- `IMAGEFORGE_BASE_URL` defaults to `http://127.0.0.1:8090`
- `IMAGEFORGE_TIMEOUT_SECONDS` defaults to `300`
- `IMAGEFORGE_DEFAULT_PROVIDER` defaults to `comfyui`
- `IMAGEFORGE_DEFAULT_MODEL` defaults to `sd_xl_base_1.0`
- `IMAGEFORGE_DEFAULT_CANDIDATE_COUNT` defaults to `3`

### ContentForge

Important keys in `contentforge/.env`:

- `OLLAMA_URL`
- `OLLAMA_CHAT_MODELS`
- `OLLAMA_EMBEDDING_MODELS`
- `MAX_CONCURRENT_JOBS`
- `MAX_QUEUE`
- `BUSY_RETRY_AFTER_MS`
- `REQUEST_TIMEOUT_SEC`
- `JUDGE_ENABLED`
- `JUDGE_PROVIDER`
- `JUDGE_MODEL`
- `OPENAI_JUDGE_ENABLED`
- `OPENAI_API_KEY`
- `QUALITY_MEMORY_ENABLED`
- `QUALITY_MEMORY_DSN`
- `LOG_LEVEL`

### ImageForge

Important keys in `imageforge/.env`:

- `PORT=8090`
- `COMFYUI_BASE_URL=http://127.0.0.1:8188`
- `COMFYUI_WORKFLOW_PATH=workflows/comfyui/ecard_sdxl_basic.json`
- `COMFYUI_POSITIVE_NODE_ID`
- `COMFYUI_NEGATIVE_NODE_ID`
- `COMFYUI_SAVE_NODE_ID`
- `COMFYUI_BATCH_NODE_ID`
- `COMFYUI_TIMEOUT_SECONDS`
- `COMFYUI_POLL_INTERVAL_MS`
- `IMAGE_PROVIDER=comfyui`
- `IMAGE_STORAGE_BACKEND=filesystem`
- `IMAGE_STORAGE_ROOT`
- `IMAGE_PUBLIC_BASE_URL=http://localhost:8090/assets`
- `DATABASE_URL`
- `MAX_CONCURRENT_JOBS`
- `MAX_QUEUE`
- `DEFAULT_IMAGE_CANDIDATE_COUNT`

### n8n

There is no dedicated `n8n/.env` in this repo. Local startup currently inherits everything from `ecard-factory/config/local.ports.env` plus the Docker image defaults.

## 8. Dependencies / Prerequisites

Required before local startup:

- Python virtual environments already prepared:
  - `ecard-factory/venv`
  - `contentforge/venv`
  - `imageforge/.venv`
- Node.js and npm for the eCardFactory console bundle
- Docker for n8n
- PostgreSQL reachable on `localhost:5432`
- Ollama reachable on `127.0.0.1:11434`
- `psql` CLI available for `imageforge/scripts/setup_db.sh`
- Writable asset roots configured in:
  - `ecard-factory/.env` via `ASSET_STORAGE_ROOT`
  - `imageforge/.env` via `IMAGE_STORAGE_ROOT`

ComfyUI handling:

- `./start-all.sh` now attempts to start ComfyUI automatically if it is not already reachable.
- Auto-detection currently comes from `ecard-factory/startup.txt`.
- Override values when needed:
  - `COMFYUI_DIR`
  - `COMFYUI_ACTIVATE`
  - `COMFYUI_START_CMD`
  - `START_COMFYUI=false` to disable auto-start

Current local asset paths configured in the repo:

- eCardFactory: `/Volumes/Ari_SSD_01/ecardfactory-assets`
- ImageForge: `/Volumes/Ari_SSD_01/imageforge-assets`

If those volumes are not mounted locally, startup or readiness will fail.

## 9. Common Failure Points

1. `ecard-factory/.env` says `APP_PORT=8000`, but the local wrapper uses `ECARD_PORT=8080`. For the standard local workflow, treat `8080` as the real host port.
2. `ecard-factory/docker-compose.yml` also uses port `8000`. That Docker path is not the standard local multi-service bootstrap flow documented here.
3. `ecard-factory/scripts/run-contentforge.sh` is stale for this workspace. It looks for `contentforge/main.py` inside `ecard-factory/` and prints “Nothing to run separately.” Use the real sibling `contentforge/` service instead.
4. ImageForge starts only after `./scripts/setup_db.sh` has been run successfully against PostgreSQL.
5. ImageForge `/health` can be up while `/ready` is still failing because ComfyUI, storage, or DB schema are not ready.
6. ContentForge `/health` can be up while `ollama_reachable=false`, which means generation requests will still fail.
7. The eCardFactory local wrapper builds frontend assets. If `npm install` or `npm run build:console` fails, the backend may start but the UI will not be usable.
8. n8n workflow JSONs are hardcoded to `http://host.docker.internal:8080`. If you move eCardFactory to a different port, update both `ECARD_BASE_URL` and the imported n8n workflow URLs.
9. Repo docs are slightly inconsistent on Python versions. Overall project notes say Python `3.11`, while `contentforge/README.md` says `3.12` or `3.13`. Reuse the existing local virtualenvs unless you are intentionally rebuilding them.

## 10. Combined Start All Services

Use the root helper:

```bash
./start-all.sh
```

What `start-all.sh` does:

- starts ComfyUI first if it is not already reachable and a startup path/command is available
- starts eCardFactory from `ecard-factory/`
- starts ContentForge from `contentforge/`
- runs ImageForge DB bootstrap, then starts ImageForge from `imageforge/`
- starts n8n as a detached Docker container
- writes logs under `.ops/logs/`
- writes PID files under `.ops/pids/`

Important scope note:

- `./start-all.sh` starts the four repo-managed services plus ComfyUI when ComfyUI is locally configured or detected.
- It still does not start PostgreSQL or Ollama. Those remain external prerequisites.

## 11. Combined Stop All Services

Use the root helper:

```bash
./stop-all.sh
```

What `stop-all.sh` does:

- stops ComfyUI if it was started through the root helper
- stops eCardFactory, ContentForge, and ImageForge using the PID files created by `start-all.sh`
- stops the Docker container named `n8n` if it is running
- leaves unrelated processes untouched

## 12. Notes For Codex / AI Agents

1. Use `./start-all.sh` and `./stop-all.sh` from the repo root before inventing new local startup commands.
2. If the 1-job pipeline is failing, verify services in this order:
   - `curl -s -o /dev/null -w '%{http_code}\n' http://127.0.0.1:8188`
   - `curl -s http://localhost:8001/health`
   - `curl -i http://127.0.0.1:8090/ready`
   - `curl -s http://localhost:8080/health`
   - `curl -I http://localhost:5678`
3. Do not assume `docker-compose.yml` is the active local workflow. In this repo, the standard local path is direct Python service runs plus Docker n8n.
4. Do not use `ecard-factory/scripts/run-contentforge.sh` as the source of truth for ContentForge in this workspace.
5. If ports change, update these places together:
   - `ecard-factory/config/local.ports.env`
   - `ecard-factory/.env` values that embed public URLs
   - `imageforge/.env`
   - imported n8n workflow URLs
6. If ComfyUI moved from the path in `ecard-factory/startup.txt`, export `COMFYUI_DIR` before using `./start-all.sh`.
7. Logs from the root startup helper are under `.ops/logs/`. Check those first before changing code.
8. Respect the service boundaries already documented in `AGENTS.md`:
   - ContentForge owns text generation
   - ImageForge owns image generation
   - eCardFactory owns orchestration and final composition
