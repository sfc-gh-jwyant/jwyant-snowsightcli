# SnowSight CLI

A terminal UI (TUI) SQL client for Snowflake, built with [Textual](https://textual.textualize.io/) and the Snowflake Python Connector.

```
┌────────────────────────────────┬──────────────────────────────────────────────┐
│        Snowflake               │  DB: MYDB  |  Schema: PUBLIC  |  WH: XS      │
│   SnowSight CLI                │  Run Query   Run All ▶                        │
│                                │                                                │
│  ▼ MYDB                        │  SELECT * FROM orders LIMIT 100;              │
│    ▼ PUBLIC                    │                                                │
│      ▶ Tables                  ├──────────────────────────────────────────────┤
│      ▶ Views                   │  ORDER_ID  CUSTOMER_ID  AMOUNT   STATUS       │
│      ▶ Procedures              │  1001       42          199.99   SHIPPED       │
│      ...                       │  1002       17           49.00   PENDING       │
│                                │                                                │
│ [JW]  John Wyant               │  2 rows  |  0.143s                            │
└────────────────────────────────┴──────────────────────────────────────────────┘
```

## Features

- **Object explorer** — lazy-loading tree: Databases → Schemas → Tables, Views, Dynamic Tables, Procedures, Functions, Stages, Streams, Tasks, Sequences
- **SQL editor** — syntax-highlighted editor with statement-at-cursor execution
- **Run Query** — executes the selected text, or the single statement under the cursor (`;`-delimited)
- **Run All** — executes the entire editor contents
- **Paginated results** — up to 50,000 rows fetched, displayed 500 rows per page (`[` / `]` to navigate)
- **Live status bar** — connection info, query state, row count, elapsed time
- **Context tracking** — `USE DATABASE/SCHEMA/WAREHOUSE/ROLE` changes are reflected automatically
- **Cancel support** — press `Escape` to cancel a running query
- **Snowflake branding** — `#29B5E8` blue palette, dark backgrounds

## Requirements

- Python 3.11+
- [uv](https://docs.astral.sh/uv/) (dependency manager)
- A Snowflake account with connection details in `~/.snowflake/connections.toml`

## Installation

```bash
git clone https://github.com/sfc-gh-jwyant/jwyant-snowsightcli.git
cd jwyant-snowsightcli
uv sync
```

## Configuration

Connection parameters are loaded from `~/.snowflake/connections.toml`. Example:

```toml
[myconnection]
account   = "myaccount.us-east-1"
user      = "myuser"
password  = "..."        # or use authenticator below
# authenticator = "externalbrowser"
warehouse = "COMPUTE_WH"
database  = "MYDB"
schema    = "PUBLIC"
role      = "SYSADMIN"
```

Alternatively, set environment variables:

```bash
export SNOWFLAKE_ACCOUNT=myaccount.us-east-1
export SNOWFLAKE_USER=myuser
export SNOWFLAKE_PASSWORD=...
export SNOWFLAKE_WAREHOUSE=COMPUTE_WH
```

## Usage

```bash
# Use the default connection from connections.toml
uv run snowsightcli

# Specify a named connection
uv run snowsightcli -c myconnection
```

Or after `uv sync`, the script is available directly:

```bash
.venv/bin/snowsightcli -c myconnection
```

## Key Bindings

| Key | Action |
|-----|--------|
| `F5` / `Ctrl+Enter` | Run Query (selection or statement at cursor) |
| `[` / `]` | Previous / next results page |
| `Ctrl+L` | Focus object explorer |
| `Ctrl+E` | Focus SQL editor |
| `Ctrl+R` | Focus results table |
| `Escape` | Cancel running query |
| `Ctrl+C` | Quit |

## Project Structure

```
snowsight-cli/
├── snowflake_logo.ansi          # ANSI colour logo for the header
├── pyproject.toml               # Project metadata and dependencies (uv / hatchling)
├── uv.lock                      # Locked dependency graph
└── snowsight/
    ├── app.py                   # Main Textual App
    ├── cli.py                   # argparse entry point (snowsightcli)
    ├── config.py                # Connection loader (~/.snowflake/connections.toml)
    ├── db/
    │   └── client.py            # SnowflakeClient — thread-safe query execution
    ├── styles/
    │   └── app.tcss             # Snowflake-branded Textual CSS
    └── widgets/
        ├── editor_pane.py       # SQL editor + run buttons
        ├── explorer.py          # Lazy-loading object tree
        ├── results_pane.py      # Paginated DataTable
        └── user_badge.py        # Initials badge + display name
```

## Development

```bash
# Install dev environment
uv sync

# Run directly
uv run snowsightcli -c myconnection

# Textual devtools (live CSS reload, layout inspector)
uv run textual run --dev snowsight/app.py
```

## License

MIT
