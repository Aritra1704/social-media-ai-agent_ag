# Project Overview
eCardFactory system that generates greeting cards using text (ContentForge) and images (ImageForge), then composes final cards.

## Architecture
Microservices:

- ecardfactory → orchestration + UI + final render
- contentforge → text generation
- imageforge → image generation (ComfyUI)

## Flow
1. Generate text options
2. Shortlist text
3. Select text
4. Generate images
5. Select image
6. Render final card
7. Approve export

## Tech Stack
- Backend: FastAPI (Python 3.11)
- DB: PostgreSQL
- Image: ComfyUI (local)
- AI: OpenAI / Ollama / Groq
- Automation: n8n

## Key Rules
- imageforge NEVER generates text inside images
- ecardfactory owns final composition
- services communicate via REST APIs
- configs are DB-driven

## Current Focus
Stage 4 deterministic quality and operator-config hardening:
text shortlist → text select → image generate → image select → final preview → quality check → export

## Known Issues
- Stage 3 composition still needs one live Studio visual signoff pass
- Stage 4 scoring is implemented, but content quality still needs real improvement in downstream prompts/ranking
- config catalog now exists, but it still needs live UI verification against the running stack
- image generation can still be slow

## Coding Guidelines
- keep services independent
- no cross-service tight coupling
- use clear API contracts
- log every stage of pipeline
