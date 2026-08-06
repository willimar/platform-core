# platform-core

Motor de execução genérico de agentes. Carrega definições
declarativas (`agent.yaml`), conecta ao LLM, executa ferramentas
e gerencia o loop de raciocínio-ação.

A plataforma **não conhece** nenhum agente específico.
Agentes são plugáveis via `agent.yaml` + ferramentas registradas.

---

## Arquitetura
