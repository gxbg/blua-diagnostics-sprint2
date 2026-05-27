"""Tools mockadas do BluaDiagnostics."""

from .mock_tools import (
    consultar_historico_paciente,
    verificar_interacoes_medicamentosas,
    agendar_teleconsulta,
    executar_tool,
    PACIENTES,
)

__all__ = [
    "consultar_historico_paciente",
    "verificar_interacoes_medicamentosas",
    "agendar_teleconsulta",
    "executar_tool",
    "PACIENTES",
]