from tars.cli.load import load_file , load_files
from tars.cli.connections import resolve_credentials
from faker import Faker
import pytest
import pandas as pd
from unittest.mock import patch
from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL
import secrets
import random
import tars.cli.load as load_module


Faker.seed(42)
fake = Faker()

TEST_SCHEMA = "test"


def _engine_from_creds():
    """SQLAlchemy engine for the active connection in creds.json (the same one tars loads into)."""
    c = resolve_credentials()
    url = URL.create(
        c["drivername"],
        username=c.get("username") or None,
        password=c.get("password") or None,
        host=c["host"],
        port=c.get("port"),
        database=c["database"],
        query={**c.get("query", {}), "driver": c["driver"]},
    )
    return create_engine(url)


def _list_tables(conn, schema: str) -> set[str]:
    rows = conn.execute(
        text("SELECT name FROM sys.tables WHERE schema_id = SCHEMA_ID(:schema)"),
        {"schema": schema},
    )
    return set(rows.scalars().all())


def drop_test_tables(keep: set[str] = frozenset(), schema: str = TEST_SCHEMA) -> list[str]:
    """Drop every table in `schema` (incl. dlt's _dlt_* tables) except the ones in `keep`."""
    engine = _engine_from_creds()
    with engine.begin() as conn:
        tables = sorted(_list_tables(conn, schema) - set(keep))
        for table in tables:
            conn.execute(text(f"DROP TABLE {_quote(schema)}.{_quote(table)}"))
    engine.dispose()
    return tables


def _quote(name: str) -> str:
    return "[" + name.replace("]", "]]") + "]"


@pytest.fixture(scope="session", autouse=True)
def clean_test_schema(tmp_path_factory):
    """After the whole test run, drop the tables the tests created (tables that were already there are kept)."""
    engine = _engine_from_creds()
    with engine.connect() as conn:
        existing = _list_tables(conn, TEST_SCHEMA)
    engine.dispose()
    # keep dlt's local pipeline state in a throwaway folder, so it starts fresh every run
    with pytest.MonkeyPatch.context() as mp:
        mp.setenv("DLT_DATA_DIR", str(tmp_path_factory.mktemp("dlt")))
        yield
    drop_test_tables(keep=existing)


def create_file(path,file_extension:str,rows:int,is_bad_file:bool , cols:list)->str:
    pandas_export_mapping = {
    ".csv": "to_csv",
    ".xls": "to_excel",
    ".xlsx": "to_excel"
    }

    clean_ext = file_extension.lstrip('.') 
    file_name = fake.file_name(extension=clean_ext)
    test_file = path / file_name
    unique_rows = set()

    if is_bad_file:
            test_file.write_bytes(secrets.token_bytes(1000))  # random bytes: not valid text, not a valid workbook
            return file_name

    while len(unique_rows) < rows:
            row = tuple(getattr(fake, c)() for c in cols)
            unique_rows.add(row)

    df = pd.DataFrame(list(unique_rows), columns=cols)
    method = pandas_export_mapping.get(file_extension)
    if method == "to_excel":
        df.to_excel(test_file, index=False, engine="openpyxl")  # pandas can't write real .xls; the reader detects the content
    else:
        df.to_csv(test_file, index=False)
    return file_name

def create_files(tmp_path, extension, rows, good_files, bad_files):
    specs = [("good", False)] * good_files + [("bad", True)] * bad_files
    columns = generate_random_columns()
    return [ create_file(tmp_path, extension, rows, is_bad_file=is_bad,cols=columns) for _ , (label, is_bad) in enumerate(specs)]
      

SINGLE_FILE_LOAD_CASES = pytest.mark.parametrize("file_extension , write_disposition  , failed_files_count , rows , bad_file",
[
    (".csv", "append", 0, 2000,False),  
    (".csv", "replace", 0, 300,False),   
    (".csv", "merge", 0, 400,False),     
    (".xls", "append", 0, 500,False),    
    (".xls", "replace", 0, 100,False),   
    (".xls", "merge", 0, 600,False),     
    (".xlsx", "append", 0, 700,False),    
    (".xlsx", "replace", 0, 800,False),   
    (".xlsx", "merge", 0, 200,False),
    (".xlsx", "merge", 1, 200,True),
    (".csv", "merge", 1, 400,True),
    (".xls", "merge", 1, 600,True)    
])



MULTIPLE_FILE_LOAD_CASES = pytest.mark.parametrize(
    "file_extension, write_disposition, failed_files_count, files_config, table_name",
    [
        (".csv",  "append",  0, {"rows": 2000, "bad_files": 0,  "good_files": 10}, "customer_orders"),
        (".csv",  "replace", 0, {"rows": 300,  "bad_files": 0,  "good_files": 3},  "product_catalog"),
        (".csv",  "merge",   0, {"rows": 400,  "bad_files": 0,  "good_files": 5},  "inventory_levels"),
        (".xls",  "append",  0, {"rows": 500,  "bad_files": 0,  "good_files": 9},  "sales_transactions"),
        (".xls",  "replace", 0, {"rows": 100,  "bad_files": 0,  "good_files": 2},  "employee_roster"),
        (".xls",  "merge",   0, {"rows": 600,  "bad_files": 0,  "good_files": 4},  "vendor_contacts"),
        (".xlsx", "append",  0, {"rows": 700,  "bad_files": 0,  "good_files": 18}, "web_sessions"),
        (".xlsx", "replace", 0, {"rows": 800,  "bad_files": 0,  "good_files": 7},  "monthly_budget"),
        (".xlsx", "merge",   0, {"rows": 200,  "bad_files": 0,  "good_files": 11}, "shipping_routes"),

        (".csv",  "append",  3,  {"rows": 100,  "bad_files": 3,  "good_files": 4},  "invoice_lines"),
        (".csv",  "replace", 2,  {"rows": 250,  "bad_files": 2,  "good_files": 6},  "support_tickets"),
        (".csv",  "merge",   5,  {"rows": 400,  "bad_files": 5,  "good_files": 5},  "store_locations"),
        (".xls",  "append",  1,  {"rows": 1000, "bad_files": 1,  "good_files": 12}, "payment_events"),
        (".xls",  "replace", 4,  {"rows": 150,  "bad_files": 4,  "good_files": 2},  "warehouse_stock"),
        (".xls",  "merge",   6,  {"rows": 600,  "bad_files": 6,  "good_files": 3},  "marketing_leads"),
        (".xlsx", "append",  13, {"rows": 100,  "bad_files": 13, "good_files": 4},  "device_readings"),
        (".xlsx", "replace", 7,  {"rows": 800,  "bad_files": 7,  "good_files": 7},  "subscription_plans"),
        (".xlsx", "merge",   4,  {"rows": 200,  "bad_files": 4,  "good_files": 11}, "user_profiles"),

        (".csv",  "append",  0, {"rows": 1,     "bad_files": 0, "good_files": 1},  "audit_log"),
        (".xlsx", "append",  0, {"rows": 0,     "bad_files": 0, "good_files": 3},  "empty_reports"),
        (".xls",  "replace", 3, {"rows": 100,   "bad_files": 3, "good_files": 0},  "refund_requests"),
        (".csv",  "merge",   1, {"rows": 100,   "bad_files": 1, "good_files": 0},  "tax_rates"),
        (".xlsx", "merge",   0, {"rows": 50000, "bad_files": 0, "good_files": 2},  "clickstream_events"),
        (".csv",  "replace", 0, {"rows": 10,    "bad_files": 0, "good_files": 50}, "daily_snapshots"),
    ],
)

def generate_random_columns():
    pool = ["name", "email", "job", "city", "company", "phone_number", "date_of_birth", "iban", "color_name"]
    n = random.randint(1, len(pool))    
    # uuid4 first so every row is unique (a lone column like color_name runs out of values)
    return ["uuid4", *fake.random_elements(pool, length=n, unique=True)]


@SINGLE_FILE_LOAD_CASES
def test_load_file(tmp_path,monkeypatch,file_extension,write_disposition,failed_files_count,rows,bad_file):
    "Create test files"
    columns = generate_random_columns()
    file_name = create_file(tmp_path , file_extension,rows,bad_file,cols=columns)
    "load file (load_file looks the file name up in the current folder)"
    monkeypatch.chdir(tmp_path)
    failed_files , total_rows = load_file(ctx=None, file_name=file_name,table_name=file_name,schema_name=TEST_SCHEMA,load_strategy= write_disposition)

    assert failed_files == failed_files_count
    assert total_rows == (0 if bad_file else rows)



@MULTIPLE_FILE_LOAD_CASES
def test_load_files( tmp_path,file_extension ,write_disposition , failed_files_count , files_config , table_name):
    rows = files_config["rows"]
    good_files  = files_config["good_files"]
    bad_files = files_config["bad_files"]

    create_files(tmp_path , file_extension,rows,good_files,bad_files)

    total_files = good_files + bad_files

    # load_files calls _process_file once per file (it never calls load_file)
    with patch.object(load_module, "_process_file", wraps=load_module._process_file) as spy:
        processed , failed = load_module.load_files(ctx=None, source_folder=str(tmp_path), file_extension=file_extension.lstrip("."),table_name=table_name,schema_name=TEST_SCHEMA,load_strategy= write_disposition )

    assert spy.call_count == total_files
    assert processed == good_files
    assert failed == bad_files








