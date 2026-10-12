import os

import click
import typer
from rich.prompt import IntPrompt

from tars.core.settings import (
    AUTH_MODES,
    PASSWORD_ENV_VAR,
    add_connection,
    add_credentials,
    config_path,
    creds_path,
    get_settings,
    load_credentials,
)
from tars.ui.display import build_connections_table, console


def init():
    "Enter a new server and database connection"
    server = typer.prompt("server ")
    database = typer.prompt("database ")
    auth = typer.prompt("authentication ", type=click.Choice(AUTH_MODES), default="windows")
    username = typer.prompt("username ") if auth == "sql" else ""
    add_connection(server,database,auth,username)
    add_credentials(server,database,auth,username)


def setup_connection():
    "Choose a connection from saved configurations"
    connections = list(get_settings(config_path).values())
    current_settings_table = build_connections_table()
    console.print(current_settings_table)
    console.print("")

    choice = IntPrompt.ask("Select a row",
                           choices=[str(i) for i in range(1, current_settings_table.row_count + 1)],
                           )
    selected = connections[choice - 1]

    if choice:
        return selected["server"] , selected["database"] , selected.get("auth", "windows") , selected.get("username", "")
    else:
        console.print("\n[red]No connection selected.[/red]")


def use_connection():
    "Choose a saved connection and make it the active one"
    server , database , auth , username = setup_connection()
    add_credentials(server,database,auth,username)
    console.print(f"Active connection: {server} / {database} ({auth})")


def resolve_credentials() -> dict:
    """Load the active connection's credentials, asking for the SQL password if it isn't set."""
    saved = get_settings(creds_path)
    if not saved:
        console.print("[red]No active connection. Run `tars init` or `tars use` first.[/red]")
        raise typer.Exit(code=1)

    password = None
    if saved.get("auth") == "sql" and not os.environ.get(PASSWORD_ENV_VAR):
        password = typer.prompt(f"password for {saved.get('username')} (or set {PASSWORD_ENV_VAR})", hide_input=True)
    return load_credentials(password)


def check_current_setup():
    "See available saved database connections"
    connections = build_connections_table()
    console.print(connections)

def check_chosen_connection():
    "Show the active connection (the password is never stored)"
    saved = get_settings(creds_path)
    if saved:
        console.print(saved)
    else:
        console.print("No credentials set up")
        console.print("Please set up  db connection first")
