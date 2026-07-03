# AGENTS.md — Helpdesk AI (RAG Soporte al Cliente)

Guía para agentes que trabajan en este repo. Contiene stack, arquitectura, convenciones y todos los gotchas específicos verificados contra el código (no contra el README).

---

## Propósito

Sistema de soporte al cliente basado en RAG. Cada consulta se clasifica en tres acciones: **RESPONDER** automáticamente, **DERIVAR** a ticket, o **ESCALAR** a un agente humano.

---

## Stack

**Backend** — Python 3.11, FastAPI 0.115.0, Uvicorn 0.30.6, Pydantic v2 + pydantic-settings, LangChain 0.3.28, langchain-openai 0.3.35, langchain-huggingface + sentence-transformers, ChromaDB 1.5.8 (SQLite local), langchain-text-splitters, structlog.

**LLM:** `gpt-4o-mini` (OpenAI).
**Embeddings:** `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` (multilingüe, 384-dim).

**Frontend:** Streamlit 1.39.0 (`frontend/app.py`), consume la API vía `API_URL` (default `http://127.0.0.1:8000`).

**Gestor de paquetes:** [uv](https://docs.astral.sh/uv/) (astral-sh). Cada subproyecto (`backend/`, `frontend/`) tiene su propio `pyproject.toml` + `uv.lock`. **No usar `pip` directamente**; siempre `uv sync` / `uv add` / `uv run`.

**Infra:** Docker multi-stage (builder + runtime) con binario `uv` copiado desde `ghcr.io/astral-sh/uv:0.11.19`, Docker Compose, volúmenes `chroma_data` y `logs_data`.

**Tests:** pytest, unit tests con mocks vía `typing.Protocol`. Config de pytest vive en `backend/pyproject.toml` (`[tool.pytest.ini_options]`).

---

## Layout real (el README miente en esto)

- El código Python vive **solo** en `backend/app/`. El README dibuja también un `app/` en la raíz — **no existe**.
- La raíz contiene únicamente `backend/`, `frontend/`, `docker-compose.yml`, `.env`, `.env.example`, `README.md`, `AGENTS.md`, `instrucciones.md`, `interacciones.log`.
- **No hay Dockerfile en la raíz**, solo `backend/Dockerfile` y `frontend/Dockerfile`.
- Dependencias: `backend/pyproject.toml` + `backend/uv.lock` y `frontend/pyproject.toml` + `frontend/uv.lock`. No hay `requirements.txt` ni `pyproject.toml` en la raíz.
- No hay linter/formatter/typechecker configurados. Config de pytest está en `backend/pyproject.toml`.
- `backend/data/chroma_db/` (local) y volumen `chroma_data` (Docker) no se commitean; se generan por ingesta.
- `interacciones.log` en la raíz es runtime — no editar, no commitear.

### Estructura del backend

```
backend/
  app/api/            → Endpoints HTTP (v1/), middleware, dependencies (Depends providers)
  app/core/           → config.py (Settings), logging.py, prompts.py
  app/domain/         → Entidades puras (Fragmento, RespuestaInterna) sin deps externas
  app/schemas/        → DTOs Pydantic + enums (AccionRouter)
  app/services/       → Lógica de negocio, orquestación RAG, Protocols en interfaces.py
  app/repositories/   → ChromaRepository + Protocol VectorStoreRepository
  app/infrastructure/ → OpenAILLMClient, build_embeddings (HuggingFace)
  scripts/            → ingest.py, diagnostico.py (CLIs, no forman parte del runtime)
  tests/              → conftest.py + unit/services/
  docs/               → Base de conocimiento (FAQ, guías, políticas) — fuente única de verdad
  data/               → Persistencia local de ChromaDB (gitignored)
  Dockerfile          → Multi-stage con uv
  pyproject.toml      → Deps declaradas, `[tool.uv] package = false` (app, no librería)
  uv.lock             → Lockfile determinista (commitear siempre)
```

---

## CWD y comandos base (uv)

Setup inicial: crear el entorno virtual reproducible desde el lockfile.

```bash
# En cada subproyecto por separado (no hay workspace)
uv sync --frozen              # backend/  → crea backend/.venv desde uv.lock
uv sync --frozen              # frontend/ → crea frontend/.venv desde uv.lock
```

Todos los imports son `from app.xxx`. Solo funcionan si el CWD es `backend/`:

```bash
# API con hot reload
cd backend && uv run uvicorn app.main:app --reload

# Ingesta inicial (obligatoria antes del primer /ask)
cd backend && uv run python scripts/ingest.py     # --limpiar para recrear la colección

# Tests (config y conftest en backend/)
cd backend && uv run pytest tests/unit -v
cd backend && uv run pytest tests/unit/services/test_routing_service.py::test_palabra_de_escalacion_siempre_escala -v

# Diagnóstico completo del pipeline
cd backend && uv run python scripts/diagnostico.py

# Añadir / quitar dependencias (actualiza pyproject.toml + uv.lock)
cd backend && uv add <paquete>
cd backend && uv remove <paquete>
cd backend && uv lock --upgrade-package <paquete>
```

Alternativa desde la raíz sin `cd`: `uv run --project backend pytest backend/tests/unit -v` funciona porque pytest descubre `backend/pyproject.toml` como rootdir y aplica `pythonpath = ["."]`. Pero para uvicorn/scripts sí hace falta `cd backend` porque los imports `from app.xxx` requieren que `backend/` esté en `sys.path`.

Nunca instalar con `pip install` — sale del entorno gestionado por uv y rompe el lock.

---

## Carga de configuración (gotcha grande)

`backend/app/core/config.py` ancla rutas al **layout del repo, no al CWD**:

- `.env` se carga desde `<repo>/.env` (dos niveles arriba de `backend/`), no desde `backend/.env`.
- `docs_dir` y `chroma_dir` relativos se resuelven contra `<repo>/backend/`, no contra el CWD.
- `get_settings()` está cacheada con `@lru_cache` — no re-lee `.env` en un mismo proceso.

Cambiar `.env` requiere reiniciar el proceso (uvicorn `--reload` no lo detecta automáticamente).

En tests: usar siempre la fixture `settings` de `backend/tests/conftest.py`; nunca construir `Settings()` a mano (leería el `.env` real).

---

## Variables de entorno clave

| Variable | Default | Descripción |
|---|---|---|
| `OPENAI_API_KEY` | (requerido) | Clave de OpenAI |
| `LLM_MODEL` | `gpt-4o-mini` | Modelo de lenguaje |
| `OPENAI_BASE_URL` | — | Opcional, para proxies u OpenAI-compatible |
| `EMBEDDING_MODEL` | `paraphrase-multilingual-MiniLM-L12-v2` | Modelo de embeddings |
| `CONFIDENCE_THRESHOLD` | `0.65` | Score mínimo para "tiene información suficiente" |
| `MINIMUM_SCORE` | `0.60` | Score mínimo para responder automáticamente |
| `TOP_K` | `4` | Fragmentos a recuperar por consulta |
| `CHUNK_SIZE` / `CHUNK_OVERLAP` | `400` / `80` | Chunking en caracteres |
| `DOCS_DIR` | `./docs` | Documentos para ingesta (relativo a `backend/`) |
| `CHROMA_DIR` | `./data/chroma_db` | Persistencia del vector store (relativo a `backend/`) |
| `COLLECTION_NAME` | `soporte_docs` | Colección ChromaDB |
| `HOST` / `PORT` | `0.0.0.0` / `8000` | Servidor |
| `LOG_LEVEL` / `LOG_JSON` | `INFO` / `false` | Logging estructurado |

---

## Docker

- `docker-compose.yml` usa `context: ./backend` con `target: runtime`. **No hay Dockerfile en la raíz** aunque el README lo sugiera.
- Los Dockerfiles usan `uv sync --frozen --no-dev --no-install-project` en la stage builder (venv en `/opt/venv`, luego copiado a la stage runtime). El binario de `uv` se copia desde `ghcr.io/astral-sh/uv:0.11.19` — bumpear ese tag si actualizas uv localmente.
- Compose fuerza `LOG_JSON=true` sin importar el `.env` — logs estructurados en stdout para el driver de logs (Loki, Fluent Bit, CloudWatch).
- El servicio `ui` espera al healthcheck de `api` (`condition: service_healthy`, `start_period: 60s`).
- La imagen corre como `appuser` (uid 1001). Volúmenes montados deben ser escribibles por ese uid.
- Docs se montan **read-only** en `/app/docs`. Editar docs requiere rebuild o cambiar el mount.
- ChromaDB persiste en el volumen `chroma_data` (no se reconstruye entre restarts).

Primera vez y solo entonces:
```bash
docker compose up --build -d
docker compose exec api python scripts/ingest.py
```

Uso normal: `docker compose up -d` / `docker compose logs -f api` / `docker compose down`.
`docker compose down -v` elimina también los volúmenes (borra la base vectorial).

---

## Arquitectura — puntos no obvios

Patrón: **monolito modular en capas DDD** con DI explícita vía `typing.Protocol`.

Flujo de `POST /ask`:
```
PreguntaRequest (Pydantic)
  → RAGServiceImpl.consultar()
      → retrieval_service.recuperar()      [ChromaDB similarity]
      → generation_service.generar()       [OpenAI]
      → scoring_service.calcular()         [LLM evalúa 0.0–1.0]
      → derivation_service.requiere()      [LLM: ¿necesita 2do nivel?]
  → RespuestaInterna (dominio)
  → routing_service.definir_accion()       [RESPONDER | DERIVAR | ESCALAR]
  → PreguntaResponse (DTO)
  → BackgroundTask: registrar en interacciones.log
```

Endpoints: `GET /`, `GET /health`, `POST /ask`, `POST /ingest`.

Notas que un agente pasaría por alto:

- Wire-up manual en `backend/app/main.py` (`lifespan`). No hay contenedor DI: los servicios se instancian y se cuelgan en `app.state`. Providers de FastAPI leen desde ahí (`backend/app/api/dependencies.py`).
- El endpoint `POST /ingest` reconstruye el `RAGService` completo al terminar, vía `app.state.rebuild_rag_service` (ver `backend/app/api/v1/admin.py:22`). La ingesta usa `BackgroundTasks`.
- `rag_service.estadisticas` se **monkey-patchea** en el lifespan (`backend/app/main.py:72`). No buscar el método en la clase.
- El routing (`RESPONDER | DERIVAR | ESCALAR`) vive **fuera** de `rag_service`: se invoca desde el endpoint `POST /ask` con datos de la `RespuestaInterna`.
- Reglas del router (`backend/app/services/routing_service.py`): palabra clave de escalación → ESCALAR (tiene prioridad); `score < 0.3` → ESCALAR; con info y `score > minimum_score` + derivación requerida → DERIVAR; con info y `score > minimum_score` → RESPONDER; default → ESCALAR.
- Contratos vía `typing.Protocol` en `services/interfaces.py` y `repositories/interfaces.py`. Implementaciones llevan sufijo `Impl`. Los tests mockean por Protocol (no herencia).
- Prompts centralizados en `backend/app/core/prompts.py`. No hardcodear prompts en servicios.
- Todo el conocimiento del sistema proviene de `backend/docs/` — no añadir hechos en prompts.
- Los thresholds son env vars, no constantes en código.

---

## Convenciones de código

- Carpetas y módulos: `snake_case`.
- Clases: `PascalCase`. Implementaciones de servicios/repos: sufijo `Impl`.
- Funciones y métodos: `snake_case`.
- Constantes y prompts: `UPPER_SNAKE_CASE` (`PROMPT_SISTEMA`, `PALABRAS_ESCALACION`).
- Enums: `PascalCase.UPPER_SNAKE_CASE` (`AccionRouter.RESPONDER`).
- Type hints obligatorios en métodos públicos. Usar tipos nativos 3.10+ (`list[X]`, no `List[X]`).
- Abstracciones vía `typing.Protocol`, no ABCs.
- Logging por módulo con `logger = logging.getLogger(__name__)`. Nunca `print()` en código de aplicación.
- Comentarios solo cuando el **por qué** no es obvio.
- Separación de capas estricta: los services no conocen FastAPI ni Pydantic; los schemas no llevan lógica de negocio.

---

## Tests

- Solo hay unit tests (`backend/tests/unit/services/test_routing_service.py`). `tests/integration/` está vacío y reservado.
- Fixture `settings` en `backend/tests/conftest.py` — usar siempre.
- No hay tests de la capa API ni de ChromaDB. Al añadir features, mockear por Protocol.

---

## Idioma

Todo el código, comentarios, docstrings, mensajes de log, nombres de variables y prompts están en **español**. Mantener consistencia.

---

## Seguridad (estado actual)

- La API **no** tiene autenticación de clientes. No exponer a internet sin agregar auth.
- HTTPS se resuelve en un reverse proxy (nginx/traefik) en producción.
- `interacciones.log` puede contener PII de usuarios; revisar antes de persistir fuera del entorno de dev.
