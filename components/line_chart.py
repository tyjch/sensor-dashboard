import streamlit as st
import plotly.express as px
from influxdb.scripts import run_script
import pandas as pd
from datetime import datetime, time
import pytz

def temperature_history():
    # Define labels as variables
    chart_title = "Temperature History"
    x_label = "Time"
    y_label = "Temperature"
    time_column = "_time"
    temp_column = "temperature_biased"
    
    # Define formatting
    decimal_places = 2
    
    # Define chart dimensions
    chart_height = 400
    
    # Get data - timezone and time range handled in Flux
    df = run_script("temperature_history.flux")
    
    # Check if we have data
    if df.empty:
        st.warning("No temperature data available for today.")
        return
    
    # Convert UTC timestamps to local time
    local_tz = pytz.timezone('America/Los_Angeles')
    df[time_column] = pd.to_datetime(df[time_column], utc=True).dt.tz_convert(local_tz)
    
    # Get today's full range in LOCAL time
    now_local = datetime.now(local_tz)
    today_local = now_local.date()
    
    # Create local midnight times
    x_min = local_tz.localize(datetime.combine(today_local, time.min))
    x_max = local_tz.localize(datetime.combine(today_local, time.max))
    
    # Get latest temperature from session state
    latest_temp = st.session_state.get('data.temperature.latest', 0)
    disconnected_limit = st.session_state.get('status.disconnected.limit', 90)
    
    # Set y-axis range and tick interval based on latest temperature
    if latest_temp < disconnected_limit:
        y_min = 60
        y_max = 100
        tick_interval = 5
        y_tick_format = 'd'  # Integer format
    else:
        y_min = 95
        y_max = 100
        tick_interval = 0.5
        y_tick_format = 'g'  # General format (allows decimals)
    
    # Create Plotly chart
    fig = px.line(df, x=time_column, y=temp_column,
                  title=chart_title,
                  labels={temp_column: y_label, time_column: x_label},
                  height=chart_height)
    
    fig.update_layout(
        xaxis=dict(
            fixedrange=True,
            tickformat='%-I:%M %p',
            range=[x_min, x_max]
        ),
        yaxis=dict(
            fixedrange=True, 
            range=[y_min, y_max], 
            tickformat=y_tick_format,
            ticksuffix='°F',
            dtick=tick_interval,
            side='right',
            title=None
        )
    )
    
    fig.update_traces(
        hovertemplate=f'{x_label}: %{{x|%-I:%M %p}}<br>{y_label}: %{{y:.{decimal_places}f}}°F<extra></extra>'
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    with st.expander(label='Data'):
        df