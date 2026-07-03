"""Clasificador de intención basado en LLM.

Se invoca antes del pipeline RAG para diferenciar small-talk (saludos,
despedidas, agradecimientos, meta-preguntas) de consultas técnicas reales.
Los mensajes de small-talk se responden con textos canned; el resto sigue
el flujo normal de retrieval + generation + scoring.
"""
import logging

from app.core.prompts import PROMPT_CLASIFICACION_INTENCION
from app.infrastructure.llm_client import LLMClient
from app.schemas.enums import TipoIntencion

logger = logging.getLogger(__name__)


# Ante fallo del LLM o respuesta no parseable asumimos consulta técnica:
# es la ruta segura porque el pipeline RAG ya sabe manejar preguntas sin
# información suficiente (devolvería ESCALAR) y evita responder con un
# texto canned a una consulta legítima.
_INTENCION_FALLBACK = TipoIntencion.CONSULTA_SOPORTE


class IntentClassifierServiceImpl:
    """Clasifica el mensaje del usuario en una TipoIntencion vía LLM."""

    def __init__(self, llm: LLMClient):
        self._llm = llm

    def clasificar(self, pregunta: str) -> TipoIntencion:
        try:
            prompt = PROMPT_CLASIFICACION_INTENCION.format(pregunta=pregunta)
            respuesta_cruda = self._llm.invoke(prompt).strip()
        except Exception as e:
            logger.warning(
                "IntentClassifier: fallo llamando al LLM (%s). Fallback a %s",
                e,
                _INTENCION_FALLBACK.value,
            )
            return _INTENCION_FALLBACK

        etiqueta = self._normalizar(respuesta_cruda)
        intencion = self._parsear(etiqueta)

        logger.info(
            "IntentClassifier: '%s' → %s",
            pregunta[:60],
            intencion.value,
        )
        return intencion

    @staticmethod
    def _normalizar(texto: str) -> str:
        """Deja solo caracteres alfabéticos + underscore, en mayúsculas.

        Cubre casos como '`SALUDO`', 'Saludo.', '"SALUDO"' o respuestas
        con explicación extra ('SALUDO - saludo cordial').
        """
        limpio = texto.strip().strip("`\"'.,: ").upper()
        # Nos quedamos con la primera "palabra" (secuencia de letras y _)
        buffer: list[str] = []
        for ch in limpio:
            if ch.isalpha() or ch == "_":
                buffer.append(ch)
            elif buffer:
                break
        return "".join(buffer)

    @staticmethod
    def _parsear(etiqueta: str) -> TipoIntencion:
        mapping = {
            "SALUDO": TipoIntencion.SALUDO,
            "DESPEDIDA": TipoIntencion.DESPEDIDA,
            "AGRADECIMIENTO": TipoIntencion.AGRADECIMIENTO,
            "IDENTIDAD": TipoIntencion.IDENTIDAD,
            "CAPACIDADES": TipoIntencion.CAPACIDADES,
            "CONSULTA_SOPORTE": TipoIntencion.CONSULTA_SOPORTE,
            "OTRO": TipoIntencion.OTRO,
        }
        intencion = mapping.get(etiqueta)
        if intencion is None:
            logger.warning(
                "IntentClassifier: etiqueta no reconocida '%s'. Fallback a %s",
                etiqueta,
                _INTENCION_FALLBACK.value,
            )
            return _INTENCION_FALLBACK
        return intencion
