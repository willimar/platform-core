# platform-core

Motor de execução genérico de agentes. Carrega definições
declarativas (`agent.yaml`), conecta ao LLM, executa ferramentas
e gerencia o loop de raciocínio-ação.

A plataforma **não conhece** nenhum agente específico.
Agentes são plugáveis via `agent.yaml` + ferramentas registradas.

---

## Arquitetura

```
agent.yaml ──► Config Loader ──► Engine ──► LLM Client (Ollama)
                                    │
                                    ▼
                              Tool Registry ──► tool functions
```

Documentação completa em [`platform-docs/architecture.md`](https://github.com/<org>/platform-docs/blob/main/architecture.md).

---

## Requisitos

- Python 3.11+
- [Ollama](https://ollama.com) rodando localmente (ou endpoint compatível)
- [uv](https://docs.astral.sh/uv/) para gerenciamento de dependências

---

## Instalação

```bash
git clone https://github.com/<org>/platform-core.git
cd platform-core
uv sync
```
## Uso
### Executar um agente

```bash
uv run platform run ../google-calendar-agent/agent.yaml
```

### Validar um YAML sem executar

```bash
uv run platform validate ../google-calendar-agent/agent.yaml
```

### Listar ferramentas registradas

```bash
uv run platform tools list
```

### Modo verbose (log de cada passo)

```bash
uv run platform run ../google-calendar-agent/agent.yaml --verbose
```

## Estrutura

```
src/
└── platform_core/
    ├── __init__.py
    ├── cli.py                  # CLI entry point (typer)
    ├── config/
    │   ├── __init__.py
    │   ├── loader.py           # lê e parseia agent.yaml
    │   └── schema.py           # modelos Pydantic
    ├── engine/
    │   ├── __init__.py
    │   ├── executor.py         # loop principal
    │   ├── state.py            # AgentState dataclass
    │   └── validator.py        # validações pré-execução
    ├── llm/
    │   ├── __init__.py
    │   ├── client.py           # interface abstrata
    │   ├── ollama.py           # implementação Ollama
    │   └── parser.py           # parse JSON do LLM
    ├── tools/
    │   ├── __init__.py
    │   └── registry.py         # ToolRegistry + descoberta
    └── logging/
        ├── __init__.py
        └── structured.py       # structlog config

tests/
├── test_executor.py
├── test_registry.py
├── test_parser.py
└── conftest.py

pyproject.toml
Makefile
README.md
```

## Desenvolvimento

```bash
# Instalar deps de dev
uv sync --group dev

# Rodar testes
uv run pytest

# Lint + format
uv run ruff check src/ tests/
uv run ruff format src/ tests/

# Rodar tudo (CI local)
make check
```

## Makefile targets

 | Target        | Ação                         | 
 | ------------- | ---------------------------- | 
 | `make check`  | lint + format check + testes | 
 | `make test`   | pytest com coverage          | 
 | `make lint`   | ruff check                   | 
 | `make format` | ruff format                  | 
 | `make run`    | executa exemplo local        | 
