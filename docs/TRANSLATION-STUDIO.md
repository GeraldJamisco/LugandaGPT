# LugandaGPT Translation Studio

**Status:** local development application. Not deployed, not public, and not a substitute for the existing training-data gate.

The Translation Studio is a private web application for native Luganda speakers to translate the project's English source examples and for a second speaker to review those translations. The interface is in plain English. It does not ask teachers to edit CSV, JSON, or training splits.

## Access model

The default server binds to `127.0.0.1`, which means it is reachable only from the computer running the server.

The application can be started with `--host 0.0.0.0` for a trusted local network, but that is optional and must be treated as an administrative action. If the server is bound to a local network address:

- use only a trusted private network;
- do not forward a port or expose it through a tunnel;
- do not place it behind a public hostname;
- stop the server when the work session ends.

The application has no public registration, no external authentication provider, no analytics, and no external AI API. It uses a local SQLite database and local static files. It does not send teacher content to a third party.

The local server is HTTP, not HTTPS. Do not use it over an untrusted network. Public deployment requires separate owner approval and a security review.

## Stack

- Python 3.11 or newer for the local app.
- Python standard library WSGI server.
- SQLite database.
- Jinja2 templates. `Jinja2==3.1.6` is listed in `requirements-studio.txt` and is already present in the local environment.
- No new database service, no cloud service, and no machine-learning inference.

## Windows setup

Open PowerShell in the repository root:

```powershell
cd C:\xampp\htdocs\LugandaGPT
$env:PYTHONPATH = "src"
```

Create the local database:

```powershell
.\.venv-gemma\Scripts\python.exe -m translation_studio init-db
```

Create the first administrator. The command prompts for the password. It does not accept a password on the command line and does not contain a hardcoded credential.

```powershell
.\.venv-gemma\Scripts\python.exe -m translation_studio create-user `
  --username owner `
  --display-name "Project Owner" `
  --role admin
```

Create a translator and a reviewer the same way:

```powershell
.\.venv-gemma\Scripts\python.exe -m translation_studio create-user `
  --username teacher1 `
  --display-name "Teacher One" `
  --role translator

.\.venv-gemma\Scripts\python.exe -m translation_studio create-user `
  --username reviewer1 `
  --display-name "Teacher Two" `
  --role reviewer
```

Import the validated English source draft:

```powershell
.\.venv-gemma\Scripts\python.exe -m translation_studio import-source
```

Start the local server:

```powershell
.\.venv-gemma\Scripts\python.exe -m translation_studio serve
```

Open this address in a browser on the same computer:

```text
http://127.0.0.1:8765/
```

The default database is `data/studio/studio.sqlite3`. It is excluded from Git by `.gitignore`. Do not commit the database, exports, or passwords.

## Start with another database

Use a separate database for a manual acceptance test:

```powershell
.\.venv-gemma\Scripts\python.exe -m translation_studio `
  --db data/studio/acceptance.sqlite3 init-db

.\.venv-gemma\Scripts\python.exe -m translation_studio `
  --db data/studio/acceptance.sqlite3 create-user `
  --username test-owner --display-name "Test Owner" --role admin
```

Start the server with that database:

```powershell
.\.venv-gemma\Scripts\python.exe -m translation_studio `
  --db data/studio/acceptance.sqlite3 serve
```

The source import uses the canonical file `data/source/pilot-v1/source_draft.json` and validates its counts, split integrity, statuses, provenance, and checksums before inserting anything.

## Administrator workflow

1. Open `/admin`.
2. Import the source examples. The import inserts 124 records on a fresh database. Reimport skips records that have not changed and reports conflicts instead of overwriting stored source.
3. Create translator and reviewer accounts in `/admin/users`.
4. Assign translation work in `/admin/assign`. The same example cannot have two translators.
5. Wait for translations to be submitted.
6. Assign review work to a second speaker. A translator cannot be assigned to review their own translation.
7. Inspect `/admin/items` for status, disagreements, review history, submitted versions, and audit history.
8. Resolve a disagreement from the administrator item page.
9. Record dataset preparation fields separately: collaboration and consent status, licence status, privacy check, contamination notes, and validation checks.
10. Approve an item for dataset preparation only after the translation is reviewed and the dataset fields are complete.
11. Export from `/admin/export`.

The studio CSV is an inspection and handoff file. The training-preparation JSONL export includes only pilot items marked `approved_for_dataset`, excludes evaluation items, and runs each record through the existing `validate_pilot_record` gate. The export still does not authorize training.

## Teacher workflow

1. Sign in with the account created by the administrator.
2. Open **My translation work**.
3. Choose an example. The page shows the English request, background passage, earlier conversation turns, response criteria, and constraints.
4. Write the Luganda background passage when one is present. It is required, not optional. Then translate the earlier turns, translate the user's final message, and write the assistant's reply.
5. The page saves a draft automatically. The save indicator shows **Saving**, **Saved at a time**, or an autosave failure. **Save progress** is always available.
6. If the browser loses the saved request, a local recovery banner may offer the last text stored on that device. Restore it and save again.
7. **Mark as ready for review** requires the required Luganda fields, including the background passage when the example has one. A saved draft is not submitted.
8. After submission, the translation is locked until a reviewer returns it for correction. The translator can see review feedback.
9. Open **Rewards** to see the estimated approved-work reward. The estimate uses $0.20 per approved translation and a $2 reward at every 10 approved translations. It is not a payment record.

The teacher view does not show `P-` or `E-` identifiers, training splits, JSON, CSV, or dataset approval controls.

A missing background passage is a missing required part of the example. The reviewer cannot approve it, and an administrator can return the submitted work for correction. The translated passage is included in the user message of the training-preparation record.

## Reviewer workflow

1. Sign in as a reviewer.
2. Open **Review work**.
3. Open an assigned translation.
4. Compare the English source, earlier conversation, expected-result notes, and the full Luganda translation.
5. Choose **Approved**, **Needs revision**, or **Cannot assess yet**.
6. Explain a revision request or a cannot-assess decision. Suggested corrections are optional.
7. Submit the review.

The reviewer cannot edit the translator's text. Reviews are stored as separate records. A translator cannot review their own work. When two reviewers disagree, the item is marked for owner resolution instead of being treated as approved.

## Status model

These states are deliberately separate:

| Area | Values |
|---|---|
| Translation | Not started, In progress, Ready for review, Returned for correction, Needs owner resolution, Reviewed |
| Review | Approved, Needs revision, Cannot assess yet |
| Collaboration and consent | Not recorded, Owner reported, Recorded |
| Licence | Unresolved, Recorded |
| Dataset preparation | Not ready, Approved for dataset preparation |

A review approval is not training authorization. A dataset approval is not a training run. Formal consent, licence, provenance, and retention records remain a separate gate.

## Rewards

The Project Director has set a motivational reward of **$2 for every 10 approved translations**. The studio displays this as an estimate:

- Each approved translation adds $0.20.
- Every 10 approved translations reaches a $2 reward.
- Only translations approved by review count.
- Drafts, returned work, disputed work, and unapproved work do not count.
- If a review approval is later reversed, the estimate can go down.

Translators see the estimate on the welcome dashboard, the progress page, and the **Rewards** page. Administrators see estimated rewards by translator in the administration dashboard.

Reviewers earn **$0.10 for each completed review**. Reviewer accounts see total earned, total cleared, and the available amount on the reviewer dashboard and Rewards page.

An administrator can mark a payment as cleared on the administration payments page. That creates a payment record, reduces the available balance, and leaves the work history intact. New approved translations or reviews then add to a fresh available balance. The user sees a **Payment cleared** entry and the payment date and reference.

This is not a payment-processing feature. The local app does not move money, store payment credentials, or prove that a payment was transferred. The owner must complete the actual payment outside the app and record a note or reference. Formal compensation terms, tax treatment, and payment records remain the owner's responsibility.

## Supported implementation

`src/translation_studio/` is the sole supported Translation Studio implementation. For PythonAnywhere package contents and manual deployment instructions, see [`deployment/translation-studio/README.md`](../deployment/translation-studio/README.md).

## Security

- Passwords are hashed with PBKDF2-HMAC-SHA256 and a random salt.
- Session tokens are random, stored hashed in SQLite, and sent in an HttpOnly, SameSite=Lax cookie.
- Authenticated forms include a CSRF token checked on the server.
- Roles are checked on the server for every protected route.
- SQL statements use parameters.
- Jinja2 autoescaping is enabled. Teacher text is never rendered as HTML.
- The app sends security headers, including a restrictive content security policy.
- There is no public registration, no password reset email, and no external login provider.
- The local HTTP server does not set the cookie `Secure` flag. Do not expose it publicly or use it over an untrusted network.
- Do not keep plaintext account credentials in the repository. If a credentials file exists, move it to a password manager and delete it. The local `.gitignore` excludes `docs/teacher_passwords_and_usernames.md` as a safety measure, but that file should still be removed from the working tree.

## Backups

Create a consistent SQLite backup while the server is running:

```powershell
$env:PYTHONPATH = "src"
.\.venv-gemma\Scripts\python.exe -m translation_studio backup `
  --output data/studio/backups/studio-2026-10-23.sqlite3
```

Keep backups outside Git. A backup contains translations, reviews, accounts, and audit history. Treat it as private project data.

## Restarting after code changes

Jinja templates reload automatically, but the Python server process does not. After changing `app.py`, `workflow.py`, `auth.py`, or other Python files, stop the server with `Ctrl+C` and start it again:

```powershell
$env:PYTHONPATH = "src"
.\.venv-gemma\Scripts\python.exe -m translation_studio serve
```

If the home page says the reward dashboard is not loaded, or shows a request error after a code update, restart the server. The home page now shows a clear restart message instead of a blank 500 page. The error page also provides a working sign-out button.

## Manual acceptance test for a non-technical owner

Use a separate acceptance database as shown above.

1. Create a test administrator, translator, and reviewer.
2. Sign in as the test administrator.
3. Import the source examples.
4. Assign one pilot example to the test translator.
5. Sign out and sign in as the translator.
6. Open the assigned example. Write clearly marked test text, for example `ACCEPTANCE TEST - not a real translation`.
7. Save the draft, reload the page, and confirm the text is still there.
8. Submit the example for review.
9. Sign in as the administrator and assign the review to the test reviewer.
10. Sign in as the reviewer. Open the review, choose **Needs revision**, explain the decision, and submit.
11. Sign in as the translator and confirm the feedback appears.
12. Sign in as the administrator and inspect the item and audit history.
13. Delete the acceptance database when finished.

Do not use real teacher work for an acceptance test, and do not mark an item as reviewed unless a real reviewer made that decision.

## Known limitations

- The app is not deployed and has no TLS termination.
- There is no public registration, email delivery, password reset, or two-factor authentication.
- There is no scheduled backup service. Use the backup command.
- There is no browser automation suite. Tests cover the WSGI routes, services, templates, and security checks.
- There is no real teacher usability testing yet. The screen text and layout are a first implementation.
- The app does not call an AI model or translate text.
- Review and dataset approval do not replace provenance, consent, licence, retention, or training authorization.

## Verification

Run the studio tests:

```powershell
$env:PYTHONPATH = "src"
.\.venv-gemma\Scripts\python.exe -m unittest tests.test_translation_studio -v
```

Run the existing repository suite:

```powershell
.\.venv-gemma\Scripts\python.exe -m unittest discover -s tests -t .
```
