import typer

from tars.cli.connections import check_current_setup, init, setup_connection , check_chosen_connection , use_connection
from tars.cli.load import load_file, load_files
from tars.core.settings import config_path, ensure_files, flows_path, get_settings , add_credentials
from tars.ui.display import welcome

app = typer.Typer()

app.command("init")(init)
app.command("use")(use_connection)
app.command("inspect-connections")(check_current_setup)
app.command("load-files")(load_files)
app.command("load")(load_file)
app.command("target")(check_chosen_connection)

configs = get_settings(config_path)
flows = get_settings(flows_path)



#@app.callback(invoke_without_command=True)

@app.callback(invoke_without_command=True)
def cli(ctx: typer.Context):
    # credentials are loaded by each command when it runs (resolve_credentials), never at import
    ctx.obj = {
                "configs":configs,
                "flows":flows,
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
            server , database , auth , username = setup_connection()
            add_credentials(server,database,auth,username)
        else:
            init()

        print("Connection settings have been set successfully")
            

    except Exception as e:
        print(e)


if __name__ == "__main__":
    app()
