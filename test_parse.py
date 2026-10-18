"""Prueba rápida del parseo iCal sin red."""

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import ical_service

TZ = ZoneInfo("Europe/Madrid")
now = datetime.now(TZ)

ics = f"""BEGIN:VCALENDAR
VERSION:2.0
BEGIN:VEVENT
UID:tarea-1@test
SUMMARY:Entrega Práctica 3 - Python
DESCRIPTION:<p>Profesor: Juan García</p>
DTEND:{(now + timedelta(hours=5)).strftime('%Y%m%dT%H%M%S')}
END:VEVENT
BEGIN:VEVENT
UID:tarea-2@test
SUMMARY:Examen Parcial
DESCRIPTION:Examen de la unidad 1
DTEND:{(now + timedelta(days=10)).strftime('%Y%m%dT%H%M%S')}
END:VEVENT
BEGIN:VEVENT
UID:tarea-3@test
SUMMARY:Tarea Pasada
DTEND:{(now - timedelta(days=1)).strftime('%Y%m%dT%H%M%S')}
END:VEVENT
END:VCALENDAR
""".replace("\n", "\r\n")

tasks = ical_service._parse_calendar("Mates", ics.encode(), now)

assert len(tasks) == 2, f"esperaba 2, got {len(tasks)}"
assert tasks[0]["title"] == "Entrega Práctica 3 - Python"
assert tasks[0]["urgency"] == "urgent", tasks[0]
assert tasks[0]["teacher"] == "Juan García"
assert tasks[0]["subject"] == "Mates"
assert tasks[1]["urgency"] == "ok"
assert tasks[0]["seconds_left"] < tasks[1]["seconds_left"]

print("TEST PARSE OK:", [(t["title"], t["urgency"], t["teacher"]) for t in tasks])
