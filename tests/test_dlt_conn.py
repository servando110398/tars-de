import json
from pathlib import Path

import pyodbc
from dlt.destinations.impl.mssql.configuration import MsSqlCredentials

creds = json.loads(Path("~/.config/tars-de/creds.json").expanduser().read_text())

c = MsSqlCredentials()
c.update(creds)
dsn = c.to_odbc_dsn()
print("dlt will use:", dsn.replace(c.password or "", "***"))

conn = pyodbc.connect(dsn, timeout=5)
print("connected:", conn.execute("SELECT @@SERVERNAME").fetchone()[0])
