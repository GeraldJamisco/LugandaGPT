"""Command line setup and local server for the Translation Studio."""

import argparse
import getpass
import json
import sqlite3
import sys
from contextlib import closing
from pathlib import Path

from wsgiref.simple_server import make_server

from . import auth
from .app import StudioApp
from .db import connect, default_db_path, init_db, list_users
from .source_import import import_source

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SOURCE = PROJECT_ROOT / "data" / "source" / "pilot-v1" / "source_draft.json"


def _print(value):
    print(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True))


def cmd_init_db(args):
    with closing(connect(args.db)) as connection:
        init_db(connection)
        print(f"Initialized Translation Studio database: {Path(args.db or default_db_path()).resolve()}")
    return 0


def cmd_create_user(args):
    with closing(connect(args.db)) as connection:
        init_db(connection)
        password = getpass.getpass("Password: ")
        confirm = getpass.getpass("Confirm password: ")
        if password != confirm:
            print("ERROR: Passwords do not match.", file=sys.stderr)
            return 2
        try:
            user_id, public_id = auth.create_user(
                connection,
                args.username,
                args.display_name,
                args.role,
                password,
                actor_id=None,
            )
        except auth.AuthError as error:
            print(f"ERROR: {error}", file=sys.stderr)
            return 2
        _print(
            {
                "status": "user_created",
                "user_id": user_id,
                "username": args.username,
                "display_name": args.display_name,
                "role": args.role,
                "public_id": public_id,
            }
        )
    return 0


def cmd_import_source(args):
    with closing(connect(args.db)) as connection:
        init_db(connection)
        result = import_source(connection, args.source, actor_id=None)
        _print(result)
    return 0


def cmd_serve(args):
    db_path = Path(args.db or default_db_path())
    if not db_path.exists():
        print(
            f"ERROR: Database not found: {db_path}. Run init-db and create-user first.",
            file=sys.stderr,
        )
        return 2
    app = StudioApp(db_path=db_path, source_path=args.source)
    with make_server(args.host, args.port, app) as server:
        print(f"LugandaGPT Translation Studio: http://{args.host}:{args.port}/")
        print("Press Ctrl+C to stop. This server is for local use only.")
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            print("\nStopping Translation Studio.")
    return 0


def cmd_backup(args):
    source_path = Path(args.db or default_db_path())
    if not source_path.exists():
        print(f"ERROR: Database not found: {source_path}", file=sys.stderr)
        return 2
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    source = sqlite3.connect(str(source_path))
    destination = sqlite3.connect(str(output))
    try:
        source.backup(destination)
    finally:
        destination.close()
        source.close()
    print(f"Backup written: {output.resolve()}")
    return 0


def cmd_users(args):
    with closing(connect(args.db)) as connection:
        init_db(connection)
        _print(
            [
                {
                    "id": row["id"],
                    "username": row["username"],
                    "display_name": row["display_name"],
                    "public_id": row["public_id"],
                    "role": row["role"],
                    "active": bool(row["active"]),
                }
                for row in list_users(connection)
            ]
        )
    return 0


def build_parser():
    parser = argparse.ArgumentParser(
        prog="python -m translation_studio",
        description="Local LugandaGPT Translation Studio.",
    )
    parser.add_argument("--db", help="SQLite database path. Defaults to STUDIO_DB or data/studio/studio.sqlite3.")
    sub = parser.add_subparsers(dest="command", required=True)

    init = sub.add_parser("init-db", help="create the local database tables")
    init.set_defaults(handler=cmd_init_db)

    create_user = sub.add_parser("create-user", help="create an administrator, translator, or reviewer")
    create_user.add_argument("--username", required=True)
    create_user.add_argument("--display-name", required=True)
    create_user.add_argument("--role", required=True, choices=("admin", "translator", "reviewer"))
    create_user.set_defaults(handler=cmd_create_user)

    import_source_cmd = sub.add_parser("import-source", help="import and validate the canonical English source draft")
    import_source_cmd.add_argument("--source", default=str(DEFAULT_SOURCE))
    import_source_cmd.set_defaults(handler=cmd_import_source)

    serve = sub.add_parser("serve", help="start the local web server")
    serve.add_argument("--host", default="127.0.0.1")
    serve.add_argument("--port", type=int, default=8765)
    serve.add_argument("--source", default=str(DEFAULT_SOURCE))
    serve.set_defaults(handler=cmd_serve)

    backup = sub.add_parser("backup", help="copy the local database for backup")
    backup.add_argument("--output", required=True)
    backup.set_defaults(handler=cmd_backup)

    users = sub.add_parser("users", help="list local accounts")
    users.set_defaults(handler=cmd_users)
    return parser


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.handler(args)
    except (auth.AuthError, ValueError, OSError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
