import streamlit as st


def title(text, icon):
  st.markdown(f'{icon} **{text}**')  

def temperature():
  with st.container(key='container.temperature'):
    label = 'Temperature'
    icon  = ':material/thermometer:'
    title(text=label, icon=icon)
    
    temperature = st.slider(
      label     = label,
      value     = 97.5,
      step      = 0.1,
      min_value = 95.0,  # Hypothermia range
      max_value = 110.0, # High fever range
      label_visibility = 'collapsed',
      format    = '%.1f'
    )

def blood_pressure():
  with st.container(key='container.blood_pressure'):
    label = 'Blood Pressure'
    icon  = ':material/blood_pressure:'
    title(text=label, icon=icon)
    
    # Using range slider for systolic/diastolic
    bp_values = st.slider(
      label = label,
      value = (60, 125),
      step  = 5,
      min_value = 40,       
      max_value = 250,      
      label_visibility = 'collapsed',
      format = '%d',
      help   = "Lower value: Diastolic, Upper value: Systolic"
    )
      
def heart_rate():
  with st.container(key='container.heart_rate'):
    label = 'Heart Rate'
    icon  = ':material/stethoscope:'
    title(text=label, icon=icon)
    st.slider(
      label = label,
      value = 55,  
      step  = 5,
      min_value = 30,
      max_value = 220,
      label_visibility = 'collapsed',
      format = '%d'
    )

def respiration_rate():
  with st.container(key='container.respiration'):
    label = 'Respiration Rate'
    icon  = ':material/pulmonology:'
    title(text=label, icon=icon)
    st.slider(
      label = label,
      value = 12,       
      step  = 1,
      min_value = 8,   
      max_value = 40,   
      label_visibility = 'collapsed',
      format = '%d'
    )

def oxygen_saturation():
  with st.container(key='container.oxygen_saturation'):
    label = 'O₂ Saturation'
    icon  = ':material/oxygen_saturation:'
    title(text=label, icon=icon)
    st.slider(
      label = label,
      value = 95,
      step  = 1,
      min_value = 70,
      max_value = 100,
      label_visibility = 'collapsed',
      format = '%d%%'
    )


st.title('Vitals')
with st.form('vitals_form'):
  temperature()
  blood_pressure()
  heart_rate()
  respiration_rate()
  oxygen_saturation()
  st.form_submit_button(icon=':material/send:', use_container_width=True)