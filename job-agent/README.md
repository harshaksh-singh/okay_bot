# Portolan

**Autonomous Opportunity Intelligence Platform** — AI career operating system + B2B client intelligence pipeline for Harshaksh Singh.

Named after medieval portolan nautical charts (12th-16th c.), which guided sailors through complex coastlines by **verified bearings and landmarks, not guesses**. Same principle: every opportunity in the pipeline is sourced from a verified ATS or official API, every answer grounded in profile facts, every submission paused at `READY_TO_SUBMIT` for human review.

```bash
make run    # Preflight -> Discover -> Prepare -> Dry-run -> Status
```

Dual pipelines (JOB + B2B/Harban) share one orchestrator, one database, one audit trail. Human controls the final submit click, always. Zero credentials stored anywhere; CAPTCHA/MFA/OTP bypasses hard-blocked.

---

## Previous description (preserved below)

Personal **AI career operating system** for Harshaksh Singh.

Discovers → understands → filters → matches → ranks → researches → prepares → asks you → applies → tracks → follows up → learns.

This is **not** a scraper, demo, or Selenium script. It is a modular, test-covered, phased build that defaults to **safe, dry-run, human-in-the-loop** operation.

---

## What it does today

**Mock-first personal career OS**: full 10-agent pipeline runs end-to-end against a 50+ item mock corpus, persists everything to SQLite, writes recruiter-message drafts and `.eml` email drafts for jobs that explicitly request email application, enforces strict safety invariants, and surfaces a Rich CLI dashboard with per-application approval. Phased build is **Phase 1 complete, Phase 2–4 scaffolded with real adapters, Phase 5a/6a done, Phase 5b/6b honestly deferred**.

- Loads your real resume facts (**Ethara AI**, Handshake AI Project Dynamo, Multi-SWE-bench, Harbor Benchmark, Turing, Outlier AI; B.Tech CSE AI at NIET Greater Noida) as the single source of truth for every output.
- Ingests a **mock source** of 50+ diverse jobs covering AI/ML/SWE/evaluation roles across Gurugram / Noida / Delhi NCR / India Remote / Global Remote, part-time + contract + freelance + full-time, with deliberate duplicates, scams, and unrelated-role noise.
- Runs a 10-agent pipeline (Compliance → Discovery → Extraction → Matching → Research → Application → Communication → Follow-up → Quality → Persistence) with Compliance as a hard-blocking first gate.
- Scores every job on 8 configurable dimensions (skills, experience, role, location, employment, schedule, company priority, salary) and assigns a priority tier.
- Deduplicates across sources via normalized company/title/location + canonical URL + source IDs.
- Detects 12+ scam patterns (upfront fees, crypto payments, WhatsApp-only recruiters, free-email mismatches, suspicious TLDs, MLM, data-entry traps, …).
- Rejects via hard rules (unrelated roles, senior/VP positions beyond profile, internships, scam-high, excluded companies).
- Prepares applications with a tailored resume variant, truthful cover letter, and a form-field map tagged `PROFILE_FACT` / `JOB_FACT` / `DERIVED_FACT` / `USER_INPUT_REQUIRED` / `UNKNOWN`.
- Drafts recruiter LinkedIn messages and application emails (DRAFT ONLY — never auto-sent).
- Schedules Day-5 / Day-10 follow-ups per application.
- Enforces compliance invariants (CAPTCHA / MFA / rate-limit bypass flags are rejected, AUTO_SUBMIT without approval is flagged).
- Interactive CLI dashboard (Rich) matching the first-run spec from the brief.
- SQLAlchemy 2.0 schema for 10 tables (companies, jobs, applications, contacts, messages, emails, followups, interviews, search_runs, audit_logs, errors) — initialized to SQLite by default; a `DATABASE_URL` can point at Postgres.
- **193 tests pass** at 85% backend coverage, including the 23-step acceptance test from the brief (expanded post-Oracle-review for FSM invariants, DB persistence, LLM factory fallback, discovery registry, Google CSE + Hacker News adapters, and the FastAPI read-only API).
- **Full persistence**: `PersistenceAgent` writes `JobRow`, `ApplicationRow`, `SearchRunRow`, `MessageRow`, `FollowupRow`, `AuditLogRow` to SQLite every pipeline run. Verified end-to-end: a fresh `make discover` populates 52 jobs, 10 applications, 10 recruiter messages, 20 follow-ups, 1 search_run, 1 audit entry.
- **Compliance is a HARD BLOCK, not a warning**: `ComplianceAgent` runs *first* in the pipeline and raises `ComplianceViolation` when `CAPTCHA_BYPASS`, `MFA_BYPASS`, `RATE_LIMIT_BYPASS` is set, or when `AUTO_SUBMIT=true` is combined with `USER_APPROVAL_REQUIRED=false`. The orchestrator halts and marks every downstream agent `skipped`. Verified by 8 compliance tests.
- **Strict matching-weight normalization**: raw `WEIGHT_*` env vars no longer leak; weights are normalized to sum = 1.0 inside `MatchingEngine`, keeping all scores bounded in `[0, 100]`. Verified by test with all-ones (previously would have scored 626).
- **Email drafts are actually written to disk**: `CommunicationAgent` instantiates `EmailDrafter` and writes RFC 5322 `.eml` files to `data/email_drafts/` for every job with an explicit `application_email`. Verified by inspecting `.eml` content.
- **37 real company careers sources** wired via public ATS APIs: Greenhouse (OpenAI, Anthropic, Perplexity, Hugging Face, Scale AI, Databricks, Cohere, Groq, Cursor, Together AI, Fireworks AI, Replicate, ElevenLabs, LangChain, W&B, OpenRouter, Notion, Stripe, Glean, Sarvam AI, Handshake, …), Lever (Mistral, NVIDIA, Palantir, Ramp, Stability, Zoox), Ashby (Cursor, Fireworks, Replit, Scale, Glean, ElevenLabs, Runway).
- **Public remote boards**: RemoteOK JSON API + WeWorkRemotely RSS.
- **HTTP client** with per-domain rate limiting, exponential-backoff retries, robots.txt caching, automatic User-Agent, and secret redaction in error logs.
- **Observability**: structlog-based structured logs with aggressive secret redaction (OpenAI/Anthropic/Google keys, Bearer tokens, cookies, passwords, OTPs).
- **Real LLM providers** (OpenAI / Anthropic / Gemini) with graceful fallback to the deterministic MockProvider when a dependency or API key is missing.
- **Email draft writer** that produces RFC 5322 `.eml` files under `data/email_drafts/` (DRAFT_ONLY by default; OAuth send-stage is Phase 5b).
- **APScheduler-based scheduler** with morning (09:00) / evening (18:00) / night (22:00) IST cron triggers that run the full pipeline and write daily reports to `data/reports/`.
- **Assisted application mode** that opens the official job URL in the user's default browser or Playwright-controlled persistent profile at `./browser/` — the bot never auto-submits.

---

## Architecture

```
job-agent/
├── backend/
│   ├── app/
│   │   ├── agents/            # Discovery, Extraction, Matching, Research,
│   │   │                      # Application, Communication, Followup,
│   │   │                      # Compliance, Quality, Orchestrator
│   │   ├── analytics/         # Dashboard snapshot, daily report, weekly analytics
│   │   ├── applications/      # Preparer, Form field mapper, Tracker (status FSM)
│   │   ├── cli/               # Rich interactive CLI
│   │   ├── config/            # Pydantic Settings + scoring weights/thresholds
│   │   ├── cover_letters/     # Truthful, deterministic cover-letter generator
│   │   ├── data/              # Priority companies + 50+ mock jobs
│   │   ├── database/          # SQLAlchemy 2.0 Base, engine, session_scope, models
│   │   ├── dedup/             # Normalized-signature + similarity clustering
│   │   ├── discovery/         # BaseSource / registry / MockSource / Phase-2 stubs
│   │   ├── filtering/         # Hard rejection rules
│   │   ├── llm/               # LLMProvider interface + MockLLMProvider + factory
│   │   ├── matching/          # 8-dimension scoring engine
│   │   ├── profile/           # Pydantic Profile + real Harshaksh data
│   │   ├── resumes/           # Variant selection engine
│   │   ├── scam/              # Pattern-based scam detector
│   │   ├── schemas/           # Pydantic Job / Company / Application / enums + FSM
│   │   └── __main__.py        # python -m app entrypoint
│   ├── tests/                 # 193 unit + integration + acceptance tests (85% coverage)
│   ├── requirements.txt
│   └── pyproject.toml
├── data/                      # SQLite DB, cache, logs, generated resumes
├── resumes/                   # Your resume PDFs (drop in here)
├── docs/
│   └── ARCHITECTURE.md
├── frontend/                  # Reserved for Phase 2+ (Next.js)
├── scripts/
├── .env.example               # Safe defaults
├── Makefile                   # make dry-run, test, acceptance, dashboard, ...
└── README.md
```

See `docs/ARCHITECTURE.md` for data-flow and extension points.

---

## Install & run

```bash
# From repo root
make setup           # creates .venv, installs backend/requirements.txt
cp .env.example .env # safe defaults — do NOT add passwords, see "Security"
make dry-run         # launches interactive CLI
```

Non-interactive variants:

```bash
make discover        # runs the pipeline and prints top matches + dashboard
make dashboard       # runs the pipeline and prints just the dashboard
make acceptance      # runs the 23-step acceptance test from the brief
make test            # runs all 193 tests
make test-cov        # with coverage report
```

The first-run CLI banner matches section 52 of the brief exactly:

```
======================================================
AI JOB APPLICATION ASSISTANT
======================================================

Profile:         Harshaksh Singh
Target:          AI / ML / Software Engineering
Locations:       Gurugram / Noida / Delhi NCR / India Remote / Global Remote
Employment:      Part-time / Contract / Remote / Full-time
Mode:            DRY RUN / MOCK
Auto Submit:     OFF
Auto Email:      OFF
User Approval:   ON
======================================================

[1] Discover Jobs
[2] Analyze Jobs
[3] Review Matches
[4] Prepare Applications
...
```

---

## Environment variables (.env)

All variables are optional — safe defaults ship in `.env.example`. Key flags:

| Variable | Default | Notes |
|---|---|---|
| `MOCK_MODE` | `true` | Uses deterministic mock LLM and mock source only |
| `DRY_RUN` | `true` | Pipeline can prepare but never submits/sends |
| `AUTO_SUBMIT` | `false` | **MUST remain false unless each application was approved** |
| `AUTO_EMAIL` | `false` | Email drafts never auto-send |
| `USER_APPROVAL_REQUIRED` | `true` | Mandatory human-in-the-loop before any submission |
| `CAPTCHA_BYPASS`, `MFA_BYPASS`, `RATE_LIMIT_BYPASS` | `false` | **Forbidden; the compliance agent will reject these if ever flipped** |
| `DATABASE_URL` | `sqlite:///./data/job_agent.db` | Set to Postgres URL for production |
| `LLM_PROVIDER` | `mock` | `openai` / `anthropic` / `gemini` enabled in later phases |
| `*_ENABLED` for discovery sources | all `false` | Enabled per source in Phase 2 |
| Scoring thresholds `SCORE_APPLY_IMMEDIATELY=95`, `SCORE_HIGH_PRIORITY=85`, etc. | tunable | see section 9 of the brief |
| Matching weights `WEIGHT_TECHNICAL_SKILLS=0.30`, … | tunable, sum ≈ 1.0 | see section 9 of the brief |

---

## Security & platform compliance

**I will never ask for or store a raw password.** This is a hard rule, documented in `app/agents/compliance_agent.py` and enforced by the test suite.

- **Job platforms (LinkedIn, Naukri, Indeed, Glassdoor, Wellfound, Handshake AI, Outlier, …):** when enabled in Phase 2, discovery uses **persistent Playwright profile at `./browser/`**. You log in **yourself** in the real browser window; the OS-managed browser store holds your session cookies. No credentials are typed, parsed, or stored by this code. To "log out", delete `./browser/`.
- **Email (Gmail / Microsoft 365, Phase 5):** OAuth 2.0 via the official provider login page. Refresh tokens live in your macOS Keychain via `keyring`. Never in `.env`, never in DB.
- **LLM API keys** go in `.env` or Keychain; log output is redacted for anything matching token/cookie/password/bearer patterns.
- **CAPTCHA / MFA / anti-bot:** the system **stops and asks you** rather than attempting to bypass. The compliance agent errors out if the corresponding `*_BYPASS` flags are ever set to `true`.
- **ToS respect:** discovery only reads public pages (robots.txt-aware adapters in Phase 2); scraping of logged-in LinkedIn is explicitly disallowed.

See `app/scam/detector.py` for the twelve scam patterns the system refuses to apply to.

---

## Phased roadmap

| Phase | Scope | Status |
|---|---|---|
| **1** | Architecture, profile, DB schema, Job pydantic, mock source, matching, dedup, scam detection, hard rules, 10-agent orchestrator, CLI dashboard, tests | ✅ done |
| **2** | Real discovery via Greenhouse / Lever / Ashby ATS adapters (37 companies), RemoteOK JSON, WeWorkRemotely RSS, hardened HTTP client with retry / robots.txt / rate limiting / secret redaction, structlog observability | ✅ done |
| **3** | Assisted application mode: Playwright persistent profile at `./browser/` + default-browser fallback; screenshots to `data/screenshots/`; CAPTCHA/MFA stop points by design — never auto-submit | ✅ done (scaffold; install `playwright` + `playwright install chromium` to activate) |
| **4** | Real OpenAI / Anthropic / Gemini LLM providers for cover-letter and application-answer generation with graceful fallback to Mock; truthfulness quality agent greps all generated text | ✅ done |
| **5** | **5a: `.eml` draft writer** to `data/email_drafts/` (done). **5b: OAuth send** (pending — flip `EMAIL_ENABLED=true` + `EMAIL_DRAFT_ONLY=false` once Google OAuth client is configured). | 5a ✅ / 5b pending |
| **6** | **6a: APScheduler** (morning/evening/night IST, daily reports to `data/reports/`) ✅. **6b: FastAPI read-only backend** on `/health /jobs /jobs/:id /applications /applications/:id /companies /messages /emails /followups /search-runs /audit-logs /dashboard` ✅ (`make api`). **Next.js frontend** deferred — the API makes it a straightforward integration. | 6a ✅ / 6b API ✅, frontend pending |
| **3-exec** | **Pre-approved application execution + HARBAN AI LABS client pipeline**: `SubmissionAgent` + `ApprovedSubmitter` with `ApplicationEligibilityChecker` (AUTO_APPLY / REVIEW_REQUIRED / REJECT tiering) and `HardStopDetector` (CAPTCHA / MFA / OTP / identity / payment / sensitive-question → `APPLICATION_BLOCKED_USER_ACTION`); `HarbanAgent` + `HarbanClientScorer` + `DualOpportunityClassifier` (JOB / CLIENT / BOTH / NEITHER); `HarbanOutreachGenerator` with mandatory company-signal personalization + `OutreachLimiter` (configurable daily caps); 8 Harban tables (ClientCompany, ClientContact, ClientLead, ClientInteraction, ClientProposal, ClientOpportunity, ClientFollowup, SubmissionEvidence); 5 new API endpoints under `/harban/*` + `/submission-evidence`; new CLI: `make daily-growth`, `make apply-approved`, `make client-discovery`, `make client-outreach-dry-run`. **Default-safe**: `PRE_APPROVED_APPLICATIONS=false`, `AUTO_SUBMIT_APPROVED=false`, `AUTO_EMAIL_APPROVED=false` — user must explicitly flip to activate. Harban services ship as `DISCUSSION`/`PLANNED` (never claimed as `DELIVERED` — enforced by test). | ✅ done |

**LinkedIn / Naukri / Indeed / Glassdoor** stay in "Discovery + User-Assisted Application" mode by design: logged-in scraping violates their ToS and risks the user's account. The persistent Playwright profile pattern (user signs in themselves in the real browser window) is the only compliant path — stubs are in place; implementation activates when the user explicitly logs in via `make browser-login` (coming in Phase 5b alongside the email OAuth polish).

## Honest limitations (what you should know before relying on this)

Oracle re-reviewed this build and flagged items that remain **genuinely limited**, not deferred-but-equivalent:

- **Real-source live reliability is partial.** Of the 37 claimed company careers tokens, some will 404 (companies change ATS or use private boards). The adapter handles 404 gracefully (per-source `errors` list, never crashes the pipeline) but you should expect a non-trivial fraction to return 0 jobs on any given run. Treat the ATS list as a seed set to prune, not a guaranteed working corpus.
- **RemoteOK / WeWorkRemotely compete with `robots.txt`.** Our HTTP client respects robots.txt by default; some of these feeds may disallow automated access from a non-approved User-Agent. If you want to use them, inspect their current `robots.txt` and consider configuring the client appropriately.
- **Google Programmable Search is wired, Bing is not.** `GoogleProgrammableSearchSource` (official Google CSE JSON API) covers the brief's `site:X AI engineer` discovery pattern when you set `GOOGLE_CSE_API_KEY`, `GOOGLE_CSE_ENGINE_ID`, and `GOOGLE_SEARCH_ENABLED=true`. Bing Search integration is not implemented (the ATS adapters + Google CSE + Hacker News cover the same ground).
- **Assisted-application mode is scope-limited by design.** Opens the job page in the user's default browser (or Playwright persistent profile if installed via `pip install playwright && playwright install chromium`), captures a screenshot, and surfaces the generated cover letter + form answers for the user to copy/paste. It does **not** auto-fill form fields on the job page — that would re-enter ToS-sensitive territory on sites like LinkedIn / Naukri. The brief's §60 "Assisted Application Mode" definition (bot finds job, opens page, prepares answers, highlights fields, waits for user, user submits manually) is what this layer implements. Deeper automated form-filling against public ATS pages is a planned future extension.
- **FastAPI backend is implemented, Next.js frontend is deferred.** The read-only FastAPI API at `backend/app/api/server.py` (start with `make api`) exposes `/health`, `/jobs`, `/jobs/{id}`, `/applications`, `/applications/{id}`, `/companies`, `/messages`, `/emails`, `/followups`, `/search-runs`, `/audit-logs`, `/dashboard`. There are no write endpoints by design — human-in-the-loop runs through the CLI. The Next.js frontend from the spec's recommended web stack is deferred; the API makes it a straightforward integration.
- **No Gmail / Microsoft Graph OAuth send transport.** Phase 5a writes `.eml` drafts to `data/email_drafts/`; Phase 5b (OAuth client registration + refresh-token storage in Keychain + actual send) is not implemented. Flip `EMAIL_ENABLED=true` only after you implement 5b against a Google OAuth client you own.
- **Resume PDFs are placeholders.** `resumes/*.README` files exist noting the expected filenames; drop in your real PDFs. The application preparer does not generate new PDFs from the profile — it selects which variant you'd attach.
- **Interview tracker** auto-creates an `InterviewRow` when `ApplicationTracker.mark_interview()` runs; `/interviews` and `/interviews?application_id=...` endpoints are live. Multi-round scheduling + the contacts CRM UI stay deferred to Phase-6b web UI.
- **Compliance is enforcement-grade, but AUTO_SUBMIT soft-warning mode is a trust contract.** When `AUTO_SUBMIT=true` + `USER_APPROVAL_REQUIRED=true`, the agent proceeds (because the per-application approval still gates submission). If future code wiring ever decouples these, update `ComplianceAgent._HARD_BYPASS_FIELDS`.

---

## Tests

```bash
make test
```

```
193 passed in 3.41s
```

Coverage includes profile correctness vs the real resume, every scoring dimension, deduplication edge cases, every scam pattern, every hard-rejection rule, FSM transitions (including invalid transitions and the OFFER→REJECTED/WITHDRAWN terminal set), dashboard aggregation, the 10-agent orchestrator (including failure recovery and ComplianceViolation halt), and the 23-step acceptance test from the brief (`tests/test_acceptance.py`).

---

## Troubleshooting

- **`sqlite3.OperationalError: unable to open database file`** — ensure the `data/` directory exists (`make setup` or `python -c "from app.config import get_settings; get_settings()"`); the `database_url` validator auto-resolves `sqlite:///./…` to repo-root.
- **`ImportError: email-validator`** — `pip install email-validator`, or re-run `make install`.
- **`UserWarning: datetime.utcnow deprecated`** — handled; all internal timestamps are timezone-naive UTC via `datetime.now(timezone.utc).replace(tzinfo=None)`.
- **No high matches** — the mock set is tuned to produce ~1 "high_priority" and ~10 "apply" results by default (zero "apply_immediately" because that tier requires 95+). Lower `SCORE_HIGH_PRIORITY` or `SCORE_APPLY` in `.env` for a wider funnel.

---

## Credits

Profile and resume facts are the user's own, used only for truthful application generation. All third-party platform integrations are built against **official public mechanisms** (ATS APIs, public job pages, OAuth) and respect `robots.txt`, rate limits, and ToS.
