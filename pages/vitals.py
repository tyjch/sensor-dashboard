import streamlit as st
import pandas as pd
from datetime import datetime
from influx.scripts import run_script
from influx.client import client

from types import MappingProxyType

# Default vital signs values (immutable)
DEFAULT_VITALS = MappingProxyType({
    'temperature': 97.5,
    'systolic': 125,
    'diastolic': 60,
    'heart_rate': 55,
    'respiration_rate': 12,
    'oxygen_saturation': 95
})

@st.cache_data(ttl=60)  # Cache for 1 minute to avoid repeated queries
def get_latest_vitals():
    """Fetch the latest vitals from InfluxDB using flux script"""
    try:
        result = run_script('latest_vitals.flux')
        
        if isinstance(result, pd.DataFrame) and not result.empty:
            # Extract the latest values from the DataFrame
            latest_record = result.iloc[-1]
            # Create dict using comprehension
            return {key: latest_record.get(key, DEFAULT_VITALS[key]) 
                   for key in DEFAULT_VITALS.keys()}
            
    except Exception as e:
        st.error(f"Error loading vitals from database: {e}")
    
    # Return defaults if no data found or on error
    return dict(DEFAULT_VITALS)

def save_vitals_to_influx(vitals_data):
    """Save vitals to InfluxDB (only fields that differ from current session state)"""
    try:
        from influxdb_client.client.write_api import SYNCHRONOUS
        from influxdb_client import Point
        import os
        
        # Compare against current session state values
        current_values = {
            'temperature': st.session_state['vitals.temperature'],
            'systolic': st.session_state['vitals.blood_pressure.systolic'],
            'diastolic': st.session_state['vitals.blood_pressure.diastolic'],
            'heart_rate': st.session_state['vitals.heart_rate'],
            'respiration_rate': st.session_state['vitals.respiration_rate'],
            'oxygen_saturation': st.session_state['vitals.oxygen_saturation']
        }
        
        # Only add fields that differ from session state
        fields_to_write = {}
        for field, value in vitals_data.items():
            if value != current_values.get(field):
                fields_to_write[field] = value
        
        # Only write if we have at least one changed field
        if len(fields_to_write) > 0:
            # Create a Point object
            point = Point("vitals").time(datetime.now())
            
            # Add fields to the point
            for field, value in fields_to_write.items():
                point = point.field(field, value)
            
            # Write to InfluxDB using the existing client
            with client.write_api(write_options=SYNCHRONOUS) as write_api:
                write_api.write(bucket="thermometer", org=os.getenv('INFLUXDB_V2_ORG'), record=point)
            
            return True
        else:
            st.info("No changes detected - nothing to save")
            return True  # Consider this a success since no action was needed
        
    except Exception as e:
        st.error(f"Error saving vitals to database: {e}")
        return False

# Load latest vitals when the app starts
if 'vitals.loaded' not in st.session_state:
    latest_vitals = get_latest_vitals()
    
    # Store individual vitals in session state
    st.session_state['vitals.temperature'] = latest_vitals['temperature']
    st.session_state['vitals.heart_rate'] = latest_vitals['heart_rate']
    st.session_state['vitals.respiration_rate'] = latest_vitals['respiration_rate']
    st.session_state['vitals.oxygen_saturation'] = latest_vitals['oxygen_saturation']
    
    # Store blood pressure components separately
    st.session_state['vitals.blood_pressure.systolic'] = latest_vitals['systolic']
    st.session_state['vitals.blood_pressure.diastolic'] = latest_vitals['diastolic']
    
    st.session_state['vitals.loaded'] = True

def title(text, icon):
    st.markdown(f'{icon} **{text}**')  

def temperature():
    with st.container(key='container.temperature'):
        label = 'Temperature'
        icon = ':material/thermometer:'
        title(text=label, icon=icon)
        
        default_temp = st.session_state['vitals.temperature']
        temperature = st.slider(
            label=label,
            value=default_temp,
            step=0.1,
            min_value=95.0,
            max_value=110.0,
            label_visibility='collapsed',
            format='%.1f'
        )
        return temperature

def blood_pressure():
    with st.container(key='container.blood_pressure'):
        label = 'Blood Pressure'
        icon = ':material/blood_pressure:'
        title(text=label, icon=icon)
        
        default_bp = (
            st.session_state['vitals.blood_pressure.diastolic'],
            st.session_state['vitals.blood_pressure.systolic']
        )
        bp_values = st.slider(
            label=label,
            value=default_bp,
            step=5,
            min_value=40,       
            max_value=250,      
            label_visibility='collapsed',
            format='%d',
            help="Lower value: Diastolic, Upper value: Systolic"
        )
        return bp_values
      
def heart_rate():
    with st.container(key='container.heart_rate'):
        label = 'Heart Rate'
        icon = ':material/stethoscope:'
        title(text=label, icon=icon)
        
        default_hr = st.session_state['vitals.heart_rate']
        hr = st.slider(
            label=label,
            value=default_hr,
            step=5,
            min_value=30,
            max_value=220,
            label_visibility='collapsed',
            format='%d'
        )
        return hr

def respiration_rate():
    with st.container(key='container.respiration'):
        label = 'Respiration Rate'
        icon = ':material/pulmonology:'
        title(text=label, icon=icon)
        
        default_rr = st.session_state['vitals.respiration_rate']
        rr = st.slider(
            label=label,
            value=default_rr,
            step=1,
            min_value=8,
            max_value=40,
            label_visibility='collapsed',
            format='%d'
        )
        return rr

def oxygen_saturation():
    with st.container(key='container.oxygen_saturation'):
        label = 'O₂ Saturation'
        icon = ':material/oxygen_saturation:'
        title(text=label, icon=icon)
        
        default_o2 = st.session_state['vitals.oxygen_saturation']
        o2 = st.slider(
            label=label,
            value=default_o2,
            step=1,
            min_value=70,
            max_value=100,
            label_visibility='collapsed',
            format='%d%%'
        )
        return o2


st.title('Vitals')

with st.form('vitals_form'):
    # Get all the values
    temp = temperature()
    bp = blood_pressure()
    hr = heart_rate()
    rr = respiration_rate()
    o2 = oxygen_saturation()
    
    # Submit button
    submitted = st.form_submit_button(
        label="Submit Vitals",
        icon=':material/send:', 
        use_container_width=True
    )
    
    if submitted:
        # Prepare data for saving
        vitals_data = {
            'temperature': temp,
            'systolic': bp[1],
            'diastolic': bp[0],
            'heart_rate': hr,
            'respiration_rate': rr,
            'oxygen_saturation': o2
        }
        
        # Save to InfluxDB
        if save_vitals_to_influx(vitals_data):
            st.success(f"✅ Vitals saved successfully!")
            st.success(f"Temp: {temp}°F | BP: {bp[1]}/{bp[0]} mmHg | HR: {hr} bpm | RR: {rr}/min | O₂: {o2}%")
            # Update the session state with new values
            st.session_state['vitals.temperature'] = temp
            st.session_state['vitals.blood_pressure.systolic'] = bp[1]
            st.session_state['vitals.blood_pressure.diastolic'] = bp[0]
            st.session_state['vitals.heart_rate'] = hr
            st.session_state['vitals.respiration_rate'] = rr
            st.session_state['vitals.oxygen_saturation'] = o2
        else:
            st.error("❌ Failed to save vitals to database")