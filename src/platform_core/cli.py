"""CLI entry point da platform-core."""

from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console
from rich.panel import Panel

from platform_core.config.loader import AgentLoadError, load_agent
from platform_core.engine.executor import Executor
from platform_core.engine.validator import ValidationError, validar_agente
from platform_core.llm.ollama import OllamaClient
from platform_core.logging.structured import setup_logging
from platform_core.tools.registry import ToolRegistry

app = typer.Typer(
    name="platform",
    help="Motor de execução genérico de agentes.",
    add_completion=False,
)
console = Console(emoji=False)


@app.command()
def run(
    agent_path: Path = typer.Argument(
        ..., help="Caminho para o agent.yaml", exists=True
    ),
    entrada: str = typer.Option(
        "", "--entrada", "-e", help="Mensagem inicial do usuário"
    ),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Log detalhado"),
):
    """Executa um agente a partir do seu agent.yaml."""
    setup_logging(verbose=verbose)

    try:
        # 1. Carrega o agente
        config = load_agent(agent_path)
        console.print(f"[bold green][OK][/] Agente carregado: {config.nome} v{config.versao}")

        # 2. Carrega as ferramentas do diretório do agente
        agent_dir = agent_path.parent
        tools_dir = agent_dir / "tools"

        registry = ToolRegistry()
        if tools_dir.exists():
            count = registry.load_from_directory(tools_dir)
            console.print(f"[bold green][OK][/] {count} ferramenta(s) carregada(s)")
        else:
            console.print("[yellow][AVISO][/] Diretorio tools/ nao encontrado")

        # 3. Validação pré-voo
        try:
            validar_agente(config, registry)
        except ValidationError as e:
            console.print(f"[bold red][ERRO][/] Validação falhou: {e}")
            raise typer.Exit(code=1)

        # 4. Cria o cliente LLM e executor
        with OllamaClient() as llm_client:
            executor = Executor(llm_client=llm_client, registry=registry)

            console.print("\n[bold]Executando agente...[/]")
            state = executor.executar(config=config, entrada=entrada)

        # 5. Mostra o resultado
        console.print()
        if state.status.value == "finalizado":
            console.print(
                Panel(
                    state.resultado or "(sem resposta)",
                    title="[bold green]Resultado Final[/]",
                    border_style="green",
                )
            )
        else:
            console.print(
                Panel(
                    state.erro or "Erro desconhecido",
                    title=f"[bold red]Erro ({state.status.value})[/]",
                    border_style="red",
                )
            )

        # 6. Mostra estatísticas
        console.print(
            f"\n[dim]Passos: {state.passo_atual} | "
            f"Ferramentas usadas: {len(state.ferramentas_usadas)} | "
            f"Duracao: {state.metadata.get('duracao_total_s', 0):.2f}s[/]"
        )

    except AgentLoadError as e:
        console.print(f"[bold red][ERRO][/] Erro ao carregar agente: {e}")
        raise typer.Exit(code=1)
    except Exception as e:
        console.print(f"[bold red][ERRO][/] Erro inesperado: {e}")
        if verbose:
            console.print_exception()
        raise typer.Exit(code=1)


@app.command()
def validate(
    agent_path: Path = typer.Argument(
        ..., help="Caminho para o agent.yaml", exists=True
    ),
):
    """Valida um agent.yaml sem executar."""
    try:
        config = load_agent(agent_path)
        console.print(f"[bold green][OK][/] YAML valido: {config.nome} v{config.versao}")
        console.print(f"  Modelo: {config.modelo}")
        console.print(f"  Ferramentas: {', '.join(config.ferramentas)}")
        console.print(f"  Max passos: {config.max_passos}")
    except AgentLoadError as e:
        console.print(f"[bold red][ERRO][/] YAML invalido: {e}")
        raise typer.Exit(code=1)


@app.command()
def version():
    """Mostra a versão."""
    console.print("platform-core 0.1.0")


# Subcomando: platform tools list
tools_app = typer.Typer(help="Gerencia ferramentas.")
app.add_typer(tools_app, name="tools")


@tools_app.command("list")
def tools_list(
    agent_path: Path = typer.Argument(
        ..., help="Caminho para o agent.yaml", exists=True
    ),
):
    """Lista ferramentas disponíveis em um agente."""
    try:
        config = load_agent(agent_path)
        agent_dir = agent_path.parent
        tools_dir = agent_dir / "tools"

        registry = ToolRegistry()
        if tools_dir.exists():
            registry.load_from_directory(tools_dir)

        console.print(f"\n[bold]Ferramentas declaradas em {config.nome}:[/]")
        for nome in config.ferramentas:
            if registry.has(nome):
                spec = registry.get(nome)
                desc = spec.descricao if spec else "N/A"
                console.print(f"  [green][OK][/] {nome}: {desc}")
            else:
                console.print(f"  [red][ERRO][/] {nome}: NAO ENCONTRADA")

    except AgentLoadError as e:
        console.print(f"[bold red][ERRO][/] {e}")
        raise typer.Exit(code=1)


if __name__ == "__main__":
    app()