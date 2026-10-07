# TARS

A command-line tool that loads CSV and Excel files from a folder into SQL Server.

Each file is loaded into a table in a schema you choose, then moved to an `Archive/` folder
(if it loaded) or a `Failed/` folder (if it didn't), so you can always see which files were
processed. Built with [Typer](https://typer.tiangolo.com/) and [dlt](https://dlthub.com/).

> **Status: early pilot (v0.1).** Test against a test schema with sample files before
> pointing it at real data.

## Requirements

- Windows, macOS or Linux
- [uv](https://docs.astral.sh/uv/) (it can install Python for you)
- **Microsoft ODBC Driver 18 for SQL Server**
  - Check on Windows (PowerShell): `Get-OdbcDriver | Where-Object Name -like '*SQL Server*'`
- Access to the SQL Server database, with permission to **create schemas and tables**
- Read/write access to the folder that contains the files

## Installation

From a wheel file (the usual way for now):

```bash
uv tool install path/to/tars-0.1.0-py3-none-any.whl
tars --help
```

From the source code (for development):

```bash
git clone https://github.com/servando110398/tars.git
cd tars
uv sync
uv run tars --help
```

## Setting up a connection

```bash
tars init
```

You'll be asked for:

| Prompt | Example | Notes |
|---|---|---|
| server | `MYSERVER` or `localhost` | The same server name you use in SQL Server Management Studio |
| database | `my_database` | |
| authentication | `windows` or `sql` | `windows` uses your Windows login, with no password needed |
| username | `sa` | Only asked for `sql` |

**Passwords are never saved.** For `sql` logins, set the password in an environment
variable, or tars will ask for it (hidden) when it connects:

```bash
# PowerShell
$env:TARS_SQL_PASSWORD = "your-password"

# bash
export TARS_SQL_PASSWORD='your-password'
```

Other connection commands:

| Command | What it does |
|---|---|
| `tars inspect-connections` | List saved connections |
| `tars use` | Pick a saved connection and make it the active one |
| `tars target` | Show the active connection |

Settings are stored in your user config folder, not in the project:
Windows `%APPDATA%\TARS-de`, Linux `~/.config/tars-de`.

## Loading files

### All matching files in a folder

```bash
tars load-files <folder> <extension> <table> <schema> [strategy]
```

```bash
tars load-files "C:\data\incoming" xlsx employee_detail bronze
```

### A single file

```bash
tars load <file> <table> <schema> [strategy]
```

```bash
tars load fake_ee_info.xlsx employee_detail bronze
```

### Arguments

| Argument | Meaning |
|---|---|
| `folder` / `file` | Where the files are, or one file |
| `extension` | `csv`, `xlsx` or `xls` (upper or lower case) |
| `table` | Target table. dlt converts names to snake_case: `tblEmployeeDetail` becomes `tbl_employee_detail` |
| `schema` | Target schema. Created if it doesn't exist |
| `strategy` | `append` (default): add the rows. `replace`: replace the table's contents |

## What happens to each file

```
incoming/
├── report.xlsx          ← waiting to be loaded
├── Archive/
│   └── report__20261008-143005.xlsx   ← loaded successfully
└── Failed/
    └── broken__20261008-143005.csv    ← could not be loaded
```

- Each file is loaded on its own, so one bad file doesn't stop the others.
- After loading, the file is moved to `Archive/` or `Failed/` with a timestamp added to its
  name. The folders are created automatically.
- To retry a failed file, fix it and move it back into the main folder.

## How the data lands

- **Every column is loaded as text**, exactly as written in the file: leading zeros are kept,
  nothing is guessed, and columns that are empty in a file are still created.
- Only empty cells become `NULL`. Values like `N/A` are kept as text.
- CSV files are read as UTF-8, falling back to Windows encoding (cp1252).
- dlt adds its own tracking columns (`_dlt_load_id`, `_dlt_id`) and `_dlt_*` tables.

Convert columns to their real types (dates, numbers) downstream, for example in dbt.

## Development

```bash
uv sync                      # install dependencies, including dev tools
uv run pytest                # run the tests
docker compose up -d         # local SQL Server for testing (SQL login)
uv run python tests/make_fake_ee_info.py   # regenerate the fake test file
```

Never use real data in tests or commit it. `tests/test_files/` holds fake data only.

Project layout:

```
src/tars/
├── cli/    # the commands (Typer)
├── core/   # loading logic, readers, settings
└── ui/     # tables and messages (Rich)
```

## Known limitations (v0.1)

- Failure reasons are printed, not yet saved next to failed files.
- The exit code doesn't yet signal failed files, so schedulers can't detect them.
- `load-files` currently expects to be run from inside the folder being loaded.
