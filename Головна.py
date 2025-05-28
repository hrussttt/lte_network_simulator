import streamlit as st
import pydeck as pdk
import numpy as np
import pandas as pd
import folium
from streamlit_folium import st_folium
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
import time
import random
from geopy.distance import geodesic

# Імпорт існуючих модулів
import sys
import os
from pathlib import Path

current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

try:
    from utils.network import VinnytsiaLTENetwork
    from utils.handover import HandoverController
    from utils.calculations import calculate_distance, calculate_path_loss
except ImportError as e:
    st.error(f"Помилка імпорту модулів: {e}")
    st.stop()

# Налаштування сторінки
st.set_page_config(
    page_title="LTE Network Simulator",
    page_icon="📡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Функція очищення даних для PyDeck (вирішує миготіння)
@st.cache_data
def clean_data_for_pydeck(data):
    """Очищення даних для PyDeck"""
    if isinstance(data, list):
        return [clean_data_for_pydeck(item) for item in data]
    elif isinstance(data, dict):
        return {k: clean_data_for_pydeck(v) for k, v in data.items()}
    elif isinstance(data, np.integer):
        return int(data)
    elif isinstance(data, np.floating):
        return float(data)
    elif isinstance(data, np.ndarray):
        return data.tolist()
    elif pd.isna(data):
        return None
    else:
        return data

# Ініціалізація стану сесії
if 'network_active' not in st.session_state:
    st.session_state.network_active = False
if 'users' not in st.session_state:
    st.session_state.users = []
if 'base_stations' not in st.session_state:
    # Використовуємо базові станції з існуючого коду
    st.session_state.base_stations = [
        {'id': 'BS001', 'name': 'Центральна', 'lat': 49.2328, 'lon': 28.4810, 'power': 45, 'users': 0, 'load': 0},
        {'id': 'BS002', 'name': 'Північна', 'lat': 49.2520, 'lon': 28.4590, 'power': 42, 'users': 0, 'load': 0},
        {'id': 'BS003', 'name': 'Східна', 'lat': 49.2180, 'lon': 28.5120, 'power': 40, 'users': 0, 'load': 0},
        {'id': 'BS004', 'name': 'Західна', 'lat': 49.2290, 'lon': 28.4650, 'power': 43, 'users': 0, 'load': 0},
        {'id': 'BS005', 'name': 'Південна', 'lat': 49.2150, 'lon': 28.4420, 'power': 41, 'users': 0, 'load': 0},
    ]
if 'handover_events' not in st.session_state:
    st.session_state.handover_events = []
if 'network_metrics' not in st.session_state:
    st.session_state.network_metrics = {
        'total_handovers': 0, 'successful_handovers': 0, 'failed_handovers': 0,
        'average_rsrp': -85, 'network_throughput': 0, 'active_users': 0
    }

# Ініціалізація існуючих класів
if 'lte_network' not in st.session_state:
    st.session_state.lte_network = VinnytsiaLTENetwork()
if 'handover_controller' not in st.session_state:
    st.session_state.handover_controller = HandoverController(st.session_state.lte_network)

# ЗМІНЕНО: Нова функція створення 3D Mapbox карти
@st.cache_data
def create_mapbox_lte_map(_users_data, _base_stations_data, _update_trigger):
    """Створення красивої Mapbox 3D карти без миготіння"""
    
    # Підготовка даних базових станцій
    bs_data = []
    for bs in _base_stations_data:
        # Висота залежно від потужності та навантаження
        height = float(bs['power'] + bs['load'] * 2)
        
        # Колір залежно від навантаження
        if bs['load'] < 30:
            color = [0, 255, 0, 200]  # Зелений
        elif bs['load'] < 70:
            color = [255, 165, 0, 200]  # Помаранчевий
        else:
            color = [255, 0, 0, 200]  # Червоний
        
        bs_data.append({
            'lat': float(bs['lat']),
            'lon': float(bs['lon']),
            'elevation': height,
            'name': str(bs['name']),
            'power': float(bs['power']),
            'users': int(bs['users']),
            'load': float(bs['load']),
            'color': color
        })
    
    # Підготовка даних користувачів
    users_processed = []
    for user in _users_data:
        if user.get('active', True):
            rsrp = float(user.get('rsrp', -85))
            
            # Колір залежно від якості сигналу
            if rsrp > -70:
                user_color = [0, 255, 0, 255]  # Зелений
            elif rsrp > -85:
                user_color = [255, 165, 0, 255]  # Помаранчевий  
            else:
                user_color = [255, 0, 0, 255]  # Червоний
            
            users_processed.append({
                'lat': float(user['lat']),
                'lon': float(user['lon']),
                'elevation': 10.0,
                'rsrp': rsrp,
                'speed': float(user['speed']),
                'user_id': str(user['id']),
                'serving_bs': str(user.get('serving_bs', 'None')),
                'color': user_color,
                'size': float(30 + user['speed'])
            })
    
    # Очищення даних для PyDeck
    bs_clean = clean_data_for_pydeck(bs_data)
    users_clean = clean_data_for_pydeck(users_processed)
    
    # Створення шарів карти
    layers = []
    
    # Шар 3D веж базових станцій
    if bs_clean:
        layers.append(pdk.Layer(
            'ColumnLayer',
            data=bs_clean,
            get_position='[lon, lat]',
            get_elevation='elevation',
            elevation_scale=1,
            radius=80,
            get_fill_color='color',
            pickable=True,
            extruded=True
        ))
    
    # Шар користувачів
    if users_clean:
        layers.append(pdk.Layer(
            'ScatterplotLayer',
            data=users_clean,
            get_position='[lon, lat]',
            get_radius='size',
            get_fill_color='color',
            get_line_color=[255, 255, 255, 200],
            pickable=True,
            filled=True,
            line_width_min_pixels=2
        ))
    
    # Налаштування камери
    view_state = pdk.ViewState(
        latitude=49.2328,
        longitude=28.4810,
        zoom=11.5,
        pitch=50,
        bearing=0
    )
    
    # Tooltip
    tooltip = {
        "html": """
        <div style="background: rgba(0,0,0,0.8); color: white; padding: 12px; border-radius: 8px;">
            <b>{name}</b><br/>
            Потужність: {power} дБм<br/>
            Користувачі: {users}<br/>
            Навантаження: {load}%<br/>
            RSRP: {rsrp} дБм<br/>
            Швидкість: {speed} км/год
        </div>
        """,
        "style": {"color": "white"}
    }
    
    return pdk.Deck(
        layers=layers,
        initial_view_state=view_state,
        tooltip=tooltip,
        map_style='mapbox://styles/mapbox/dark-v10'  # Красивий Mapbox стиль
    )

# Лічильник для карти (уникає миготіння)
if 'map_update_trigger' not in st.session_state:
    st.session_state.map_update_trigger = 0

# РЕШТА КОДУ БЕЗ ЗМІН - функції знаходження BS, генерації користувачів тощо
def calculate_rsrp(user_lat, user_lon, bs_lat, bs_lon, bs_power):
    """Розрахунок RSRP на основі відстані та потужності"""
    distance = geodesic((user_lat, user_lon), (bs_lat, bs_lon)).kilometers
    if distance == 0:
        distance = 0.001
    
    # Спрощена модель втрат на трасі
    path_loss = 128.1 + 37.6 * np.log10(distance)
    rsrp = bs_power - path_loss + np.random.normal(0, 2)  # +шум
    return max(-120, min(-40, rsrp))

def find_best_bs(user_lat, user_lon, base_stations):
    """Знаходження найкращої базової станції"""
    best_bs = None
    best_rsrp = -999
    
    for bs in base_stations:
        rsrp = calculate_rsrp(user_lat, user_lon, bs['lat'], bs['lon'], bs['power'])
        if rsrp > best_rsrp:
            best_rsrp = rsrp
            best_bs = bs
    
    return best_bs, best_rsrp

# Головний інтерфейс (БЕЗ ЗМІН)
st.title("LTE Network Simulator")

# Sidebar (БЕЗ ЗМІН)
st.sidebar.header("⚙️ Управління симуляцією")
network_control = st.sidebar.selectbox(
    "Стан мережі",
    ["🔴 Зупинено", "🟢 Активна"]
)

st.session_state.network_active = (network_control == "🟢 Активна")

st.sidebar.header("👥 Користувачі")
max_users = st.sidebar.slider("Максимум користувачів", 5, 50, 20)

if st.sidebar.button("➕ Додати користувача"):
    if len(st.session_state.users) < max_users:
        user_id = f"UE{len(st.session_state.users)+1:03d}"
        lat = random.uniform(49.20, 49.27)
        lon = random.uniform(28.42, 28.55)
        
        best_bs, rsrp = find_best_bs(lat, lon, st.session_state.base_stations)
        
        new_user = {
            'id': user_id,
            'lat': lat,
            'lon': lon,
            'serving_bs': best_bs['id'] if best_bs else None,
            'rsrp': rsrp,
            'speed': random.choice([5, 20, 40, 60, 90]),
            'direction': random.uniform(0, 360),
            'throughput': random.uniform(10, 100),
            'active': True,
            'handover_count': 0,
            'last_handover': None
        }
        
        if best_bs:
            best_bs['users'] += 1
            best_bs['load'] = min(100, (best_bs['users'] / 20) * 100)
        
        st.session_state.users.append(new_user)
        st.rerun()

# Основний інтерфейс
col1, col2 = st.columns([3, 1])

with col1:
    st.subheader("🗺️ 3D Карта мережі LTE (Mapbox)")
    
    # ЗМІНЕНО: Відображення нової Mapbox карти
    if st.session_state.network_active:
        st.session_state.map_update_trigger += 1
    
    try:
        deck = create_mapbox_lte_map(
            st.session_state.users,
            st.session_state.base_stations,
            st.session_state.map_update_trigger
        )
        selected_data = st.pydeck_chart(deck, use_container_width=True, height=500)
    except Exception as e:
        st.error(f"Помилка відображення карти: {str(e)}")

with col2:
    st.subheader("📊 Метрики мережі")
    
    # Оновлення метрик
    active_users = [u for u in st.session_state.users if u['active']]
    st.session_state.network_metrics['active_users'] = len(active_users)
    
    st.metric("Активні користувачі", len(active_users))
    st.metric("Всього хендоверів", st.session_state.network_metrics['total_handovers'])
    
    if active_users:
        avg_rsrp = np.mean([u['rsrp'] for u in active_users])
        st.metric("Середня RSRP", f"{avg_rsrp:.1f} дБм")

# Автоматичне оновлення
if st.session_state.network_active:
    # Симуляція руху користувачів
    for user in st.session_state.users:
        if user['active']:
            speed_ms = user['speed'] * 1000 / 3600
            distance = speed_ms * 1
            
            lat_change = (distance * np.cos(np.radians(user['direction']))) / 111111
            lon_change = (distance * np.sin(np.radians(user['direction']))) / (111111 * np.cos(np.radians(user['lat'])))
            
            user['lat'] += lat_change
            user['lon'] += lon_change
            
            user['lat'] = np.clip(user['lat'], 49.20, 49.27)
            user['lon'] = np.clip(user['lon'], 28.42, 28.55)
            
            if np.random.random() < 0.05:
                user['direction'] = np.random.uniform(0, 360)
            
            # ЗМІНЕНО: Виклик хендовера з utils/handover.py
            if st.session_state.handover_controller:
                measurements = st.session_state.handover_controller.measure_all_cells(
                    user['lat'], user['lon']
                )
                handover_event, status = st.session_state.handover_controller.check_handover_condition(measurements)
                
                if handover_event:
                    st.session_state.handover_events.append(handover_event)
                    st.session_state.network_metrics['total_handovers'] += 1
    
    time.sleep(2)
    st.rerun()
