# Project Reporter: Requirements and Design Specification

Status: Draft specification. No reporter implementation exists.
No dashboard, Telegram bot, scheduler, or integration has been built.

The reporter is a supporting tool for the LugandaGPT research project. It
summarizes verified project activity and supports private progress
reporting now, and building-in-public workflows later.

This document is documentation only. It does not commit the project to any
language, framework, database, hosting provider, or API.

---

## 1. Purpose

- Give the project director and agents a periodic, evidence-backed summary
  of what actually happened in the project.
- Keep a durable report history so progress can be reviewed later.
- Produce draft public updates for human review, never automatic posts.

The reporter observes the project. It never changes it.

---

## 2. Scope and authority

The reporter is **read-only with respect to project code**. It must not:

- commit, stage, or push to Git;
- modify source code, documentation, or configuration;
- change architecture or training strategy;
- launch training or fine-tuning;
- spend API credits or start paid compute;
- publish publicly, to any channel.

Human approval is required for any public posting and for any spending.
Two limits apply in all stages: never invent progress, test results, or
usage figures; never claim a model was trained or evaluated unless that is
verified from project records.

---

## 3. Requirements

### 3.1 Activity collection

The reporter gathers activity from sources that can be verified. Every
collected item carries its source and a retrieval timestamp.

| Source | Collected | Verification |
|---|---|---|
| Git | Commits, changed files, branches, working-tree status | Read directly from the repository (read-only Git queries) |
| Tests | Results, **only when actual test output exists** | Test output file or captured run output; no output means "no test data" |
| Experiments | Entries from `docs/EXPERIMENT_LOG.md` | Only records present in the file; missing fields reported as missing |
| Roadmap | Milestones and blockers from `docs/ROADMAP.md` | Parsed status lines; unstarted phases are not reported as started |
| Human-entered | Activity not represented in Git | Entered manually, marked as human-entered |
| API usage | Spend and call counts, **only when verified data exists** | Provider billing or usage export; absent data is reported as unavailable |

Rules:

- Never infer activity that is not recorded somewhere.
- Human-entered entries are labeled as such and never mixed into the same
  field as Git-derived facts.
- Collection runs read-only. No collector may write to project files.

### 3.2 Reports

- **Default interval: every eight hours.** The schedule is a default, not a
  requirement to produce meaningful content on every run.
- Each report contains, where applicable:
  - completed work;
  - attempted work;
  - failures;
  - blockers;
  - decisions (with reference to `docs/DECISIONS.md`);
  - verified spending (only when source data exists);
  - next steps.
- **Every significant claim identifies its evidence**: the commit hash,
  file path, report entry, or billing record it came from.
- Verified facts and suggestions are visually and structurally separated.
  Suggestions are labeled as proposals awaiting approval.
- A run with no meaningful activity produces a report saying so, with the
  period covered and the sources checked.
- Reports never contain invented progress, test results, or usage figures.

### 3.3 Dashboard

- Project status and current phase (from the roadmap).
- Activity timeline.
- Recent reports plus historical report archive.
- Tests, experiments, and blockers.
- Upcoming milestones.
- Verified spending when available, otherwise shown as unavailable.
- Draft public updates queued for human review.

The dashboard is an internal view. It holds no secrets and is not exposed
publicly during early stages.

### 3.4 Telegram delivery

- Reports go to a **private channel** through a **dedicated bot**.
- Bot tokens and credentials come from environment variables or a local
  secrets file outside Git. Never from source code, Git, reports, or logs.
- **A successful delivery test must pass before any scheduling is enabled.**
  Scheduling stays disabled until delivery to the private channel is
  confirmed.
- Internal sensitive information (spending, private notes, personal data,
  unreleased results) never goes to public channels.

### 3.5 Building in public

- The reporter generates **drafts only**. Publishing requires human
  approval and a separate action.
- Technical claims in drafts carry evidence or links back to commits,
  reports, or documents.
- No claim that a model was trained or evaluated unless verified from
  project records. At the time of writing, **no trained LugandaGPT model
  exists**, so no public draft may say otherwise.
- Internal engineering reports and public summaries are separate artifacts
  with separate templates. A public summary never inherits internal
  detail by default.
- Audience metrics are tracked later, only once reliable data sources
  exist. Metrics are not invented or estimated in the meantime.

### 3.6 Safety and authority

- Read-only with respect to project code and Git history.
- Deduplicate events so the same commit, test run, or human entry never
  appears twice in a report or across consecutive reports.
- Never expose secrets or private data in reports, dashboard, logs, or
  delivered messages. Secret-shaped values are redacted at collection time.
- Spending and public posting stay under human control at every stage.
- Fail closed: if verification is not possible, the reporter omits the
  claim or states that the data was unavailable.

### 3.7 Resource constraints

- Development machine: approximately 8 GB RAM and limited free disk space.
- Prefer a lightweight implementation: plain files and existing project
  documents where sufficient.
- Avoid unnecessary databases, frameworks, and AI API calls. Summaries
  are assembled from collected facts, not generated by a paid model.
- **The final technology stack is not chosen here.** It follows review of
  requirements and deployment constraints. See Open Decisions (OD-01).

---

## 4. Implementation stages

### Stage A: Local activity collection and Markdown reports

**Deliverables**
- Read-only collector for Git data (commits, files, branches, status).
- Collectors for test output, experiment log, roadmap milestones, and
  human-entered activity.
- Markdown report generator with the eight-hour interval as a default
  setting.
- Deduplication of events across reports.

**Acceptance criteria**
- Reports generated locally from real repository state, each claim with
  its evidence path.
- A run with no activity reports exactly that.
- Verified vs. suggested content clearly separated.
- Collector performs no Git writes and modifies no project files.
- No secrets present in generated reports (checked by a scan).

**Dependencies**
- Existing documentation files as data sources.

**Security considerations**
- Secrets redaction at collection; secrets read only from environment or
  an untracked local file; no network calls.

### Stage B: Minimal dashboard and report history

**Deliverables**
- Local dashboard showing status, phase, timeline, recent and historical
  reports, tests, experiments, blockers, upcoming milestones, and
  spending when available.
- Report archive with retention rules and a fixed on-disk layout.

**Acceptance criteria**
- Dashboard renders from stored reports without network access.
- Missing data (tests, spending) displays as unavailable, not as zero or
  as an estimate.
- Fits within RAM and disk limits.

**Dependencies**
- Stage A report format stable enough to store and re-read.

**Security considerations**
- Dashboard stays local; no credentials in the dashboard; no public
  exposure.

### Stage C: Telegram delivery

**Deliverables**
- Dedicated bot integration for a private channel.
- Credentials via environment variables or an untracked secrets file.
- A one-time delivery test with recorded confirmation.

**Acceptance criteria**
- Delivery test succeeds to the private channel before any scheduling
  exists.
- Token never appears in source, config committed to Git, logs, or report
  bodies.
- Failure to deliver is reported locally, not retried in a way that
  spams the channel.

**Dependencies**
- Stage A report output; project-director approval to create the bot and
  channel.

**Security considerations**
- Channel is private; membership reviewed; sensitive fields excluded from
  message bodies; delivery errors do not print the token.

### Stage D: Scheduled reporting

**Deliverables**
- Scheduler running reports at the eight-hour default, configurable.
- Missed-run handling and a visible last-run record.

**Acceptance criteria**
- Reports appear on schedule for at least one full review period.
- A run with no activity still produces the "no activity" report.
- Scheduler runs read-only and cannot trigger commits, pushes, training,
  or spending.

**Dependencies**
- Stage C delivery test passed; the machine must be available at the
  configured times (constraint: a single development computer).

**Security considerations**
- Scheduler credentials are minimal and local; no privileged Git access;
  scheduled runs follow the same redaction rules as manual runs.

### Stage E: Public-post drafts and audience analytics

**Deliverables**
- Draft generator producing public summaries from internal reports.
- Human review and approval workflow before any publication.
- Audience metric collection, only where reliable data sources exist.

**Acceptance criteria**
- Every draft carries evidence links for technical claims.
- No draft is published automatically; publishing is a separate,
  human-approved action.
- Internal and public documents use separate templates, with internal
  detail excluded from public drafts by default.
- Metrics sections show "unavailable" until a reliable source exists.

**Dependencies**
- Stages A and B; project-director approval for any public presence;
  a defined audience channel (not chosen yet).

**Security considerations**
- Public drafts pass a secret and personal-data scan before display;
  spending and private notes never appear in public output; metrics
  access respects the data-source terms.

---

## 5. Out of scope

- Any implementation, dependency install, or API call under this task.
- Creating a Telegram bot or channel.
- Job scheduling.
- Paid AI API calls for summarization.
- Publishing anything publicly.
- Training, evaluation, or data acquisition of any kind.

---

## 6. Open decisions

These must be reviewed and approved before implementation begins.

- **OD-01: Technology stack.** Language, storage format, and dashboard
  approach remain undecided pending review of requirements and deployment
  constraints. Note `AGENTS.md`: Python is the default for tooling unless a
  documented reason says otherwise, but no stack is chosen here.
- **OD-02: Storage.** Whether flat Markdown/JSON files suffice through
  Stage B, or a small database is justified later. Default is files.
- **OD-03: Hosting and scheduling.** Whether scheduled reporting runs on
  the development machine or elsewhere, given its RAM and disk limits.
- **OD-04: Telegram bot ownership and channel membership.** Who creates
  and administers the bot, and who joins the private channel.
- **OD-05: Report retention and location.** Where reports live, how long
  they are kept, and whether they are committed to Git.
- **OD-06: Public channel.** Which platform, if any, and who approves
  individual public posts.
- **OD-07: Audience metrics source.** Which platform provides reliable
  data, and under what terms, before any metric is reported.
- **OD-08: Deduplication key.** The stable event identifier used across
  runs (proposal: commit hash, test-run identifier, and human-entry ID).
- **OD-09: Approval checkpoints.** Which stages require explicit
  project-director sign-off before proceeding (at minimum Stages C, D, and
  E).

---

## 7. Relationship to existing documents

- `AGENTS.md` governs secrets, cost, and approval rules that apply to every
  stage.
- `docs/ROADMAP.md` supplies milestone and phase data.
- `docs/DECISIONS.md` supplies decision records referenced in reports.
- `docs/EXPERIMENT_LOG.md` supplies experiment entries; entries that do
  not exist are reported as not existing.
- `docs/EVALUATION_PLAN.md` governs any claim about evaluation.
- `data/README.md` governs anything dataset-related the reporter might
  summarize.

No statement in this specification asserts that any reporter component,
integration, dashboard, or bot currently exists.
