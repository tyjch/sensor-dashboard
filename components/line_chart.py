import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from influxdb.scripts import run_script
import pandas as pd
from datetime import datetime, time
import pytz
import asyncio
import threading

@st.cache_data(ttl=60)  # Cache for 60 seconds
def get_temperature_data():
    """Cached function to fetch temperature data from InfluxDB."""
    return run_script("temperature_history.flux")

def get_temperature_data_async():
    """Background function to refresh the cache."""
    try:
        # Clear the cache and fetch fresh data
        get_temperature_data.clear()
        return get_temperature_data()
    except Exception as e:
        st.error(f"Background data refresh failed: {e}")
        return None

def temperature_history():
    # Define labels as variables
    chart_title = "Temperature History"
    x_label = "Time"
    y_label = "Temperature"
    time_column = "_time"
    
    # Define formatting
    decimal_places = 2
    
    # Define chart dimensions
    chart_height = 500  # Increased for subplots
    
    # Streamlit pills for controlling series visibility
    st.write("**Show Series:**")
    pills_selection = st.pills(
        "Select series to display:",
        ["Temperature (Biased)", "Temperature (Raw)", "Bias"],
        default=["Temperature (Biased)", "Temperature (Raw)", "Bias"],
        selection_mode="multi",  # Allow multiple selections
        label_visibility="collapsed"
    )
    
    # Determine which subplots to show
    show_temperature = "Temperature (Biased)" in pills_selection or "Temperature (Raw)" in pills_selection
    show_bias = "Bias" in pills_selection
    
    # If no series selected, show message
    if not pills_selection:
        st.info("Please select at least one series to display.")
        return
    
    # Try to get cached data first (non-blocking)
    try:
        df = get_temperature_data()
    except:
        df = None
    
    # If no cached data available, show a placeholder and fetch data
    if df is None or df.empty:
        with st.spinner("Loading temperature data..."):
            df = run_script("temperature_history.flux")
        
        if df is None:
            st.error("Failed to retrieve temperature data from database.")
            return
        
        if df.empty:
            st.warning("No temperature data available for today.")
            return
    
    # Display the chart with current data
    plot_container = st.empty()
    
    # Background refresh (non-blocking)
    if 'last_refresh' not in st.session_state:
        st.session_state.last_refresh = datetime.now()
    
    # Check if we should refresh in the background (every 30 seconds)
    time_since_refresh = (datetime.now() - st.session_state.last_refresh).total_seconds()
    if time_since_refresh > 30:
        # Start background refresh
        st.session_state.last_refresh = datetime.now()
        # Note: This will refresh the cache for the next page load
        threading.Thread(target=get_temperature_data_async, daemon=True).start()
    
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
        tick_interval = 1  # Every integer for less vertical space
        y_tick_format = 'd'  # Integer format (no decimals)
    
    # Create subplots based on what's selected
    if show_temperature and show_bias:
        # Both subplots
        fig = make_subplots(
            rows=2, cols=1,
            vertical_spacing=0.12,
            row_heights=[0.5, 0.5],
            shared_xaxes=True,
            specs=[[{"secondary_y": False}], [{"secondary_y": False}]]
        )
    elif show_temperature or show_bias:
        # Single subplot
        fig = go.Figure()
    else:
        return
    
    # Add temperature traces if selected
    if show_temperature:
        row_num = 1 if show_bias else None
        col_num = 1 if show_bias else None
        
        if "Temperature (Biased)" in pills_selection:
            fig.add_trace(go.Scatter(
                x=df[time_column],
                y=df['temperature_biased'],
                mode='lines',
                name='Temperature (Biased)',
                line=dict(color='#1f77b4', width=3),
                hovertemplate=f'{x_label}: %{{x|%-I:%M %p}}<br>Biased Temp: %{{y:.{decimal_places}f}}°F<extra></extra>',
                showlegend=False  # No legend needed with pills
            ), row=row_num, col=col_num)
        
        if "Temperature (Raw)" in pills_selection:
            fig.add_trace(go.Scatter(
                x=df[time_column],
                y=df['temperature_raw'],
                mode='lines',
                name='Temperature (Raw)',
                line=dict(color='#ff7f0e', width=2, dash='dash'),
                hovertemplate=f'{x_label}: %{{x|%-I:%M %p}}<br>Raw Temp: %{{y:.{decimal_places}f}}°F<extra></extra>',
                showlegend=False  # No legend needed with pills
            ), row=row_num, col=col_num)
    
    # Add bias trace if selected
    if show_bias and "Bias" in pills_selection:
        row_num = 2 if show_temperature else None
        col_num = 1 if show_temperature else None
        
        fig.add_trace(go.Scatter(
            x=df[time_column],
            y=df['bias'],
            mode='lines',
            name='Bias',
            line=dict(color='#2ca02c', width=2),
            hovertemplate=f'{x_label}: %{{x|%-I:%M %p}}<br>Bias: %{{y:.{decimal_places}f}}°F<extra></extra>',
            showlegend=False  # No legend needed with pills
        ), row=row_num, col=col_num)
    
    # Update layout (add shared legend below plots)
    fig.update_layout(
        title=chart_title,
        height=chart_height,
        hovermode='x unified',  # Unified hover mode
        showlegend=True,  # Show legend
        legend=dict(
            orientation="h",  # Horizontal legend
            yanchor="top",
            y=-0.1,  # Position below the plots
            xanchor="center",
            x=0.5,  # Center horizontally
            bgcolor='rgba(255,255,255,0)',  # Transparent background
            borderwidth=0,  # Remove border
            groupclick="togglegroup"  # When clicking legend, toggle entire group
        ),
        spikedistance=1000,  # Large distance to ensure spikes work across subplots
        hoverdistance=1000   # Large distance for hover detection
    )
    
    # CRUCIAL: Update all traces to use the same x-axis for spike lines to work across subplots
    fig.update_traces(xaxis="x")
    
    # Update x-axes (enable spikes for crossfilter cursor and restore tick labels)
    fig.update_xaxes(
        tickformat='%-I %p',  # Remove minutes, show just hour and AM/PM
        range=[x_min, x_max],
        fixedrange=True,
        title_text="",  # Remove x-axis titles
        showspikes=True,  # Enable vertical spike line
        spikemode='across',  # Spike line goes across entire subplot
        spikesnap='cursor',  # Spike follows cursor precisely
        spikecolor='gray',  # Color of the spike line
        spikethickness=1,   # Thickness of the spike line
        spikedash='solid',  # Style of the spike line
        showticklabels=True  # Explicitly show tick labels on all x-axes
    )
    
    # Update temperature y-axis (top subplot) - move ticks to right, remove title
    fig.update_yaxes(
        range=[y_min, y_max], 
        tickformat=y_tick_format,
        ticksuffix='°F',
        dtick=tick_interval,
        fixedrange=True,
        side='right',  # Move ticks to right side
        title_text="",  # Remove y-axis title
        row=1, col=1
    )
    
    # Update bias y-axis (bottom subplot) - move ticks to right, remove title
    fig.update_yaxes(
        tickformat='.1f',
        ticksuffix='°F',
        dtick=0.5,
        fixedrange=True,
        side='right',  # Move ticks to right side
        title_text="",  # Remove y-axis title
        row=2, col=1
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    with st.expander(label='Data'):
        df