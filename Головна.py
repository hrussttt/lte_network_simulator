import streamlit as st
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import time
import random
from geopy.distance import geodesic

# Налаштування сторінки
st.set_page_config(
    page_title="LTE Network Simulator",
    page_icon="📡",
    layout="wide",
    initial_sidebar_state="expanded",
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
        'average_rsrp': -85,
        'network_throughput': 0,
        'active_users': 0
    }

# Функції симуляції
def calculate_rsrp(user_lat, user_lon, bs_lat, bs_lon, bs_power):
    """Розрахунок RSRP на основі відстані та потужності"""
    distance = geodesic((user_lat, user_lon), (bs_lat, bs_lon)).kilometers
    if distance == 0:
        distance = 0.001
    
    # Модель втрат на трасі COST-Hata
    path_loss = 128.1 + 37.6 * np.log10(distance)
    rsrp = bs_power - path_loss + np.random.normal(0, 2)
    return float(np.clip(rsrp, -120, -40))

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

def update_bs_load():
    """Оновлення навантаження базових станцій"""
    for bs in st.session_state.base_stations:
        count = sum(1 for user in st.session_state.users if user['serving_bs'] == bs['id'])
        bs['users'] = count
        bs['load'] = min(100, count * 10)  # Спрощена модель навантаження

def move_users():
    """Рух користувачів та перевірка хендовера"""
    for user in st.session_state.users:
        if user['active']:
            # Оновлення позиції
            speed_ms = user['speed'] / 3.6  # км/год в м/с
            distance_m = speed_ms * 1  # За 1 секунду
            
            # Конвертація в градуси (приблизно)
            lat_change = (distance_m * np.cos(np.radians(user['direction']))) / 111111
            lon_change = (distance_m * np.sin(np.radians(user['direction']))) / \
                        (111111 * np.cos(np.radians(user['lat'])))
            
            user['lat'] += lat_change
            user['lon'] += lon_change
            
            # Обмеження координат
            user['lat'] = np.clip(user['lat'], 49.20, 49.27)
            user['lon'] = np.clip(user['lon'], 28.42, 28.55)
            
            # Випадкова зміна напряму
            if random.random() < 0.05:
                user['direction'] = random.uniform(0, 360)
            
            # Перевірка хендовера
            current_bs = next((bs for bs in st.session_state.base_stations if bs['id'] == user['serving_bs']), None)
            if current_bs:
                current_rsrp = calculate_rsrp(user['lat'], user['lon'], current_bs['lat'], current_bs['lon'], current_bs['power'])
                user['rsrp'] = current_rsrp
                
                # Знаходження кращої БС
                best_bs, best_rsrp = find_best_bs(user['lat'], user['lon'], st.session_state.base_stations)
                
                # Умова хендовера: покращення > 5 дБ
                if best_bs and best_bs['id'] != user['serving_bs'] and best_rsrp > current_rsrp + 5:
                    # Виконання хендовера
                    handover_event = {
                        'timestamp': datetime.now(),
                        'user_id': user['id'],
                        'old_bs': user['serving_bs'],
                        'new_bs': best_bs['id'],
                        'old_rsrp': current_rsrp,
                        'new_rsrp': best_rsrp,
                        'improvement': best_rsrp - current_rsrp,
                        'success': True
                    }
                    
                    user['serving_bs'] = best_bs['id']
                    user['rsrp'] = best_rsrp
                    user['handover_count'] += 1
                    user['last_handover'] = datetime.now()
                    
                    st.session_state.handover_events.append(handover_event)
                    st.session_state.network_metrics['total_handovers'] += 1
                    st.session_state.network_metrics['successful_handovers'] += 1

def add_user():
    """Додавання нового користувача"""
    lat = random.uniform(49.20, 49.27)
    lon = random.uniform(28.42, 28.55)
    
    best_bs, rsrp = find_best_bs(lat, lon, st.session_state.base_stations)
    
    user = {
        'id': f"UE_{len(st.session_state.users)+1:03d}",
        'lat': lat,
        'lon': lon,
        'rsrp': rsrp,
        'serving_bs': best_bs['id'] if best_bs else None,
        'active': True,
        'speed': random.uniform(5, 50),  # км/год
        'direction': random.uniform(0, 360),
        'throughput': random.uniform(10, 100),
        'handover_count': 0,
        'last_handover': None
    }
    
    st.session_state.users.append(user)
    update_bs_load()

def update_network_metrics():
    """Оновлення метрик мережі"""
    active_users = [u for u in st.session_state.users if u['active']]
    st.session_state.network_metrics['active_users'] = len(active_users)
    
    if active_users:
        avg_rsrp = np.mean([u['rsrp'] for u in active_users])
        total_throughput = sum([u['throughput'] for u in active_users])
        st.session_state.network_metrics['average_rsrp'] = avg_rsrp
        st.session_state.network_metrics['network_throughput'] = total_throughput

def create_network_map():
    """Створення карти мережі з Plotly"""
    # Підготовка даних для базових станцій
    bs_data = []
    for bs in st.session_state.base_stations:
        bs_data.append({
            'lat': bs['lat'],
            'lon': bs['lon'],
            'name': bs['name'],
            'users': bs['users'],
            'load': bs['load'],
            'type': 'BaseStation'
        })
    
    # Підготовка даних для користувачів
    user_data = []
    for user in st.session_state.users:
        if user['active']:
            user_data.append({
                'lat': user['lat'],
                'lon': user['lon'],
                'name': user['id'],
                'rsrp': user['rsrp'],
                'serving_bs': user['serving_bs'],
                'type': 'User'
            })
    
    # Створення фігури
    fig = go.Figure()
    
    # Додавання базових станцій
    if bs_data:
        df_bs = pd.DataFrame(bs_data)
        fig.add_trace(go.Scattermapbox(
            lat=df_bs['lat'],
            lon=df_bs['lon'],
            mode='markers',
            marker=dict(
                size=15,
                color=df_bs['load'],
                colorscale='RdYlGn_r',
                showscale=True,
                colorbar=dict(title="Навантаження (%)")
            ),
            text=df_bs['name'],
            hovertemplate='<b>%{text}</b><br>Користувачі: %{customdata[0]}<br>Навантаження: %{customdata[1]:.1f}%<extra></extra>',
            customdata=list(zip(df_bs['users'], df_bs['load'])),
            name='Базові станції'
        ))
    
    # Додавання користувачів
    if user_data:
        df_users = pd.DataFrame(user_data)
        fig.add_trace(go.Scattermapbox(
            lat=df_users['lat'],
            lon=df_users['lon'],
            mode='markers',
            marker=dict(
                size=8,
                color='blue',
                symbol='circle'
            ),
            text=df_users['name'],
            hovertemplate='<b>%{text}</b><br>RSRP: %{customdata[0]:.1f} дБм<br>Служить: %{customdata[1]}<extra></extra>',
            customdata=list(zip(df_users['rsrp'], df_users['serving_bs'])),
            name='Користувачі'
        ))
    
    # Налаштування карти
    fig.update_layout(
        mapbox=dict(
            style="open-street-map",
            center=dict(lat=49.2328, lon=28.4810),
            zoom=12
        ),
        margin=dict(l=0, r=0, t=0, b=0),
        height=500
    )
    
    st.plotly_chart(fig, use_container_width=True)

# Головний інтерфейс
st.title("📡 LTE Network Simulator")

# Бічна панель
with st.sidebar:
    st.header("🎛️ Управління мережею")
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🚀 Запустити", use_container_width=True):
            st.session_state.network_active = True
            st.success("Мережа запущена!")
    
    with col2:
        if st.button("⏹ Зупинити", use_container_width=True):
            st.session_state.network_active = False
            st.info("Мережа зупинена")
    
    st.markdown("---")
    
    # Управління користувачами
    st.subheader("👥 Користувачі")
    if st.button("➕ Додати користувача", use_container_width=True):
        add_user()
        st.success(f"Додано користувача UE_{len(st.session_state.users):03d}")
    
    if st.button("🗑️ Очистити всіх", use_container_width=True):
        st.session_state.users = []
        st.session_state.handover_events = []
        update_bs_load()
        st.success("Користувачі очищені")
    
    # Автоматичне додавання
    auto_add = st.checkbox("🔄 Автододавання користувачів")
    if auto_add and st.session_state.network_active:
        if len(st.session_state.users) < 20 and random.random() < 0.1:
            add_user()

# Основна область
col1, col2 = st.columns([3, 1])

with col1:
    st.subheader("🗺️ Карта мережі")
    create_network_map()

with col2:
    st.subheader("📊 Метрики мережі")
    
    total_users = len(st.session_state.users)
    active_users = len([u for u in st.session_state.users if u['active']])
    total_handovers = st.session_state.network_metrics['total_handovers']
    
    st.metric("Активні користувачі", active_users)
    st.metric("Всього хендоверів", total_handovers)
    
    if st.session_state.users:
        avg_rsrp = np.mean([u['rsrp'] for u in st.session_state.users if u['active']])
        st.metric("Середній RSRP", f"{avg_rsrp:.1f} дБм")
        
        success_rate = 0
        if total_handovers > 0:
            success_rate = (st.session_state.network_metrics['successful_handovers'] / total_handovers) * 100
        st.metric("Успішність хендоверів", f"{success_rate:.1f}%")
    
    # Статус мережі
    if st.session_state.network_active:
        st.success("🟢 Мережа активна")
    else:
        st.error("🔴 Мережа неактивна")

# Таблиця базових станцій
st.subheader("📡 Базові станції")
bs_df = pd.DataFrame(st.session_state.base_stations)
st.dataframe(
    bs_df[['name', 'users', 'load', 'power']].rename(columns={
        'name': 'Назва',
        'users': 'Користувачі',
        'load': 'Навантаження (%)',
        'power': 'Потужність (дБм)'
    }),
    use_container_width=True
)

# Автоматичне оновлення
if st.session_state.network_active:
    move_users()
    update_bs_load()
    update_network_metrics()
    time.sleep(1)
    st.rerun()
