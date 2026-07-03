"""Enums compartidos entre DTOs."""
from enum import Enum


class AccionRouter(str, Enum):
    """Acciones posibles del agente. Al ser str+Enum, serializa a su value."""

    RESPONDER = "responder"
    DERIVAR = "derivar_ticket"
    ESCALAR = "escalar_humano"


class TipoIntencion(str, Enum):
    """Intención detectada en el mensaje del usuario.

    Todos los valores distintos de CONSULTA_SOPORTE se consideran "small talk"
    y se atienden con una respuesta canned sin invocar el pipeline RAG.
    """

    SALUDO = "saludo"
    DESPEDIDA = "despedida"
    AGRADECIMIENTO = "agradecimiento"
    IDENTIDAD = "identidad"
    CAPACIDADES = "capacidades"
    CONSULTA_SOPORTE = "consulta_soporte"
    OTRO = "otro"
