"""
Vitals tracking page for medical measurements.
Handles temperature, blood pressure, heart rate, respiration rate, and oxygen saturation.
"""

import streamlit as st
import pandas as pd
from datetime import datetime
from typing import Dict, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import os
from types import MappingProxyType

# Import database modules locally to avoid circular imports
def get_influxdb_modules():
    """Lazy import of InfluxDB modules to avoid circular imports."""
    from influxdb.scripts import run_script
    from influxdb.client import client
    return run_script, client


# Constants and Configuration
class Config:
    """Application configuration constants."""
    INFLUX_BUCKET = "thermometer"
    CACHE_TTL = 60
    CSS_TRANSITION_DURATION = "0.3s"


class SessionKeys:
    """Session state key constants."""
    # Main vital values
    TEMPERATURE = 'vitals.temperature'
    HEART_RATE = 'vitals.heart_rate'
    RESPIRATION_RATE = 'vitals.respiration_rate'
    OXYGEN_SATURATION = 'vitals.oxygen_saturation'
    BP_SYSTOLIC = 'vitals.blood_pressure.systolic'
    BP_DIASTOLIC = 'vitals.blood_pressure.diastolic'
    
    # Change tracking flags
    TEMPERATURE_CHANGED = 'vitals.temperature.changed'
    HEART_RATE_CHANGED = 'vitals.heart_rate.changed'
    RESPIRATION_RATE_CHANGED = 'vitals.respiration_rate.changed'
    OXYGEN_SATURATION_CHANGED = 'vitals.oxygen_saturation.changed'
    BP_CHANGED = 'vitals.blood_pressure.changed'
    
    # System flags
    LOADED = 'vitals.loaded'


class ContainerKeys:
    """CSS container key constants."""
    TEMPERATURE = 'container.temperature'
    HEART_RATE = 'container.heart_rate'
    RESPIRATION = 'container.respiration'
    OXYGEN_SATURATION = 'container.oxygen_saturation'
    BLOOD_PRESSURE = 'container.blood_pressure'


# Default vital signs values (immutable)
DEFAULT_VITALS = MappingProxyType({
    'temperature': 97.5,
    'systolic': 125,
    'diastolic': 60,
    'heart_rate': 55,
    'respiration_rate': 12,
    'oxygen_saturation': 95
})


class VitalsRepository:
    """Data access layer for vitals information."""
    
    @staticmethod
    @st.cache_data(ttl=Config.CACHE_TTL)
    def get_latest() -> Dict[str, Any]:
        """
        Fetch the latest vitals from InfluxDB.
        
        Returns:
            Dictionary containing latest vital signs or defaults if unavailable.
        """
        try:
            run_script, _ = get_influxdb_modules()
            result = run_script('latest_vitals.flux')
            
            if isinstance(result, pd.DataFrame) and not result.empty:
                latest_record = result.iloc[-1]
                # Safely extract values with type checking
                vitals = {}
                for key in DEFAULT_VITALS.keys():
                    value = latest_record.get(key)
                    if pd.notna(value) and value is not None:
                        vitals[key] = float(value) if key == 'temperature' else int(value)
                    else:
                        vitals[key] = DEFAULT_VITALS[key]
                return vitals
                
        except Exception as e:
            st.error(f"Error loading vitals from database: {e}")
        
        return dict(DEFAULT_VITALS)
    
    @staticmethod
    def save(vitals_data: Dict[str, Any]) -> bool:
        """
        Save vitals to InfluxDB (only fields that have been modified).
        
        Args:
            vitals_data: Dictionary containing vital sign values to save.
            
        Returns:
            True if save was successful, False otherwise.
        """
        try:
            from influxdb_client import InfluxDBClient, Point
            from influxdb_client.client.write_api import SYNCHRONOUS
            
            # Check which vitals have been changed
            changed_vitals = VitalsRepository._get_changed_vitals(vitals_data)
            
            if not changed_vitals:
                st.info("No vitals have been modified - nothing to save")
                return True
            
            # Write to InfluxDB
            url = 'https://' + os.getenv('INFLUXDB_V2_URL')
            token = os.getenv('INFLUXDB_V2_TOKEN')
            org = os.getenv('INFLUXDB_V2_ORG')
            
            with InfluxDBClient(url=url, token=token, org=org) as write_client:
                point = Point("vitals").time(datetime.now())
                
                for field, value in changed_vitals.items():
                    point = point.field(field, value)
                
                with write_client.write_api(write_options=SYNCHRONOUS) as write_api:
                    write_api.write(bucket=Config.INFLUX_BUCKET, org=org, record=point)
                
                return True
                
        except Exception as e:
            st.error(f"Error saving vitals to database: {e}")
            return False
    
    @staticmethod
    def _get_changed_vitals(vitals_data: Dict[str, Any]) -> Dict[str, Any]:
        """Get only the vitals that have been changed by the user."""
        changed_vitals = {}
        
        if st.session_state.get(SessionKeys.TEMPERATURE_CHANGED, False):
            changed_vitals['temperature'] = vitals_data['temperature']
            
        if st.session_state.get(SessionKeys.BP_CHANGED, False):
            changed_vitals['systolic'] = vitals_data['systolic']
            changed_vitals['diastolic'] = vitals_data['diastolic']
            
        if st.session_state.get(SessionKeys.HEART_RATE_CHANGED, False):
            changed_vitals['heart_rate'] = vitals_data['heart_rate']
            
        if st.session_state.get(SessionKeys.RESPIRATION_RATE_CHANGED, False):
            changed_vitals['respiration_rate'] = vitals_data['respiration_rate']
            
        if st.session_state.get(SessionKeys.OXYGEN_SATURATION_CHANGED, False):
            changed_vitals['oxygen_saturation'] = vitals_data['oxygen_saturation']
        
        return changed_vitals


class VitalsSession:
    """Session state management for vitals."""
    
    @staticmethod
    def initialize_if_needed() -> None:
        """Initialize session state with latest vitals if not already loaded."""
        if SessionKeys.LOADED not in st.session_state:
            latest_vitals = VitalsRepository.get_latest()
            
            # Store individual vitals with safe type conversion
            VitalsSession._safely_set_vital(
                SessionKeys.TEMPERATURE, 
                latest_vitals.get('temperature'), 
                DEFAULT_VITALS['temperature'], 
                float
            )
            VitalsSession._safely_set_vital(
                SessionKeys.HEART_RATE, 
                latest_vitals.get('heart_rate'), 
                DEFAULT_VITALS['heart_rate'], 
                int
            )
            VitalsSession._safely_set_vital(
                SessionKeys.RESPIRATION_RATE, 
                latest_vitals.get('respiration_rate'), 
                DEFAULT_VITALS['respiration_rate'], 
                int
            )
            VitalsSession._safely_set_vital(
                SessionKeys.OXYGEN_SATURATION, 
                latest_vitals.get('oxygen_saturation'), 
                DEFAULT_VITALS['oxygen_saturation'], 
                int
            )
            VitalsSession._safely_set_vital(
                SessionKeys.BP_SYSTOLIC, 
                latest_vitals.get('systolic'), 
                DEFAULT_VITALS['systolic'], 
                int
            )
            VitalsSession._safely_set_vital(
                SessionKeys.BP_DIASTOLIC, 
                latest_vitals.get('diastolic'), 
                DEFAULT_VITALS['diastolic'], 
                int
            )
            
            # Initialize change tracking flags
            VitalsSession._initialize_change_flags()
            
            st.session_state[SessionKeys.LOADED] = True
    
    @staticmethod
    def _safely_set_vital(key: str, value: Any, default: Any, type_converter: type) -> None:
        """Safely set a vital sign value with type conversion and error handling."""
        try:
            if value is not None and pd.notna(value):
                converted_value = type_converter(value)
                # Additional validation for reasonable ranges
                if key == SessionKeys.TEMPERATURE and (converted_value < 80 or converted_value > 120):
                    st.session_state[key] = default
                elif key == SessionKeys.HEART_RATE and (converted_value < 0 or converted_value > 300):
                    st.session_state[key] = default
                else:
                    st.session_state[key] = converted_value
            else:
                st.session_state[key] = default
        except (ValueError, TypeError, OverflowError):
            st.session_state[key] = default
    
    @staticmethod
    def _initialize_change_flags() -> None:
        """Initialize all change tracking flags to False."""
        change_flags = [
            SessionKeys.TEMPERATURE_CHANGED,
            SessionKeys.BP_CHANGED,
            SessionKeys.HEART_RATE_CHANGED,
            SessionKeys.RESPIRATION_RATE_CHANGED,
            SessionKeys.OXYGEN_SATURATION_CHANGED
        ]
        
        for flag in change_flags:
            st.session_state[flag] = False
    
    @staticmethod
    def update_vitals_after_save(vitals_data: Dict[str, Any]) -> None:
        """Update session state with new values after successful save."""
        st.session_state[SessionKeys.TEMPERATURE] = vitals_data['temperature']
        st.session_state[SessionKeys.BP_SYSTOLIC] = vitals_data['systolic']
        st.session_state[SessionKeys.BP_DIASTOLIC] = vitals_data['diastolic']
        st.session_state[SessionKeys.HEART_RATE] = vitals_data['heart_rate']
        st.session_state[SessionKeys.RESPIRATION_RATE] = vitals_data['respiration_rate']
        st.session_state[SessionKeys.OXYGEN_SATURATION] = vitals_data['oxygen_saturation']
        
        # Reset change tracking flags
        VitalsSession._initialize_change_flags()
    
    @staticmethod
    def reset_to_original_values() -> None:
        """Reset all vitals to their original loaded values from the database."""
        # Get fresh data from database (bypass cache to ensure we get original values)
        VitalsRepository.get_latest.clear()  # Clear the cache
        original_vitals = VitalsRepository.get_latest()
        
        # Reset all vital values to original database values
        VitalsSession._safely_set_vital(
            SessionKeys.TEMPERATURE, 
            original_vitals.get('temperature'), 
            DEFAULT_VITALS['temperature'], 
            float
        )
        VitalsSession._safely_set_vital(
            SessionKeys.HEART_RATE, 
            original_vitals.get('heart_rate'), 
            DEFAULT_VITALS['heart_rate'], 
            int
        )
        VitalsSession._safely_set_vital(
            SessionKeys.RESPIRATION_RATE, 
            original_vitals.get('respiration_rate'), 
            DEFAULT_VITALS['respiration_rate'], 
            int
        )
        VitalsSession._safely_set_vital(
            SessionKeys.OXYGEN_SATURATION, 
            original_vitals.get('oxygen_saturation'), 
            DEFAULT_VITALS['oxygen_saturation'], 
            int
        )
        VitalsSession._safely_set_vital(
            SessionKeys.BP_SYSTOLIC, 
            original_vitals.get('systolic'), 
            DEFAULT_VITALS['systolic'], 
            int
        )
        VitalsSession._safely_set_vital(
            SessionKeys.BP_DIASTOLIC, 
            original_vitals.get('diastolic'), 
            DEFAULT_VITALS['diastolic'], 
            int
        )
        
        # Reset all change tracking flags
        VitalsSession._initialize_change_flags()


class VitalsStyling:
    """CSS styling management for vitals interface."""
    
    @staticmethod
    def inject_dynamic_styles() -> None:
        """Inject dynamic CSS based on which inputs have been changed."""
        styles = VitalsStyling._generate_container_styles()
        st.markdown(f"<style>{styles}</style>", unsafe_allow_html=True)
    
    @staticmethod
    def _generate_container_styles() -> str:
        """Generate CSS styles for vital containers based on change state."""
        containers = [
            ('temperature', SessionKeys.TEMPERATURE_CHANGED),
            ('heart_rate', SessionKeys.HEART_RATE_CHANGED),
            ('respiration', SessionKeys.RESPIRATION_RATE_CHANGED),
            ('oxygen_saturation', SessionKeys.OXYGEN_SATURATION_CHANGED),
            ('blood_pressure', SessionKeys.BP_CHANGED)
        ]
        
        styles = []
        for container_name, change_key in containers:
            changed = st.session_state.get(change_key, False)
            opacity = '1.0' if changed else '0.5'
            filter_value = 'none' if changed else 'grayscale(30%)'
            
            # Fix the container key reference
            container_key_name = container_name.upper().replace('_', '_')
            if hasattr(ContainerKeys, container_key_name):
                container_key = getattr(ContainerKeys, container_key_name)
            else:
                # Fallback mapping
                key_mapping = {
                    'temperature': ContainerKeys.TEMPERATURE,
                    'heart_rate': ContainerKeys.HEART_RATE,
                    'respiration': ContainerKeys.RESPIRATION,
                    'oxygen_saturation': ContainerKeys.OXYGEN_SATURATION,
                    'blood_pressure': ContainerKeys.BLOOD_PRESSURE
                }
                container_key = key_mapping.get(container_name, f'container.{container_name}')
            
            style = f"""
            .st-key-{container_key.replace('.', '-')} {{
                opacity: {opacity};
                filter: {filter_value};
                transition: opacity {Config.CSS_TRANSITION_DURATION} ease, 
                           filter {Config.CSS_TRANSITION_DURATION} ease;
            }}
            """
            styles.append(style)
        
        return '\n'.join(styles)


class VitalsUI:
    """UI components for vitals interface."""
    
    @staticmethod
    def render_title(text: str, icon: str) -> None:
        """Render a title with icon."""
        st.markdown(f'{icon} **{text}**')
    
    @staticmethod
    def render_vital_slider(
        label: str,
        icon: str,
        container_key: str,
        session_key: str,
        change_key: str,
        slider_key: str,
        min_value: float,
        max_value: float,
        step: float,
        format_str: str,
        **kwargs
    ) -> float:
        """
        Render a standardized vital sign slider.
        
        Args:
            label: Display label for the vital sign
            icon: Material icon for the vital sign
            container_key: Key for the container
            session_key: Session state key for the value
            change_key: Session state key for change tracking
            slider_key: Key for the slider widget
            min_value: Minimum slider value
            max_value: Maximum slider value
            step: Slider step size
            format_str: Display format string
            **kwargs: Additional arguments for st.slider
            
        Returns:
            Current slider value
        """
        with st.container(key=container_key):
            VitalsUI.render_title(label, icon)
            
            # Ensure we have a valid default value
            default_value = st.session_state.get(session_key)
            if default_value is None or pd.isna(default_value):
                # Use default from our constants
                if session_key == SessionKeys.TEMPERATURE:
                    default_value = DEFAULT_VITALS['temperature']
                elif session_key == SessionKeys.HEART_RATE:
                    default_value = DEFAULT_VITALS['heart_rate']
                elif session_key == SessionKeys.RESPIRATION_RATE:
                    default_value = DEFAULT_VITALS['respiration_rate']
                elif session_key == SessionKeys.OXYGEN_SATURATION:
                    default_value = DEFAULT_VITALS['oxygen_saturation']
                else:
                    default_value = min_value
                
                # Update session state with the default
                st.session_state[session_key] = default_value
            
            # Ensure the default value is within the specified range
            default_value = max(min_value, min(max_value, default_value))
            
            value = st.slider(
                label=label,
                value=default_value,
                step=step,
                min_value=min_value,
                max_value=max_value,
                label_visibility='collapsed',
                format=format_str,
                key=slider_key,
                on_change=lambda: st.session_state.update({change_key: True}),
                **kwargs
            )
            return value
    
    @staticmethod
    def render_blood_pressure_slider() -> Tuple[int, int]:
        """Render the blood pressure range slider."""
        with st.container(key=ContainerKeys.BLOOD_PRESSURE):
            VitalsUI.render_title('Blood Pressure', ':material/blood_pressure:')
            
            # Get default values and ensure they're valid
            diastolic = st.session_state.get(SessionKeys.BP_DIASTOLIC)
            systolic = st.session_state.get(SessionKeys.BP_SYSTOLIC)
            
            if diastolic is None or pd.isna(diastolic):
                diastolic = DEFAULT_VITALS['diastolic']
                st.session_state[SessionKeys.BP_DIASTOLIC] = diastolic
                
            if systolic is None or pd.isna(systolic):
                systolic = DEFAULT_VITALS['systolic']
                st.session_state[SessionKeys.BP_SYSTOLIC] = systolic
            
            # Ensure proper order (diastolic should be lower than systolic)
            if diastolic >= systolic:
                diastolic = systolic - 20
                st.session_state[SessionKeys.BP_DIASTOLIC] = diastolic
            
            default_bp = (diastolic, systolic)
            
            bp_values = st.slider(
                label='Blood Pressure',
                value=default_bp,
                step=5,
                min_value=40,
                max_value=250,
                label_visibility='collapsed',
                format='%d',
                help="Lower value: Diastolic, Upper value: Systolic",
                key='slider_blood_pressure',
                on_change=lambda: st.session_state.update({SessionKeys.BP_CHANGED: True})
            )
            return bp_values


# Main application logic
def main():
    """Main function for the vitals page."""
    # Initialize session state
    VitalsSession.initialize_if_needed()
    
    # Page title
    st.title('Vitals')
    
    # Render all vital sign sliders
    temp = VitalsUI.render_vital_slider(
        label='Temperature',
        icon=':material/thermometer:',
        container_key=ContainerKeys.TEMPERATURE,
        session_key=SessionKeys.TEMPERATURE,
        change_key=SessionKeys.TEMPERATURE_CHANGED,
        slider_key='slider_temperature',
        min_value=95.0,
        max_value=110.0,
        step=0.1,
        format_str='%.1f'
    )
    
    bp = VitalsUI.render_blood_pressure_slider()
    
    hr = VitalsUI.render_vital_slider(
        label='Heart Rate',
        icon=':material/stethoscope:',
        container_key=ContainerKeys.HEART_RATE,
        session_key=SessionKeys.HEART_RATE,
        change_key=SessionKeys.HEART_RATE_CHANGED,
        slider_key='slider_heart_rate',
        min_value=30,
        max_value=220,
        step=5,
        format_str='%d'
    )
    
    rr = VitalsUI.render_vital_slider(
        label='Respiration Rate',
        icon=':material/pulmonology:',
        container_key=ContainerKeys.RESPIRATION,
        session_key=SessionKeys.RESPIRATION_RATE,
        change_key=SessionKeys.RESPIRATION_RATE_CHANGED,
        slider_key='slider_respiration_rate',
        min_value=8,
        max_value=40,
        step=1,
        format_str='%d'
    )
    
    o2 = VitalsUI.render_vital_slider(
        label='O₂ Saturation',
        icon=':material/oxygen_saturation:',
        container_key=ContainerKeys.OXYGEN_SATURATION,
        session_key=SessionKeys.OXYGEN_SATURATION,
        change_key=SessionKeys.OXYGEN_SATURATION_CHANGED,
        slider_key='slider_oxygen_saturation',
        min_value=70,
        max_value=100,
        step=1,
        format_str='%d%%'
    )
    
    # Apply dynamic styling
    VitalsStyling.inject_dynamic_styles()
    
    # Check if any vitals have been changed
    has_changes = any([
        st.session_state.get(SessionKeys.TEMPERATURE_CHANGED, False),
        st.session_state.get(SessionKeys.BP_CHANGED, False),
        st.session_state.get(SessionKeys.HEART_RATE_CHANGED, False),
        st.session_state.get(SessionKeys.RESPIRATION_RATE_CHANGED, False),
        st.session_state.get(SessionKeys.OXYGEN_SATURATION_CHANGED, False)
    ])
    
    # Create two columns for buttons
    col1, col2 = st.columns(2)
    
    with col1:
        # Reset button - only enabled if there are changes
        reset_clicked = st.button(
            label="Reset",
            icon=':material/refresh:',
            use_container_width=True,
            disabled=not has_changes
        )
    
    with col2:
        # Submit button - only enabled if there are changes
        submitted = st.button(
            label="Submit Vitals",
            icon=':material/send:',
            use_container_width=True,
            disabled=not has_changes
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
        
        # Save to database
        if VitalsRepository.save(vitals_data):
            # Reset change tracking flags first
            VitalsSession.update_vitals_after_save(vitals_data)
            
            # Show success messages
            st.success("✅ Vitals saved successfully!")
            st.success(
                f"Temp: {temp}°F | BP: {bp[1]}/{bp[0]} mmHg | "
                f"HR: {hr} bpm | RR: {rr}/min | O₂: {o2}%"
            )
            
            # Force a rerun to update the UI state
            st.rerun()
        else:
            st.error("❌ Failed to save vitals to database")
    
    if reset_clicked:
        # Reset all vitals to their original loaded values
        VitalsSession.reset_to_original_values()
        st.success("🔄 Vitals reset to original values")
        st.rerun()


if __name__ == "__main__":
    main()