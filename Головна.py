import streamlit as st
import pydeck as pdk
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import time
import math
import random

from utils.network import VinnytsiaLTENetwork
from utils.handover import HandoverController
from utils.visualization import create_realtime_plot
from utils.calculations import calculate_path_loss, calculate_distance

# Конфігурація сторінки
st.set_page_config(
    page_title="Симулятор мережі LTE - Вінниця",
    page_icon="📡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Ініціалізація сесії
if 'network' not in st.session_state:
    st.session_state.network = VinnytsiaLTENetwork()
if 'handover_controller' not in st.session_state:
    st.session_state.handover_controller = HandoverController(st.session_state.network)
if 'ue_position' not in st.session_state:
    st.session_state.ue_position = [49.2328, 28.4810]
if 'simulation_running' not in st.session_state:
    st.session_state.simulation_running = False
if 'handover_history' not in st.session_state:
    st.session_state.handover_history = []
if 'measurements_log' not in st.session_state:
    st.session_state.measurements_log = []
if 'map_key' not in st.session_state:
    st.session_state.map_key = 0

# Заголовок
st.title("🏗️ Симулятор хендовера LTE в мережі м. Вінниця")
st.markdown("### Архітектурні принципи та оптимізація функціонування мережі LTE")
st.markdown("**Бакалаврська робота - Хрустовський А.А.**")

# Sidebar параметри
st.sidebar.header("⚙️ Параметри хендовера")
ttt = st.sidebar.slider("Time-to-Trigger (мс)", 40, 1000, 280, 40)
hyst = st.sidebar.slider("Hysteresis (дБ)", 0, 10, 4, 1)
offset = st.sidebar.slider("Offset (дБ)", -10, 10, 0, 1)

st.sidebar.header("🔬 Метрологічні параметри")
metrology_error = st.sidebar.slider("Похибка RSRP (дБ)", 0.1, 3.0, 1.0, 0.1)
calibration_factor = st.sidebar.slider("Коефіцієнт калібрування", 0.95, 1.05, 1.0, 0.01)

st.sidebar.header("🚶 Параметри руху UE")
speed_kmh = st.sidebar.slider("Швидкість UE (км/год)", 5, 120, 20, 5)
route_type = st.sidebar.selectbox("Тип маршруту", 
    ["Коло навколо центру", "Лінія північ-південь", "Випадковий рух", "Ручне керування"])

# Оновлення параметрів контролера
st.session_state.handover_controller.update_parameters(ttt, hyst, offset, metrology_error)

# Основний інтерфейс
col1, col2 = st.columns([2.5, 1.5])

with col1:
    st.subheader("🗺️ 3D Карта мережі LTE Вінниці")
    
    # Створення 3D карти з pydeck
    def create_3d_lte_map():
        # Базові станції
        bs_data = []
        for bs_id, bs in st.session_state.network.base_stations.items():
            # Колір залежно від навантаження
            load = random.uniform(0, 100)  # Тимчасово для демонстрації
            if load < 30:
                color = [0, 255, 0, 160]  # Зелений
            elif load < 70:
                color = [255, 165, 0, 160]  # Помаранчевий
            else:
                color = [255, 0, 0, 160]  # Червоний
            
            bs_data.append({
                'lat': bs['lat'],
                'lon': bs['lon'],
                'elevation': 50,  # Висота вежі
                'radius': 2000,  # Радіус покриття
                'name': bs['name'],
                'operator': bs['operator'],
                'power': bs['power'],
                'color': color,
                'load': load
            })
        
        # Користувачі
        users_data = []
        if hasattr(st.session_state, 'users') and st.session_state.users:
            for user in st.session_state.users:
                if user.get('active', True):
                    rsrp = user.get('rsrp', -85)
                    if rsrp > -70:
                        user_color = [0, 255, 0, 200]  # Зелений
                    elif rsrp > -85:
                        user_color = [255, 165, 0, 200]  # Помаранчевий
                    else:
                        user_color = [255, 0, 0, 200]  # Червоний
                    
                    users_data.append({
                        'lat': user['lat'],
                        'lon': user['lon'],
                        'elevation': 10,
                        'rsrp': rsrp,
                        'color': user_color
                    })
        else:
            # Додаємо поточного користувача UE
            current_rsrp = -75 + random.uniform(-10, 10)
            if current_rsrp > -70:
                user_color = [0, 255, 0, 200]
            elif current_rsrp > -85:
                user_color = [255, 165, 0, 200]
            else:
                user_color = [255, 0, 0, 200]
            
            users_data.append({
                'lat': st.session_state.ue_position[0],
                'lon': st.session_state.ue_position[1],
                'elevation': 10,
                'rsrp': current_rsrp,
                'color': user_color
            })
        
        # Шари для pydeck
        layers = []
        
        # Шар базових станцій (циліндри)
        if bs_data:
            layers.append(pdk.Layer(
                'ColumnLayer',
                data=bs_data,
                get_position='[lon, lat]',
                get_elevation='elevation',
                elevation_scale=10,
                radius=50,
                get_fill_color='color',
                pickable=True,
                extruded=True
            ))
            
            # Шар зон покриття (кола)
            layers.append(pdk.Layer(
                'ScatterplotLayer',
                data=bs_data,
                get_position='[lon, lat]',
                get_radius='radius',
                get_fill_color='color',
                get_line_color=[255, 255, 255, 100],
                pickable=True,
                filled=True,
                radius_scale=1,
                radius_min_pixels=5,
                line_width_min_pixels=1
            ))
        
        # Шар користувачів
        if users_data:
            layers.append(pdk.Layer(
                'ScatterplotLayer',
                data=users_data,
                get_position='[lon, lat]',
                get_radius=30,
                get_fill_color='color',
                get_line_color=[255, 255, 255, 200],
                pickable=True,
                filled=True,
                line_width_min_pixels=2
            ))
        
        # Конфігурація відображення
        view_state = pdk.ViewState(
            latitude=49.2328,
            longitude=28.4810,
            zoom=12,
            pitch=60,
            bearing=0
        )
        
        # Налаштування tooltip
        tooltip = {
            "html": """
            <b>Назва:</b> {name}<br>
            <b>Оператор:</b> {operator}<br>
            <b>Потужність:</b> {power} дБм<br>
            <b>Навантаження:</b> {load:.1f}%<br>
            <b>RSRP:</b> {rsrp:.1f} дБм
            """,
            "style": {
                "backgroundColor": "steelblue",
                "color": "white",
                "fontSize": "12px",
                "padding": "10px",
                "borderRadius": "5px"
            }
        }
        
        return pdk.Deck(
            layers=layers,
            initial_view_state=view_state,
            tooltip=tooltip,
            map_style='mapbox://styles/mapbox/light-v9'
        )
    
    # Відображення 3D карти з ключем для уникнення миготіння
    deck = create_3d_lte_map()
    
    # Використовуємо container для стабільного відображення
    map_container = st.container()
    with map_container:
        selected_data = st.pydeck_chart(
            deck, 
            use_container_width=True, 
            height=500,
            key=f"lte_map_{st.session_state.map_key}"
        )
    
    # Обробка кліків на карті для ручного керування
    if route_type == "Ручне керування" and selected_data:
        if 'latitude' in selected_data and 'longitude' in selected_data:
            st.session_state.ue_position = [
                selected_data['latitude'],
                selected_data['longitude']
            ]

with col2:
    st.subheader("📊 Поточний стан системи")
    
    # Кнопки керування
    col_btn1, col_btn2 = st.columns(2)
    with col_btn1:
        if st.button("▶️ Старт", use_container_width=True):
            st.session_state.simulation_running = True
    with col_btn2:
        if st.button("⏸️ Стоп", use_container_width=True):
            st.session_state.simulation_running = False
    
    # Поточні вимірювання
    measurements = st.session_state.handover_controller.measure_all_cells(
        st.session_state.ue_position[0],
        st.session_state.ue_position[1],
        metrology_error,
        calibration_factor
    )
    
    # Збереження вимірювань
    st.session_state.measurements_log.append({
        'timestamp': datetime.now(),
        'position': st.session_state.ue_position.copy(),
        'measurements': measurements.copy()
    })
    
    # Обмеження історії до 50 записів
    if len(st.session_state.measurements_log) > 50:
        st.session_state.measurements_log = st.session_state.measurements_log[-50:]
    
    # Перевірка хендовера
    handover_event, status = st.session_state.handover_controller.check_handover_condition(measurements)
    
    if handover_event:
        st.session_state.handover_history.append({
            'timestamp': datetime.now(),
            'old_cell': handover_event['old_cell'],
            'new_cell': handover_event['new_cell'],
            'old_rsrp': handover_event['old_rsrp'],
            'new_rsrp': handover_event['new_rsrp'],
            'type': handover_event['type']
        })
    
    # Відображення вимірювань
    st.write("**🔬 Поточні вимірювання RSRP:**")
    rsrp_data = []
    for bs_id, data in measurements.items():
        is_serving = "🔘" if bs_id == st.session_state.handover_controller.current_serving else "⚪"
        bs_name = st.session_state.network.base_stations[bs_id]['name']
        operator = st.session_state.network.base_stations[bs_id]['operator']
        
        # Кольорове кодування якості сигналу
        if data['rsrp'] > -70:
            quality = "🟢 Відмінно"
        elif data['rsrp'] > -85:
            quality = "🟡 Добре" 
        elif data['rsrp'] > -100:
            quality = "🟠 Задовільно"
        else:
            quality = "🔴 Погано"
            
        rsrp_data.append({
            "Статус": is_serving,
            "Базова станція": f"{bs_name} ({operator})",
            "RSRP (дБм)": f"{data['rsrp']:.1f}",
            "RSRQ (дБ)": f"{data['rsrq']:.1f}",
            "Якість": quality
        })
    
    st.dataframe(rsrp_data, hide_index=True, use_container_width=True)
    
    # Статус хендовера
    st.write("**🔄 Статус хендовера:**")
    
    if handover_event:
        st.success(f"✅ Хендовер виконано успішно!")
        st.write(f"**{st.session_state.network.base_stations[handover_event['old_cell']]['name']}** → **{st.session_state.network.base_stations[handover_event['new_cell']]['name']}**")
        st.write(f"RSRP: {handover_event['old_rsrp']:.1f} → {handover_event['new_rsrp']:.1f} дБм")
        st.write(f"Покращення: +{handover_event['new_rsrp'] - handover_event['old_rsrp']:.1f} дБ")
    else:
        st.info(status)
    
    # Метрики системи
    st.write("**📈 Метрики якості:**")
    if st.session_state.handover_controller.current_serving:
        current_rsrp = measurements[st.session_state.handover_controller.current_serving]['rsrp']
        serving_bs = st.session_state.network.base_stations[st.session_state.handover_controller.current_serving]
        
        col_m1, col_m2 = st.columns(2)
        with col_m1:
            st.metric("Поточна RSRP", f"{current_rsrp:.1f} дБм")
            st.metric("Кількість хендоверів", len(st.session_state.handover_history))
        with col_m2:
            st.metric("Обслуговуюча БС", serving_bs['name'])
            st.metric("Оператор", serving_bs['operator'])

# Графіки реального часу
st.subheader("📈 Моніторинг параметрів у реальному часі")

if len(st.session_state.measurements_log) > 1:
    col3, col4 = st.columns(2)
    
    with col3:
        # Графік RSRP у часі
        fig_rsrp = create_realtime_plot(
            st.session_state.measurements_log,
            st.session_state.network,
            st.session_state.handover_controller.current_serving,
            'rsrp'
        )
        st.plotly_chart(fig_rsrp, use_container_width=True)
    
    with col4:
        # Графік RSRQ у часі  
        fig_rsrq = create_realtime_plot(
            st.session_state.measurements_log,
            st.session_state.network,
            st.session_state.handover_controller.current_serving,
            'rsrq'
        )
        st.plotly_chart(fig_rsrq, use_container_width=True)

# Таблиця останніх хендоверів
if st.session_state.handover_history:
    st.subheader("🔄 Історія хендоверів")
    recent_handovers = st.session_state.handover_history[-10:]  # Останні 10
    ho_df = pd.DataFrame([
        {
            'Час': ho['timestamp'].strftime('%H:%M:%S'),
            'Від': st.session_state.network.base_stations[ho['old_cell']]['name'],
            'До': st.session_state.network.base_stations[ho['new_cell']]['name'],
            'RSRP до': f"{ho['old_rsrp']:.1f} дБм",
            'RSRP після': f"{ho['new_rsrp']:.1f} дБм", 
            'Покращення': f"+{ho['new_rsrp'] - ho['old_rsrp']:.1f} дБ",
            'Тип': ho['type']
        }
        for ho in reversed(recent_handovers)
    ])
    st.dataframe(ho_df, hide_index=True, use_container_width=True)

# Автоматичне оновлення симуляції
if st.session_state.simulation_running:
    # Симуляція руху UE
    if route_type == "Коло навколо центру":
        angle = (time.time() * speed_kmh / 50) % (2 * np.pi)
        radius = 0.008
        center_lat, center_lon = 49.2328, 28.4810
        st.session_state.ue_position[0] = center_lat + radius * np.cos(angle)
        st.session_state.ue_position[1] = center_lon + radius * np.sin(angle)
    
    elif route_type == "Лінія північ-південь":
        t = (time.time() * speed_kmh / 100) % 4
        if t < 1:
            st.session_state.ue_position[0] = 49.2328 + 0.01 * t
        elif t < 2:
            st.session_state.ue_position[0] = 49.2428 - 0.01 * (t - 1)
        elif t < 3:
            st.session_state.ue_position[0] = 49.2328 - 0.01 * (t - 2)
        else:
            st.session_state.ue_position[0] = 49.2228 + 0.01 * (t - 3)
    
    elif route_type == "Випадковий рух":
        delta = speed_kmh / 1000000
        st.session_state.ue_position[0] += np.random.normal(0, delta)
        st.session_state.ue_position[1] += np.random.normal(0, delta)
        
        st.session_state.ue_position[0] = np.clip(st.session_state.ue_position[0], 49.20, 49.26)
        st.session_state.ue_position[1] = np.clip(st.session_state.ue_position[1], 28.43, 28.53)
    
    # Оновлення карти без повного перерендерингу
    time.sleep(1)
    st.rerun()

# Інформаційна панель
with st.expander("ℹ️ Інформація про 3D карту"):
    st.markdown("""
    ### 🗺️ Особливості 3D візуалізації:
    
    **📡 Базові станції** - відображаються як 3D циліндри з кольорами:
    - 🟢 Зелений: низьке навантаження (<30%)
    - 🟡 Жовтий: середнє навантаження (30-70%)
    - 🔴 Червоний: високе навантаження (>70%)
    
    **📱 Користувачі UE** - точки з кольорами якості сигналу:
    - 🟢 Зелений: відмінний сигнал (RSRP > -70 дБм)
    - 🟡 Жовтий: хороший сигнал (-85 до -70 дБм)
    - 🔴 Червоний: слабкий сигнал (< -85 дБм)
    
    **🔄 Зони покриття** - кола навколо базових станцій
    
    **⚡ Переваги 3D карти:**
    - Відсутність миготіння при оновленні
    - Інтерактивність (обертання, масштабування)
    - Наочне відображення висоти антен
    - Кращий огляд топології мережі
    """)
