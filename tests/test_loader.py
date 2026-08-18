"""Testes da resolução do diretório de ferramentas."""

from platform_core.config.loader import resolve_tools_dir
from platform_core.config.schema import AgentConfig, TarefaSpec


def _config(tools_dir: str | None = None) -> AgentConfig:
    return AgentConfig(
        nome="Teste",
        versao="1.0.0",
        modelo="fake",
        instrucoes="Instrucoes de teste com tamanho minimo ok.",
        ferramentas=["dummy_tool"],  # Pydantic exige min_length=1
        tarefa=TarefaSpec(descricao="Faca algo.", saida_esperada="Algo feito."),
        tools_dir=tools_dir,
    )

class TestResolveToolsDir:
    def test_convencao_yaml_ao_lado_de_tools(self, tmp_path):
        (tmp_path / "tools").mkdir()
        yaml_path = tmp_path / "agent.yaml"
        yaml_path.write_text("")
        assert resolve_tools_dir(yaml_path, _config()) == (tmp_path / "tools").resolve()

    def test_busca_ascendente_a_partir_de_agents(self, tmp_path):
        (tmp_path / "tools").mkdir()
        agents = tmp_path / "agents"
        agents.mkdir()
        yaml_path = agents / "readonly.yaml"
        yaml_path.write_text("")
        assert resolve_tools_dir(yaml_path, _config()) == (tmp_path / "tools").resolve()

    def test_tools_dir_explicito_sobrepoe_convencao(self, tmp_path):
        (tmp_path / "tools").mkdir()
        (tmp_path / "outro").mkdir()
        yaml_path = tmp_path / "agent.yaml"
        yaml_path.write_text("")
        got = resolve_tools_dir(yaml_path, _config(tools_dir="outro"))
        assert got == (tmp_path / "outro").resolve()

    def test_sem_tools_retorna_convencional_inexistente(self, tmp_path):
        yaml_path = tmp_path / "agent.yaml"
        yaml_path.write_text("")
        got = resolve_tools_dir(yaml_path, _config())
        assert not got.exists()
