# /influx/scripts.py

import os, warnings
import pandas as pd
import streamlit as st
from string import Template
from pathlib import Path
from loguru import logger
from influxdb_client.client.warnings import MissingPivotFunction
from .client import client


warnings.simplefilter("ignore", MissingPivotFunction)

query_api = client.query_api()

def load_script_template(file_name):
  module_dir = Path(__file__).parent
  file_path  = module_dir / 'flux' / file_name

  try:
    with open(file_path, 'r') as flux_file:
      script = flux_file.read()
      return script
    
  except Exception as e:
    logger.error(f'Error loading flux script ({file_path}): {e}')
  
def run_script(file_name, **kwargs):
  template = Template(load_script_template(file_name=file_name))
  script   = template.substitute(**kwargs)
  
  with client:
    try:
      return query_api.query_data_frame(script)
    except Exception as e:
      logger.error(f'Error running flux script: {e}')
      
def get_latest_temperature():
    try:
        result = run_script('latest_temperature.flux')
        if isinstance(result, pd.DataFrame) and not result.empty:
            # Check if columns exist before accessing them
            if 'temperature_biased' in result.columns:
                st.session_state['data.temperature.latest'] = result['temperature_biased'].iloc[-1]
            if 'bias' in result.columns:
                st.session_state['data.bias.latest'] = result['bias'].iloc[-1]
            if '_time' in result.columns:
                st.session_state['data.measurement.latest'] = pd.to_datetime(result['_time'].iloc[-1])
    except Exception as e:
        st.error(f"Error getting latest temperature: {e}")