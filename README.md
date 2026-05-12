# Recruiter Signal

A recruiting intelligence tool that seeds real GitHub developer profiles into a PostgreSQL database, scores every candidate against a free-text job description using an explainable heuristic model, re-scores the top 25 with GPT-4o-mini, and surfaces ranked results in a live React dashboard.

---

## What it does

Paste a job description into the sidebar. The system:

1. **Scores every candidate instantly** using a four-component heuristic model (zero latency, fully explainable).
2. **Fires GPT-4o-mini against the top 25** in parallel batches — all 5 API calls run concurrently so AI results land in ~15s.
3. **Re-ranks in real time** — the frontend polls every 3s and updates scores and summaries as they arrive.
4. **Per-candidate breakdowns** — a four-bar score chart, plain-English AI summary, strengths, and concerns.
5. **On-demand Gemini summarization** — candidates outside the top 25 can be individually summarized via a button that calls Gemini 2.5 Flash.
6. **Shortlisting** — bookmark any candidate; data is cached to `localStorage` at the moment of bookmarking so the Shortlisted tab loads instantly with no extra API call.

In browse mode (no job description), the full candidate pool is filterable by name, language, location, follower range, repo count, and profile completeness.

---

## Architecture

```
Browser (React 18 + Vite + Tailwind)
├── Browse tab     — filterable candidate list
├── Shortlist tab  — bookmarked candidates (localStorage cache)
└── Detail panel   — score breakdown, AI summary, repos, languages

FastAPI backend
├── /candidates        — list + detail
├── /jobs              — create job from description
├── /evaluation-runs   — trigger heuristic + AI scoring
└── /candidate-evaluations/:id/ai-summarize  — on-demand Gemini

PostgreSQL (SQLAlchemy, create_all on startup)
```

**Deployment:** Frontend as a Render static site, backend as a Render web service, Render-managed PostgreSQL.

---

## Architecture decisions

**Heuristic-first, AI-second.** Every candidate gets a heuristic score immediately on request. The AI pass only re-scores the top 25 — this keeps response time fast and cost low while ensuring the candidates worth evaluating deeply get the full treatment.

**Parallel AI batches.** GPT-4o-mini is called in 5 concurrent batches of 5 using `ThreadPoolExecutor`. The batch HTTP calls are pure I/O with no shared DB state, making parallelism safe and cutting wall time from ~75s to ~15s.

**Score blending.** `final_score = ai_score × 0.7 + heuristic_score × 0.3`. The AI score dominates but the heuristic acts as a prior, preventing the model from wildly re-ranking candidates with thin profiles.

**localStorage shortlisting.** Rather than building a full auth + server-side shortlist system, candidate data is cached to `localStorage` at bookmark time. The shortlist tab renders instantly from that cache. The tradeoff is no cross-device sync, but for a single-user tool this is the right call.

**No migrations (yet).** `Base.metadata.create_all()` on startup is sufficient for a project where the schema is still evolving. This becomes a liability the moment there is live data that cannot be wiped.

---

## Scoring system

| Component | Weight | Signal |
|---|---|---|
| Technical match | 50 pts | Language overlap between JD keywords and candidate's top languages |
| Activity signal | 25 pts | Recent pushes, commit frequency, account age |
| Profile completeness | 15 pts | Bio, company, location, avatar present |
| Repo quality | 10 pts | Stars and forks on top repositories |

All four components are returned as a breakdown with raw score and max, rendered as bars in the detail panel.

---

## AI evaluation pipeline

1. **Heuristic pass** — all candidates scored synchronously, results persisted, response returned to frontend.
2. **Background task** — FastAPI `BackgroundTasks` fires `run_ai_evaluation` after the HTTP response is sent.
3. **Profile serialisation** — each candidate's top 5 languages and top 5 repos are serialised to a compact JSON dict (bio truncated to 150 chars, null fields omitted) to minimize prompt tokens.
4. **Parallel batches** — candidates ranked 1–25 by heuristic score are split into 5 batches of 5. All 5 `gpt-4o-mini` calls fire simultaneously via `ThreadPoolExecutor`. The DB session is never touched inside threads — only the HTTP calls run in parallel.
5. **Score blending** — AI score blended with heuristic at 70/30.
6. **On-demand Gemini** — candidates outside the top 25 show a "Summarize with Gemini" button. This calls `gemini-2.5-flash` synchronously with retry logic for 5xx errors.

---

## Data model

```
candidates
  id, github_username, name, avatar_url, profile_url
  bio, location, company, followers, following, public_repos
  profile_completeness (low | medium | high)

candidate_languages
  candidate_id → candidates, language, repo_count

candidate_repositories
  candidate_id → candidates, name, description, language
  stars, forks, url, pushed_at

jobs
  id, title, description, created_at

evaluation_runs
  id, job_id → jobs, status, candidate_count, completed_count
  created_at, completed_at

candidate_evaluations
  id, evaluation_run_id → evaluation_runs, candidate_id → candidates
  heuristic_score, ai_score, final_score
  technical_match, activity_signal, profile_completeness_score
  summary, evidence_json, strengths_json, concerns_json
  status (heuristic | completed | ai_failed)

-- Modelled but not currently active:
users, guest_sessions, shortlists, shortlist_candidates
```

---

## What I'd improve with more time

**Incremental AI commits.** All 5 parallel batches currently commit in a single write after all futures resolve. The frontend polls for progress but `completed_count` stays at 0 until everything finishes. Committing after each batch resolves would make the progress counter actually move.

**Alembic migrations.** `create_all` is fine during development but unsafe on a live database. Now that there is deployed data, schema changes need proper migrations.

**Server-side shortlisting.** The `users`, `shortlists`, and `shortlist_candidates` tables are already modelled in the DB. Wiring these up with a lightweight session token would give cross-device persistence and let shortlists survive a browser clear.

**Evaluation run deduplication.** Every run creates `candidate_evaluations` for every candidate in the pool. As the pool grows this becomes expensive. A smarter strategy would cache heuristic scores per candidate per job and only re-run when the job description changes significantly.

**Smarter seeding.** The current seed script pulls GitHub profiles by keyword search. Signal quality would improve by targeting contributors to specific open-source repositories relevant to the role being hired for.
