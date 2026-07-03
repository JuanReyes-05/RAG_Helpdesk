"""Providers de FastAPI para inyección de dependencias."""
from typing import Annotated

from fastapi import Depends, Request

from app.core.config import Settings, get_settings
from app.services.ingestion_service import ejecutar_ingesta as _ejecutar_ingesta
from app.services.intent_classifier_service import IntentClassifierServiceImpl
from app.services.rag_service import RAGServiceImpl
from app.services.routing_service import RoutingServiceImpl


def get_rag_service(request: Request) -> RAGServiceImpl:
    rag = getattr(request.app.state, "rag_service", None)
    if rag is None:
        raise RuntimeError(
            "RAGService no disponible en app.state. "
            "Verifica la inicialización en el lifespan."
        )
    return rag


def get_routing_service(request: Request) -> RoutingServiceImpl:
    routing = getattr(request.app.state, "routing_service", None)
    if routing is None:
        raise RuntimeError(
            "RoutingService no disponible en app.state. "
            "Verifica la inicialización en el lifespan."
        )
    return routing


def get_intent_classifier_service(request: Request) -> IntentClassifierServiceImpl:
    clasificador = getattr(request.app.state, "intent_classifier_service", None)
    if clasificador is None:
        raise RuntimeError(
            "IntentClassifierService no disponible en app.state. "
            "Verifica la inicialización en el lifespan."
        )
    return clasificador


SettingsDep = Annotated[Settings, Depends(get_settings)]
RAGServiceDep = Annotated[RAGServiceImpl, Depends(get_rag_service)]
RoutingServiceDep = Annotated[RoutingServiceImpl, Depends(get_routing_service)]
IntentClassifierServiceDep = Annotated[
    IntentClassifierServiceImpl, Depends(get_intent_classifier_service)
]


# Alias para permitir mockear el pipeline de ingesta en tests
ejecutar_ingesta = _ejecutar_ingesta
