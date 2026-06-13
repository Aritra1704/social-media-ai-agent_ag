# ContentForge — Gemini Primary + Greeting-Card Quality Plan

Status: SPEC / for review. No code written yet.
Scope: `contentforge/` FastAPI service. Goal: replace poor Ollama output with Gemini-primary
generation, a greeting-card-specific prompt architecture, an optional seed-KB tailoring mode, and a
generate→judge→rewrite pipeline — while staying stateless, returning ranked candidates, and keeping
p95 latency < 10s.

---

## 0. What already exists (reuse, don't rebuild)

| Capability | Location | Reuse decision |
|---|---|---|
| Backend routing on `payload.backend` ∈ {ollama, groq} | `app/llm.py:1017 call_backend` | **Add `gemini` branch** |
| OpenAI-compatible HTTP caller | `app/llm.py:933 call_groq` | **Clone → `call_gemini`** |
| Quality scoring (task_fit, originality, tone, format) | `app/quality.py` | Reuse as-is; tune weights |
| Judge subsystem (OpenAI/Groq/Ollama) | `app/judge.py`, `src/judge/` | **Add Gemini judge provider** |
| Prompt builder w/ voice packs + cultural context | `src/prompts/phrase_prompt.py` | Extend, don't replace |
| Quality memory (Postgres) | `app/quality_memory.py` | Reuse for KB + few-shot store |
| Candidate ranking | `app/candidate_ranking.py` | Reuse |
| Concurrency/busy guard, timeouts | `app/busy.py`, `app/config.py` | Reuse |

Key implication: the existing `backend` enum and per-request model selection mean Gemini slots in as
a **third backend** with minimal blast radius. The judge already supports a non-generator provider,
so generator=Gemini-Flash + judge=Gemini-Pro is a natural pairing.

---

## 1. Switch to Gemini as primary generator

### 1.1 Provider integration
- Add `call_gemini(...)` in `app/llm.py`, mirroring `call_gemini` on the **OpenAI-compatibility
  endpoint** Google exposes:
  `https://generativelanguage.googleapis.com/v1beta/openai/chat/completions`.
  This lets us reuse the existing message/parse path almost verbatim (lowest-risk integration). Auth
  via `Authorization: Bearer ${GEMINI_API_KEY}`.
- Extend `backend` literal to `{"ollama", "groq", "gemini"}` in `app/schemas.py` and the
  `call_backend` dispatch at `app/llm.py:1017`.

### 1.2 Config (`app/config.py`)
```
GEMINI_API_KEY=...
GEMINI_GENERATOR_MODEL=gemini-2.5-flash      # primary generator
GEMINI_REWRITE_MODEL=gemini-2.5-flash        # pass-2 rewrite (cheap)
GEMINI_JUDGE_MODEL=gemini-2.5-pro            # pass-2 judge (smarter)
GEMINI_CONNECT_TIMEOUT_SEC=5
GEMINI_TIMEOUT_SEC=12
GEMINI_MAX_RETRIES=2                          # exp backoff: 0.5s, 1.5s
DEFAULT_BACKEND=gemini                         # flip default off ollama
```
- Add `request_timeout` defaults tuned to the 10s budget (see §5).
- Keep Ollama as a **configured fallback** (degraded mode) but no longer the default. Groq stays
  available as alt judge.

### 1.3 Sampling defaults for card copy
- `temperature` 0.9, `top_p` 0.95 for generation diversity across the 3–5 candidates.
- Generate candidates in **one call** (ask for N variants in a single response) rather than N calls —
  critical for latency. Fallback to 2 parallel calls only if a single call underfills.
- `temperature` 0.3 for judge and rewrite (determinism).

### 1.4 Cost/latency posture
- Flash for generation + rewrite (fast, cheap); Pro only for the judge pass, and only on the top
  candidates (not all). This keeps the smart-model cost bounded and within budget.

---

## 2. Prompt architecture for greeting-card copy

Greeting-card copy fails in specific, predictable ways with small models: generic blessings, clichés
("may your life be filled with…"), emoji spam, over-explaining the emotion, and Hinglish that reads
like translated English. The prompt system must attack these directly.

### 2.1 Layered prompt (extend `phrase_prompt.py`)
```
SYSTEM:
  - Role: expert greeting-card copywriter for the Indian market.
  - Hard rules: 1–3 sentences; no emojis unless requested; no salutation/sign-off;
    no meta ("Here are…"); never restate the occasion name as a definition.
  - Anti-cliché blocklist (occasion-specific) injected here.
  - Language contract: English | Hinglish. Hinglish = natural Roman-script code-mixing as a
    native bilingual speaker texts — NOT word-by-word translation. Give 1 gold Hinglish example.

USER (assembled from request):
  - Occasion + cultural_context (reuse cultural_context_guidance)
  - Voice pack (reuse selected_voice_pack) + tone sliders (reuse tone_direction)
  - Relationship/audience (sender→recipient), if provided
  - OPTIONAL seed lines (see §3) — "tailor in the spirit of these, do not copy"
  - Output contract: "Return exactly N candidates, one per line, no numbering, no commentary."
```

### 2.2 Occasion knowledge packs
Add an occasion registry keyed by normalized theme (Diwali, Valentine's, Eid, Holi, Raksha Bandhan,
birthday, anniversary…). Each pack supplies:
- **Emotional core** (Diwali → light over darkness, togetherness, fresh starts; Valentine's →
  intimacy/playful longing).
- **Concrete imagery allowed** (diyas, rangoli, mithai) vs **banned clichés**.
- **Register** (festival_respectful for Eid/Ramadan already wired at `phrase_prompt.py`).
This is the single biggest quality lever for a small/mid model: replacing "be culturally relevant"
(vague) with curated, occasion-specific raw material.

### 2.3 Few-shot conditioning
- Inject 2–3 **gold human-written exemplars** for the matched occasion+voice pack into the system
  prompt. Pulled from the seed KB (§3). Few-shot > instruction for tone fidelity.

---

## 3. Seed-KB approach — recommended, as a *conditioning* layer (not a selector)

Your other project's pattern (curate human variants, LLM selects/tailors) maps well here **but with a
twist**: greeting cards need controllable novelty (users regenerate; repetition is visible), so a
pure "select from KB" mode will feel stale fast. Recommendation:

**Hybrid: KB-conditioned generation.**
- KB stores ~10–30 gold human-written lines per (occasion × voice pack), tagged with
  cultural_context and language. Reuse the Postgres layer (`quality_memory.py`) — add a `seed_lines`
  table; service stays stateless (KB is read-only reference data, not session state).
- At request time: retrieve top-k matching seeds → inject as **few-shot exemplars + "tailor, don't
  copy" instruction**. The model generates fresh variants in the proven register.
- This gives the tone-quality of curation with the novelty of generation. It also creates a quality
  flywheel: judge-winning outputs (§4) can be promoted back into the KB.

**Two modes, request-controlled:**
- `kb_mode=off` — pure generation (cold occasions, long tail).
- `kb_mode=condition` (default) — few-shot from KB, generate fresh.
- (Optional later) `kb_mode=select` — for ultra-safe occasions, return lightly-tailored KB lines
  directly (lowest latency, lowest novelty).

Verdict: **Yes, build the seed KB**, but as a conditioning/few-shot source with a generation step on
top — not as the primary output path. Start with `condition` mode; seed ~6–8 top occasions first.

---

## 4. Two-pass generate → judge → rewrite pipeline

Stateless, single request, within 10s. Reuses the existing judge + quality engine.

```
PASS 1 — GENERATE (Gemini Flash, 1 call, ~2–4s)
  build_messages(...) with §2 layered prompt + §3 KB few-shot
  → N+2 candidates (over-generate to give the judge/filter room)
  → deterministic quality.py scoring (task_fit, originality, tone, format)
  → hard-fail drops (wrong sentence count, emoji, JSON leak, cliché hits)

GATE
  if ≥N candidates pass hard checks AND top score ≥ HIGH_CONF_THRESHOLD:
      skip rewrite → rank → return   (fast path, saves latency on easy occasions)

PASS 2 — JUDGE + REWRITE (only when needed)
  JUDGE (Gemini Pro, 1 call, ~3–5s):
     score top 4 survivors on: cultural_fit, emotional_resonance, originality,
     language_naturalness (Hinglish authenticity), brevity-compliance.
     Returns per-candidate scores + a short "what's weak" note per candidate.
  REWRITE (Gemini Flash, 1 call, ~2–3s):
     feed the 2–3 best candidates + judge's weakness notes back:
     "improve these specific lines on these specific axes; keep what works."
     Re-score rewrites with quality.py; keep best of {original, rewritten}.

RANK & RETURN
  candidate_ranking.py → ranked list of 3–5, each with score breakdown + provenance
  (generated | kb_conditioned | rewritten).
```

### Pipeline guarantees
- **Idempotency / determinism**: judge & rewrite at temp 0.3; pipeline is pure function of request.
- **Graceful degradation**: any pass-2 timeout → return best pass-1 candidates (never fail the
  request for a rewrite miss). Reuse `judge_fallback_to_baseline`.
- **Latency control**: fast-path gate means most easy requests never pay for pass-2.
- **Flywheel**: persist judge scores to quality_memory; promote consistent winners into seed KB.

---

## 5. Latency budget (target p95 < 10s)

| Stage | Model | Budget |
|---|---|---|
| Pass-1 generate | Flash | 2–4s |
| Deterministic scoring/filter | local | <100ms |
| Judge (only if gated in) | Pro | 3–5s |
| Rewrite (only if gated in) | Flash | 2–3s |
| Rank/serialize | local | <100ms |
| **Easy (fast path)** | | **~3–4s** |
| **Hard (full 2-pass)** | | **~8–9s** |

Controls: per-call connect timeout 5s, total 12s hard ceiling; pass-2 budget-aware (skip rewrite if
<3s remaining); single-call multi-candidate generation; Pro judge only on ≤4 survivors.

---

## 6. Rollout / sequencing

1. **M1 — Gemini backend**: `call_gemini`, config, dispatch, schema enum. Flip `DEFAULT_BACKEND`.
   A/B against Ollama on a fixed eval set. (No pipeline change yet.)
2. **M2 — Prompt architecture**: occasion packs + anti-cliché blocklists + Hinglish contract +
   few-shot scaffolding (static exemplars first, no DB).
3. **M3 — Seed KB**: `seed_lines` table + retrieval + `kb_mode`. Seed 6–8 occasions.
4. **M4 — Two-pass pipeline**: Gemini judge provider + rewrite stage + fast-path gate + provenance.
5. **M5 — Flywheel**: promote judge winners → KB; dashboards on win-rate by occasion/voice pack.

Each milestone is independently shippable and measurable on a held-out eval set (define ~30
occasion×tone prompts with human quality ratings before M1, so "quality is poor" becomes a number).

---

## Decisions (locked 2026-06-13)
1. **Gemini access**: existing AI Studio API key (reused from other projects). Endpoint
   `…/v1beta/openai/chat/completions`, Bearer auth. No Vertex.
2. **Hinglish default**: HEAVY code-mix (Roman-script bilingual texting style). Because heavy
   code-mix is the hardest mode for mid-size models, the KB gold exemplars are the primary quality
   lever, and `language_naturalness` is a first-class scored axis in the judge.
3. **Eval set**: build first as **M0** (~30 prompts + 1–5 rubric across emotional resonance,
   cultural/Hinglish authenticity, freshness). Targets: avg ≥4.0, hard-fail <2%, ≥90% of requests
   with at least one 4+ candidate.
4. **Ollama**: KEEP as offline/quota fallback. Gemini primary; Ollama only when Gemini unreachable.

## Still open
- Occasion priority for the seed KB — which 6–8 occasions to seed first?
