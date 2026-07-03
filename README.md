# Helpdesk AI — Agente de Soporte con RAG

Sistema de soporte al cliente basado en **Retrieval-Augmented Generation (RAG)**.
Responde preguntas de usuarios usando una base de conocimiento vectorial, y decide
de forma autónoma si responde directamente, deriva a un ticket o escala a un agente humano.

Arquitectura en capas estilo DDD (Domain-Driven Design) sobre FastAPI: `api` → `services` → `repositories` + `infrastructure`, con inyección de dependencias explícita mediante `typing.Protocol`.

---

## Tabla de Contenidos

1. [Arquitectura](#arquitectura)
2. [Capas y responsabilidades](#capas-y-responsabilidades)
3. [Stack Tecnologico](#stack-tecnologico)
4. [Estructura del Proyecto](#estructura-del-proyecto)
5. [Flujo de Datos](#flujo-de-datos)
6. [Endpoints de la API](#endpoints-de-la-api)
7. [Configuracion](#configuracion)
8. [Ejecucion Local](#ejecucion-local)
9. [Docker](#docker)
10. [Tests](#tests)
11. [Roadmap](#roadmap)

---

## Arquitectura

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                           Cliente / Frontend                                  │
│                 Streamlit UI  ·  REST Client  ·  curl / Postman               │
└──────────────────────────────┬───────────────────────────────────────────────┘
                               │ HTTP
                               ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│   API (controllers)              app/api/v1/                                  │
│   ─ sistema.py    GET /    GET /health                                        │
│   ─ consultas.py  POST /ask                                                   │
│   ─ admin.py      POST /ingest                                                │
│                                                                               │
│   Dependency Injection           app/api/dependencies.py                      │
│   ─ SettingsDep   RAGServiceDep   RoutingServiceDep                           │
└──────────────────────────────┬───────────────────────────────────────────────┘
                               │
                               ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│   Services (casos de uso)        app/services/                                │
│                                                                               │
│       rag_service.py                                                          │
│       (orquestador)                                                           │
│            │                                                                  │
│            ├── retrieval_service   ── buscar fragmentos                       │
│            ├── generation_service  ── generar respuesta LLM                   │
│            ├── scoring_service     ── calcular confianza                      │
│            ├── derivation_service  ── requiere 2do nivel?                     │
│            └── routing_service     ── definir_accion()                        │
│                                                                               │
│       ingestion_service.py  ── pipeline de ingesta                            │
│   Protocols: services/interfaces.py                                           │
└──────────────┬───────────────────────────────────┬──────────────────────────┘
               │                                   │
               ▼                                   ▼
┌────────────────────────────────┐   ┌────────────────────────────────────────┐
│ Repositories (acceso a datos)  │   │ Infrastructure (integraciones ext.)    │
│ app/repositories/              │   │ app/infrastructure/                    │
│                                │   │                                        │
│ ─ VectorStoreRepository (P)    │   │ ─ OpenAILLMClient (ChatOpenAI)         │
│ ─ ChromaRepository             │   │ ─ build_embeddings (HuggingFace)       │
│                                │   │                                        │
│ ChromaDB  (persist: data/)     │   │ OpenAI API  +  HF sentence-transformers│
└────────────────────────────────┘   └────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────────────┐
│   Domain (entidades)             app/domain/                                  │
│   ─ Fragmento     (chunk + metadata + similitud)                              │
│   ─ RespuestaInterna  (resultado del pipeline)                                │
│                                                                               │
│   Schemas / DTOs                 app/schemas/                                 │
│   ─ PreguntaRequest · PreguntaResponse · FuenteResponse · HealthResponse      │
│   ─ IngestRequest   · AccionRouter (enum)                                     │
│                                                                               │
│   Core (cross-cutting)           app/core/                                    │
│   ─ config.py (Settings)   ─ prompts.py   ─ logging.py                        │
└──────────────────────────────────────────────────────────────────────────────┘
```

---

## Capas y responsabilidades

| Capa | Carpeta | Responsabilidad | Depende de |
|------|---------|-----------------|-----------|
| **API / Controllers** | `app/api/v1/` | Exponer endpoints HTTP, validar I/O, inyectar services | services, schemas |
| **Services** | `app/services/` | Casos de uso y reglas de negocio | domain, repositories, infrastructure |
| **Domain** | `app/domain/` | Entidades internas (dataclasses) sin dependencias externas | — |
| **Repositories** | `app/repositories/` | Acceso a datos persistentes (vector store) | domain, infrastructure |
| **Infrastructure** | `app/infrastructure/` | Clientes de servicios externos (LLM, embeddings) | core |
| **Schemas / DTOs** | `app/schemas/` | Modelos Pydantic para I/O de la API | — |
| **Core** | `app/core/` | Configuración, logging, prompts | — |

La capa API **no conoce** ChromaDB ni OpenAI directamente: solo interactúa con services, que a su vez usan los `Protocol` de `interfaces.py` como contrato.

---

## Stack Tecnologico

| Capa | Tecnologia | Version |
|------|-----------|---------|
| API Framework | FastAPI | 0.115.0 |
| ASGI Server | Uvicorn | 0.30.6 |
| LLM | OpenAI `gpt-4o-mini` | via LangChain |
| Embeddings | HuggingFace `paraphrase-multilingual-MiniLM-L12-v2` | sentence-transformers |
| Vector Store | ChromaDB | local persistence |
| Orquestacion LLM | LangChain | latest |
| Validacion | Pydantic v2 | 2.9.2 |
| Frontend | Streamlit | 1.39.0 |
| Contenedores | Docker + Compose | multi-stage build (con uv) |
| Gestor de paquetes | [uv](https://docs.astral.sh/uv/) | 0.11.19 |
| Testing | pytest | - |
| Python | CPython | 3.11 |

---

## Estructura del Proyecto

```
MiProyecto_IAEngineering/
│
├── backend/                                  # API FastAPI (gestionado con uv)
│   ├── app/                                  # Paquete principal (from app.xxx)
│   │   ├── __init__.py
│   │   ├── main.py                           # FastAPI + lifespan + wire-up
│   │   │
│   │   ├── api/                              # Capa de presentación
│   │   │   ├── dependencies.py               # Providers de FastAPI Depends()
│   │   │   ├── middleware.py
│   │   │   └── v1/
│   │   │       ├── sistema.py
│   │   │       ├── consultas.py
│   │   │       └── admin.py
│   │   │
│   │   ├── core/                             # Cross-cutting concerns
│   │   │   ├── config.py                     # Settings (pydantic-settings)
│   │   │   ├── logging.py
│   │   │   └── prompts.py                    # PROMPT_SISTEMA, PROMPT_SCORE, PROMPT_DERIVACION
│   │   │
│   │   ├── schemas/                          # DTOs
│   │   │   ├── enums.py                      # AccionRouter
│   │   │   ├── consulta.py                   # PreguntaRequest, PreguntaResponse, FuenteResponse
│   │   │   ├── sistema.py                    # HealthResponse
│   │   │   └── admin.py                      # IngestRequest
│   │   │
│   │   ├── domain/                           # Entidades internas
│   │   │   ├── fragmento.py
│   │   │   └── consulta.py
│   │   │
│   │   ├── repositories/                     # Acceso a datos
│   │   │   ├── interfaces.py                 # Protocol: VectorStoreRepository
│   │   │   └── chroma_repository.py
│   │   │
│   │   ├── services/                         # Lógica de negocio
│   │   │   ├── interfaces.py                 # Protocols de services
│   │   │   ├── retrieval_service.py
│   │   │   ├── generation_service.py
│   │   │   ├── scoring_service.py            # ScoringService + DerivationService
│   │   │   ├── routing_service.py
│   │   │   ├── ingestion_service.py
│   │   │   └── rag_service.py                # Orquestador
│   │   │
│   │   └── infrastructure/                   # Integraciones externas
│   │       ├── llm_client.py
│   │       └── embeddings_client.py
│   │
│   ├── scripts/
│   │   ├── ingest.py                         # uv run python scripts/ingest.py --limpiar
│   │   └── diagnostico.py
│   ├── tests/
│   │   ├── conftest.py                       # fixture `settings`
│   │   └── unit/services/test_routing_service.py
│   ├── docs/                                 # Base de conocimiento (ingestada al vector store)
│   │   ├── PRD.md
│   │   ├── guia_vpn.md
│   │   ├── politicas_soporte.md
│   │   └── preguntas_frecuentes.txt
│   ├── data/chroma_db/                       # Persistencia local (gitignored)
│   ├── Dockerfile                            # Multi-stage con uv
│   ├── pyproject.toml                        # Deps declaradas + config pytest
│   └── uv.lock                               # Lockfile determinista (commitear)
│
├── frontend/                                 # UI Streamlit (gestionado con uv)
│   ├── app.py                                # uv run streamlit run app.py
│   ├── Dockerfile
│   ├── pyproject.toml
│   └── uv.lock
│
├── docker-compose.yml
├── .env.example
├── .gitignore
├── AGENTS.md                                 # Guía para agentes de IA
└── README.md
```

> **No** hay `Dockerfile`, `requirements.txt` ni paquete `app/` en la raíz. Todo vive dentro de `backend/` y `frontend/`.

---

## Flujo de Datos

```
Usuario
  │  POST /ask { "pregunta": "...", "usuario_id": "..." }
  ▼
api/v1/consultas.py
  │  rag.consultar(pregunta)
  ▼
services/rag_service.py  (orquestador)
  │
  ├── retrieval_service.recuperar(pregunta)
  │     └─► chroma_repository.buscar()  →  list[Fragmento]
  │
  ├── generation_service.generar(pregunta, fragmentos)
  │     └─► llm_client.invoke(PROMPT_SISTEMA)  →  str
  │
  ├── scoring_service.calcular(pregunta, respuesta)
  │     └─► llm_client.invoke(PROMPT_SCORE)  →  float 0.0-1.0
  │
  └── derivation_service.requiere_derivacion(pregunta)
        └─► llm_client.invoke(PROMPT_DERIVACION)  →  bool
  │
  ▼  RespuestaInterna (dominio)
api/v1/consultas.py
  │  routing_service.definir_accion(score, tiene_info, requiere_derivacion, pregunta)
  │     ├── palabra_escalacion  →  ESCALAR
  │     ├── score < 0.3         →  ESCALAR
  │     ├── tiene_info && score > min && requiere_derivacion  →  DERIVAR
  │     ├── tiene_info && score > min                         →  RESPONDER
  │     └── default             →  ESCALAR
  ▼
PreguntaResponse (DTO)  +  BackgroundTask: registrar_interaccion()
```

---

## Endpoints de la API

| Metodo | Ruta | Descripcion |
|--------|------|-------------|
| `GET`  | `/`        | Metadata de la API y listado de endpoints |
| `GET`  | `/health`  | Estado del sistema: RAG listo, chunks indexados, modelos |
| `POST` | `/ask`     | Consulta principal — devuelve respuesta con acción y fuentes |
| `POST` | `/ingest`  | Re-ingesta de documentos en background (flag `limpiar`) |

### Ejemplo: POST /ask

```bash
curl -X POST http://localhost:8000/ask \
  -H "Content-Type: application/json" \
  -d '{"pregunta": "Como restablezco mi contrasena?", "usuario_id": "u001"}'
```

```json
{
  "consulta_id": "abc123",
  "respuesta": "Para restablecer tu contrasena...",
  "accion": "responder",
  "score_confianza": 0.87,
  "tiene_info": true,
  "fuentes": [
    {
      "archivo": "preguntas_frecuentes.txt",
      "fragmento": "Para restablecer tu contrasena...",
      "pagina": null,
      "score": 0.91
    }
  ],
  "modelo": "gpt-4o-mini",
  "timestamp": "2026-04-18T12:34:56Z"
}
```

### Acciones posibles (`AccionRouter`)

| Accion | Condicion |
|--------|-----------|
| `responder` | Confianza >= `MINIMUM_SCORE` y sin derivación ni escalación |
| `derivar_ticket` | Confianza >= `MINIMUM_SCORE` y LLM detecta necesidad de 2do nivel |
| `escalar_humano` | Confianza < 0.3, keyword crítica en la pregunta o sin info suficiente |

---

## Configuracion

Copia `.env.example` a `.env`:

```env
OPENAI_API_KEY=sk-proj-...
LLM_MODEL=gpt-4o-mini
OPENAI_BASE_URL=

CONFIDENCE_THRESHOLD=0.65
MINIMUM_SCORE=0.60

HOST=0.0.0.0
PORT=8000

EMBEDDING_MODEL=sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2

DOCS_DIR=./docs
CHROMA_DIR=./data/chroma_db
COLLECTION_NAME=soporte_docs

CHUNK_SIZE=400
CHUNK_OVERLAP=80
TOP_K=4
```

---

## Ejecucion Local

Requisito previo: instalar [uv](https://docs.astral.sh/uv/getting-started/installation/).

```bash
# 1. Configurar entorno (una vez)
cp .env.example .env
# Editar .env con tu OPENAI_API_KEY

# 2. Instalar dependencias del backend (crea backend/.venv desde uv.lock)
cd backend
uv sync --frozen

# 3. Ingestar documentos (obligatorio antes del primer /ask)
uv run python scripts/ingest.py      # o: uv run python scripts/ingest.py --limpiar

# 4. Iniciar API
uv run uvicorn app.main:app --reload
# API en  http://localhost:8000
# Docs en http://localhost:8000/docs

# 5. (Opcional) UI Streamlit — en otra terminal
cd ../frontend
uv sync --frozen
uv run streamlit run app.py

# 6. (Opcional) Diagnóstico completo — desde backend/
uv run python scripts/diagnostico.py

# 7. Tests
cd ../backend
uv run pytest tests/unit -v
```

> **No usar `pip install`** — rompe el entorno gestionado por uv. Para añadir dependencias: `uv add <paquete>` (actualiza `pyproject.toml` y `uv.lock`).

---

## Docker

Las imágenes usan **multi-stage con uv**: la stage `builder` ejecuta `uv sync --frozen --no-dev --no-install-project` para crear el venv en `/opt/venv`; la stage `runtime` solo copia ese venv y el código. El binario de `uv` se importa desde `ghcr.io/astral-sh/uv:0.11.19`.

### Build

```bash
# API — el contexto es backend/, no la raíz
docker build -f backend/Dockerfile -t helpdesk-api:latest backend/

# Apuntando explícitamente al stage runtime (por defecto)
docker build --target runtime -f backend/Dockerfile -t helpdesk-api:prod backend/

# UI Streamlit
docker build -f frontend/Dockerfile -t helpdesk-ui:latest frontend/
```

### Ejecutar solo la API

```bash
cp .env.example .env                # editar con tu OPENAI_API_KEY

docker run -d \
  --name helpdesk_api \
  --env-file .env \
  -p 8000:8000 \
  -v $(pwd)/backend/data/chroma_db:/app/data/chroma_db \
  -v $(pwd)/backend/docs:/app/docs:ro \
  helpdesk-api:latest
```

### Ejecutar con Docker Compose (recomendado)

```bash
# Levantar todos los servicios (API + UI)
docker compose up -d

# Logs en tiempo real
docker compose logs -f

# Solo logs de la API
docker compose logs -f api

# Estado de los servicios
docker compose ps

# Detener sin eliminar volúmenes
docker compose stop

# Detener y eliminar contenedores (volúmenes persisten)
docker compose down

# Detener y eliminar TODO (incluye volúmenes con ChromaDB)
docker compose down -v
```
  Resumen de comandos

  # Primera vez
  docker compose up --build
  docker compose exec api python scripts/ingest.py

  # Veces siguientes
  docker compose up

  # Apagar
  docker compose down

  # Ver logs en tiempo real
  docker compose logs -f

  ---
  Si algo falla

  # Ver qué contenedores están corriendo
  docker compose ps

  # Ver logs de un servicio específico
  docker compose logs api
  docker compose logs ui3
  
### Ingesta dentro del contenedor

```bash
# Con docker compose activo
docker compose exec api python scripts/ingest.py

# Contenedor standalone
docker exec -it helpdesk_api python scripts/ingest.py

# Vía API (sin acceso al contenedor)
curl -X POST http://localhost:8000/ingest \
  -H "Content-Type: application/json" \
  -d '{"limpiar": false}'
```

### Verificar salud

```bash
curl http://localhost:8000/health
```

---

## Tests

```bash
# Desde backend/ — la config de pytest vive en backend/pyproject.toml
cd backend

# Suite unitaria completa
uv run pytest tests/unit -v

# Un test específico
uv run pytest tests/unit/services/test_routing_service.py -v

# Un caso individual
uv run pytest tests/unit/services/test_routing_service.py::test_palabra_de_escalacion_siempre_escala -v
```

También funciona desde la raíz con `uv run --project backend pytest backend/tests/unit -v`, pero para los scripts (`uvicorn`, `ingest.py`) sí hace falta `cd backend` porque los imports son `from app.xxx`.

La estrategia es usar los `Protocol` de `services/interfaces.py` y `repositories/interfaces.py` para mockear dependencias externas en tests unitarios. La carpeta `tests/integration/` se reserva para tests que hitan ChromaDB y el LLM real.

---

## Roadmap

| Etapa | Estado | Descripcion |
|-------|--------|-------------|
| **Etapa 0** | Completada | MVP RAG con FastAPI + arquitectura en capas DDD |
| **Etapa 1** | En progreso | Ingesta de historial de emails, mejora de scoring |
| **Etapa 2** | Planeada | Integración con ServiceDesk, evaluador QA |
| **Etapa 3** | Planeada | Hardening: caching, observabilidad, PII redaction, JWT |

Ver [`docs/PRD.md`](docs/PRD.md) para la especificación completa.
