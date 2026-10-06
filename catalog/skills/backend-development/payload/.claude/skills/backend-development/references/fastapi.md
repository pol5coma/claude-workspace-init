# FastAPI reference

- Routers live per domain (`APIRouter(prefix="/users", tags=["users"])`) and are included in the app factory.
- Request/response models are Pydantic models. Use `response_model` to control what is returned.
- Dependencies (`Depends`) provide DB sessions, current user and settings. Do not create sessions inside handlers.
- Use `async def` only when the whole call chain is async (async driver, httpx.AsyncClient). Blocking calls in async handlers stall the event loop.
- Raise `HTTPException(status_code=..., detail=...)` for expected errors; register exception handlers for domain errors.
- Settings via `pydantic-settings` `BaseSettings`; never read `os.environ` scattered across modules.
- Tests: `fastapi.testclient.TestClient` or `httpx.AsyncClient(transport=ASGITransport(app))`; override dependencies with `app.dependency_overrides`.
- Dev server: `fastapi dev` (or `uvicorn app.main:app --reload`).
