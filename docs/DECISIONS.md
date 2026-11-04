# Decisions (Lightweight ADR Log)

Architecture decision records in a lightweight format. Each entry includes
**Context**, **Decision**, **Rationale**, **Consequences**, and **Status**.

Statuses: *Accepted* | *Open* | *Superseded* | *Rejected*.

---

## D-001 — Luganda-native model, not a translation app or chatbot wrapper

**Context:** Available Luganda tooling tends to be translation-focused or a
wrapper over a general-purpose model. Neither provides deep, native command
of the language.

**Decision:** The project aims to build a **Luganda-native conversational
language model**, not merely a translation application or a wrapper around
another provider's chatbot API.

**Rationale:** The stated goal — natural conversational Luganda, register
control, code-switching, and cultural accuracy — is not achievable by
translation shims alone.

**Consequences:** The project carries the cost and complexity of model
development rather than only prompt engineering. Translation may still be a
useful internal component or benchmark, but it is not the product.

**Status:** Accepted.

---

## D-002 — Initial scope is text-only

**Context:** Speech and multimodal work expand scope and cost substantially.

**Decision:** The initial scope is **text-only**.

**Rationale:** Text provides the fastest path to a usable conversational
model and a testable evaluation benchmark.

**Consequences:** Speech capabilities are explicitly out of scope for now.
Architecture choices should not be forced to accommodate audio yet.

**Status:** Accepted.

---

## D-003 — DeepSeek is the engineering agent, not the model foundation

**Context:** Division of labor among AI systems needs to be explicit.

**Decision:** **DeepSeek** acts as the primary engineering agent
(implementation, debugging, tests, data tooling, training infrastructure).
It is not itself the model that LugandaGPT is built on.

**Rationale:** Separating "who builds the system" from "what the system is"
avoids conflating tooling with architecture.

**Consequences:** No architectural commitment to any DeepSeek model. Model
foundation remains undecided (see D-005).

**Status:** Accepted.

---

## D-004 — Native-speaker evaluation is required

**Context:** Automated metrics and AI judgments do not reliably capture
Luganda grammaticality, naturalness, or cultural accuracy.

**Decision:** **Native Luganda speakers** are required for meaningful
language-quality assessment.

**Rationale:** Human judgment is the reference standard for language
quality; AI-generated judgments are not ground truth.

**Consequences:** Evaluation designs must include a human-review component
and budget/coordinate evaluator time. Automated metrics are supporting
evidence only.

**Status:** Accepted.

---

## D-005 — Model architecture, parameter count, and training strategy remain unselected

**Context:** Choosing a model family, size, tokenizer, or training method
before evidence would be an unjustified assumption and could waste compute.

**Decision:** **Model architecture, parameter count, and training strategy
remain unselected** pending evidence from research, baseline evaluation,
tokenizer experiments, and feasibility studies.

**Rationale:** Decisions should follow documented experiments and
constraints (data volume, licensing, compute, budget), not assumptions.

**Consequences:** No training runs are authorized on the basis of a chosen
architecture yet. When a choice is proposed, it must be documented here with
rationale and approved by the project director before implementation.

**Status:** Open. The working direction is recorded in D-017. This decision closes only through a base-selection record at Gate 5 of `docs/WORKING-PLAN.md`.

---

## D-006 — Separation of responsibilities

**Context:** The project involves a human owner, multiple AI systems, and
human language evaluators. Without an explicit division of labor, roles can
blur — an engineering agent could appear to authorize spending, or an AI
judgment could be mistaken for linguistic ground truth.

**Decision:** Responsibilities are separated as follows:

- **Human project director:** priorities, approvals, and spending.
- **DeepSeek:** primary engineering agent.
- **ChatGPT:** architecture and research review.
- **Native Luganda speakers:** human linguistic evaluation.

**Rationale:** Keeping decision authority, implementation, review, and
language-quality judgment in distinct hands prevents any one party from
simultaneously producing work, reviewing it, and approving it — and keeps
spending control with the human owner.

**Consequences:** Engineering agents implement but do not authorize scope,
budget, or architecture changes. Research and architecture proposals come
from ChatGPT as review input, not as instructions to be executed without
project-director approval. Luganda quality claims require native-speaker
evaluation. These responsibilities are also recorded in `AGENTS.md` §6.

**Status:** Accepted.

---

## D-007 - Benchmark specification approved, benchmark not yet approved

**Context:** The Project Director reviewed and explicitly approved the current
contents of `docs/BENCHMARK-SPECIFICATION.md`, then labelled version
`0.1-draft`. The document still carried draft approval metadata and listed its
own approval as open. No benchmark items, native reviews, or evaluation runs
exist.

**Decision:** The benchmark specification is approved at specification
version `1.0`, without substantive changes to the reviewed contents. The
approval covers the specification's categories, dimensions, item schema,
language rules, reference and ambiguity policy, scoring rules, review rules,
versioning, and run-record requirements. It resolves O-01 and O-03 through
O-07 in section 19 of the specification.

This decision does not approve an item file, benchmark version, native-review
process, model access, budget, evaluation run, or release. It is not a native
speaker sign-off and does not replace the `ApprovalRecord` required for a
frozen benchmark version. The actual benchmark remains unfrozen and
unapproved.

**Rationale:** Owner approval of a specification is separate from native
language review and from release approval. Recording the distinction prevents
the approved document from being mistaken for an approved benchmark.

**Consequences:** The specification approval is recorded in D-007. Prompt
authoring, native review, benchmark freezing, and evaluation remain blocked on
the owner actions listed in section 19 and the native-review dependencies in
section 20. O-02, O-08 through O-15, and O-17 remain open. O-16 is partly
resolved because this decision record was added; the owner has not decided
whether to update roadmap or README status.

**Status:** Accepted.

---

## D-008 - Bounded Runpod RTX 4090 gate for Approach B

**Context:** The Project Director reviewed `reports/FINE-TUNING-FEASIBILITY.md`
and approved Approach B for a first bounded gate. The owner selected Runpod
and an NVIDIA RTX 4090 with 24 GB of VRAM, capped total compute and storage
spending at $20, authorized a 100-example data pilot and a 50 to 100 example
training smoke test, and required a separate approval before full fine-tuning.
D-005 remains open. This decision does not select the final architecture,
parameter count, or training strategy.

**Decision:** The first gate uses one Runpod Secure Cloud RTX 4090 at the
publicly listed $0.89 per hour, checked on 2026-10-21. The candidate is a fresh
LoRA adapter from the pinned base, not a continuation of the existing adapter.
The gate covers licence and provenance review, native-teacher agreements and
consent, a 100-example native-authored pilot, a separate evaluation set, and a
50 to 100 example smoke test. The total cash cap is $20 including taxes and
fees. The existing adapter remains a translation baseline and is not continued
as the main conversational model. No full 1,000 to 1,500 example run,
deployment, publication, or release is approved.

**Rationale:** A 24 GB RTX 4090 is sufficient for a 4-bit LoRA smoke test on a
1B model and avoids the memory limits of the local machine. Runpod's prepaid
credits and short-running Pods allow a hard spending stop. Secure Cloud is
selected over the cheaper Community Cloud tier for predictable host quality
during a short, supervised run.

**Consequences:** Execution is blocked until the owner completes account and
payment setup, live RTX 4090 availability and the tax-inclusive charge are
verified, data and teacher approvals exist, and a training script and GPU
environment have been tested. Runpod credits are non-refundable and sales tax
is charged on top of credit purchases, so the purchase must keep the total
charge at or below $20. No paid infrastructure was launched for this decision.
See `reports/RUNPOD-FIRST-GATE-REPORT.md` and
`configs/gemma3-1b-lora-smoke.yaml`.

**Status:** Accepted for the bounded gate only. D-005 remains open. Materials archived 2026-11-02 under D-018; no GPU spending is currently approved.

---

## D-009 - English source draft first, then native translation and review

**Context:** The Project Director reports that native Luganda speakers are
available and have agreed to collaborate. The owner and team discussed working
arrangements, and compensation is intended after the project earns its first
dollar. The repository does not contain signed agreements, formal consent
records, a compensation amount or schedule, retention terms, or a licence for
translated data. No Luganda pilot dataset exists yet.

**Decision:** The engineering workflow prepares 100 original English source
examples for the pilot and a separate 24-item English evaluation draft. The
native-speaking team translates the source into Luganda, and a second native
speaker reviews each translated item. The English source keeps stable IDs and
a draft schema that reports every translation and review as pending. The
training-data schema and its authorization checks are not weakened.

This refines the data-authoring method in D-008. The D-008 provider, GPU,
budget, and bounded-gate decision remain in force. The pilot source is
authored in English and translated and reviewed by native speakers rather
than fully authored in Luganda by the engineering workflow.

**Rationale:** English source authoring can proceed without inventing
translations, reviewers, consent, or approvals. Separating the source draft
from the training dataset prevents the English material from being mistaken
for Luganda training data. Native speakers remain the reference standard for
translation and review.

**Consequences:** The English source pilot is available for owner review in
`data/source/pilot-v1/` and `reports/ENGLISH-SOURCE-PILOT-REPORT.md`. The
Luganda training dataset remains blocked until translations, second-speaker
reviews, formal consent and compensation records, licence terms, provenance,
and training approvals exist. This decision does not create a formal
agreement or authorize a paid run. The approved benchmark specification is
unchanged. The 24-item feasibility set is not a benchmark.

**Status:** Accepted for source preparation only. Training remains blocked.

---

## D-010 - Local Translation Studio on the existing Python stack

**Context:** Native-speaking teachers need a simple way to translate the 124 English source records and review each other's work. The repository already uses Python and has no web framework. The work is local and private. The project must not add a public service, external login, paid infrastructure, or an AI translation API.

**Decision:** Build a local-only Translation Studio in `src/translation_studio/` using the Python standard library WSGI server, SQLite, and the Jinja2 package already present in the environment. Keep imported English source records read-only. Store translations, immutable submitted versions, reviews, resolutions, audit events, and dataset-preparation fields separately. Keep translation status, review status, collaboration and consent status, licence status, and dataset approval separate. Exports must pass the existing training-record validator, and evaluation items are excluded from training exports by default. The default server binds to `127.0.0.1`. A trusted local network option is documented but is not a public deployment.

**Rationale:** This gives teachers a usable browser interface without adding a database service, cloud dependency, authentication provider, or model call. Keeping studio work in a separate SQLite database prevents the English source draft and review workflow from being mistaken for approved training data. Submitted versions and review history remain inspectable.

**Consequences:** The studio requires a local setup command and a local SQLite backup procedure. It has no public registration, email reset, TLS, or deployment approval. Running the server on a trusted local network is an explicit operator action, and public exposure is not authorized. The approved benchmark specification is unchanged. Training remains blocked until the existing data, provenance, consent, licence, review, and authorization requirements are met.

**Status:** Accepted for local development only.

---

## D-011 - Approved-translation reward display

**Context:** The Project Director wants a simple motivation for translators: $2 for every 10 translations completed and approved. The studio should show teachers how much approved work has accumulated after login. Actual payment, formal compensation terms, tax handling, and payment records are separate project responsibilities.

**Decision:** The Translation Studio displays an estimated reward of $0.20 per approved translation, with a $2 reward reached at every 10 approved translations. Only translations whose current version has passed review count. Drafts, returned work, disputed work, and unapproved work do not count. The dashboard labels the amount as an estimate and states that payment is not recorded in the local app.

**Rationale:** Showing approved progress and a small accruing reward gives translators visible feedback without pretending that a payment has occurred or creating a payment-processing integration. The rule remains separate from dataset approval, consent, licence, and training authorization.

**Consequences:** The owner still needs to confirm formal compensation terms, payment schedule, payment method, tax treatment, and records. A review approval can later be reversed, so the estimate can go down. The studio does not move money, store payment credentials, or claim that a translator has been paid. The owner dashboard shows estimated rewards by translator for planning and review.

**Status:** Accepted for display and motivation only.

---

## D-012 - Background passage translation is required

**Context:** The work screen shows a Luganda background passage for source examples that contain an English passage. A missing passage was displayed as "Not translated", which made it unclear whether translators could ignore it. The passage is needed for comprehension and question-answering examples.

**Decision:** When a source example has a background passage, its Luganda translation is required before the translation can be submitted for review or approved. The Luganda passage is included in the user message of the training-preparation record, before the final question or request. Reviewers cannot approve a translation with a missing required passage. Administrators can return submitted work for correction without deleting translation or review history.

**Rationale:** Removing the passage would make a comprehension or question-answering example incomplete. The training example must include the same context that the English source supplies. Making the requirement explicit prevents incomplete work from looking finished.

**Consequences:** Missing passage text blocks review approval and dataset preparation. A translator can correct it after the item is returned. The studio does not silently fill the passage or treat it as optional.

**Status:** Accepted.

---

## D-013 - Reviewer rewards and cleared payment records

**Context:** The Project Director wants reviewer accounts to receive a share of $0.10 per completed review. The owner also needs a way to record when a payment has been completed so the reviewer's available balance clears and new work can accumulate again.

**Decision:** Reviewer accounts accrue $0.10 for each completed review submission. The Rewards page and reviewer dashboard show total earned, total cleared, and the available amount since the last cleared payment. Administrators can mark a payment as cleared from the administration payments page. Recording a cleared payment subtracts the paid amount from the available balance while preserving the full review and payment history.

**Rationale:** A separate payment record lets the owner acknowledge completed payments without deleting work history. Available earnings can reset after payment while the total earned and the review history remain visible.

**Consequences:** The local app records payment clearing only. It does not move money, store payment credentials, or prove that a bank transfer occurred. The owner must complete the actual payment outside the app and enter a note or reference. Formal compensation terms, tax treatment, and payment records remain the owner's responsibility.

**Status:** Accepted for local reward accounting only.

---

## D-014 - PHP deployment edition for cPanel (retired)

**Context:** The owner needs to deploy the studio on a cPanel domain where configuring a Python application is inconvenient. The existing SQLite database, users, and password hashes should remain usable.

**Decision:** Add a PHP 8.1+ deployment edition under `php/`. It uses PDO SQLite, the same database schema, and the same PBKDF2 password hashes. It covers login, translation work, autosave, review, reviewer rewards, translator rewards, cleared payments, assignment, user creation, item inspection, return-for-correction, and disagreement resolution. The Python edition remains the reference implementation for training-data validation and training-preparation export.

**Rationale:** PHP is the native deployment path on most cPanel hosts. Reusing SQLite and the existing password hashes avoids a database migration and keeps the accounts and work already created in the local studio.

**Consequences:** The PHP edition requires the `pdo_sqlite` extension and a writable database path. The database should be stored outside public web access. Training export, training validation, benchmark work, and model execution are not reimplemented in PHP. The live domain must use HTTPS and must not expose the database or credentials. Public deployment remains an owner decision.

**Status:** Retired. Superseded by D-016. This record is retained as project history.

---

## D-015 - Confirmed contributor reward rates and earnings ledger

**Context:** The Project Director confirmed a reward rate of $0.20 per reviewer-approved translation and $0.20 per valid completed review. The previous reviewer rate in D-013 was $0.10 and reward amounts were hidden pending confirmation.

**Decision:** Use one central integer-cent rate configuration for both contribution types. Record each earned translation reward once per item and each review reward once per review record. Preserve existing cleared-payment administration and calculate balances in integer cents. On database initialization, backfill reviewer rewards from valid stored review records and translation rewards only for translations that currently satisfy the existing approval eligibility checks. Do not infer earnings for earlier translation versions whose approval state cannot be established from current records.

**Rationale:** A durable earnings row preserves the first qualifying approval even if a translation is later reopened. Unique database indexes prevent retries from creating duplicate rewards. Existing review and translation records provide the evidence for the limited backfill.

**Consequences:** The additive migration creates `reward_earnings` and adds `amount_cents` to `reward_payments`, retaining the existing dollar column for compatibility. Back up an existing database before running `init-db` with this version. The app records payment history only; it does not move money. Older payment records remain aggregate records and are assigned to contribution history in chronological order for display.

**Status:** Accepted for local reward accounting. Production migration and deployment remain separate owner actions.

---

## D-016 - Python Translation Studio as the sole supported implementation

**Context:** The project has a Python Translation Studio and a separate PHP implementation. Maintaining two applications creates duplicated workflows and risks differences in behavior and maintenance.

**Decision:** Retire and remove the legacy PHP application. The Python application in `src/translation_studio/` is the sole supported Translation Studio. Continue preparing PythonAnywhere releases from `deployment/translation-studio/`.

**Rationale:** A single maintained application keeps workflows and deployment guidance aligned with the Python source of truth.

**Consequences:** This retirement does not change the database schema, initialize or migrate a database, or alter stored records. The Python deployment package remains separate from the live database and must be deployed manually under the existing approval process.

**Status:** Accepted.

---

## D-017 - Sunflower-14B as baseline to beat and preferred candidate base

**Context:** On 2026-11-02 the Project Director asked to align the project with a plan that builds on Sunbird's open Sunflower models instead of starting from scratch, and that proves improvement against them. `docs/PHASE-1-RESEARCH.md` already lists `Sunbird/Sunflower-14B` as shortlist candidate 2. D-005 leaves the base model and training strategy open. D-008 approved a bounded Gemma 3 1B smoke test only.

**Decision:** Adopt Sunflower-14B in two roles. It is the baseline that every LugandaGPT candidate must be measured against on the frozen benchmark, and it is the preferred candidate base for adapter training. Work is sequenced through the gates in `docs/WORKING-PLAN.md`. Evaluation uses the approved benchmark specification unchanged: independent per-dimension scores from native reviewers, with no composite score. D-008 stays in force as a low-cost pipeline test. The base is chosen at Gate 5 from baseline evidence. If Sunflower already performs well on the conversational categories, the project picks a narrower niche before spending on training.

**Rationale:** An Apache-2.0 model already trained on Ugandan languages avoids a corpus the project cannot assemble alone. Measuring the baseline first shows where a gap exists before any training money is spent, and it keeps public claims tied to category-level evidence.

**Consequences:** D-005 stays Open and is closed only by a Gate 5 record. This record authorizes no spending, API call, dataset acquisition, gated-model download, or training run. Sunflower's weights and the data behind them need a licence and provenance review before any commercial or investor use: SALT is tagged CC BY-SA 4.0 and Sunflower's training data is not documented in the metadata reviewed. The training pipeline is pinned to Gemma 3 1B and needs a documented, tested change before it can train Sunflower. The benchmark specification, D-007, and the open owner items in its section 19 are unchanged. The owner's request to align status documents settles the question left open in O-16 about updating roadmap and README status; the specification text itself is not edited.

**Status:** Accepted as the working direction for planning and baseline preparation. D-005 remains Open.

---

## D-018 - Archive the Gemma 1B and reporter material; connect to the Sunbird API

**Context:** On 2026-11-02 the Project Director chose to proceed with the Sunflower plan in D-017 and asked that material outside it be removed, and for a connection that runs Sunflower through Sunbird's API and returns translations for comparison with the Director's own. Asked whether to delete or archive, the Director chose archive. The Translation Studio imports parts of `src/training/`, and its database holds teacher accounts and translations that are not in Git.

**Decision:** Move the Gemma 1B training, inference, config, data, environment and artifact modules, the Runpod documents and configuration, the project reporter, and their tests into `archive/2026-11-02-gemma-runpod-reporter/`. Keep `training.constants`, `errors`, `storage`, `pilot`, and `source_pilot` and a slim `training` CLI because the Studio depends on them. Keep the Studio, its database, the benchmark, the English source data, the experiment records, and every decision record. Add `src/sunbird_api/`, a standard-library client for `POST /tasks/chat/completions` with the models `sunflower-9b` and `sunflower-14b`, and a `translate-source` command that writes machine suggestions to `data/machine/`. The Director's request is the approval for this provider, these models, and these two tasks (baseline chat and source-record translation suggestions). No budget was set, so every run is capped at 25 requests unless the cap is raised on the command line, and every request is logged without prompt text or credentials.

**Rationale:** Archiving is reversible and avoids breaking the Studio. A request cap and ledger give spending control while Sunbird's pricing and rate limits are unpublished. Keeping suggestions out of the Studio keeps translators and reviewers independent of machine output.

**Consequences:** D-008 authorized a bounded Gemma 1B gate. Its materials are archived and no GPU spending is currently approved. D-005 stays Open and closes at Gate 5, now defined as confirming Sunflower-14B as the base. Any Sunflower fine-tuning script, GPU rental, or budget needs a new approval. The hosted `sunflower-14b` may differ from the pinned Hugging Face revision, and API terms for retention and benchmark use are unverified, as recorded in `docs/SUNBIRD-API.md`. D-010 is unchanged: the Studio calls no AI service. The reporter is not running and its scheduled delivery, which was disabled, stays off.

**Status:** Accepted.


## D-019: Contributor terms reported by the owner (Gate 0)

**Date:** 2026-11-03

**Decision:** The Project Director reports the following terms, which he says the native translators and reviewers accepted in writing. The repository holds no copy of that agreement, so this is an owner report and not a verified or signed record.

1. Pay: $0.20 per finished translation (the Studio also tracks $0.20 per approved review, D-015). Pay only for approved items. Keep a payment ledger and a monthly approval limit so the project does not overspend before any model is trained.
2. Use: training, testing, and research reporting for the Luganda AI product (communication use first). Sharing is possible later and needs a separate decision.
3. Names: contributors stay pseudonymous.
4. Ownership: the data belongs to the project owner. Contributors help translate, understand, and give feedback and keep no ownership. Work already used cannot be withdrawn from a trained model. Larger data programmes later need new terms.
5. Retention (proposal, owner said to proceed): keep approved translations and reviews for the life of the project and a period after it ends (suggested 3 years); delete login details 12 months after last activity; store locally with backups and owner-only access; on leaving, delete personal login details and keep contributed text.

**Rationale:** The owner asked to proceed without sharing the agreement. This record states what is claimed so that no later document treats it as verified.

**Consequences:** Gate 0 stays "owner reported". Strict data validation still needs signed consent records matched to each contributor's pseudonymous ID before any training. A lawyer should read the ownership terms before an investor pitch. No training or paid compute is authorized by this record.

**Status:** Accepted. On 2026-11-03 the owner confirmed that the contributors consented in writing and that he is satisfied. The confirmation is the owner's own; the repository holds no copy. Per-contributor consent records for the data validator still need to be entered.


## D-020: Rule-generated time and day practice data, with held-out hours

**Date:** 2026-11-03

**Decision:** Generate practice questions and answers for Luganda clock time and days of the week from rules confirmed by the native group (`data/rules/rules-check-Group-1-2026-11-03.csv`), using `src/rule_data/`. Hours 8, 9, 10, 13 and 14 and the day facts used by the benchmark are held out of generated data, so the benchmark tests the skill on hours the model was not taught. Generated rows are labelled `rule_generated_from_group_rules`, start as unreviewed, and are checked by native speakers on a sample before any use.

**Rationale:** Sunflower failed time and day items in the pilot. The rules are fixed, so generated examples are cheap and consistent, but they are not native-authored data and could teach the wrong thing if a rule is wrong.

**Consequences:** No training is authorized by this record. Open spelling questions are listed in `docs/PILOT-COMPARISON-2026-11-02.md`. Gate 0 still applies before any training.

**Status:** Accepted as a working direction.


## D-021: RunPod spending approved for Sunflower-14B QLoRA fine-tuning (not yet used)

**Date:** 2026-11-03

**Decision:** The Project Director approves up to $20 total on RunPod for fine-tuning Sunflower-14B with QLoRA, and the pod must be stopped after each run. The approval is recorded now and not yet used. No pod is running and no training run has started.

**Rationale:** The owner stated that $20 of RunPod credit is available and gave this approval in his own words on 2026-11-03.

**Consequences:** This replaces the statement in D-018 that no GPU spending is currently approved, for this one purpose and this cap only. It does not approve any other model, provider, or spend above $20. Each run should state its expected cost before starting. Practical prerequisites still apply and are not approvals: access to the gated Sunflower-14B weights, a training script, enough reviewed data, and the Gate 5 base confirmation.

**Status:** Accepted. Waiting to use.


## D-022: Luganda style rules from the native group

**Date:** 2026-11-03

**Decision:** Adopt the spelling and wording rules in `docs/LUGANDA-STYLE.md`, decided by the native group on 2026-11-03: ssaawa (not saawa), ez'emisana, kkumi, kkumi na bbiri; Lwo- after "on" and Lwa- when stating the day; 4pm accepted as ez'emisana or eza kawungeezi. Group-written text is stored raw and normalised separately, and only these rules are applied automatically.

**Rationale:** The model learns spelling from the data, so inconsistent spellings count as different words.

**Consequences:** `src/rule_data/` now follows these rules. Benchmark items EVERYDAY-003 and EVERYDAY-007 may need updating (open question).

**Status:** Accepted.


## D-023: Approval to acquire outside Luganda data from open-licensed sources

**Date:** 2026-11-04

**Decision:** The Project Director approves acquiring outside Luganda text. Scope recorded here: open-licensed sources only, starting with the Luganda Wikipedia dump and the Sunbird SALT text subset. Newspapers and other copyrighted text are not downloaded or copied without a written licence from the publisher; native writers may use them only as topic inspiration and write new text in their own words.

**Rationale:** More data is the main thing limiting the model. Open licences give us a clear basis for use, and the project rule is that a public web page is not a licence.

**Consequences:** Each downloaded file gets a provenance record (URL, date, hash, licence, approval D-023) beside it, using `src/open_data/`. Downloads run on the owner's computer because the cloud workspace cannot reach those sites. CC BY-SA 4.0 requires attribution and share-alike for adapted material, so the licence terms must be read before any release of data or models. SALT is gated and its test splits stay out of training. Sunflower's training data is undocumented, so overlap with these sources is possible. This record does not authorize any training run beyond D-021.

**Status:** Accepted.

## D-024: Rules for using outside data (SALT and Luganda Wikipedia)

**Date:** 2026-11-04

**Decision:** The Project Director accepts these rules, based on the native group's quality check of 80 random passages (`data/external/outside-check-Group-1-2026-11-04.csv`). Results: SALT 35 good, 4 needs fixing, 1 don't use (of 40); Wikipedia 22 good, 16 needs fixing, 2 don't use (of 40). One group, 40 passages per source, so rates are rough.

Rules:
1. SALT train split may be used for training. The 4 passages the group corrected enter with their corrected text, and the 1 rejected passage is excluded. SALT dev and test splits never enter training.
2. Luganda Wikipedia paragraphs are NOT used for training for now. The 38 paragraphs the group marked good or corrected form a small verified set that may be used.
3. Science and technical articles are excluded until native speakers agree on the terms, because the group found invented, non-Luganda vocabulary there.
4. The 20 before-and-after corrections are kept as a record of common mistakes (spelling, spacing, y'e vs ye, run-together words).
5. Larger use of Wikipedia needs the group to correct a bigger batch first, and a fresh quality check showing a rate we accept. Any data source is re-checked this way before it is added.
6. Held-out clock hours (8, 9, 10, 13, 14) and held-out day facts stay out of all training data (D-020), including outside data.

**Rationale:** About 1 in 8 SALT sentences has a flaw, which is acceptable for a first run. About 4 in 10 Wikipedia paragraphs need fixing, and spelling and phrasing errors cannot be filtered automatically. Training on them would teach the model the mistakes.

**Consequences:** The first training set is built from the time-and-day rule data, the native-written situations, and the cleaned SALT train split under these rules. SALT is translation pairs, not conversation, and Sunflower may already have seen it, so it adds volume more than new ability. This record does not authorize any training run beyond D-021.

**Status:** Accepted.

## D-025: Training approach and preference comparison stage

**Date:** 2026-11-04

**Decision:** The Project Director confirms: (1) pretraining is skipped, because Sunflower-14B is already pretrained; (2) the first adaptation is supervised fine-tuning with QLoRA under the D-021 budget; (3) a preference comparison stage, in which native speakers choose between two blind answers, is added to the roadmap as Phase 6b; (4) an early audience is built through that comparison page and measured findings, before a chat interface exists.

**Rationale:** Supervised fine-tuning on reviewed examples is the affordable step. Preference comparison gives evidence of what natives prefer and helps choose between versions. An audience and measured evidence make the project visible without claiming a finished product.

**Consequences:** `docs/ROADMAP.md` Phase 6b and `docs/WORKING-PLAN.md` section 8 record the plan. Hosting any public page, collecting public input, and any preference-tuning run each need separate owner approval. Public claims follow `docs/WORKING-PLAN.md` section 6.

**Status:** Accepted.

## D-026: Public beta launch plan (Luganda AI under Schmarc Technologies)

**Date:** 2026-11-04

**Decision:** The Project Director sets the launch direction. A fine-tuned Luganda model will be hosted on a rented GPU and opened to the public as a beta, under Schmarc Technologies as the operating company. Confirmed choices:
- **Name:** The product is called "Luganda AI". The interface shows a visible "Beta / research preview" label, but the product name is not "research preview".
- **Sign-up:** Users sign up (so Schmarc can contact them about improvements). This makes Schmarc a data controller; data-protection law applies.
- **Legal basis:** Launch as a company following Uganda's Data Protection and Privacy Act and other applicable law. A privacy notice and consent are required before public launch.
- **Feedback loop:** The hosted chat collects feedback (thumbs, a "write a better answer" box, and A/B preference where two answers are shown). The native group reviews feedback; only reviewed, corrected examples enter retraining. Public input is never trained on without notice and approval.
- **Safety:** Limits on harmful requests; the interface states the model is an early version and can be wrong.
- **Staged launch:** private beta (native group) → friends and community → public.
- **Infrastructure:** GPU rented (RunPod). Domain **castalore.com** (owned, no hosting yet) will host the web app. Budget is $20 now, with intent to raise toward $100+.
- **Scale target:** plan for roughly 500 users per day as an initial ceiling.

**Rationale:** Launching publicly builds an audience and a real-feedback loop, as the large labs did early. Sign-up and company operation let Schmarc stay legal and keep users informed.

**Consequences:** Public hosting, collecting public data, and any retraining on public feedback each remain owner-gated and require the privacy notice and a cost estimate first (Gate 8). The product cannot launch until a fine-tuned model exists and has been compared to Sunflower on the frozen benchmark; launching plain Sunflower is not permitted (D-001). Serving cost must be estimated before any paid GPU is left running. This decision does not raise the training budget beyond D-021 ($20); any serving spend is a separate owner approval.

**Status:** Accepted. Launch itself gated on the prerequisites above.
