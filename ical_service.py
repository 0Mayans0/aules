"""Servicio de datos: descarga y parsea los feeds iCal de Aules con caché TTL."""

import asyncio
import hashlib
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import httpx
import icalendar

TZ = ZoneInfo("Europe/Madrid")
CACHE_TTL = int(os.getenv("AULES_CACHE_TTL", "600"))
FETCH_TIMEOUT = 15

_TEACHER_RE = re.compile(
    r"(?:profesor(?:a)?|docente|teacher)\s*:?\s*([^\n.,;|]+)", re.IGNORECASE
)
_HTML_TAG_RE = re.compile(r"<[^>]+>")

_cache = {"at": None, "data": None}
_lock = asyncio.Lock()


def load_calendars() -> list[dict]:
  """Carga la lista de calendarios desde config o variables de entorno."""
  config_path = Path(os.getenv("AULES_CALENDARS_FILE", "calendars.json"))
  if config_path.exists():
    with open(config_path, encoding="utf-8") as fh:
      return json.load(fh)
  return json.loads(os.getenv("AULES_CALENDARS", "[]"))


def _clean_html(text: str) -> str:
  return _HTML_TAG_RE.sub(" ", text or "").strip()


def _to_datetime(value) -> datetime | None:
  if value is None:
    return None
  dt = value.dt if hasattr(value, "dt") else value
  if not isinstance(dt, datetime):
    dt = datetime.combine(dt, datetime.min.time())
  if dt.tzinfo is None:
    dt = dt.replace(tzinfo=TZ)
  return dt.astimezone(TZ)


def _extract_teacher(description: str) -> str:
  match = _TEACHER_RE.search(description or "")
  return match.group(1).strip() if match else ""


def _urgency(seconds_left: int) -> str:
  if seconds_left < 86400:
    return "urgent"
  if seconds_left < 3 * 86400:
    return "warning"
  return "ok"


def _parse_calendar(name: str, content: bytes, now: datetime) -> list[dict]:
  cal = icalendar.Calendar.from_ical(content)
  tasks = []

  for event in cal.walk("VEVENT"):
    due = _to_datetime(event.get("dtend")) or _to_datetime(event.get("dtstart"))
    if not due or due <= now:
      continue

    title = str(event.get("summary", "Tarea sin nombre"))
    description = _clean_html(str(event.get("description", "")))
    teacher = _extract_teacher(description) or str(event.get("location", "")).strip()

    seconds_left = int((due - now).total_seconds())
    uid = str(event.get("uid", f"{name}:{title}:{due.isoformat()}"))
    task_id = hashlib.sha1(f"{uid}:{name}".encode()).hexdigest()[:12]

    tasks.append({
        "id": task_id,
        "title": title,
        "subject": name,
        "teacher": teacher,
        "description": description,
        "due": due.isoformat(),
        "seconds_left": seconds_left,
        "urgency": _urgency(seconds_left),
    })

  return tasks


async def _fetch_all() -> dict:
  now = datetime.now(TZ)
  calendars = load_calendars()
  tasks: list[dict] = []
  errors: list[str] = []

  async with httpx.AsyncClient(timeout=FETCH_TIMEOUT, follow_redirects=True) as client:
    results = await asyncio.gather(
        *(
            _safe_fetch(client, cal, now)
            for cal in calendars
        ),
        return_exceptions=True,
    )

  for (cal, result) in zip(calendars, results):
    name = cal.get("name", "Sin nombre")
    if isinstance(result, Exception):
      errors.append(f"{name}: {result}")
    elif isinstance(result, list):
      tasks.extend(result)

  tasks.sort(key=lambda t: t["seconds_left"])
  return {
      "updated_at": datetime.now(timezone.utc).isoformat(),
      "total": len(tasks),
      "urgent": sum(1 for t in tasks if t["urgency"] == "urgent"),
      "tasks": tasks,
      "errors": errors,
  }


async def _safe_fetch(client: httpx.AsyncClient, cal: dict, now: datetime) -> list[dict]:
  url = cal.get("url")
  name = cal.get("name", "Sin nombre")
  if not url:
    raise ValueError("calendario sin url")
  response = await client.get(url)
  response.raise_for_status()
  return _parse_calendar(name, response.content, now)


async def get_tasks(force: bool = False) -> dict:
  """Devuelve las tareas pendientes usando caché TTL en memoria."""
  async with _lock:
    cached = _cache["data"]
    expired = _cache["at"] is None or (
        asyncio.get_event_loop().time() - _cache["at"] > CACHE_TTL
    )
    if cached is not None and not expired and not force:
      return cached

    data = await _fetch_all()
    _cache["at"] = asyncio.get_event_loop().time()
    _cache["data"] = data
    return data
