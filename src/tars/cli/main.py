import typer

from tars.cli.connections import check_current_setup, init, setup_connection , check_chosen_connection
from tars.cli.load import load_file, load_files
from tars.core.settings import add_connection, config_path, ensure_files, flows_path, get_settings , creds_path , add_credentials
from tars.ui.display import welcome

app = typer.Typer()

app.command("init")(init)
app.command("use")(setup_connection)
app.command("inspect-connections")(check_current_setup)
app.command("load-files")(load_files)
app.command("load")(load_file)
app.command("target")(check_chosen_connection)

configs = get_settings(config_path)
flows = get_settings(flows_path)
creds = get_settings(creds_path)



#@app.callback(invoke_without_command=True)

@app.callback(invoke_without_command=True)
def cli(ctx: typer.Context):
    ctx.obj = {
                "configs":configs,
                "flows":flows,
                "creds":creds
                }
    
    if ctx.invoked_subcommand is None:
        main(ctx)
        

app.command(name="exit")
def exit():
    """Exit the application."""
    raise typer.Exit()


#@app.result_callback()
def main(ctx:typer.Context):
    
    welcome()
    ensure_files()

    try:
        if configs:
            "extract server an db from here"
            server , database = setup_connection()
            add_credentials(server,database)
        else:
            server = typer.prompt("server ")
            database = typer.prompt("database ")
            add_connection(server,database)
            add_credentials(server,database)

        print("Connection settings have been set successfully")

        ctx.obj = {
                        "configs":configs,
                        "flows":flows,
                        "creds":creds
                        }
            

    except Exception as e:
        print(e)


if __name__ == "__main__":
    app()
