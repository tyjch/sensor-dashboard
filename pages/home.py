import streamlit as st
import pandas as pd
import plotly.express as px
from components.metrics import latest_temperature_metric, latest_measurement_metric
#from components.line_chart import temperature_history
from influxdb.scripts import run_script, get_latest_temperature
from streamlit_elements import elements, mui, html
from components.line_chart import temperature_history

st.title('Home')

c1, c2, c3, c4 = st.columns(4)

def bias():
  st.number_input(
      label     = 'Current Bias',
      key       = 'data.bias.latest',
      # Other icons: discover_tune, height, instant_mix, unknown_2, swap_vert, tune, expand_all, arrow_split
      icon      = ':material/arrow_split:',
      step      = 0.1,
      format    = '%0.1f',
      min_value = -5.0,
      max_value = 5.0,
    )

st.session_state

with c1:
  latest_temperature_metric()
with c2:
  latest_measurement_metric()

temperature_history()


