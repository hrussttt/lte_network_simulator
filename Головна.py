import streamlit as st
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
import time
import random
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
    # Створення мережі базових станцій
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

def create_network_map():
    """Створення карти мережі з Plotly"""
    fig = go.Figure()
    
    # Додавання базових станцій
    for bs in st.session_state.base_stations:
        # Визначення кольору залежно від навантаження
        if bs['load'] < 30:
            color = 'green'
        elif bs['load'] < 70:
            color = 'orange'
        else:
            color = 'red'
        
        fig.add_trace(go.Scattermapbox(
            lat=[bs['lat']],
            lon=[bs['lon']],
            mode='markers',
            marker=dict(
                size=15,
                color=color,
                symbol='circle'
            ),
            text=bs['name'],
            hovertemplate='<b>%{text}</b><br>' +
                        f'Навантаження: {bs["load"]:.1f}%<br>' +
                        f'Користувачі: {bs["users"]}<br>' +
                        f'Потужність: {bs["power"]} дБм<extra></extra>',
            name=f'БС {bs["name"]}',
            showlegend=True
        ))
    
    # Додавання користувачів
    for user in st.session_state.users:
        if user['active']:
            # Визначення кольору залежно від RSRP
            if user['rsrp'] > -70:
                color = 'lightgreen'
            elif user['rsrp'] > -85:
                color = 'yellow'
            else:
                color = 'red'
            
            fig.add_trace(go.Scattermapbox(
                lat=[user['lat']],
                lon=[user['lon']],
                mode='markers',
                marker=dict(
                    size=8,
                    color=color,
                    symbol='triangle-up'
                ),
                text=user['id'],
                hovertemplate='<b>%{text}</b><br>' +
                            f'RSRP: {user["rsrp"]:.1f} дБм<br>' +
                            f'Обслуговуюча БС: {user["serving_bs"]}<br>' +
                            f'Швидкість: {user["speed"]} км/год<extra></extra>',
                name=f'Користувач {user["id"]}',
                showlegend=False
            ))
    
    # Налаштування карти
    fig.update_layout(
        mapbox=dict(
            style="open-street-map",
            center=dict(lat=49.2328, lon=28.4810),
            zoom=11
        ),
        height=600,
        margin=dict(r=0, t=0, l=0, b=0),
        showlegend=True,
        uirevision='constant'
    )
    
    return fig

def move_user(user):
    """Переміщення користувача"""
    # Випадкове переміщення
    speed_ms = user['speed'] / 3.6  # км/год в м/с
    distance_m = speed_ms * 1  # за 1 секунду
    
    # Конвертація в градуси (приблизно)
    lat_change = (distance_m * np.cos(np.radians(user['direction']))) / 111111
    lon_change = (distance_m * np.sin(np.radians(user['direction']))) / (111111 * np.cos(np.radians(user['lat'])))
    
    user['lat'] += lat_change
    user['lon'] += lon_change
    
    # Обмеження координат (для Вінниці)
    user['lat'] = np.clip(user['lat'], 49.20, 49.27)
    user['lon'] = np.clip(user['lon'], 28.42, 28.55)
    
    # Випадкова зміна напряму (5% ймовірність)
    if random.random() < 0.05:
        user['direction'] = random.uniform(0, 360)

def update_user_metrics(user):
    """Оновлення метрик користувача"""
    # Знаходження найкращої BS
    best_bs, best_rsrp = find_best_bs(user['lat'], user['lon'], st.session_state.base_stations)
    
    if best_bs:
        # Перевірка хендовера
        if user['serving_bs'] != best_bs['id'] and best_rsrp > user['rsrp'] + 5:
            # Виконання хендовера
            old_bs = user['serving_bs']
            user['serving_bs'] = best_bs['id']
            user['handover_count'] += 1
            user['last_handover'] = datetime.now()
            
            # Додавання події хендовера
            handover_event = {
                'timestamp': datetime.now(),
                'user_id': user['id'],
                'old_bs': old_bs,
                'new_bs': best_bs['id'],
                'old_rsrp': user['rsrp'],
                'new_rsrp': best_rsrp,
                'improvement': best_rsrp - user['rsrp'],
                'success': best_rsrp > user['rsrp']
            }
            st.session_state.handover_events.append(handover_event)
            
            # Оновлення статистики
            st.session_state.network_metrics['total_handovers'] += 1
            if handover_event['success']:
                st.session_state.network_metrics['successful_handovers'] += 1
            else:
                st.session_state.network_metrics['failed_handovers'] += 1
        
        user['rsrp'] = best_rsrp
        user['throughput'] = max(0, (best_rsrp + 120) * 2)  # Спрощений розрахунок

def add_random_user():
    """Додавання випадкового користувача"""
    user_id = f"UE_{len(st.session_state.users) + 1:03d}"
    user = {
        'id': user_id,
        'lat': random.uniform(49.20, 49.27),
        'lon': random.uniform(28.42, 28.55),
        'speed': random.uniform(5, 60),
        'direction': random.uniform(0, 360),
        'active': True,
        'serving_bs': None,
        'rsrp': -85,
        'throughput': 0,
        'handover_count': 0,
        'last_handover': None
    }
    
    # Знаходження початкової BS
    best_bs, best_rsrp = find_best_bs(user['lat'], user['lon'], st.session_state.base_stations)
    if best_bs:
        user['serving_bs'] = best_bs['id']
        user['rsrp'] = best_rsrp
    
    st.session_state.users.append(user)

def update_bs_load():
    """Оновлення навантаження базових станцій"""
    for bs in st.session_state.base_stations:
        bs['users'] = len([u for u in st.session_state.users if u['active'] and u['serving_bs'] == bs['id']])
        bs['load'] = min(100, bs['users'] * 2)  # Спрощений розрахунок

# Заголовок
st.title("📡 Симулятор хендовера LTE в мережі м. Вінниця")

# Бічна панель
st.sidebar.header("⚙️ Параметри симуляції")

# Кнопки управління
if st.sidebar.button("🚀 Запустити мережу"):
    st.session_state.network_active = True
    st.sidebar.success("Мережа запущена!")

if st.sidebar.button("⏹️ Зупинити мережу"):
    st.session_state.network_active = False
    st.sidebar.warning("Мережа зупинена!")

if st.sidebar.button("🔄 Скинути симуляцію"):
    st.session_state.users = []
    st.session_state.handover_events = []
    st.session_state.network_metrics = {
        'total_handovers': 0,
        'successful_handovers': 0,
        'failed_handovers': 0,
        'average_rsrp': -85,
        'network_throughput': 0,
        'active_users': 0
    }
    st.sidebar.info("Симуляція скинута!")

# Параметри користувачів
st.sidebar.subheader("👥 Користувачі")
max_users = st.sidebar.slider("Максимум користувачів", 1, 50, 10)
auto_add_users = st.sidebar.checkbox("Автоматично додавати користувачів")

if st.sidebar.button("➕ Додати користувача"):
    if len(st.session_state.users) < max_users:
        add_random_user()
        st.sidebar.success(f"Додано користувача {st.session_state.users[-1]['id']}")

# Основний інтерфейс
col1, col2 = st.columns([2, 1])

with col1:
    st.subheader("🗺️ Карта мережі")
    
    # Відображення карти
    map_fig = create_network_map()
    st.plotly_chart(map_fig, use_container_width=True)

with col2:
    st.subheader("📊 Метрики мережі")
    
    # Поточні метрики
    active_users = len([u for u in st.session_state.users if u['active']])
    st.metric("Активні користувачі", active_users)
    st.metric("Всього хендоверів", st.session_state.network_metrics['total_handovers'])
    
    if st.session_state.network_metrics['total_handovers'] > 0:
        success_rate = (st.session_state.network_metrics['successful_handovers'] / 
                       st.session_state.network_metrics['total_handovers']) * 100
        st.metric("Успішність хендоверів", f"{success_rate:.1f}%")
    
    if active_users > 0:
        avg_rsrp = np.mean([u['rsrp'] for u in st.session_state.users if u['active']])
        st.metric("Середня RSRP", f"{avg_rsrp:.1f} дБм")
    
    # Статус мережі
    if st.session_state.network_active:
        st.success("🟢 Мережа активна")
    else:
        st.error("🔴 Мережа неактивна")

# Таблиця базових станцій
st.subheader("📡 Базові станції")
bs_df = pd.DataFrame(st.session_state.base_stations)
st.dataframe(bs_df, use_container_width=True)

# Таблиця користувачів
if st.session_state.users:
    st.subheader("👥 Активні користувачі")
    users_data = []
    for user in st.session_state.users:
        if user['active']:
            users_data.append({
                'ID': user['id'],
                'Обслуговуюча БС': user['serving_bs'],
                'RSRP (дБм)': f"{user['rsrp']:.1f}",
                'Швидкість (км/год)': user['speed'],
                'Хендовери': user['handover_count'],
                'Throughput (Мбіт/с)': f"{user['throughput']:.1f}"
            })
    
    if users_data:
        users_df = pd.DataFrame(users_data)
        st.dataframe(users_df, use_container_width=True)

# Автоматичне оновлення
if st.session_state.network_active:
    # Переміщення користувачів
    for user in st.session_state.users:
        if user['active']:
            move_user(user)
            update_user_metrics(user)
    
    # Автоматичне додавання користувачів
    if auto_add_users and len(st.session_state.users) < max_users and random.random() < 0.1:
        add_random_user()
    
    # Оновлення навантаження BS
    update_bs_load()
    
    # Оновлення метрик мережі
    st.session_state.network_metrics['active_users'] = len([u for u in st.session_state.users if u['active']])
    
    # Автоматичне оновлення сторінки
    time.sleep(1)
    st.rerun()
