# Translation Studio Implementation Report

**Status:** Historical implementation report from 2026-10-23. The Python Translation Studio is now the sole supported implementation. PythonAnywhere package preparation is documented separately in `deployment/translation-studio/README.md`.

**Date:** 2026-10-23

**Owner:** Project Director

**Scope:** Build the local LugandaGPT Translation Studio for native-speaker translation and independent review. This report does not authorize a public release, paid service, GPU run, model training, or dataset approval.

## 1. What was implemented

### Accounts and access

- Local login with usernames and passwords.
- Password hashing with PBKDF2-HMAC-SHA256 and a random salt.
- Hashed session tokens stored in SQLite.
- HttpOnly, SameSite=Lax session cookies.
- CSRF tokens on authenticated forms.
- Server-side role checks for administrator, translator, and reviewer routes.
- No public registration and no external authentication provider.
- Administrator-created accounts.
- Security headers, including a restrictive content security policy.

### Source import

- Import from the validated canonical file `data/source/pilot-v1/source_draft.json`.
- The existing source validator and export checks run before insertion.
- 124 records import on a fresh database: 100 pilot examples and 24 evaluation items.
- Reimport is idempotent. Unchanged records are skipped.
- A changed source record is reported as a conflict and the stored record is preserved.
- Imported source records are read-only in the studio.
- Evaluation items remain visually and operationally separate from pilot examples.

### Translation workspace

- One example at a time.
- English request and background passage.
- Earlier conversation turns in order with speaker labels.
- Plain-English task purpose.
- Response criteria and constraints.
- English meaning guide kept separate from the Luganda translation.
- Large Luganda text areas for context, earlier turns, final request, response, and notes.
- Unicode-preserving save and reload.
- Autosave with visible saving, saved, and failure states.
- Manual save, save and next, and mark ready for review.
- Local browser draft recovery when autosave fails or a page closes unexpectedly.
- Unsaved-changes warning.
- Translator feedback from reviews.
- Teacher views do not show technical IDs, training splits, JSON, or CSV.

### Review workspace

- Separate reviewer dashboard and review screen.
- Reviewer sees the English source, earlier turns, the full Luganda translation, criteria, constraints, and translator notes.
- Decisions: Approved, Needs revision, Cannot assess yet.
- Comments required for revision and cannot-assess decisions.
- Suggested corrections are preserved separately.
- Reviewer cannot edit or overwrite the translator's submission.
- Translator cannot review their own article.
- Review history is append-only.
- Conflicting reviewer decisions flag the item for owner resolution.
- Administrators resolve disagreements separately.
- Submitted translation versions are preserved in `translation_versions`.

### Administration

- Dashboard with pilot, evaluation, review, and dataset-preparation counts.
- User creation with role selection.
- Bulk assignment of translation and review work.
- All-items view with filters for collection, translation state, dataset state, and search.
- Item inspection with source, translation, review history, versions, assignments, provenance, audit, and dataset fields.
- Separate collaboration and consent status.
- Separate licence status.
- Separate privacy, contamination, validation, and dataset-preparation status.
- Dataset approval is blocked until the current translation is reviewed, assigned reviewers have submitted, and required dataset fields are complete.
- Evaluation items cannot be approved for training dataset preparation.
- Estimated translator rewards: $0.20 per approved translation, with a $2 reward at every 10 approved translations. The teacher dashboard, progress page, and Rewards page show the estimate. The owner dashboard shows estimates by translator.
- Reviewer rewards: $0.10 per completed review. Reviewer dashboards and Rewards pages show total earned, total cleared, and available balance.
- Administrator payment clearing: the owner can mark a payment as cleared, which records the amount and reference, resets the available balance, and preserves the full work and payment history.

### Reward rules

- Only translations approved by review count.
- Drafts, returned work, disputed work, and unapproved work do not count.
- A reversed approval can reduce the estimate.
- Reviewer rewards add $0.10 per completed review.
- A cleared payment remains in history and resets the available balance for new work.
- The amount is labelled as an estimate, not a payment receipt.
- The app does not move money, store payment credentials, or prove that a payment was transferred.
- The owner still needs to confirm formal compensation terms, schedule, method, tax treatment, and payment records.

### Exports and audit

- Studio CSV export for inspection and handoff.
- Training-preparation JSONL export for pilot items approved for dataset preparation.
- The training export runs every record through the existing `validate_pilot_record` gate.
- Evaluation items are excluded from the training export.
- The export does not authorize training or replace provenance, consent, licence, or retention records.
- Audit records cover imports, logins, assignments, saves, submissions, reviews, resolutions, metadata changes, dataset approvals, and exports.
- Passwords and translation text are not written into audit details.

### Design

- Split-screen sign-in page with project orientation.
- Role-specific workflow guidance on the welcome page.
- Compact one-row desktop header with active navigation.
- Responsive layout for phones and laptops.
- Large readable type, generous spacing, clear focus styles, and accessible contrast.
- Calm green, cream, and gold palette.
- No external fonts, analytics, trackers, or assets.

## 2. How to start on Windows

From the repository root:

```powershell
cd C:\xampp\htdocs\LugandaGPT
$env:PYTHONPATH = "src"
.\.venv-gemma\Scripts\python.exe -m translation_studio init-db
.\.venv-gemma\Scripts\python.exe -m translation_studio create-user `
  --username owner `
  --display-name "Project Owner" `
  --role admin
.\.venv-gemma\Scripts\python.exe -m translation_studio import-source
.\.venv-gemma\Scripts\python.exe -m translation_studio serve
```

Open:

```text
http://127.0.0.1:8765/
```

The `create-user` command prompts for a password. There are no hardcoded credentials.

Create the translator and reviewer with the same command and `--role translator` or `--role reviewer`.

## 3. Access model

The default server is host-only on `127.0.0.1`. It is not reachable from another device.

An operator may bind to a trusted local network with `--host 0.0.0.0`, but the application is HTTP, has no TLS, and must not be exposed to the public internet, port-forwarded, or placed behind a public tunnel. Public deployment requires separate owner approval and a security review.

The full access and security notes are in `docs/TRANSLATION-STUDIO.md`.

## 4. What was tested

The new studio suite has 19 test methods covering these acceptance behaviours:

1. Source import preserves 124 records and stable IDs.
2. Reimport does not create duplicates.
3. English prompts, context, and conversation turns display correctly.
4. Luganda Unicode text saves and reloads.
5. Partial autosave saves, reloads, and does not submit the translation.
6. A submit with missing fields is rejected and the draft remains.
7. Translation and review status transitions work.
8. Reviewers cannot overwrite a translator's submitted text.
9. Reviewers cannot review their own work.
10. Translator, reviewer, and administrator route access is enforced.
11. Two-reviewer disagreement becomes an owner-resolution flag.
12. Submitted versions survive a revision round.
13. Dataset approval requires separate consent and licence status.
14. Training export includes only approved pilot items.
15. Training export excludes evaluation items.
16. Exported records pass `validate_pilot_record`.
17. Administrator pages render.
18. The viewport meta and mobile CSS breakpoint are present.
19. CSRF rejection and no public registration are tested.
20. An owner-approved resolution can override a disagreement without pretending the reviewers agreed.
21. Reward arithmetic works at 0, 9, 10, and 23 approved translations.
22. Only approved translations count toward the teacher reward, and the administrator sees the estimate.
23. A stale-server template mismatch shows a restart message instead of a 500 on the home page.
24. The translated background passage is included in the training-preparation user message.
25. An administrator can return submitted work to the translator for correction.
26. A reviewer cannot approve a translation whose required background passage is missing.
27. A reviewer sees a completed review as reviewed instead of an open review.
28. Reviewer rewards accrue $0.10 per review, a cleared payment resets the available balance, and new reviews accrue again.
29. Translator payments clear the available balance and appear in the payment history.

Measured results:

- Studio tests: 19 tests, `OK`.
- Full repository suite: 420 tests, `OK`.
- JavaScript syntax check: `node --check` passed.
- Python compilation: no syntax errors.

The full suite output includes an expected reporter failure message from an existing reporter test. The unittest summary was `OK`.

## 5. What was checked manually in a browser

- The real local server started and served the app.
- The split-screen sign-in page rendered.
- A translator login rendered the welcome dashboard.
- The desktop navigation, active state, hero workflow panel, and progress cards rendered.
- A work example rendered with the progress indicator and translator workflow.
- The teacher reward card and Rewards page rendered, including the approved-only rule and payment estimate note.
- The review dashboard and review workspace rendered.
- The administrator dashboard rendered with source import status, counts, assignment controls, reward estimates, and audit history.
- Static assets loaded without a JavaScript console error on the inspected pages.

The visual check was desktop-sized. Mobile behavior is verified by responsive CSS and the viewport meta, but it has not been tested on a real phone.

## 6. Source data protection

The canonical source file was not rewritten. The studio stores source JSON in its own SQLite database. A translation save does not change the source JSON.

- 100 pilot examples are preserved.
- 24 evaluation items are preserved.
- Stable IDs are preserved.
- Evaluation items are excluded from training exports by default.
- The training configuration remains `pilot-v1-unapproved` and `execution_authorized=false`.
- The training-data validator was not weakened.

## 7. Known limitations

- The application is local only and has no public deployment, TLS, or reverse proxy configuration.
- There is no public registration, password reset email, or two-factor authentication.
- There is no scheduled backup service. Use the backup command.
- The studio is single-process SQLite. It is designed for a small local team, not high-concurrency hosting.
- There is no browser automation test suite. The 19 tests exercise the WSGI routes, services, templates, and security checks.
- No real teacher or reviewer has tested the application yet. The manual acceptance guide must be run before claiming teacher usability.
- The interface is in English. Luganda interface translation was not requested.
- The app does not translate or call an AI model.
- Dataset approval in the studio is not training authorization.
- Formal consent, compensation, retention, licence, provenance, and release terms remain outstanding.
- The Python Translation Studio is the sole supported implementation. This report records the state of an earlier implementation snapshot; its historical test counts and browser checks are not current verification results. The local server must be restarted after Python code changes. Templates reload automatically, but Python modules do not. The home page now shows a restart message instead of a 500 when a stale server lacks the reward context.
- The reward dashboard is an estimate only. It does not process payments, store payment credentials, or record a completed payout.
- The formal compensation schedule, payment method, tax treatment, and payment records remain outstanding.
- A working-tree file `docs/teacher_passwords_and_usernames.md` appears to contain account credentials. It was not read or modified. It is now ignored by Git. Move any credentials to a password manager and delete that file before sharing or committing the repository.
- The local SQLite databases under `data/studio/` may contain saved work and account records. They are ignored by Git and should be backed up privately, not committed.

## 8. Files created or changed

Created:

- `src/translation_studio/__init__.py`
- `src/translation_studio/__main__.py`
- `src/translation_studio/app.py`
- `src/translation_studio/auth.py`
- `src/translation_studio/db.py`
- `src/translation_studio/source_import.py`
- `src/translation_studio/workflow.py`
- `src/translation_studio/templates/*.html`
- `src/translation_studio/static/studio.css`
- `src/translation_studio/static/studio.js`
- `src/translation_studio/static/favicon.svg`
- `tests/test_translation_studio.py`
- `docs/TRANSLATION-STUDIO.md`
- `reports/TRANSLATION-STUDIO-REPORT.md`
- `requirements-studio.txt`

Changed:

- `.gitignore` for the local studio database, exports, and credential-file exclusion.
- `docs/DECISIONS.md` with D-010 through D-016, including the retirement decision.
- `README.md` with the studio documentation link and status.
- `data/README.md` with the studio working-data note.

Preserved:

- `docs/BENCHMARK-SPECIFICATION.md` was not edited.
- The English source CSV and source records were not rewritten.
- Existing uncommitted benchmark and experiment-log work was not overwritten.

## 9. Final status

**Translation Studio:** WORKING LOCAL APPLICATION. READY FOR OWNER REVIEW AND A SUPERVISED MANUAL ACCEPTANCE TEST.

**Public deployment:** NOT AUTHORIZED.

**Training:** BLOCKED BY THE EXISTING DATA, PROVENANCE, CONSENT, LICENCE, REVIEW, AND AUTHORIZATION GATES.

No deployment, public access, paid service, GPU launch, model training, external dataset download, commit, or push was performed.
