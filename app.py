import streamlit as st
import streamlit_nested_layout
from datetime import datetime
from influx.scripts import get_latest_temperature

st.set_page_config(
  page_title            = "Temperature Dashboard",
  page_icon             = "🌡️",
  initial_sidebar_state = "collapsed"
)

def load_css(file_name):
  with open(file_name) as f:
    st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)
        
load_css('assets/style.css')

# SESSION STATE
default_states = {
  'settings.temperature.baseline' : 97.5,
  
  'data.temperature.latest'   : 0.0,
  'data.measurement.latest'   : None,
  #'data.bias.latest'          : 0.0,

  'states.disconnected.limit' : 94.5,
  'states.cold.limit'         : 96.5,
  'states.cool.limit'         : 97.0,
  'states.average.limit'      : 98.0,
  'states.warm.limit'         : 98.5,

  'states.disconnected.color' : None,
  'states.cold.color'         : None,
  'states.cool.color'         : None,
  'states.average.color'      : None,
  'states.warm.color'         : None,
  'states.hot.color'          : None
}

for k,v in default_states.items():
  st.session_state[k] = v

get_latest_temperature()

pages = [
  st.Page(
    title = 'Home',
    page  = 'pages/home.py',
    icon  = ':material/home:'
  ),
  st.Page(
    title = 'Vitals',
    page  = 'pages/vitals.py',
    icon  = ':material/vital_signs:'
  ),
  st.Page(
    title = 'Settings',
    page  = 'pages/settings.py',
    icon  = ':material/settings:'
  )
]

current_page = st.navigation(pages=pages)

current_page.run()