import streamlit as st
import numpy as np
import pandas as pd
import folium
from streamlit_folium import st_folium
import plotly.graph_objects as go # Збережено з вашого коду
import plotly.express as px # Збережено з вашого коду
from datetime import datetime, timedelta # timedelta збережено з вашого коду
import time
import random # Збережено з вашого коду (хоча np.random переважно використовується)
from geopy.distance import geodesic

# Налаштування сторінки
st.set_page_config(
    page_title="LTE Network Simulator",
    page_icon="📡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Ініціалізація стану сесії
if 'network_active' not in st.session_state:
    st.session_state.network_active = False
if 'users' not in st.session_state:
    st.session_state.users = []
if 'base_stations' not in st.session_state:
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
        'total_handovers': 0,
        'successful_handovers': 0,
        'failed_handovers': 0,
        'average_rsrp': -85.0,  # Оновлено на float
        'network_throughput': 0.0, # Оновлено на float
        'active_users': 0
    }

# Функції симуляції
def calculate_rsrp(user_lat, user_lon, bs_lat, bs_lon, bs_power):
    distance = geodesic((user_lat, user_lon), (bs_lat, bs_lon)).kilometers
    if distance == 0:
        distance = 0.001
    path_loss = 128.1 + 37.6 * np.log10(distance)
    rsrp = bs_power - path_loss + np.random.normal(0, 2)
    return float(max(-120, min(-40, rsrp))) # Забезпечуємо float

def find_best_bs(user_lat, user_lon, base_stations):
    best_bs_info = None # Змінено з best_bs
    best_rsrp_val = -float('inf') # Змінено з -999 та best_rsrp
    for bs in base_stations:
        rsrp = calculate_rsrp(user_lat, user_lon, bs['lat'], bs['lon'], bs['power'])
        if rsrp > best_rsrp_val:
            best_rsrp_val = rsrp
            best_bs_info = bs
    return best_bs_info, best_rsrp_val

@st.cache_resource # Кешування базової карти
def create_network_map_base():
    """Створення базової карти мережі з Mapbox"""
    center = [49.2328, 28.4810]
    MAPBOX_API_KEY = "pk.eyJ1IjoiaHJ1c3N0dHQiLCJhIjoiY21iNnR0OXh1MDJ2ODJsczk3emdhdDh4ayJ9.CNygw7kmAPb6JGd0CFvUBg"
    MAPBOX_STYLE_ID = "mapbox/light-v11"
    tiles_url = f"https://api.mapbox.com/styles/v1/{MAPBOX_STYLE_ID}/tiles/{{z}}/{{x}}/{{y}}@2x?access_token={MAPBOX_API_KEY}"
    attribution = (
        '© <a href="https://www.mapbox.com/about/maps/">Mapbox</a> '
        '© <a href="http://www.openstreetmap.org/copyright">OpenStreetMap</a> '
        '<strong><a href="https://www.mapbox.com/map-feedback/" target="_blank">Improve this map</a></strong>'
    )
    m = folium.Map(
        location=center,
        zoom_start=12,
        tiles=tiles_url,
        attr=attribution,
        attributionControl=False  # Прибираємо стандартну атрибуцію Leaflet
    )
    return m

def add_elements_to_map(folium_map_object):
    """Додавання динамічних елементів (станції, користувачі) на карту"""
    # Додавання базових станцій
    for bs in st.session_state.base_stations:
        if bs['load'] < 30: color = 'green'
        elif bs['load'] < 70: color = 'orange'
        else: color = 'red'
        folium.Marker(
            [bs['lat'], bs['lon']],
            popup=f"""<div style="font-family: Arial; font-size: 12px;"><b>{bs['name']}</b><br>ID: {bs['id']}<br>Потужність: {bs['power']} дБм<br>Користувачі: {bs['users']}<br>Навантаження: {bs['load']:.1f}%</div>""",
            icon=folium.Icon(color=color, icon='tower-broadcast', prefix='fa'),
            tooltip=f"{bs['name']} ({bs['load']:.1f}% load)"
        ).add_to(folium_map_object)
        folium.Circle(
            location=[bs['lat'], bs['lon']], radius=2000, color=color,
            fillColor=color, fillOpacity=0.1, weight=2
        ).add_to(folium_map_object)

    # Додавання активних користувачів
    for user in st.session_state.users:
        if user['active']:
            if user['rsrp'] > -70: user_color = 'green'
            elif user['rsrp'] > -90: user_color = 'orange'
            else: user_color = 'red'
            folium.Marker(
                [user['lat'], user['lon']],
                popup=f"""<div style="font-family: Arial; font-size: 12px;"><b>User {user['id']}</b><br>RSRP: {user['rsrp']:.1f} дБм<br>Serving BS: {user['serving_bs']}<br>Швидкість: {user['speed']} км/год<br>Throughput: {user['throughput']:.1f} Мбіт/с</div>""",
                icon=folium.Icon(color=user_color, icon='mobile', prefix='fa'),
                tooltip=f"User {user['id']} (RSRP: {user['rsrp']:.1f} дБм)"
            ).add_to(folium_map_object)
    return folium_map_object

def generate_new_user():
    user_id = f"UE{len(st.session_state.users)+1:03d}"
    lat = 49.2328 + np.random.uniform(-0.03, 0.03)
    lon = 28.4810 + np.random.uniform(-0.05, 0.05)
    best_bs, rsrp = find_best_bs(lat, lon, st.session_state.base_stations)
    user = {
        'id': user_id, 'lat': lat, 'lon': lon,
        'serving_bs': best_bs['id'] if best_bs else None,
        'rsrp': rsrp, 'speed': np.random.choice([5, 20, 60, 90]),
        'direction': np.random.uniform(0, 360),
        'throughput': np.random.uniform(10, 100), 'active': True,
        'handover_count': 0, 'last_handover': None
    }
    return user

def simulate_user_movement():
    for user in st.session_state.users:
        if not user['active']: continue
        speed_ms = user['speed'] * 1000 / 3600
        distance = speed_ms * 1
        lat_change = (distance * np.cos(np.radians(user['direction']))) / 111111
        lon_change = (distance * np.sin(np.radians(user['direction']))) / (111111 * np.cos(np.radians(user['lat'])))
        user['lat'] = np.clip(user['lat'] + lat_change, 49.20, 49.27)
        user['lon'] = np.clip(user['lon'] + lon_change, 28.42, 28.55)
        if np.random.random() < 0.05: user['direction'] = np.random.uniform(0, 360)
        check_handover(user)

def check_handover(user):
    current_bs_obj = next((bs for bs in st.session_state.base_stations if bs['id'] == user['serving_bs']), None) # Змінено ім'я змінної
    if not current_bs_obj: return
    current_rsrp = calculate_rsrp(user['lat'], user['lon'], current_bs_obj['lat'], current_bs_obj['lon'], current_bs_obj['power'])
    best_candidate_bs, best_candidate_rsrp = find_best_bs(user['lat'], user['lon'], st.session_state.base_stations) # Змінено імена змінних
    hysteresis_margin = 5 # З вашого коду
    if best_candidate_bs and best_candidate_bs['id'] != user['serving_bs'] and \
       best_candidate_rsrp > current_rsrp + hysteresis_margin:
        execute_handover(user, best_candidate_bs, current_rsrp, best_candidate_rsrp)
    else:
        user['rsrp'] = current_rsrp

def execute_handover(user, new_bs, old_rsrp, new_rsrp):
    old_bs_id = user['serving_bs']
    user.update({'serving_bs': new_bs['id'], 'rsrp': new_rsrp, 'handover_count': user['handover_count'] + 1, 'last_handover': datetime.now()})
    success = new_rsrp > old_rsrp + 3
    handover_event = {
        'timestamp': datetime.now(), 'user_id': user['id'], 'old_bs': old_bs_id, 'new_bs': new_bs['id'],
        'old_rsrp': old_rsrp, 'new_rsrp': new_rsrp, 'improvement': new_rsrp - old_rsrp, 'success': success
    }
    st.session_state.handover_events.append(handover_event)
    st.session_state.network_metrics['total_handovers'] += 1
    if success: st.session_state.network_metrics['successful_handovers'] += 1
    else: st.session_state.network_metrics['failed_handovers'] += 1

def update_network_metrics():
    active_users_list = [u for u in st.session_state.users if u['active']] # Змінено ім'я змінної
    st.session_state.network_metrics['active_users'] = len(active_users_list)
    if active_users_list:
        avg_rsrp_val = np.mean([u['rsrp'] for u in active_users_list if u['rsrp'] is not None])
        avg_throughput_val = np.mean([u['throughput'] for u in active_users_list if u['throughput'] is not None])
        st.session_state.network_metrics['average_rsrp'] = float(avg_rsrp_val) if not np.isnan(avg_rsrp_val) else -120.0
        st.session_state.network_metrics['network_throughput'] = float(avg_throughput_val * len(active_users_list)) if not np.isnan(avg_throughput_val) else 0.0
    else:
        st.session_state.network_metrics.update({'average_rsrp': -120.0, 'network_throughput': 0.0})
    for bs in st.session_state.base_stations:
        users_on_bs = len([u for u in active_users_list if u['serving_bs'] == bs['id']])
        bs.update({'users': users_on_bs, 'load': min(100, users_on_bs * 20)}) # Використано *20 з вашого коду

st.title("🌐 LTE Network Simulator")
st.markdown("### Інтерактивний симулятор мережі LTE в реальному часі")

st.sidebar.header("🎛️ Управління симуляцією")
if st.sidebar.button("🚀 Запустити мережу" if not st.session_state.network_active else "⏹️ Зупинити мережу"):
    st.session_state.network_active = not st.session_state.network_active
    if not st.session_state.network_active:
        st.session_state.users = []
        st.session_state.handover_events = []
        st.session_state.network_metrics.update({
            'total_handovers': 0, 'successful_handovers': 0, 'failed_handovers': 0,
            'average_rsrp': -85.0, 'network_throughput': 0.0, 'active_users': 0})
        for bs_reset in st.session_state.base_stations: bs_reset.update({'users': 0, 'load': 0})
st.sidebar.success("✅ Мережа активна") if st.session_state.network_active else st.sidebar.info("⏸️ Мережа зупинена")

st.sidebar.subheader("⚙️ Параметри")
max_users = st.sidebar.slider("Максимум користувачів", 5, 50, 20)
user_spawn_rate = st.sidebar.slider("Швидкість появи користувачів", 0.1, 2.0, 0.5) # З вашого коду

if st.sidebar.button("➕ Додати користувача"): # З вашого коду
    if len(st.session_state.users) < max_users:
        st.session_state.users.append(generate_new_user())
        st.rerun()
if st.sidebar.button("🗑️ Очистити всіх користувачів"):
    st.session_state.users = []
    st.session_state.handover_events = []
    st.rerun()

col1, col2 = st.columns([2, 1])
with col1:
    st.subheader("🗺️ Карта мережі")
    base_map = create_network_map_base() # Виклик кешованої функції для бази
    network_map_with_elements = add_elements_to_map(base_map) # Додавання елементів
    st_folium(network_map_with_elements, width=700, height=500, returned_objects=["last_clicked"]) # Використання returned_objects з вашого коду

with col2:
    st.subheader("📊 Метрики мережі")
    update_network_metrics()
    metrics = st.session_state.network_metrics
    st.metric("Активні користувачі", metrics['active_users'])
    st.metric("Всього хендоверів", metrics['total_handovers'])
    success_rate_display = f"{(metrics['successful_handovers'] / metrics['total_handovers'] * 100):.1f}%" if metrics['total_handovers'] > 0 else "N/A"
    st.metric("Успішність хендоверів", success_rate_display)
    st.metric("Середня RSRP", f"{metrics['average_rsrp']:.1f} дБм")
    st.metric("Пропускна здатність", f"{metrics['network_throughput']:.1f} Мбіт/с")

st.subheader("📡 Статус базових станцій")
bs_data_display = [{'ID': b['id'], 'Назва': b['name'], 'Потужність (дБм)': b['power'], 'Користувачі': b['users'], 'Навантаження (%)': f"{b['load']:.1f}"} for b in st.session_state.base_stations]
st.dataframe(pd.DataFrame(bs_data_display), use_container_width=True)

if st.session_state.handover_events:
    st.subheader("🔄 Останні хендовери")
    recent_handovers_display = st.session_state.handover_events[-5:]
    ho_data_display = [{'Час': h['timestamp'].strftime('%H:%M:%S'), 'Користувач': h['user_id'], 'Від': h['old_bs'], 'До': h['new_bs'], 'Покращення (дБ)': f"{h.get('improvement', 0.0):.1f}", 'Статус': '✅ Успішно' if h['success'] else '❌ Невдало'} for h in reversed(recent_handovers_display)]
    if ho_data_display: st.dataframe(pd.DataFrame(ho_data_display), use_container_width=True)

simulation_interval_seconds = 2.0 # З вашого коду (непрямо, time.sleep(2))
if st.session_state.network_active:
    if len(st.session_state.users) < max_users and np.random.random() < user_spawn_rate * 0.1: # Логіка з вашого коду
        st.session_state.users.append(generate_new_user())
    simulate_user_movement()
    update_network_metrics() # Важливо оновити метрики після симуляції
    time.sleep(simulation_interval_seconds) # З вашого коду
    st.rerun()

with st.expander("ℹ️ Про симулятор"):
    st.markdown("""
    ### Функції симулятора:
    **🌐 Реальна мережа LTE** - 5 базових станцій з різними характеристиками
    **👥 Динамічні користувачі** - автоматична генерація та рух користувачів
    **📡 Реалтайм хендовери** - автоматичне переключення між станціями
    **📊 Живі метрики** - моніторинг ефективності мережі в реальному часі
    **🗺️ Інтерактивна карта** - візуалізація всіх елементів мережі
    **⚙️ Налаштування** - контроль параметрів симуляції
    ### Алгоритм хендовера:
    - Користувач переключається на нову BS, якщо RSRP покращується > 5 дБ
    - Враховується відстань та потужність передавачів
    - Автоматичний розрахунок успішності хендовера
    """)

