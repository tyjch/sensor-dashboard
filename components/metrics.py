import inspect
import streamlit as st
from streamlit_elements import elements, mui, html
from abc import ABC, abstractmethod, abstractproperty
from datetime import datetime, time, timedelta, timezone

def latest_temperature_metric():
  latest_temp   = st.session_state.get('data.temperature.latest')
  baseline_temp = st.session_state.get('settings.temperature.baseline')
  
  delta = None
  if latest_temp and latest_temp > 0.0:
    value = f'{latest_temp:.1f} °F'
    if baseline_temp:
      delta = f'{latest_temp-baseline_temp:.1f} °F'
  else:
    value = '-'
  
  return st.metric(
    label            = 'Latest Temperature',
    value            = value,
    delta            = delta,
    label_visibility = 'collapsed'
  )
  
def latest_measurement_metric():
  latest_measurement_time = st.session_state.get('data.measurement.latest')
  now = datetime.now(timezone.utc)
  
  if not latest_measurement_time:
    text = '-'
  elif latest_measurement_time > now:
    text = 'Just now'
  else:
    delta = now - latest_measurement_time
    total_seconds = delta.total_seconds()
    
    if total_seconds < 60:
      text = "Just now"
    elif total_seconds < 3600:
      text = f"{int(total_seconds // 60)}m ago"
    elif total_seconds < 86400:
      text = f"{int(total_seconds // 3600)}h ago"
    else:
      text = f"{int(total_seconds // 86400)}d ago"
      
  return st.metric(
    label            = 'Latest Measurement',
    value            = text,
    label_visibility = 'collapsed',
  )

