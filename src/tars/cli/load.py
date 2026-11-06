import shutil
from datetime import datetime
from pathlib import Path
from typing import Annotated
import dlt
from openpyxl import reader
from urllib.parse import urlparse
import typer
from dlt.destinations import mssql
from dlt.sources.filesystem import filesystem 
from rich import print
from tars.cli.connections import resolve_credentials
from tars.core.files import setup_folders , _get_file_extension
from tars.core.readers import read_excel , read_csv
from dlt.common.storages.fsspec_filesystem import FileItemDict
import os 
from dlt.pipeline.exceptions import PipelineStepFailed
from dlt.common.pipeline import LoadInfo

""" 
Build a single function for procesisng files that is reused by load_files and load_file. 

"""

strategy ={"csv":read_csv, "xls":read_excel , "xlsx":read_excel,"txt":read_csv}

def load_files(
        ctx:typer.Context,
        source_folder:Annotated[str,typer.Argument(help="Path to the folder containing the files to be loaded.",  exists=True, file_okay=False, dir_okay=True, readable=True)] ,
        file_extension:Annotated[str,typer.Argument(help="File extension used to identify the files to be loaded.")],
        table_name : Annotated[str,typer.Argument(help="Name of the target table where the files will be loaded.")] ,
        schema_name:Annotated[str,typer.Argument(help="Name of the schema where the files will be loaded.")],
        load_strategy:Annotated[str,typer.Argument(help="Loading strategy to be used")] = "append",
        primary_key:Annotated[list[str],typer.Option(help="Primary key for merge strategy")] = []
        
        ):
    """
    Load all files with the selected extension from the source folder into the target schema and table using the selected load strategy.
    """

    _ensure_primary_key(load_strategy,primary_key)
    

    creds = resolve_credentials()
    pipeline = dlt.pipeline(
            pipeline_name="tars_file_loader",
            destination=mssql(credentials=creds, naming_convention="direct"),
            dataset_name=schema_name  
        )

    folder = source_folder

    files = filesystem(
        bucket_url=folder,
        file_glob=("*."+file_extension)  
        )


    files_processed = 0
    failed_files = 0
    total_rows = 0

  
    total_files = len(list(files))
    print(f"Folder: {folder}")
    print(f"Extension: {file_extension}")
    print(f"Files found: {total_files}")


    if total_files == 0:
        print("No files found in folder")
        return


    for file in list(files):  # snapshot the folder before moving anything
        print(f"Processing file : {file['file_name']} ...")
        load_info = _process_file(file=file, table_name=table_name, load_strategy=load_strategy,
                                  pipeline=pipeline, primary_key=primary_key)

        if load_info.has_failed_jobs:
            failed_files += 1
        else:
            row_counts = pipeline.last_trace.last_normalize_info.row_counts
            rows = sum(n for table, n in row_counts.items() if not table.startswith("_dlt"))
            total_rows += rows
            files_processed += 1


    pipeline.abort_packages()
    print(f"Processed files: {files_processed}")
    print(f"Total rows ingested: {total_rows}")
    print(f"Failed files: {failed_files}")
    return files_processed , failed_files

def load_file(ctx:typer.Context,
              file_path: Annotated[str,typer.Argument(help="Path or name of file to be loaded")],
              table_name: Annotated[str,typer.Argument(help="Name of the target table where the files will be loaded.")],
              schema_name:Annotated[str,typer.Argument(help="Name of the schema where the file will be loaded.")],
              load_strategy:Annotated[str,typer.Argument(help="Loading strategy to be used")] = "append",
              primary_key:Annotated[list[str],typer.Option(help="Primary key for merge strategy")] = []
              ):
    """
    Load file into the specified target schema and table using the selected load strategy.
    """

    _ensure_primary_key(load_strategy,primary_key)
    
    row_counts = 0
    total_rows = 0
    failed_files = 0


    creds = resolve_credentials()
    pipeline = dlt.pipeline(
            pipeline_name="tars_file_loader",
            destination=mssql(credentials=creds, naming_convention="direct"),
            dataset_name=schema_name  # This will map to a schema in SQL Server
        )

    absolute_path = os.path.abspath(file_path)
    bucket_url = os.path.dirname(os.path.abspath(absolute_path))
    strict_glob = os.path.basename(absolute_path)    
    file_resource = filesystem(bucket_url=bucket_url, file_glob=strict_glob)
    file_obj = next(iter(file_resource))

    print(f"Processing file : {strict_glob} ...")
    load_info = _process_file(file=file_obj, table_name=table_name, load_strategy=load_strategy, pipeline=pipeline,primary_key=primary_key)

    if load_info.has_failed_jobs:
        failed_files += 1
        # A real LoadInfo has no .errors; its str() lists the failed jobs instead
        message = f"[red]:x: load failed![/red] \n {getattr(load_info, 'errors', load_info)}"
    else:

        row_counts = pipeline.last_trace.last_normalize_info.row_counts
        total_rows = sum(n for table, n in row_counts.items() if not table.startswith("_dlt"))

        trace = pipeline.last_trace
        duration = trace.finished_at - trace.started_at
        seconds = duration.total_seconds()
        message = f"[green]:white_check_mark: Done. File {strict_glob} has been processed. \n{total_rows} rows ingested in {seconds:.2f} seconds[/green]"

    pipeline.abort_packages()
    print(message)

    return failed_files , total_rows  


def _process_file(file: FileItemDict,table_name,load_strategy,pipeline ,primary_key):
    """
    Process a single file and return the load info object.
    """

    file_extension = _get_file_extension(file)
    load_dt_tm = datetime.now()  # one timestamp per load, stamped on every row
    reader = (
        ([file] | strategy[file_extension]())
        .with_name(table_name)
        .add_map(lambda row: {**row, "loadDtTm": load_dt_tm,"FileName":file["file_name"]})
    )
    file_path = Path(file.local_file_path)
    file_name = Path(file["file_name"])
    source_folder = file_path.parent

    timestamp = load_dt_tm.strftime("%Y%m%d-%H%M%S")
    archive_dir , failed_dir = setup_folders(source_folder=source_folder)
    new_file_name = f"{file_name.stem}__{timestamp}{file_name.suffix}" 
    load_info = None
    error_message = "Unknown error occurred"

    try:
        load_info = pipeline.run(
            reader,
            write_disposition=load_strategy,
            table_name=table_name,
            primary_key=primary_key or None,  # None = don't override any existing hint
        )

        # Check for dlt's internal job failures (Scenario 2)
        if load_info.has_failed_jobs:
            shutil.move(file_path, failed_dir / new_file_name)
        else:
            shutil.move(file_path, archive_dir / new_file_name)

    except PipelineStepFailed as step_failed:
        # Extract the partial load info from the dlt exception (Scenario 1).
        # Only a LoadInfo has has_failed_jobs; if extract/normalize failed, step_info is
        # an ExtractInfo/NormalizeInfo, so fall back to the dummy failure object below.
        if isinstance(step_failed.step_info, LoadInfo):
            load_info = step_failed.step_info
        error_message = str(step_failed)
        shutil.move(file_path, failed_dir / new_file_name)

    except Exception as e:
        # Catch-all for non-dlt exceptions (like OS/File errors)
        #shutil.move(file_path, failed_dir / new_file_name)
        print(f"[red]:x: An error occurred while processing {file_path}: {e}[/red]")
        error_message = str(e)
        raise typer.Exit()
    finally:
        if load_info is None:
            # If load_info is still None, create a dummy object to avoid further errors
            load_info = type('LoadInfo', (object,), {'has_failed_jobs': True, 'errors': [error_message], 'metrics': {}})()   
        return load_info

def _ensure_primary_key(load_strategy:str , primary_key:list):
    if load_strategy == "merge" and not primary_key:
            typer.echo("Error: No primary key for merge strategy", err=True)
            raise typer.Exit(code=1)
        