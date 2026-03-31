from __future__ import annotations

import os
from pathlib import Path
from typing import Any


def load_connection_params(connection_name: str | None = None) -> dict[str, Any]:
    """Load Snowflake connection parameters.

    Resolution order:
    1. Named connection from ~/.snowflake/connections.toml
    2. SNOWFLAKE_* environment variables
    """
    connections_file = Path.home() / ".snowflake" / "connections.toml"

    if connections_file.exists():
        try:
            import toml

            config = toml.load(connections_file)
            name = connection_name or os.environ.get(
                "SNOWFLAKE_DEFAULT_CONNECTION_NAME", ""
            )
            if name and name in config:
                return dict(config[name])
            # If no name given but only one connection exists, use it
            if not name and len(config) == 1:
                return dict(next(iter(config.values())))
        except Exception:
            pass

    # Fall back to environment variables
    env_map = {
        "SNOWFLAKE_ACCOUNT": "account",
        "SNOWFLAKE_USER": "user",
        "SNOWFLAKE_PASSWORD": "password",
        "SNOWFLAKE_DATABASE": "database",
        "SNOWFLAKE_SCHEMA": "schema",
        "SNOWFLAKE_WAREHOUSE": "warehouse",
        "SNOWFLAKE_ROLE": "role",
        "SNOWFLAKE_PRIVATE_KEY_PATH": "private_key_path",
        "SNOWFLAKE_AUTHENTICATOR": "authenticator",
    }
    params: dict[str, Any] = {}
    for env_key, param_key in env_map.items():
        val = os.environ.get(env_key)
        if val:
            params[param_key] = val

    if params.get("account"):
        return params

    raise ValueError(
        "No Snowflake connection found.\n"
        "Options:\n"
        "  1. Add a connection to ~/.snowflake/connections.toml\n"
        "  2. Set SNOWFLAKE_ACCOUNT, SNOWFLAKE_USER, etc. env vars\n"
        "  3. Pass -c <connection_name> to specify a named connection"
    )
