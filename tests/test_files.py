from tars.core.files import setup_folders ,  _get_file_extension
import pytest
from dlt.common.storages.fsspec_filesystem import FileItemDict
import orjson
import dlt
import shutil
from dlt.sources.filesystem import filesystem  
from pathlib import Path


def make_file_item(relative_path: str) -> FileItemDict:
    """Build a FileItemDict with only the field _get_file_extension reads."""
    return FileItemDict({"relative_path": relative_path})
  
@pytest.mark.parametrize(
    ("relative_path", "expected"),
    [
        # the supported types
        ("sales.csv", "csv"),
        ("sales.xlsx", "xlsx"),
        ("sales.xls", "xls"),
        # case is normalised
        ("SALES.CSV", "csv"),
        ("Sales.XlSx", "xlsx"),
        # only the last suffix counts
        ("report.final.xlsx", "xlsx"),
        ("archive.csv.xls", "xls"),
        # folders in the path are ignored
        ("2024/q1/sales.csv", "csv"),
        ("nested.dir/sales.xlsx", "xlsx"),
    ],
)
def test_get_file_extension(relative_path, expected):
    assert _get_file_extension(make_file_item(relative_path)) == expected


def test_setup_folders():
    path = "/workspaces/tars/tests"
    archive , failed = setup_folders(path)
    assert archive == Path("/workspaces/tars/tests/Archive")
    assert failed == Path("/workspaces/tars/tests/Failed")
    shutil.rmtree(archive)
    shutil.rmtree(failed)




