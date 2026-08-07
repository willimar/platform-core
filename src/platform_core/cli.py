"""CLI entry point da platform-core."""

import typer

app = typer.Typer(
    name="platform",
    help="Motor de execução genérico de agentes.",
    add_completion=False,
)

@app.command()
def run(
    agent_path: str = typer.Argument(..., help="Caminho para o agent.yaml"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Log detalhado"),
):
    """Executa um agente a partir do seu agent.yaml."""
    typer.echo(f"[STUB] Executar agente: {agent_path}")
    typer.echo(f"[STUB] Verbose: {verbose}")
    raise typer.Exit(code=0)

@app.command()
def validate(
    agent_path: str = typer.Argument(..., help="Caminho para o agent.yaml"),
):
    """Valida um agent.yaml sem executar."""
    typer.echo(f"[STUB] Validar: {agent_path}")

@app.command()
def version():
    """Mostra a versão."""
    typer.echo("platform-core 0.1.0")

# Subcomando: platform tools list
tools_app = typer.Typer(help="Gerencia ferramentas.")
app.add_typer(tools_app, name="tools")

@tools_app.command("list")
def tools_list():
    """Lista ferramentas registradas."""
    typer.echo("[STUB] Nenhuma ferramenta registrada ainda.")

if __name__ == "__main__":
    app()
