from datetime import datetime, timezone
import re
import icalendar
import requests
import streamlit as st

# Configuración de la página
st.set_page_config(
    page_title="Aules Dashboard",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Estilo personalizado para TV / Modo Oscuro
st.markdown(
    """
    <style>
    .main {
        background-color: #0e1117;
        color: #ffffff;
    }
    .task-card {
        background-color: #1e222a;
        padding: 20px;
        border-radius: 12px;
        border-left: 6px solid #4CAF50;
        margin-bottom: 15px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.3);
    }
    .task-urgent {
        border-left-color: #f44336 !important; /* Rojo: menos de 24h */
    }
    .task-warning {
        border-left-color: #ff9800 !important; /* Naranja: menos de 3 días */
    }
    .task-title {
        font-size: 1.3rem;
        font-weight: bold;
        margin-bottom: 5px;
    }
    .task-meta {
        font-size: 0.95rem;
        color: #b0b3b8;
    }
    .countdown-badge {
        display: inline-block;
        background-color: #2d3139;
        padding: 5px 12px;
        border-radius: 20px;
        font-weight: bold;
        font-size: 1.1rem;
        margin-top: 10px;
    }
    </style>
""",
    unsafe_allow_html=True,
)


def clean_html(text):
  """Limpia etiquetas HTML de las descripciones del iCal."""
  if not text:
    return ""
  clean = re.compile("<.*?>")
  return re.sub(clean, "", text).strip()


@st.cache_data(ttl=600)  # Recarga los datos automáticamente cada 10 minutos
def parse_aules_ical(ical_url):
  try:
    response = requests.get(ical_url, timeout=10)
    if response.status_code != 200:
      return None, f"Error HTTP {response.status_code}"

    cal = icalendar.Calendar.from_ical(response.content)
    tasks = []
    now = datetime.now(timezone.utc)

    for component in cal.walk("VEVENT"):
      dtend = component.get("dtend") or component.get("dtstart")
      if dtend:
        due_date = dtend.dt
        if not isinstance(due_date, datetime):
          # Convertir date simple a datetime UTC
          due_date = datetime.combine(
              due_date, datetime.min.time(), tzinfo=timezone.utc
          )
        elif due_date.tzinfo is None:
          due_date = due_date.replace(tzinfo=timezone.utc)

        if due_date > now:  # Tareas pendientes
          summary = str(component.get("summary", "Tarea sin nombre"))
          description = clean_html(
              str(component.get("description", "Sin descripción"))
          )

          # Extraer información útil del texto
          delta = due_date - now
          seconds_left = int(delta.total_seconds())

          days = delta.days
          hours, remainder = divmod(delta.seconds, 3600)
          minutes, seconds = divmod(remainder, 60)

          time_str = f"{days}d {hours}h {minutes}m" if days > 0 else f"{hours}h {minutes}m {seconds}s"

          tasks.append({
              "title": summary,
              "description": description,
              "due_date": due_date.strftime("%d/%m/%Y %H:%M"),
              "seconds_left": seconds_left,
              "time_str": time_str,
              "days_left": days,
          })

    # Ordenar de la más urgente a la menos urgente
    tasks.sort(key=lambda x: x["seconds_left"])
    return tasks, None

  except Exception as e:
    return None, str(e)


# --- INTERFAZ / DASHBOARD ---

st.title("🎓 Dashboard de Entregas - Aules")

# Barra lateral para configurar la URL
with st.sidebar:
  st.header("⚙️ Configuración")
  ical_url = st.text_input(
      "URL del Calendario iCal:",
      placeholder="https://aules.edu.gva.es/moodle/calendar/export_execute.php?...",
      type="password",
  )
  st.caption(
      "Obtenla en Aules > Calendario > Exportar calendario > Obtener URL del"
      " calendario."
  )
  auto_refresh = st.checkbox("Modo TV (Auto-refresco)", value=True)

if not ical_url:
  st.info(
      "👈 Introduce tu URL de iCal de Aules en la barra lateral para empezar."
  )
else:
  tasks, error = parse_aules_ical(ical_url)

  if error:
    st.error(f"Error al obtener las tareas: {error}")
  elif not tasks:
    st.success("🎉 ¡No tienes tareas pendientes próximas en Aules!")
  else:
    # Métricas generales
    col1, col2 = st.columns(2)
    with col1:
      st.metric("Tareas Pendientes", len(tasks))
    with col2:
      urgentes = sum(1 for t in tasks if t["days_left"] < 1)
      st.metric("Urgentes (< 24h)", urgentes)

    st.markdown("---")

    # Renderizado de tarjetas de tareas
    for task in tasks:
      card_class = "task-card"
      if task["days_left"] < 1:
        card_class += " task-urgent"
      elif task["days_left"] < 3:
        card_class += " task-warning"

      st.markdown(
          f"""
        <div class="{card_class}">
            <div class="task-title">📌 {task['title']}</div>
            <div class="task-meta">📅 <b>Fecha límite:</b> {task['due_date']}</div>
            <div class="countdown-badge">⏳ Quedan: {task['time_str']}</div>
        </div>
        """,
          unsafe_allow_html=True,
      )

      # Mostrar detalle/descripción replegable si existe
      if task["description"]:
        with st.expander("Ver detalles de la tarea"):
          st.write(task["description"])

  # Auto-refresco de pantalla para la TV cada 60 segundos
  if auto_refresh:
    import time

    time.sleep(60)
    st.rerun()