"""Servidor FastAPI del dashboard Aules. Arranque: uvicorn server:app"""

from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

import ical_service

app = FastAPI(title="Aules Dashboard", version="1.0.0")

STATIC_DIR = Path(__file__).parent / "static"


@app.get("/api/tasks")
async def api_tasks():
  """Devuelve las tareas pendientes (caché TTL del servidor)."""
  data = await ical_service.get_tasks()
  return JSONResponse(data)


@app.post("/api/refresh")
async def api_refresh():
  """Fuerza la recarga de todos los calendarios."""
  data = await ical_service.get_tasks(force=True)
  return JSONResponse(data)


@app.get("/health")
async def health():
  return {"status": "ok"}


app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="static")
