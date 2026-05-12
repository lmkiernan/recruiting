# Recruiter Signal

A full-stack recruiting intelligence tool that seeds a pool of real GitHub developer profiles into PostgreSQL, scores every candidate against a free-text job description using an explainable heuristic model, then re-scores the top 25 with GPT-4o-mini and surfaces the ranked results in a live React dashboard.

---

## Table of Contents

1. [What it does](#what-it-does)
2. [Architecture overview](#architecture-overview)
3. [Tech stack](#tech-stack)
4. [Project structure](#project-structure)
5. [Prerequisites](#prerequisites)
6. [Environment variables](#environment-variables)
7. [Database setup](#database-setup)
8. [Seeding the candidate pool](#seeding-the-candidate-pool)
9. [Running the backend](#running-the-backend)
10. [Running the frontend](#running-the-frontend)
11. [API reference](#api-reference)
12. [Scoring system](#scoring-system)
13. [AI evaluation pipeline](#ai-evaluation-pipeline)
14. [Frontend architecture](#frontend-architecture)
15. [Data models](#data-models)
16. [Configuration reference](#configuration-reference)

---

## What it does

Paste a job description into the sidebar. The system immediately:

1. Scores every candidate in the database with a fully-explainable, zero-latency heuristic model and returns ranked results.
2. Fires GPT-4o-mini against the top 25 candidates in parallel batches — all 5 API calls run concurrently so AI results arrive in ~15 s instead of ~75 s.
3. Re-ranks the list as AI scores stream in; the frontend polls every 3 s and updates cards and detail panels in real time.
4. Shows per-candidate breakdowns: a four-bar score chart (Technical match / Activity signal / Profile signal / Repo quality), a plain-English summary, heuristic evidence bullets, and AI-generated strengths and concerns.

In browse mode (no job description), the candidate pool is fully filterable by name, language, location, follower range, repo count, and profile completeness.

---

## Architecture overview

```
┌──────────────────────────────────────────────────────────────────────┐
│  Browser (React 18 + Vite + Tailwind)                                │
│                                                                      │
│  DashboardPage                                                       │
│  ├── Left sidebar  — JobDescriptionInput, CandidateFiltersPanel      │
│  ├── Center list   — CandidateCard × N (live score badges)           │
│  └── Right panel  — CandidateDetailPanel (breakdown bars + evidence) │
│                                                                      │
│  Polling: useEvaluationPolling → GET /evaluation-runs/{id}/candidates│
│           every 3 s until status = "completed" | "ai_failed"        │
└───────────────┬──────────────────────────────────────────────────────┘
                │  HTTP (dev: Vite proxy /api → :8000)
                ▼
┌──────────────────────────────────────────────────────────────────────┐
│  FastAPI  (uvicorn, port 8000)                                       │
│                                                                      │
│  POST /jobs                  — create or reuse job record            │
│  POST /evaluation-runs       — heuristic-score all candidates,       │
│                                return immediately (status=            │
│                                "heuristic_complete"), kick off AI    │
│                                as a BackgroundTask                   │
│  GET  /evaluation-runs/{id}  — poll run status + progress counts     │
│  GET  /evaluation-runs/{id}/candidates — ranked evaluation list      │
│  GET  /candidates            — filterable browse mode                │
│  GET  /candidates/{id}       — full candidate detail                 │
└───────────┬────────────────────────┬─────────────────────────────────┘
            │ SQLAlchemy             │ BackgroundTask thread
            ▼                        ▼
┌───────────────────┐    ┌───────────────────────────────────────────┐
│  PostgreSQL        │    │  ai_evaluation_service.run_ai_evaluation  │
│                   │    │                                           │
│  candidates       │    │  1. Query top 25 evals by heuristic_score │
│  candidate_repos  │    │  2. Preload all candidate profiles        │
│  candidate_langs  │◄───│  3. Build 5 batches of 5 profiles each   │
│  jobs             │    │  4. Fire all 5 OpenAI calls in parallel   │
│  evaluation_runs  │    │     (ThreadPoolExecutor, max_workers=5)   │
│  candidate_evals  │    │  5. Blend scores: ai*0.7 + heuristic*0.3  │
└───────────────────┘    │  6. Commit all results, mark "completed"  │
                         └───────────────────────────────────────────┘
                                          │
                                          ▼
                                   OpenAI gpt-4o-mini
```

### Request / response flow for an evaluation

```
Client                          FastAPI                     Background thread
  │                               │                               │
  ├─POST /jobs ──────────────────►│ create Job row                │
  │◄─ {id: 42} ──────────────────┤                               │
  │                               │                               │
  ├─POST /evaluation-runs ───────►│ score_all_candidates()        │
  │  {job_id: 42}                 │  (heuristic, ~50 ms)          │
  │                               │ persist all CandidateEval rows│
  │                               │ status → "heuristic_complete" │
  │                               │ add_task(run_ai_evaluation)   │
  │◄─ {status:"heuristic_        │                               │
  │    complete", evaluations:…} ─┤ ─────────────────────────────►│
  │                               │                               │ 5× OpenAI calls
  ├─GET /evaluation-runs/1 ──────►│ return run status             │  in parallel
  │◄─ {status:"heuristic_        │                               │  (~15 s total)
  │    complete", completed: 0} ──┤                               │
  │  (poll every 3 s)             │                               │ blend & commit
  ├─GET /evaluation-runs/1 ──────►│                               │
  │◄─ {status:"completed",       │                               │
  │    completed: 25} ────────────┤◄──────────────────────────────┘
  │                               │
  ├─GET /evaluation-runs/1/      │
  │  candidates ─────────────────►│ return all evals ordered by
  │◄─ [{final_score:87,…},…] ────┤  final_score DESC
```

---

## Tech stack

| Layer | Technology |
|---|---|
| Frontend | React 18, TypeScript 5.6, Vite 5, Tailwind CSS 3 |
| Backend | Python 3.11+, FastAPI, Uvicorn |
| ORM | SQLAlchemy 2 (sync, psycopg2-binary) |
| Database | PostgreSQL 14+ |
| AI | OpenAI Python SDK, gpt-4o-mini |
| GitHub data | GitHub REST API v3 (via httpx) |
| Config | pydantic-settings (.env file) |
| Parallelism | `concurrent.futures.ThreadPoolExecutor` for AI batches |

---

## Project structure

```
recruiting/
├── backend/
│   ├── .env                          # secret keys, never committed
│   ├── requirements.txt
│   └── app/
│       ├── main.py                   # FastAPI app, CORS, lifespan
│       ├── core/
│       │   ├── config.py             # pydantic-settings env loader
│       │   ├── database.py           # engine, SessionLocal, Base
│       │   └── deps.py               # get_db() FastAPI dependency
│       ├── models/
│       │   ├── candidate.py          # Candidate, CandidateRepository, CandidateLanguage
│       │   ├── evaluation.py         # EvaluationRun, CandidateEvaluation
│       │   ├── job.py                # Job
│       │   ├── user.py               # User, GuestSession (future auth)
│       │   └── shortlist.py          # Shortlist, ShortlistCandidate (stub)
│       ├── schemas/
│       │   ├── candidate.py          # Pydantic v2 response schemas
│       │   ├── evaluation.py         # EvaluationRunOut, CandidateEvaluationOut, …
│       │   └── job.py                # JobCreate, JobOut
│       ├── api/routes/
│       │   ├── candidates.py         # GET /candidates, GET /candidates/{id}
│       │   ├── evaluations.py        # POST/GET /evaluation-runs
│       │   └── jobs.py               # POST /jobs
│       ├── services/
│       │   ├── candidate_signal_service.py   # heuristic scoring engine
│       │   └── ai_evaluation_service.py      # OpenAI evaluation + blending
│       └── scripts/
│           └── seed_github_candidates.py     # one-shot GitHub seeder
│
└── frontend/
    ├── index.html
    ├── vite.config.ts                # dev proxy: /api → http://localhost:8000
    ├── tailwind.config.js
    ├── src/
    │   ├── main.tsx
    │   ├── App.tsx
    │   ├── styles/globals.css
    │   ├── vite-env.d.ts
    │   ├── pages/
    │   │   └── DashboardPage.tsx     # top-level page — all state lives here
    │   ├── components/
    │   │   ├── candidates/
    │   │   │   ├── CandidateCard.tsx        # list item with score badge
    │   │   │   ├── CandidateDetailPanel.tsx # right panel, breakdown bars
    │   │   │   └── CandidateFilters.tsx     # browse-mode filter inputs
    │   │   ├── jobs/
    │   │   │   └── JobDescriptionInput.tsx  # JD textarea + evaluate button
    │   │   └── ui/
    │   │       ├── EmptyState.tsx
    │   │       ├── ErrorState.tsx
    │   │       └── Spinner.tsx
    │   ├── features/
    │   │   ├── candidates/
    │   │   │   ├── api.ts            # fetchCandidates, fetchCandidateDetail
    │   │   │   ├── hooks.ts          # useCandidates, useCandidateDetail
    │   │   │   └── types.ts          # CandidateSummary, CandidateDetail, …
    │   │   └── evaluations/
    │   │       ├── api.ts            # runEvaluation, fetchRunStatus, fetchRunCandidates
    │   │       ├── hooks.ts          # useEvaluationPolling
    │   │       └── types.ts          # CandidateEvaluation, EvaluationRunWithResults, …
    │   └── utils/
    │       └── scoreColor.ts         # shared score → Tailwind class helpers
```

---

## Prerequisites

- **Python 3.11+** with pip
- **Node.js 20+** with npm
- **PostgreSQL 14+** running locally (or a remote connection string)
- A **GitHub personal access token** (classic, no scopes required for public data — raises the rate limit from 60 to 5 000 req/h)
- An **OpenAI API key** (optional — heuristic scoring works without it; AI re-ranking requires it)

---

## Environment variables

### `backend/.env`

```dotenv
# Required
DATABASE_URL=postgresql://postgres:password@localhost:5432/recruiter_signal
GITHUB_TOKEN=ghp_xxxxxxxxxxxxxxxxxxxx

# Optional — AI evaluation is skipped when blank
OPENAI_API_KEY=sk-proj-xxxxxxxxxxxxxxxxxxxx

# Optional — defaults shown
FRONTEND_ORIGIN=http://localhost:5173
SECRET_KEY=change-me-in-production
```

`GITHUB_TOKEN` must be a classic PAT. Fine-grained tokens work too provided they have **read-only access to public repositories**.

`DATABASE_URL` must use the `postgresql://` scheme. The `postgresql+psycopg2://` dialect prefix is also accepted.

### `frontend/.env`

```dotenv
# Only needed if you change the backend port
VITE_API_BASE=http://localhost:8000
```

The Vite dev proxy rewrites `/api/*` to `http://localhost:8000/*` so in development the frontend never needs the base URL in code — all fetches use relative `/api/…` paths.

---

## Database setup

Create the database (if it does not already exist):

```bash
psql -U postgres -c "CREATE DATABASE recruiter_signal;"
```

Tables are created automatically by FastAPI's `lifespan` handler on first startup using `Base.metadata.create_all()`. No migrations are required for a fresh install.

If you need to reset the schema completely (e.g. after a model change that adds columns to existing tables):

```sql
DROP TABLE IF EXISTS
  shortlist_candidates, shortlists,
  candidate_evaluations, evaluation_runs,
  jobs, users, guest_sessions,
  candidate_languages, candidate_repositories, candidates
CASCADE;
```

Then restart the backend — `create_all` will recreate all tables.

---

## Seeding the candidate pool

The seeder fetches real GitHub developer profiles and writes them to PostgreSQL. It uses 9 search queries across popular languages and cities, collects 4× the target login count to account for profiles that fail post-fetch quality filters, then resolves each login to a full profile and saves it.

```bash
cd backend
python -m app.scripts.seed_github_candidates --limit 100
```

`--limit` controls the maximum number of candidates saved (default: 100). The script will collect up to `4 × limit` login candidates via search, then stop as soon as `limit` passing profiles have been saved.

### What the seeder collects

For each candidate it saves:

| Field | Source |
|---|---|
| github_id, github_username | `GET /users/{login}` |
| name, bio, company, location | `GET /users/{login}` |
| avatar_url, profile_url | `GET /users/{login}` |
| followers, following, public_repos | `GET /users/{login}` |
| profile_completeness | computed (see below) |
| repositories (up to 10) | `GET /users/{login}/repos?sort=pushed` |
| languages | aggregated from repo primary languages |

**Profile completeness** is computed from five fields — name, bio, location, company, website:

| Fields present | Label |
|---|---|
| 4–5 | `high` |
| 2–3 | `medium` |
| 0–1 | `low` |

### Quality filters

A profile is **skipped** (not saved) if any of the following are true:

- GitHub account type is not `"User"` (i.e., organisations are excluded)
- Followers ≥ 2 000 (filters out celebrities who would skew scores)
- Public repos < 3 or > 150
- Both `name` and `bio` are missing (no signal for the heuristic model)
- Zero non-forked repositories after fetching

### Rate limiting

The seeder handles GitHub's rate limit automatically. If it receives a `403`, it reads `X-RateLimit-Reset` and sleeps until the window resets. The GitHub Search API has a separate, stricter limit; the seeder sleeps 1.2 s between search calls to stay comfortably under it.

### Re-running the seeder

The seeder is **idempotent**. If a candidate already exists (matched by `github_id`), the script updates all profile fields and replaces their repositories and language aggregates. It will not create duplicate rows.

---

## Running the backend

```bash
cd backend

# First time only
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# Every time
source .venv/bin/activate
uvicorn app.main:app --reload --port 8000
```

The API will be available at `http://localhost:8000`. Interactive docs are at `http://localhost:8000/docs`.

Health check:

```bash
curl http://localhost:8000/health
# {"status":"ok"}
```

---

## Running the frontend

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173`. The Vite dev server proxies all requests that start with `/api` to `http://localhost:8000`, stripping the `/api` prefix, so the frontend and backend can run on different ports without CORS issues.

---

## API reference

All endpoints return JSON. Error responses follow FastAPI's default `{"detail": "…"}` shape.

### `GET /health`

Returns `{"status": "ok"}`. Useful for uptime checks.

---

### `POST /jobs`

Creates a job record from a free-text description.

**Request body**

```json
{
  "title": "Senior Backend Engineer",
  "description": "We need a Python / Go engineer with PostgreSQL and AWS experience…"
}
```

**Response** `201`

```json
{
  "id": 42,
  "title": "Senior Backend Engineer",
  "description": "…",
  "created_at": "2026-05-12T14:00:00Z"
}
```

---

### `POST /evaluation-runs`

Scores all candidates against a job and returns immediately with heuristic results. AI evaluation runs in a background thread.

**Request body**

```json
{ "job_id": 42 }
```

**Response** `201`

```json
{
  "id": 1,
  "job_id": 42,
  "status": "heuristic_complete",
  "candidate_count": 200,
  "completed_count": 0,
  "created_at": "2026-05-12T14:00:01Z",
  "completed_at": null,
  "evaluations": [
    {
      "id": 1,
      "candidate_id": 55,
      "heuristic_score": 78.4,
      "ai_score": null,
      "final_score": 78.4,
      "technical_match": 41.2,
      "activity_signal": 22.1,
      "profile_completeness_score": 12.0,
      "summary": "Strong technical match with Python/Go signal…",
      "breakdown": [
        {"label": "Technical match", "score": 41.2, "max": 50},
        {"label": "Activity signal", "score": 22.1, "max": 25},
        {"label": "Profile signal",  "score": 12.0, "max": 15},
        {"label": "Repo quality",    "score": 3.1,  "max": 10}
      ],
      "evidence": [
        "Python appears in 14 repositories",
        "Keywords found in profile/repos: api, postgresql, docker",
        "3 repositories pushed in the last 6 months"
      ],
      "concerns": [
        "No explicit cloud/deployment signal found"
      ],
      "status": "heuristic",
      "candidate": { "id": 55, "github_username": "…", … }
    },
    …
  ]
}
```

The list is sorted by `final_score DESC`. While `status` is `"heuristic_complete"`, `ai_score` is `null` for all candidates and `final_score` equals `heuristic_score`. Once AI completes, the top 25 will have blended `final_score` values and the list order may change.

---

### `GET /evaluation-runs/{run_id}`

Polls the run's status and progress counters. Does **not** return evaluation detail.

**Response** `200`

```json
{
  "id": 1,
  "job_id": 42,
  "status": "completed",
  "candidate_count": 200,
  "completed_count": 25,
  "created_at": "2026-05-12T14:00:01Z",
  "completed_at": "2026-05-12T14:00:17Z"
}
```

**Status values**

| Value | Meaning |
|---|---|
| `running` | Heuristic scoring in progress (very short) |
| `heuristic_complete` | Heuristic done, AI in progress |
| `completed` | Both heuristic and AI done |
| `ai_failed` | Heuristic succeeded, AI threw an unrecoverable error |

---

### `GET /evaluation-runs/{run_id}/candidates`

Returns all candidate evaluations for a run, ordered by `final_score DESC`. Structure is identical to the `evaluations` array in the `POST /evaluation-runs` response.

After AI completes, the top 25 candidates will have `ai_score` populated, `status: "completed"`, and blended `final_score` values. Candidates ranked 26+ retain their heuristic-only `final_score`.

---

### `GET /candidates`

Browse the full candidate pool with optional filters.

**Query parameters**

| Parameter | Type | Description |
|---|---|---|
| `q` | string | Full-text search on name, username, bio, location (case-insensitive `ILIKE`) |
| `language` | string | Exact primary language match (case-insensitive) |
| `location` | string | Partial location match |
| `min_followers` | int | Lower follower bound (≥ 0) |
| `max_followers` | int | Upper follower bound (≤ 1999) |
| `min_repos` | int | Minimum public repo count |
| `profile_completeness` | string | `low` \| `medium` \| `high` |
| `limit` | int | Page size, 1–200, default 100 |
| `offset` | int | Pagination offset, default 0 |

Results are ordered by `followers DESC`.

---

### `GET /candidates/{candidate_id}`

Returns the full candidate detail including all repositories and languages.

---

## Scoring system

Every evaluation produces a transparent score out of 100 broken into four weighted components.

### Score breakdown

| Component | Weight | Max pts | What it measures |
|---|---|---|---|
| Technical match | 50% | 50 | Language + keyword overlap between candidate and job description |
| Activity signal | 25% | 25 | Recency of repository activity |
| Profile signal | 15% | 15 | Profile completeness + follower count |
| Repo quality | 10% | 10 | Described repos + aggregate stars |

### Technical match (50 pts)

**Language overlap (30 pts of the 50)**

Languages are extracted from the job description using a regex word-boundary search against a canonical map (e.g. `"golang"` → `"Go"`, `"ts"` → `"TypeScript"`). The candidate's languages are weighted by repo count. The score is:

```
matched_repos / total_repos × 100   (capped at 100)
```

This means a candidate with 15 Python repos and 5 other repos would score 75% on a Python job.

**Keyword overlap (20 pts of the 50)**

A set of ~70 technical keywords (API patterns, frameworks, databases, cloud providers, etc.) is extracted from the job description. The candidate's bio, company, and all repository names and descriptions are searched for each keyword. The score is:

```
matched_keywords / jd_keywords × 100   (capped at 100)
```

### Activity signal (25 pts)

The most recently pushed repository determines the score using exponential decay with a one-year half-life:

```
score = 100 × e^(−days_since_push / 365)
```

A push today scores 100; a push 365 days ago scores ~37; a push two years ago scores ~14.

### Profile signal (15 pts)

Two sub-components:

- **Completeness (10 pts):** `high` → 100, `medium` → 60, `low` → 20 (then × 0.10)
- **Followers (5 pts):** log-scaled between 20 (the seed floor) and 2 000 (the seed ceiling), mapped to 0–100 (then × 0.05)

### Repo quality (10 pts)

Three sub-components summed and capped at 100 before weighting:

- **Described repos:** fraction of repos with a description longer than 20 characters (max 50 pts contribution)
- **Star score:** `log(total_stars + 1) / log(100) × 40` (max 40 pts contribution)
- **Count bonus:** 10 pts if ≥ 5 repos, 5 pts otherwise

### Evidence and concerns

For each scored candidate, the heuristic engine generates plain-English bullets:

**Evidence** (green ✓ in the UI) — things the candidate demonstrably has:
- `"Python appears in 14 repositories"`
- `"Keywords found in profile/repos: api, postgresql, docker"`
- `"3 repositories pushed in the last 6 months"`
- `"5 repositories with notable GitHub stars"`
- `"Profile is highly complete (name, bio, location all present)"`

**Concerns** (amber ! in the UI) — gaps relative to the job description:
- `"No explicit Go signal found in profile or repositories"`
- `"No explicit cloud/deployment signal found"`
- `"No repository activity found in the last 6 months"`
- `"Profile is incomplete — limited signal available"`

---

## AI evaluation pipeline

When `OPENAI_API_KEY` is set, the top 25 candidates by heuristic score are re-evaluated using GPT-4o-mini after the heuristic pass completes.

### Score blending

```
final_score = ai_score × 0.7 + heuristic_score × 0.3
```

This blend means heuristic scores for candidates ranked 26+ stay unchanged (no AI call is made), and the AI score has majority weight for the top 25.

### Parallel batch processing

The 25 candidates are split into 5 batches of 5. All 5 OpenAI API calls are fired simultaneously using `ThreadPoolExecutor`:

```python
with ThreadPoolExecutor(max_workers=len(batches)) as pool:
    futures = {
        pool.submit(call_batch, i, batch_evals, profiles): i
        for i, (batch_evals, profiles) in enumerate(batches)
    }
    batch_results = [f.result() for f in as_completed(futures)]
```

Since the candidate profile data is already loaded into memory before the thread pool starts, no thread touches the SQLAlchemy session — the session is only used in the main thread after all futures resolve. This avoids any session threading issues.

Total AI evaluation time is dominated by the slowest of the 5 parallel calls rather than their sum — typically ~10–20 s depending on OpenAI latency.

### Prompt structure

Each batch call sends a system prompt establishing the evaluator persona and a user prompt containing:

- The full job description
- JSON array of candidate profiles (username, bio, company, location, followers, top 8 languages, top 8 repos with name/description/stars/language)

The model is instructed to return a JSON object with an `evaluations` array. Each element must include:

| Field | Type | Description |
|---|---|---|
| `candidate_id` | integer | Matched back to the database row |
| `ai_score` | integer 0–100 | Role-specific fit |
| `summary` | string | 2–3 evidence-backed sentences |
| `strengths` | string[] | 2–4 specific strengths relevant to the JD |
| `concerns` | string[] | 1–3 honest gaps for this specific role |

`response_format: {"type": "json_object"}` is used to guarantee parseable output. Temperature is set to 0.3 for consistency.

### What AI replaces vs. preserves

| Field | After heuristic | After AI |
|---|---|---|
| `breakdown` bars | Computed heuristic sub-scores | **Unchanged** — always shows heuristic breakdown |
| `evidence` bullets | Heuristic observations | Replaced with AI `strengths` |
| `concerns` bullets | Heuristic gaps | Replaced with AI `concerns` |
| `summary` | Generic heuristic summary | Replaced with AI summary |
| `heuristic_score` | Set | **Unchanged** |
| `ai_score` | null | Set by AI |
| `final_score` | = heuristic_score | Blended (ai × 0.7 + heuristic × 0.3) |

The four breakdown bars always reflect the heuristic model so the score is always explainable — the AI score is additive context, not a black box replacement.

---

## Frontend architecture

### State management

All state lives in `DashboardPage`. There is no global store. The two modes — browse and eval — are mutually exclusive and managed by a single `evalRun` state variable:

```
evalRun === null  →  browse mode (useCandidates hook active, filters shown)
evalRun !== null  →  eval mode  (useCandidates returns null/skips fetch)
```

Derived values (never stored as state):

```typescript
const isEvalMode  = evalRun !== null;
const isAiRunning = evalRun?.status === "heuristic_complete";
const evalItems   = useMemo(…);   // filtered evalRun.evaluations
const selectedEval = useMemo(…);  // single eval for detail panel
```

### Polling

`useEvaluationPolling` uses a `useRef`-based cancellation flag instead of state so that unmounting or clearing the eval doesn't cause state updates on a dead component:

```typescript
active.current = true;

async function tick() {
  if (!active.current) return;
  const [runInfo, candidates] = await Promise.all([
    fetchRunStatus(runId),
    fetchRunCandidates(runId),
  ]);
  if (!active.current) return;
  onUpdate(…);
  if (TERMINAL_STATUSES.has(runInfo.status)) stop();
  else setTimeout(tick, 3000);
}
```

The `onUpdate` callback is stabilized with `useCallback(…, [])` at the call site, preventing stale closures inside the polling loop.

### Score color utility

All score → color mappings use a single shared utility (`src/utils/scoreColor.ts`) to keep thresholds consistent:

```
score ≥ 70  →  green
score ≥ 45  →  yellow
score < 45  →  gray
```

Three exports: `scoreBadgeColor` (badge bg+text), `scoreTextColor` (large text), `scoreBarColor` (bar fill).

### Component tree

```
DashboardPage
├── aside.left
│   ├── JobDescriptionInput     — textarea + Evaluate / Clear buttons
│   └── CandidateFiltersPanel   — only visible in browse mode
├── main.center
│   ├── status banner           — amber (AI running) | blue (AI complete)
│   ├── search input
│   └── CandidateCard × N       — score badge (purple AI pill + colored score)
└── aside.right
    └── CandidateDetailPanel
        ├── EvalSection         — only in eval mode
        │   ├── score header (blended final_score)
        │   ├── BreakdownBar × 4
        │   ├── evidence list (✓ bullets)
        │   └── concerns list (! bullets)
        ├── profile header (avatar, name, GitHub link, company, location)
        ├── bio
        ├── stats (followers / repos / following)
        ├── languages (bubble pills with repo count)
        ├── top repositories (linked cards with stars + forks)
        └── profile completeness badge
```

---

## Data models

### `candidates`

| Column | Type | Notes |
|---|---|---|
| id | integer PK | |
| github_id | integer unique | Used for upsert identity |
| github_username | varchar(255) unique | |
| name | varchar(255) nullable | |
| avatar_url | text nullable | |
| profile_url | text nullable | |
| bio | text nullable | |
| company | varchar(255) nullable | |
| location | varchar(255) nullable | |
| followers | integer | |
| following | integer | |
| public_repos | integer | |
| profile_completeness | varchar(50) | `low` \| `medium` \| `high` |
| created_at | timestamptz | server default |
| updated_at | timestamptz | auto on update |
| last_synced_at | timestamptz | set by seeder |

### `candidate_repositories`

Stores up to 10 non-forked repos per candidate (sorted by `pushed_at` DESC).

| Column | Type | Notes |
|---|---|---|
| github_repo_id | integer unique | Used for upsert identity |
| candidate_id | integer FK | |
| name, description, url | text | |
| language | varchar(100) | Primary language |
| stars, forks | integer | |
| pushed_at | varchar(100) | ISO 8601 string from GitHub |

### `candidate_languages`

Aggregated language → repo_count per candidate. Unique constraint on `(candidate_id, language)`.

### `jobs`

| Column | Type |
|---|---|
| id | integer PK |
| title | varchar(500) |
| description | text |
| user_id | integer nullable FK (future auth) |
| guest_session_id | varchar nullable FK (future auth) |
| created_at | timestamptz |

### `evaluation_runs`

| Column | Type | Notes |
|---|---|---|
| id | integer PK | |
| job_id | integer FK | |
| status | varchar(50) | `running` → `heuristic_complete` → `completed` \| `ai_failed` |
| candidate_count | integer | Total candidates scored |
| completed_count | integer | Candidates with AI scores |
| created_at | timestamptz | |
| completed_at | timestamptz nullable | Set when terminal status reached |

### `candidate_evaluations`

One row per candidate per evaluation run.

| Column | Type | Notes |
|---|---|---|
| id | integer PK | |
| evaluation_run_id | integer FK | |
| candidate_id | integer FK | |
| heuristic_score | float | 0–100, always set |
| ai_score | float nullable | Set after AI evaluation |
| final_score | float | = heuristic initially; blended after AI |
| technical_match | float | Sub-score for breakdown bar |
| activity_signal | float | Sub-score for breakdown bar |
| profile_completeness_score | float | Sub-score for breakdown bar |
| summary | text nullable | Human-readable summary |
| evidence_json | text | JSON array — heuristic breakdown bar data |
| strengths_json | text | JSON array — heuristic evidence / AI strengths |
| concerns_json | text | JSON array — heuristic / AI concerns |
| status | varchar(50) | `heuristic` \| `completed` \| `failed` |

---

## Configuration reference

All backend configuration is loaded by pydantic-settings from `backend/.env`. Unknown keys are silently ignored (`extra="ignore"`).

| Variable | Required | Default | Description |
|---|---|---|---|
| `DATABASE_URL` | Yes | — | PostgreSQL connection string |
| `GITHUB_TOKEN` | Yes | — | GitHub PAT for API access |
| `OPENAI_API_KEY` | No | `""` | OpenAI key; AI evaluation skipped when blank |
| `FRONTEND_ORIGIN` | No | `http://localhost:5173` | Allowed CORS origin |
| `SECRET_KEY` | No | `change-me-in-production` | Future JWT signing key |
| `GOOGLE_CLIENT_ID` | No | `""` | Future OAuth |
| `GOOGLE_CLIENT_SECRET` | No | `""` | Future OAuth |

The frontend reads one optional variable from `frontend/.env`:

| Variable | Default | Description |
|---|---|---|
| `VITE_API_BASE` | (Vite proxy) | Backend base URL — only needed outside dev |
