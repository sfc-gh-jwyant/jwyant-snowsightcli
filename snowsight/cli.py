from __future__ import annotations

import argparse
import sys

from snowsight.config import load_connection_params
from snowsight.db.client import SnowflakeClient
from snowsight.app import SnowSightApp


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="snowsightcli",
        description="SnowSight — a TUI SQL client for Snowflake",
    )
    parser.add_argument(
        "-c", "--connection",
        metavar="NAME",
        default=None,
        help="Connection name from ~/.snowflake/connections.toml",
    )
    args = parser.parse_args()

    try:
        params = load_connection_params(args.connection)
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)

    client = SnowflakeClient(params)
    try:
        client.connect()
    except Exception as exc:
        print(f"Failed to connect to Snowflake: {exc}", file=sys.stderr)
        sys.exit(1)

    try:
        app = SnowSightApp(client)
        app.run()
    finally:
        client.close()


if __name__ == "__main__":
    main()
