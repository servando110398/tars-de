from tars.cli.load import load_file , load_files
from tars.core.settings import creds_path , add_connection
from faker import Faker
import pytest
import pandas as pd

Faker.seed(42)
fake = Faker()


def create_files(path,file_extension):
    pandas_export_mapping = {
    ".csv": "to_csv",
    ".xls": "to_excel",
    ".xlsx": "to_excel"
    }
    pool = ["name", "email", "job", "city", "company", "phone_number", "date_of_birth", "iban", "color_name"]
    cols = fake.random_elements(pool, length=5, unique=True)
    df = pd.DataFrame([[getattr(fake, c)() for c in cols] for _ in range(100)], columns=cols)
    file_name = fake.file_name(extension=file_extension)
    test_file = path / file_name
    method = pandas_export_mapping.get(file_extension)
    getattr(df,method)(test_file)

    return file_name


@pytest.mark.parametrize("file_extension", [".csv",".xls",".xlsx"])
def test_load_files( tmp_path,file_extension):
    "Create test files"
    create_files(tmp_path , file_extension)
    "Set up connection credentials"







def test_load_file():
    create_files(tmp_path , file_extension)





