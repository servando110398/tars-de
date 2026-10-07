import pyodbc

conn = pyodbc.connect(
      "DRIVER={ODBC Driver 18 for SQL Server};"
      "SERVER=localhost,1433;"
      "DATABASE=test;"
      "UID=sa;"
      "PWD=***REMOVED***;"
      "TrustServerCertificate=yes",
      timeout=5,
  )
print(conn.execute("SELECT @@VERSION").fetchone()[0])
