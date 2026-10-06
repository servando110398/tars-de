import shutil
from datetime import datetime
from pathlib import Path
from typing import Annotated
import dlt
import typer
from dlt.destinations import mssql
from dlt.sources.filesystem import filesystem , read_csv
from rich import print
from tars.core.files import setup_folders
from tars.core.readers import read_excel

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
    creds = ctx.obj["creds"]

    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    pipeline = dlt.pipeline(
            pipeline_name="file_to_mssql_pipeline",
            destination=mssql(credentials=creds),
            dataset_name=schema_name  # This will map to a schema in SQL Server
        )

    files = filesystem(
        bucket_url=source_folder,
        file_glob=("*."+file_extension)  # Filter for specific file types if needed
        )


    archive_dir , failed_dir , source  = setup_folders(source_folder=source_folder)

    files_processed = 0
    failed_files = 0
    total_rows = 0

    total_files = len(list(files))
    print(f"Folder: {source_folder}")
    print(f"Extension: {file_extension}")
    print(f"Files found: {total_files}")

    for file in list(files):  # snapshot the folder before moving anything
          file_name = file["file_name"]
          print(f"Processing file : {file_name} ...")
          file_path = source / file["relative_path"]
          new_file_name = f"{file_path.stem}__{timestamp}{file_path.suffix}"
          reader = ([file] | strategy[file_extension]()).with_name(table_name)

          try:
            load_info = pipeline.run(reader , load_strategy)
            rows = load_info.metrics['row_counts'][table_name]
            shutil.move(file_path, archive_dir / new_file_name)
            files_processed += 1
            total_rows = total_rows + rows
          except:
                failed_files += 1
                shutil.move(file_path, failed_dir / new_file_name)

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

    print(f"Processing file : {file_name} ...")

    creds = ctx.obj["creds"]
    
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    pipeline = dlt.pipeline(
            pipeline_name="file_to_mssql_pipeline",
            #destination="mssql",
            destination=mssql(credentials=creds),
            dataset_name=schema_name  # This will map to a schema in SQL Server
        )
    current_dir = str(Path.cwd() / "")
    archive_dir , failed_dir , source  = setup_folders(source_folder=current_dir)

    file_source = filesystem(
    bucket_url=current_dir,  # Path to the parent folder
    file_glob=f"{file_name}*"# Add * to match the exact single file
    )


    file_extension = Path(file_name).suffix[1:]
    file_path = Path(file_name).resolve()
    #file_path = source / file_source["relative_path"]
    new_file_name = f"{file_path.stem}__{timestamp}{file_path.suffix}"

    reader = (file_source |  strategy[file_extension]).with_name(table_name)

    try:
        load_info = pipeline.run(reader, write_disposition=load_strategy)
        shutil.move(file_path,archive_dir/new_file_name)
        total_rows = load_info.metrics['row_counts'][table_name]
        trace = pipeline.last_trace
        duration = trace.finished_at - trace.started_at
        seconds = duration.total_seconds()
        message = f"[green]:white_check_mark: Done. File {file_name} has been processed. \n{total_rows} rows ingested in {seconds:.2f} seconds[/green]"
    except Exception as e:
        shutil.move(file_path,failed_dir/new_file_name)
        message = f"[red]:x: load failed![/red] \n {e}"
    finally:
        print(message)
        raise typer.Exit()
