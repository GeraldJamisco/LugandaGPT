# LugandaGPT Translation Studio deployment package

This folder is the minimal PythonAnywhere deployment package for the Python Translation Studio. It contains only the runtime files required by the audited import closure. It does not contain a database, credentials, datasets, model weights, training code, or generated exports.

## Package layout

```text
deployment/translation-studio/
  wsgi.py
  requirements.txt
  README.md
  .gitignore
  data/
    studio/
      .gitkeep
    exports/
      .gitkeep
  src/
    translation_studio/
      __init__.py
      __main__.py
      app.py
      auth.py
      db.py
      reward_rules.py
      source_import.py
      workflow.py
      templates/
        base.html
        login.html
        home.html
        dashboard.html
        work_item.html
        progress.html
        review_dashboard.html
        review_item.html
        rewards.html
        reward_summary_card.html
        admin.html
        admin_users.html
        admin_assign.html
        admin_items.html
        admin_item.html
        admin_export.html
        admin_payments.html
        admin_audit.html
        error.html
      static/
        Background_img.png
        studio.css
        studio.js
        favicon.svg
    training/
      __init__.py
      constants.py
      errors.py
      pilot.py
      source_pilot.py
      storage.py
```

`src/training` is present because the studio imports `training.constants`, `training.errors`, `training.pilot`, `training.source_pilot`, and `training.storage`. None of those modules import PyTorch, Transformers, TRL, or any other model dependency.

## What is intentionally excluded

- SQLite databases, WAL files, SHM files, and backups
- Teacher credentials, passwords, tokens, `.env` files, and keys
- Model checkpoints, LoRA adapters, and downloaded weights
- The training stack and `requirements-training.txt`
- Training or evaluation datasets, including the canonical English source draft
- Generated exports and reports
- Benchmark, reporter, and test code
- Virtual environments and Python bytecode

## Updating the existing PythonAnywhere application

Extract the release ZIP into a staging directory. For the existing application at `/home/Geraldjamisco/lugandagpt`, copy only `wsgi.py`, `requirements.txt`, and `src/` from staging into that application root. Do not extract the ZIP over the live directory and do not copy its `data/` placeholders. Keep the existing `data/studio/`, `data/exports/`, and `.venv/` paths intact. The ZIP has no database or virtual environment.

The packaged `wsgi.py` uses paths relative to its own location. At the existing application root, its database path is `/home/Geraldjamisco/lugandagpt/data/studio/studio.sqlite3` and its export path is `/home/Geraldjamisco/lugandagpt/data/exports/`. This selective copy leaves those paths and their contents in place. Keep the current PythonAnywhere Web tab WSGI configuration pointed at the existing application root, and do not replace that configuration file. The remote WSGI configuration and database were not inspected as part of this local package audit.

This release adds an earnings ledger and an integer cents field for payment records. After copying the code, stop the web app and make a private SQLite backup before migrating. With the existing virtual environment activated, run:

```bash
export PYTHONPATH=/home/Geraldjamisco/lugandagpt/src
python -m translation_studio \
  --db /home/Geraldjamisco/lugandagpt/data/studio/studio.sqlite3 \
  backup \
  --output /home/Geraldjamisco/lugandagpt/data/backups/studio-pre-reward-migration-2026-10-25.sqlite3
```

Check the backup with `sqlite3 <backup-path> 'PRAGMA integrity_check;'`. First migrate a private copy of the production database and reconcile historical rewards as described below. Only after that review passes, keep the web app stopped and run against the live path:

```bash
python -m translation_studio \
  --db /home/Geraldjamisco/lugandagpt/data/studio/studio.sqlite3 \
  init-db
```

Check the live file with `sqlite3 /home/Geraldjamisco/lugandagpt/data/studio/studio.sqlite3 'PRAGMA integrity_check;'` before reloading. The migration is additive and does not create payments. It backfills reviews with durable reviewer, assignment, and version records, plus the earliest translation version per item whose durable review and resolution rows establish approval and whose assigned reviewers all reviewed that version. It cannot classify versions with missing snapshots, incomplete review coverage, or conflicting history. An earlier version can still earn after a later correction, so review the production history for missing version or review rows before migration. Existing payment rows are retained and converted to integer cents; their recorded paid totals remain in payment history. If an old qualifying translation cannot be reconstructed, accrued and outstanding totals will be understated until it is reconciled. If the migration reports an invalid legacy payment amount or an integrity error, leave the web app stopped and restore the private backup before retrying after investigation. Since the PythonAnywhere database was not inspected for this release, do not run the migration against it until a private copy has been migrated and the resulting earnings have been reconciled against the historical translations, reviews, assignments, resolutions, and payments. Resolve any missing eligible contributions before applying the migration to the live file.

Keep the current Web tab WSGI path and Python version. Reload the web app after the migration and code files have been applied. The application serves `/static/Background_img.png` through its WSGI static handler; no static mapping is required. If a static mapping is already configured, it must point to this package's `src/translation_studio/static/` directory.

## Security notes

- Use HTTPS on the live domain.
- Do not upload `docs/teacher_passwords_and_usernames.md` or any credential file.
- Do not store passwords, tokens, or API keys in `wsgi.py`, the README, or shell scripts.
- Keep the database and exports outside public static mappings.
- Review the account list and remove test accounts before public use.
- Training and model execution are not part of this package. The Python training tools remain in the main repository.

## Verification performed on this package

The package was checked without connecting to the original database:

- all deployed Python modules import successfully
- `wsgi.application` is callable
- no heavy training modules are imported by the web app
- all Jinja2 templates parse
- static assets are present
- no SQLite, WAL/SHM, credential, environment, model, dataset, or generated export files are present
- `requirements.txt` contains only the audited pins

## Remaining risks

- The package has not been executed against PythonAnywhere itself.
- Python 3.11 compatibility is expected from the source audit but should be confirmed by running the test suite once in the PythonAnywhere environment.
- SQLite WAL mode requires a writable filesystem. Confirm that PythonAnywhere can create the `-wal` and `-shm` files beside the database.
- The source dataset is excluded by design. Source import requires an external path, and the admin import action will not work until that path is set.
- This package does not include a database. A fresh database has accounts but no examples until the source import is run.
