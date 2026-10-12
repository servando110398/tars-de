import shutil
from datetime import datetime
from pathlib import Path
from typing import Annotated
import dlt
from openpyxl import reader
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
""" 
Build a single function for procesisng files that is reused by load_files and load_file. 

"""

strategy ={"csv":read_csv, "xls":read_excel , "xlsx":read_excel}

def load_files(
        ctx:typer.Context,
        source_folder:Annotated[str,typer.Argument(help="Path to the folder containing the files to be loaded.")] ,
        file_extension:Annotated[str,typer.Argument(help="File extension used to identify the files to be loaded.")],
        table_name : Annotated[str,typer.Argument(help="Name of the target table where the files will be loaded.")] ,
        schema_name:Annotated[str,typer.Argument(help="Name of the schema where the files will be loaded.")],
        load_strategy:Annotated[str,typer.Argument(help="Loading strategy to be used")] = "append"):
    """
    Load all files with the selected extension from the source folder into the target schema and table using the selected load strategy.
    """
    creds = resolve_credentials()
    pipeline = dlt.pipeline(
            pipeline_name="file_to_mssql_pipeline",
            destination=mssql(credentials=creds),
            dataset_name=schema_name  # This will map to a schema in SQL Server
        )

    files = filesystem(
        bucket_url=source_folder,
        file_glob=("*."+file_extension)  # Filter for specific file types if needed
        )

    files_processed = 0
    failed_files = 0
    total_rows = 0

    total_files = len(list(files))
    print(f"Folder: {source_folder}")
    print(f"Extension: {file_extension}")
    print(f"Files found: {total_files}")

    for file in list(files):  # snapshot the folder before moving anything
        print(f"Processing file : {file['file_name']} ...")
        load_info = _process_file(file=file, table_name=
                                  table_name, load_strategy=load_strategy, pipeline=pipeline)
        if load_info.has_failed_jobs:
            failed_files += 1
        else:
            row_counts = pipeline.last_trace.last_normalize_info.row_counts
            rows = sum(n for table, n in row_counts.items() if not table.startswith("_dlt"))
            total_rows += rows
            files_processed += 1
            
    print(f"Processed files: {files_processed}")
    print(f"Total rows ingested: {total_rows}")
    print(f"Failed files: {failed_files}")


def load_file(ctx:typer.Context,
              file_name: Annotated[str,typer.Argument(help="Name of file to be loaded")],
              table_name: Annotated[str,typer.Argument(help="Name of the target table where the files will be loaded.")],
              schema_name:Annotated[str,typer.Argument(help="Name of the schema where the file will be loaded.")],
              load_strategy:Annotated[str,typer.Argument(help="Loading strategy to be used")] = "append"):
    """
    Load file into the specified target schema and table using the selected load strategy.
    """
    creds = resolve_credentials()
    pipeline = dlt.pipeline(
            pipeline_name="file_to_mssql_pipeline",
            destination=mssql(credentials=creds),
            dataset_name=schema_name  # This will map to a schema in SQL Server
        )

    bucket_url = os.path.dirname(os.path.abspath(file_name))
    # Grabs the very first FileItemDict directly out of the generator
    file_obj = next(iter(filesystem(bucket_url=bucket_url, file_glob=file_name)))

    print(f"Processing file : {file_name} ...")
    load_info = _process_file(file=file_obj, table_name=table_name, load_strategy=load_strategy, pipeline=pipeline)

    if load_info.has_failed_jobs:
        failed_files += 1
        message = f"[red]:x: load failed![/red] \n {load_info.errors}"    
    else:
        #job_metrics = load_info.metrics.get("job_metrics", {})

        row_counts = pipeline.last_trace.last_normalize_info.row_counts
        total_rows = sum(n for table, n in row_counts.items() if not table.startswith("_dlt"))

        trace = pipeline.last_trace
        duration = trace.finished_at - trace.started_at
        seconds = duration.total_seconds()
        message = f"[green]:white_check_mark: Done. File {file_name} has been processed. \n{total_rows} rows ingested in {seconds:.2f} seconds[/green]"

    print(message)
            


def _process_file(file: FileItemDict,table_name,load_strategy,pipeline):
    """
    Process a single file and return the load info object.
    """
    file_extension = _get_file_extension(file)
    reader = ([file] | strategy[file_extension]()).with_name(table_name)
    file_path = Path(file["relative_path"])
    source_folder = Path(file["relative_path"]).resolve().parent
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    archive_dir , failed_dir = setup_folders(source_folder=source_folder)
    new_file_name = f"{file_path.stem}__{timestamp}{file_path.suffix}" 
    load_info = None  

    try:    
        load_info = pipeline.run(reader, write_disposition= load_strategy)
    
        # Check for dlt's internal job failures (Scenario 2)
        if load_info.has_failed_jobs:
            shutil.move(file_path, failed_dir / new_file_name)
        else:
            shutil.move(file_path, archive_dir / new_file_name)

    except PipelineStepFailed as step_failed:
        # Extract the partial load info from the dlt exception (Scenario 1)
        load_info = step_failed.step_info  
        shutil.move(file_path, failed_dir / new_file_name)

    except Exception as e:
        # Catch-all for non-dlt exceptions (like OS/File errors)
        #shutil.move(file_path, failed_dir / new_file_name)
        print(f"[red]:x: An error occurred while processing {file_path}: {e}[/red]")
        typer.Exit()
    finally:
        if load_info is None:
            # If load_info is still None, create a dummy object to avoid further errors
            load_info = type('LoadInfo', (object,), {'has_failed_jobs': True, 'errors': ['Unknown error occurred'], 'metrics': {}})()   
        return load_info

