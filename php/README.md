# LugandaGPT Translation Studio, PHP edition

This is the cPanel-friendly PHP edition of the Translation Studio. It uses the same SQLite database schema and the same password hashes as the Python app. It does not require Python, cron jobs, a queue, or an external service.

## What this edition covers

- login and logout
- translator dashboard and assigned work
- autosave, save, submit, and review
- reviewer dashboard with a reviewed state
- reviewer rewards at $0.10 per review
- translator rewards at $0.20 per approved translation
- administrator assignment, item inspection, return-for-correction, user creation, and reward payment clearing
- payment history visible to the translator or reviewer
- evaluation items remain separate from pilot items

The PHP edition intentionally does not run model training or inference. The validated Python tooling remains the authority for training-data export and validation.

## Requirements

- PHP 8.1 or newer
- PDO SQLite extension
- writable SQLite database file and directory

Check on the server with:

```bash
php -v
php -m
```

Look for `pdo_sqlite` and `sqlite3`.

## Upload to cPanel

1. Upload the `php/` folder to your domain document root, or to a subfolder.
2. Upload the existing `data/studio/studio.sqlite3` database somewhere writable. Prefer a location outside `public_html`.
3. Edit `php/config.php` and set `db_path` to the absolute path of the database.
4. Make sure the PHP process can write to the database file and its directory.
5. Open `https://your-domain.example/php/` or the subfolder you uploaded.

The database contains the accounts and work from the local app. Passwords are compatible because both editions use PBKDF2-HMAC-SHA256 with the same salt and iteration count.

If you start with a new empty database, create the schema with the Python app first, then copy the database. The PHP edition adds the `reward_payments` table automatically when it opens an existing database.

## Security

- Keep the database outside public web access whenever possible.
- Do not upload `docs/teacher_passwords_and_usernames.md`.
- Do not place credentials in the PHP files.
- Use HTTPS on the live domain.
- Do not use the PHP edition on a public domain until the owner has reviewed access, backups, and the deployment.
- PHP sessions and CSRF tokens protect authenticated forms.

## Local test

From the repository root:

```powershell
php -S 127.0.0.1:8088 -t php
```

Open:

```text
http://127.0.0.1:8088/
```

Set `STUDIO_DB` to a test database if you do not want to use the local default.

## Deliberate limitation

Training-data export and the Python training validator are not reimplemented in PHP. Use the Python tools for dataset preparation and training gates.
