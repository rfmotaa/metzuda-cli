import click
import typer
from metzuda.cli.commands import billing, config, fix, init, login, logout, report, scan, status, upgrade

app = typer.Typer(
    name="metzuda",
    help="Security scanner for AI-generated code.",
    add_completion=False,
    rich_markup_mode="rich",
    pretty_exceptions_enable=False,
)

app.command("init")(init.init)
app.command("scan")(scan.scan)
app.command("report")(report.report)
app.command("fix")(fix.fix)
app.command("config")(config.config)
app.command("login")(login.login)
app.command("logout")(logout.logout)
app.command("status")(status.status)
app.command("upgrade")(upgrade.upgrade)
app.command("billing")(billing.billing)


def entrypoint():
    try:
        app()
    except click.ClickException as e:
        from metzuda.cli.renderer import ErrorMessage

        ErrorMessage.display(e.format_message())
        raise SystemExit(e.exit_code)
    except typer.Exit as e:
        raise SystemExit(e.code)
    except typer.Abort:
        click.echo("Aborted.", err=True)
        raise SystemExit(1)


if __name__ == "__main__":
    entrypoint()