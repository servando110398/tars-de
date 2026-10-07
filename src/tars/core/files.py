from pathlib import Path
from dlt.common.storages.fsspec_filesystem import FileItemDict

def setup_folders(source_folder):
    source = Path(source_folder)
    archive_dir = source / "Archive"
    failed_dir = source / "Failed"
    archive_dir.mkdir(exist_ok=True)
    failed_dir.mkdir(exist_ok=True)
    return archive_dir , failed_dir 


def _get_file_extension(file_obj: FileItemDict) -> str:
    path_str = file_obj["relative_path"]    
    # Extract extension natively without the dot, and lowercased
    # .suffix gets '.csv' -> .lstrip('.') leaves 'csv'
    ext = Path(path_str).suffix.lstrip('.').lower()
    return ext

