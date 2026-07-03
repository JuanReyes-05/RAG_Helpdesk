"""Tests del IntentClassifierService — clasificación de intención vía LLM."""
import pytest

from app.services.intent_classifier_service import IntentClassifierServiceImpl
from app.schemas.enums import TipoIntencion


class LLMFalso:
    """Mock que devuelve una respuesta fija; captura el último prompt recibido."""

    def __init__(self, respuesta: str):
        self.respuesta = respuesta
        self.ultimo_prompt: str | None = None

    def invoke(self, prompt: str) -> str:
        self.ultimo_prompt = prompt
        return self.respuesta


class LLMQueFalla:
    def invoke(self, prompt: str) -> str:
        raise RuntimeError("timeout llamando al modelo")


@pytest.mark.parametrize(
    "salida_llm,esperado",
    [
        ("SALUDO", TipoIntencion.SALUDO),
        ("DESPEDIDA", TipoIntencion.DESPEDIDA),
        ("AGRADECIMIENTO", TipoIntencion.AGRADECIMIENTO),
        ("IDENTIDAD", TipoIntencion.IDENTIDAD),
        ("CAPACIDADES", TipoIntencion.CAPACIDADES),
        ("CONSULTA_SOPORTE", TipoIntencion.CONSULTA_SOPORTE),
        ("OTRO", TipoIntencion.OTRO),
    ],
)
def test_clasifica_etiquetas_limpias(salida_llm, esperado):
    clasificador = IntentClassifierServiceImpl(LLMFalso(salida_llm))
    assert clasificador.clasificar("mensaje cualquiera") == esperado


@pytest.mark.parametrize(
    "salida_sucia",
    [
        "`SALUDO`",
        "Saludo.",
        '"SALUDO"',
        "SALUDO ",
        "SALUDO - saludo cordial del usuario",
        "  saludo\n",
    ],
)
def test_normaliza_salidas_ruidosas_del_llm(salida_sucia):
    clasificador = IntentClassifierServiceImpl(LLMFalso(salida_sucia))
    assert clasificador.clasificar("hola") == TipoIntencion.SALUDO


def test_etiqueta_desconocida_cae_al_fallback():
    clasificador = IntentClassifierServiceImpl(LLMFalso("NARANJA"))
    # Fallback conservador: asumimos consulta técnica
    assert clasificador.clasificar("algo raro") == TipoIntencion.CONSULTA_SOPORTE


def test_error_del_llm_cae_al_fallback():
    clasificador = IntentClassifierServiceImpl(LLMQueFalla())
    assert (
        clasificador.clasificar("¿cómo restablezco mi contraseña?")
        == TipoIntencion.CONSULTA_SOPORTE
    )


def test_prompt_incluye_la_pregunta_del_usuario():
    llm = LLMFalso("SALUDO")
    clasificador = IntentClassifierServiceImpl(llm)
    clasificador.clasificar("hola buenos días")
    assert llm.ultimo_prompt is not None
    assert "hola buenos días" in llm.ultimo_prompt


def test_saludo_con_pregunta_tecnica_se_clasifica_como_consulta():
    """El prompt le indica al LLM que priorice CONSULTA_SOPORTE en mensajes mixtos.

    Aquí solo verificamos que si el LLM lo clasifica así, se propaga correcto.
    """
    clasificador = IntentClassifierServiceImpl(LLMFalso("CONSULTA_SOPORTE"))
    intencion = clasificador.clasificar("hola, cómo restablezco mi VPN")
    assert intencion == TipoIntencion.CONSULTA_SOPORTE
