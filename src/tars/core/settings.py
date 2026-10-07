import hashlib
import json
import os
from pathlib import Path

import typer
from rich import print

VERSION = "1.0.0"
APP_NAME = "TARS-de"
app_dir = Path(typer.get_app_dir(APP_NAME))
config_path: Path = Path(app_dir) / "config.json"
flows_path: Path = Path(app_dir) / "flows.json"
creds_path: Path = Path(app_dir)/ "creds.json"

def ensure_files():
    app_dir.mkdir(parents=True, exist_ok=True)
    for path in (config_path, flows_path):
        if not path.exists():
            path.write_text(json.dumps({}, indent=2))


def get_settings(path: str)-> dict:
    if os.path.exists(path) and os.path.getsize(path) > 0:
        print(path)
        with open(path, "r") as file:
            current_settings = json.load(file)
    else:
        current_settings = {}
    return current_settings


def update_json(new_entry_key:str , configs:dict , new_entry:dict,configs_path)->str:
    if new_entry_key in configs :
        print("Those settings already exists")
        raise typer.Exit()
    else:
        configs.update(new_entry)
        with open(configs_path,"w",encoding="utf-8") as file:
                json.dump(configs,file,indent=4)

        print("New connection setttings added successfully")
        return new_entry_key


AUTH_MODES = ("windows", "sql")
PASSWORD_ENV_VAR = "TARS_SQL_PASSWORD"


def add_connection(server_name , database_name , auth="windows" , username=""):
    key = hashlib.sha256(f"{server_name}:{database_name}".encode()).hexdigest()
    new_connection = {
        key :{
         "server": server_name ,
         "database": database_name ,
         "auth": auth ,
         "username": username
        }
    }

    current_content = get_settings(config_path)
    return update_json(key,current_content,new_connection,config_path)


def build_credentials(server_name , database_name , auth="windows" , username="" , password="") -> dict:
    """Build dlt mssql credentials for Windows authentication or a SQL Server login."""
    if auth not in AUTH_MODES:
        raise ValueError(f"Unknown auth mode '{auth}'. Use one of: {', '.join(AUTH_MODES)}")

    credentials = {
        "drivername": "mssql+pyodbc",
        "host": server_name,
        "database": database_name,
        "port": 1433,
        "driver": "ODBC Driver 18 for SQL Server",
        "query": {
            "Encrypt": "yes",
            "TrustServerCertificate": "yes"
        }
    }

    if auth == "windows":
        # dlt requires the fields to exist; the driver ignores them with Trusted_Connection
        credentials["username"] = ""
        credentials["password"] = ""
        credentials["query"]["Trusted_Connection"] = "yes"
    else:
        credentials["username"] = username
        credentials["password"] = password

    return credentials


def add_credentials(server_name , database_name , auth="windows" , username=""):
    """Save the active connection. The password is never written to disk."""
    saved = build_credentials(server_name , database_name , auth , username)
    saved.pop("password")
    saved["auth"] = auth

    with open(creds_path,"w",encoding="utf-8") as file:
        json.dump(saved,file,indent=4)


def load_credentials(password=None) -> dict:
    """Read the active connection and complete it for dlt.

    For SQL logins the password comes from the `password` argument or the
    TARS_SQL_PASSWORD environment variable. Returns {} if no connection is saved.
    """
    saved = get_settings(creds_path)
    if not saved:
        return {}

    # files saved before auth modes existed have no "auth": a username means a SQL login
    auth = saved.get("auth") or ("sql" if saved.get("username") else "windows")
    if auth == "sql":
        password = password or os.environ.get(PASSWORD_ENV_VAR, "")
    return build_credentials(saved["host"] , saved["database"] , auth , saved.get("username", "") , password or "")
