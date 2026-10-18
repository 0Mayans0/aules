"""Construye el sitio estático para GitHub Pages: copia static/ + genera data.json."""

import asyncio
import json
import os
import shutil
import sys
from pathlib import Path

BASE = Path(__file__).parent
OUT = BASE / "_site"
DOMAIN = os.getenv("AULES_DOMAIN", "aules.trayans.online")


def write_calendars_from_env() -> None:
  """Si existe la variable secreta AULES_CALENDARS, se usa como configuración."""
  raw = os.getenv("AULES_CALENDARS", "").strip()
  if raw:
    json.loads(raw)  # valida que sea JSON
    (BASE / "calendars.json").write_text(raw, encoding="utf-8")


async def main() -> int:
  write_calendars_from_env()

  import ical_service

  data = await ical_service.get_tasks(force=True)
  errors = data.get("errors", [])

  if errors:
    print("Avisos del fetch:")
    for err in errors:
      print(f"  - {err}")
    if data["total"] == 0:
      print("ERROR: no se pudo obtener ningún dato, se aborta el despliegue.")
      return 1

  if OUT.exists():
    shutil.rmtree(OUT)
  shutil.copytree(BASE / "static", OUT)

  (OUT / "data.json").write_text(
      json.dumps(data, ensure_ascii=False), encoding="utf-8"
  )
  (OUT / "CNAME").write_text(DOMAIN + "\n", encoding="utf-8")

  print(f"OK: {data['total']} tareas ({data['urgent']} urgentes) -> _site/")
  return 0


if __name__ == "__main__":
  sys.exit(asyncio.run(main()))
