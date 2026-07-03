"""Endpoint /ask — expone el pipeline RAG."""
import time
import uuid
from datetime import datetime

import structlog
from fastapi import APIRouter, BackgroundTasks, HTTPException

from app.api.dependencies import RAGServiceDep, RoutingServiceDep
from app.core.logging import get_logger
from app.schemas.consulta import FuenteResponse, PreguntaRequest, PreguntaResponse

logger = get_logger(__name__)

router = APIRouter(tags=["consultas"])


def registrar_interaccion(
    consulta_id: str,
    pregunta: str,
    respuesta: PreguntaResponse,
    duration_ms: float,
) -> None:
    """Emite un evento estructurado con el resumen de la interacción."""
    logger.info(
        "interaccion_registrada",
        consulta_id=consulta_id,
        accion=respuesta.accion.value,
        score=respuesta.score_confianza,
        tiene_info=respuesta.tiene_info,
        modelo=respuesta.modelo,
        fuentes=[f.archivo for f in respuesta.fuentes],
        num_fuentes=len(respuesta.fuentes),
        pregunta=pregunta[:200],
        duration_ms=duration_ms,
    )


@router.post("/ask", response_model=PreguntaResponse)
async def preguntar(
    request: PreguntaRequest,
    background_tasks: BackgroundTasks,
    rag: RAGServiceDep,
    routing: RoutingServiceDep,
):
    """Procesa una pregunta y devuelve respuesta + acción recomendada."""
    consulta_id = str(uuid.uuid4())
    structlog.contextvars.bind_contextvars(
        consulta_id=consulta_id,
        usuario_id=request.usuario_id or "anon",
    )
    start = time.perf_counter()
    try:
        resultado = rag.consultar(
            pregunta=request.pregunta,
            usuario_id=request.usuario_id,
        )

        accion = routing.definir_accion(
            score=resultado.score_confianza,
            tiene_info=resultado.tiene_info,
            requiere_derivacion=resultado.requiere_derivacion,
            pregunta=request.pregunta,
        )

        respuesta = PreguntaResponse(
            consulta_id=consulta_id,
            respuesta=resultado.respuesta,
            accion=accion,
            score_confianza=resultado.score_confianza,
            tiene_info=resultado.tiene_info,
            fuentes=[
                FuenteResponse(
                    archivo=f.archivo,
                    fragmento=(
                        f.contenido[:200] + "..."
                        if len(f.contenido) > 200
                        else f.contenido
                    ),
                    pagina=f.pagina,
                    score=round(f.similitud, 3),
                )
                for f in resultado.fragmentos
            ],
            modelo=resultado.modelo,
            timestamp=datetime.now().isoformat(),
        )

        duration_ms = round((time.perf_counter() - start) * 1000, 2)
        background_tasks.add_task(
            registrar_interaccion, consulta_id, request.pregunta, respuesta, duration_ms
        )

        return respuesta

    except RuntimeError as e:
        raise HTTPException(
            status_code=503,
            detail=(
                f"Sistema no disponible: {str(e)}. "
                "Verifica que ejecutaste 'python scripts/ingest.py' primero."
            ),
        )
    except Exception as e:
        logger.exception("consulta_error", consulta_id=consulta_id, error=str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Error interno al procesar la consulta. ID: {consulta_id}",
        )
