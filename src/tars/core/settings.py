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


def add_connection(server_name , database_name):
    key = hashlib.sha256(f"{server_name}:{database_name}".encode()).hexdigest()
    new_connection = {
        key :{
         "server": server_name ,
         "database": database_name
        }
    }

    current_content = get_settings(config_path)
    return update_json(key,current_content,new_connection,config_path)

def add_credentials(server_name , database_name):
    mssql_credentials = {
                        "drivername": "mssql+pyodbc",
                        "host": server_name,
                        "database": database_name,
                        "username": "",  # Set as empty string to pass dlt validation
                        "password": "***REMOVED***",  # Set as empty string to pass dlt validation
                        "port": 1433,
                        "driver": "ODBC Driver 18 for SQL Server",
                        "query": {
                                "Trusted_Connection": "yes",
                                 "TrustServerCertificate": "yes"
                                }
                        }
    with open(creds_path,"w",encoding="utf-8") as file:
                    json.dump(mssql_credentials,file,indent=4)
    
    