# Architecture

Phase-1-complete reference for the job-agent build.

## Overview

The system is a **pipeline of nine specialized agents** coordinated by a single orchestrator, running against a **modular source registry** and a **profile that is the single source of truth** for every truthfulness check. Every stage can fail independently; the orchestrator captures per-agent errors and continues.

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        JobAgentOrchestrator                              │
│                                                                          │
│  Discovery → Extraction → Matching → Research → Application              │
│     ↓          ↓            ↓          ↓            ↓                    │
│  sources   dedupe       scorer      notes       preparer                 │
│  (mock,    (normalize + hard rules   priority   (resume variant,         │
│   LinkedIn fuzzy sig + scam          company,   cover letter,            │
│   Naukri   clusters)   detector)     caution)   form answers)            │
│   Phase 2)                                           ↓                   │
│                                                 Communication            │
│                                                 (email drafts,           │
│                                                  recruiter msgs)         │
│                                                      ↓                   │
│                                                   Follow-up              │
│                                                   (Day 5, Day 10)        │
│                                                      ↓                   │
│                                                  Compliance              │
│                                                  (bypass checks,         │
│                                                   approval invariants)   │
│                                                      ↓                   │
│                                                   Quality                │
│                                                   (truthfulness,         │
│                                                    forbidden claims)     │
└─────────────────────────────────────────────────────────────────────────┘
```

## Modules

### `app.profile`
The user's `Profile` pydantic model (experiences, projects, skills, education, availability, locations, tiered target roles, hard-pass terms, priority companies, resume variants). `profile.data.build_default_profile()` returns Harshaksh's real resume; `get_profile()` is the memoized access point. `Profile.to_fact_list()` yields `Fact(key, value, source=PROFILE_FACT, confidence=1.0)` records consumed by the truthfulness engine.

### `app.schemas`
Pydantic v2 schemas for jobs, companies, applications, and all enums. `Job.from_create(JobCreate)` derives a canonical `job_id` from `(company, title, location, source_job_id)` SHA-1. Status transitions are enforced by `is_valid_transition()` against a static `ALLOWED_STATUS_TRANSITIONS` dict (the application FSM).

### `app.database`
SQLAlchemy 2.0 declarative Base with 10 tables and `init_database()` + `session_scope()`. Default SQLite with a model validator that auto-resolves relative paths against repo-root. Swap `DATABASE_URL` to a Postgres URL for production — no code change required.

### `app.config`
`Settings` (pydantic-settings) is the central configuration. `ScoringWeights` and `ScoringThresholds` are nested models with `WEIGHT_*` / `SCORE_*` env prefixes. `get_settings()` is memoized and auto-creates the `data/`, `cache/`, `logs/`, `resumes/`, `resumes_generated/` directories.

### `app.discovery`
`BaseSource` is the discovery adapter interface. `MockSource` returns the 50+ synthetic jobs. `SourceRegistry` is populated at startup from feature flags — every non-mock source is a Phase-2 stub today that returns an informative error when enabled. New sources need only subclass `BaseSource` and implement `discover(SourceContext) -> SourceResult`.

### `app.matching`
`MatchingEngine.score(job, profile) -> (ScoreBreakdown, reasons, missing)` computes 8 sub-scores:

1. **Technical skills** — canonicalized against `_SKILL_SYNONYMS`, matched against job tokens + required/preferred fields.
2. **Experience** — detects `(\d+)\+?\s*years?` requirements against `profile.total_experience_months()` (span from earliest start to today).
3. **Role relevance** — tier-1 (AI/ML/LLM) 1.0, tier-2 (SWE/Backend/Data) 0.75, tier-3 (eval/training) 0.55, fallback 0.1.
4. **Location** — Gurugram 1.0, Noida/NCR 0.85/0.75, Remote India 1.0, Remote Global (unverified) 0.6.
5. **Employment type** — part-time 1.0, contract/freelance 0.9, temporary 0.7, full-time 0.5, internship 0.1.
6. **Schedule** — evening/night/flexible/async 1.0, weekend 0.95, day 0.4.
7. **Company priority** — hit on `profile.priority_companies` → 1.0 else 0.5.
8. **Salary** — currency-aware (INR monthly/yearly, USD hourly/yearly).

Each sub-score is multiplied by its configurable weight (sum ≈ 1.0) and scaled to 100. **If `role_score < 0.3`, the entire breakdown is dampened by `(0.5 + role_score)`** so that unrelated roles can't accumulate score from coincidental schedule / location hits.

The thresholds (`APPLY_IMMEDIATELY=95`, `HIGH_PRIORITY=85`, `APPLY=75`, `CONSIDER=65`, `LOW_PRIORITY=50`) map total → `PriorityTier` enum.

### `app.dedup`
Two-step deduplication:
1. **Strict signature** — normalized `(company, title_tokens_sorted, location, canonical_url)` + exact `(source, source_job_id)` match.
2. **Fuzzy similarity** — `difflib.SequenceMatcher` on normalized titles + token-overlap on noise-stripped locations. Title ≥ 0.9 is enough; 0.7-0.9 requires a shared non-noise location token (e.g. both mention "gurugram" or both "noida").

Clusters pick a canonical job by (longest description, has application URL, has salary) and mark the rest as `is_duplicate=True`.

### `app.scam`
Pattern-based detector with 12 red flags + heuristics: upfront payment, crypto wallet requests, WhatsApp / Telegram-only recruitment, MLM language, unrealistic salary, gift-card payment, personal bank-detail demands, data-entry traps, no identifiable company, free-email-domain-vs-company mismatch, suspicious TLDs (`.tk`, `.ml`, `.gq`, `.xyz`, `.top`, …), too-good-to-be-true claims. Each flag has a weight; total → `ScamRisk.NONE / LOW / MEDIUM / HIGH`.

### `app.filtering.hard_rules`
Hard rejections (never auto-recovered): unrelated role (nurse, driver, sales, …), hard-pass term (MLM, pay-to-apply, …), senior/executive role with profile below the 60-month floor, 10+ years requirement with insufficient profile experience, HIGH scam risk, duplicate-of-applied, no identifiable company, internship, excluded company.

### `app.applications`
- `FormFieldMapper.map(job, profile) -> list[FormAnswer]` — the 22 standard application fields (name, email, phone, linkedin, github, portfolio, resume, cover letter, work authorization, current role, years of experience, education, skills, expected salary, notice period, earliest start, employment type, hours per week, timezone, …). Every answer carries a `source_tag` (`PROFILE_FACT`, `DERIVED_FACT`, `USER_PROVIDED_FACT`, `USER_INPUT_REQUIRED`, `UNKNOWN`). Sensitive questions (salary, notice period, work auth) default to `USER_INPUT_REQUIRED` rather than guess.
- `ApplicationPreparer.prepare(job, profile)` — ties resume-engine selection, cover-letter generation, and form-field mapping into one `Application` row, status = `MATCHED` in dry-run or `APPLICATION_PREPARED` otherwise, with `REVIEW_REQUIRED` added if the compliance flag is on.
- `ApplicationTracker.transition(application, new_status)` — strict FSM; raises `InvalidStatusTransition` on illegal moves.

### `app.resumes.engine`
`ResumeEngine.choose_variant(job, profile)` scores each `ResumeVariant` by role-overlap + highlighted-skill overlap + employment-type bias (part-time ⇒ part_time_remote; evaluation ⇒ ai_evaluation; software/backend ⇒ software_engineer; everything else ⇒ ai_ml).

### `app.cover_letters.generator`
Deterministic generator (no LLM call in Phase 1). Uses only profile facts: Ethara AI bullet, independent-contractor platforms (Project Dynamo / Multi-SWE-bench / Harbor / Turing / Outlier), one project, and a line listing shared skills between the job and profile. Returns a plain-text letter signed with `profile.email · profile.phone`. The quality agent later greps for forbidden claims (10+ years, PhD, Principal Engineer, US Citizen, Green Card, …).

### `app.llm`
`LLMProvider` abstract interface with `analyze_job`, `score_job`, `generate_cover_letter`, `generate_email`, `answer_application_question`, `detect_scam`, `deduplicate_jobs`, `generate_resume_rationale`. `MockLLMProvider` delegates to the deterministic modules so the full pipeline runs with zero external calls. `get_llm_provider()` returns Mock when `LLM_PROVIDER=mock` or `MOCK_MODE=true`; the OpenAI / Anthropic / Gemini providers are Phase-2 stubs that fall back to Mock on import error.

### `app.agents`
Each agent subclasses `BaseAgent` and implements `run(context, previous_results) -> AgentResult`. The `AgentResult` carries `jobs`, `rejected_jobs`, `notes`, `errors`, and a free-form `metadata` dict. The orchestrator preserves per-agent exceptions and continues.

### `app.analytics`
`build_dashboard_snapshot(result)` aggregates the orchestrator output into counts by location, by employment type, by priority tier, by source, plus the application funnel. `build_daily_report(result)` renders the exact format specified in section 46 of the brief.

### `app.cli`
`run_cli(args)` — the interactive CLI. Supports `--discover` / `--dashboard` / `--daily-report` / `--non-interactive` for scripted runs, and an interactive menu matching section 52 of the brief.

## Pipeline invariants

- **Dry-run mode (default) never submits anything.** `AUTO_SUBMIT=false` is enforced by `ApplicationAgent` (status stays `MATCHED` / `REVIEW_REQUIRED`) and by `ComplianceAgent` (which treats the flag as a hard violation if raised without approval).
- **Status transitions are strict.** `ApplicationTracker.transition()` raises on any disallowed FSM move. See `ALLOWED_STATUS_TRANSITIONS` in `app/schemas/enums.py`.
- **Every form answer is tagged with a source.** `UNKNOWN` is never emitted silently; it is routed to `pending_user_inputs` for the CLI to surface.
- **Truthfulness is enforced after generation.** `QualityAgent` greps every generated cover letter for forbidden claims, and flags any form answer tagged `UNKNOWN` that carries a non-empty value.
- **Compliance stops the pipeline when a bypass flag is set.** `ComplianceAgent` writes a violation list to `result.get("compliance").metadata["compliance_violations"]`; the CLI dashboard renders them in a red panel.

## Extension points

| What | Where | How |
|---|---|---|
| New discovery source | `app/discovery/sources/your_source.py` | subclass `BaseSource`, register with a feature flag in `Settings` and in `app/discovery/registry.py` |
| New scoring dimension | `app/matching/scorer.py` | add `_score_*` method, extend `ScoreBreakdown` and `ScoringWeights`, update the normalized() sum |
| New scam pattern | `app/scam/detector.py` | append to `_RED_FLAGS` with a weight; a weight ≥ 50 triggers `ScamRisk.HIGH` on its own |
| New hard rule | `app/filtering/hard_rules.py` | add a check and append to `reasons`; any non-empty reasons list rejects the job |
| New resume variant | `app/profile/data.py` | append to `resume_variants`; `ResumeEngine` picks it up automatically |
| New agent | `app/agents/your_agent.py` | subclass `BaseAgent`, add to the default `JobAgentOrchestrator.__init__` list |
| New LLM backend | `app/llm/your_provider.py` | subclass `LLMProvider`, register in `app/llm/factory.py` |

## Data flow

1. **Discovery** reads from each enabled source (today: `MockSource` only) → `list[Job]`.
2. **Extraction** runs the `Deduplicator` across the full set; folds duplicates into clusters, picks a canonical job per cluster, marks the rest `is_duplicate=True`. Only canonical jobs flow downstream.
3. **Matching** runs `ScamDetector` + `MatchingEngine` + `apply_hard_rules` on each canonical job. Rejected jobs land in `AgentResult.rejected_jobs`; kept jobs are sorted by `match_score` desc.
4. **Research** attaches lightweight notes (priority company flag, scam caution, match score, tier) to each kept job — in Phase 2 this becomes real company research via Librarian-style queries.
5. **Application** picks top-N jobs (default 25) with `match_score >= 75`, selects a resume variant, generates a cover letter, maps form fields, and emits `Application` rows with `status=REVIEW_REQUIRED` when `USER_APPROVAL_REQUIRED=true`.
6. **Communication** drafts an email per job with `application_email` set, and a LinkedIn-style recruiter message per application. Draft-only.
7. **Follow-up** schedules Day-5 and Day-10 reminders per non-terminal application.
8. **Compliance** verifies all bypass flags are off and all pending applications are user-approved before any submission could happen.
9. **Quality** greps generated text for forbidden claims and inspects form answers for mis-tagged values.

## Testing strategy

- Unit tests per module (profile, matching, dedup, scam, hard rules, DB schema).
- Integration test of the orchestrator (`tests/test_orchestrator.py`).
- Acceptance test suite (`tests/test_acceptance.py`) that executes the 22 numbered demonstrations from section 59 of the brief, plus the daily-report format.
- All tests run in <2 seconds (no external calls, no network, in-memory SQLite).

## What's not in Phase 1 (by design)

- Real discovery sources (Phase 2).
- Playwright browser automation (Phase 3).
- Real LLM calls for cover letter / application answers (Phase 4).
- Gmail/Microsoft OAuth email send (Phase 5).
- APScheduler / notifications / weekly analytics / Next.js dashboard (Phase 6).

Every one of those has either (a) a stub in the appropriate module or (b) a feature flag in `Settings` + a Phase-2+ error in the matching source — so turning them on is additive, never destructive.
