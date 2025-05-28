import streamlit as st
import numpy as np
import pandas as pd
import folium
from streamlit_folium import st_folium
# import plotly.graph_objects as go # Не використовується у наданому коді
# import plotly.express as px # Не використовується у наданому коді
from datetime import datetime #, timedelta # timedelta не використовується
import time # Використовується для time.sleep, але може бути переглянуто для усунення моргання
import random # Не використовується напряму, np.random використовується
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
        'average_rsrp': -85.0, # Ініціалізуємо як float
        'network_throughput': 0.0, # Ініціалізуємо як float
        'active_users': 0
    }

# Функції симуляції
def calculate_rsrp(user_lat, user_lon, bs_lat, bs_lon, bs_power):
    """Розрахунок RSRP на основі відстані та потужності"""
    distance = geodesic((user_lat, user_lon), (bs_lat, bs_lon)).kilometers
    if distance == 0:
        distance = 0.001 # Уникнення ділення на нуль або log(0)

    # Спрощена модель втрат на трасі (COST-231 Hata model for urban areas)
    # Для частоти ~2GHz, висота антени BS ~30m, висота антени UE ~1.5m
    # L = 46.3 + 33.9log10(f) - 13.82log10(hb) - a(hm) + (44.9 - 6.55log10(hb))log10(d) + Cm
    # Спростимо для фіксованих параметрів, залишивши залежність від відстані:
    # path_loss = A + B * np.log10(distance_km)
    # Приблизні значення для міського середовища:
    path_loss = 128.1 + 37.6 * np.log10(distance) # Path loss in dB

    rsrp = bs_power - path_loss + np.random.normal(0, 2)  # +шум для реалістичності
    return max(-120.0, min(-40.0, rsrp)) # Обмеження типовими значеннями RSRP

def find_best_bs(user_lat, user_lon, base_stations):
    """Знаходження найкращої базової станції"""
    best_bs_info = None
    best_rsrp_val = -float('inf') # Починаємо з дуже малого значення

    for bs in base_stations:
        rsrp = calculate_rsrp(user_lat, user_lon, bs['lat'], bs['lon'], bs['power'])
        if rsrp > best_rsrp_val:
            best_rsrp_val = rsrp
            best_bs_info = bs

    return best_bs_info, best_rsrp_val

@st.cache_resource # Кешування карти для уникнення перемальовування
def create_network_map_cached():
    """Створення карти мережі з використанням тайлів Mapbox та кешуванням"""
    center = [49.2328, 28.4810]

    # ---- Зміни для Mapbox ----
    MAPBOX_API_KEY = "pk.eyJ1IjoiaHJ1c3N0dHQiLCJhIjoiY21iNnR0OXh1MDJ2ODJsczk3emdhdDh4ayJ9.CNygw7kmAPb6JGd0CFvUBg"
    MAPBOX_STYLE_ID = "mapbox/light-v11"

    tiles_url = f"https://api.mapbox.com/styles/v1/{MAPBOX_STYLE_ID}/tiles/{{z}}/{{x}}/{{y}}@2x?access_token={MAPBOX_API_KEY}"
    # Атрибуція для Mapbox (хоча ми її приховаємо)
    attribution = (
        '© <a href="https://www.mapbox.com/about/maps/">Mapbox</a> '
        '© <a href="http://www.openstreetmap.org/copyright">OpenStreetMap</a> '
        '<strong><a href="https://www.mapbox.com/map-feedback/" target="_blank">Improve this map</a></strong>'
    )
    # --------------------------

    m = folium.Map(
        location=center,
        zoom_start=12,
        tiles=tiles_url,
        attr=attribution,
        attributionControl=False  # Прибираємо напис "Leaflet" та стандартну атрибуцію
    )
    return m

def add_map_elements(folium_map):
    """Додавання динамічних елементів (станції, користувачі) на карту"""
    # Додавання базових станцій
    for bs in st.session_state.base_stations:
        if bs['load'] < 30:
            color = 'green'
        elif bs['load'] < 70:
            color = 'orange'
        else:
            color = 'red'

        folium.Marker(
            [bs['lat'], bs['lon']],
            popup=f"""
            <div style="font-family: Arial; font-size: 12px;">
                <b>{bs['name']}</b><br>
                ID: {bs['id']}<br>
                Потужність: {bs['power']} дБм<br>
                Користувачі: {bs['users']}<br>
                Навантаження: {bs['load']:.1f}%
            </div>
            """,
            icon=folium.Icon(color=color, icon='tower-broadcast', prefix='fa'),
            tooltip=f"{bs['name']} ({bs['load']:.1f}% load)"
        ).add_to(folium_map)

        folium.Circle(
            location=[bs['lat'], bs['lon']],
            radius=2000,
            color=color,
            fillColor=color,
            fillOpacity=0.1,
            weight=2
        ).add_to(folium_map)

    # Додавання активних користувачів
    for user in st.session_state.users:
        if user['active']:
            if user['rsrp'] > -70:
                user_color = 'green'
            elif user['rsrp'] > -90:
                user_color = 'orange'
            else:
                user_color = 'red'

            folium.Marker(
                [user['lat'], user['lon']],
                popup=f"""
                <div style="font-family: Arial; font-size: 12px;">
                    <b>User {user['id']}</b><br>
                    RSRP: {user['rsrp']:.1f} дБм<br>
                    Serving BS: {user['serving_bs']}<br>
                    Швидкість: {user['speed']} км/год<br>
                    Throughput: {user['throughput']:.1f} Мбіт/с
                </div>
                """,
                icon=folium.Icon(color=user_color, icon='mobile', prefix='fa'),
                tooltip=f"User {user['id']} (RSRP: {user['rsrp']:.1f} дБм)"
            ).add_to(folium_map)
    return folium_map


def generate_new_user():
    """Генерація нового користувача"""
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
    """Симуляція руху користувачів"""
    for user in st.session_state.users:
        if not user['active']:
            continue
        speed_ms = user['speed'] * 1000 / 3600
        distance_moved = speed_ms * 1 # Оновлення кожну секунду (інтервал симуляції)

        lat_change = (distance_moved * np.cos(np.radians(user['direction']))) / 111111
        lon_change = (distance_moved * np.sin(np.radians(user['direction']))) / (111111 * np.cos(np.radians(user['lat'])))

        user['lat'] += lat_change
        user['lon'] += lon_change
        user['lat'] = np.clip(user['lat'], 49.20, 49.27)
        user['lon'] = np.clip(user['lon'], 28.42, 28.55)

        if np.random.random() < 0.05: # 5% шанс змінити напрямок
            user['direction'] = np.random.uniform(0, 360)
        check_handover(user)

def check_handover(user):
    """Перевірка необхідності хендовера"""
    current_bs_list = [bs for bs in st.session_state.base_stations if bs['id'] == user['serving_bs']]
    if not current_bs_list: return
    current_bs = current_bs_list[0]

    current_rsrp = calculate_rsrp(user['lat'], user['lon'], current_bs['lat'], current_bs['lon'], current_bs['power'])
    best_candidate_bs, best_candidate_rsrp = find_best_bs(user['lat'], user['lon'], st.session_state.base_stations)

    # Критерій хендовера: RSRP нової станції кращий за RSRP поточної на hysteresis_margin,
    # і RSRP нової станції вищий за handover_threshold
    hysteresis_margin = 5  # дБ
    # handover_threshold = -95 # дБ (мінімальний RSRP для розгляду хендовера)

    if best_candidate_bs and best_candidate_bs['id'] != user['serving_bs'] and \
       best_candidate_rsrp > current_rsrp + hysteresis_margin:
        # and best_candidate_rsrp > handover_threshold: # Додаткова умова, якщо потрібна
        execute_handover(user, best_candidate_bs, current_rsrp, best_candidate_rsrp)
    else:
        user['rsrp'] = current_rsrp # Оновлюємо RSRP, навіть якщо хендовер не відбувся

def execute_handover(user, new_bs, old_rsrp, new_rsrp):
    """Виконання хендовера"""
    old_bs_id = user['serving_bs']
    user['serving_bs'] = new_bs['id']
    user['rsrp'] = new_rsrp
    user['handover_count'] += 1
    user['last_handover'] = datetime.now()

    # Визначення успішності хендовера (можна додати більш складні критерії)
    success = new_rsrp > old_rsrp + 3 # Наприклад, покращення мінімум на 3 дБ

    handover_event = {
        'timestamp': datetime.now(), 'user_id': user['id'],
        'old_bs': old_bs_id, 'new_bs': new_bs['id'],
        'old_rsrp': old_rsrp, 'new_rsrp': new_rsrp,
        'improvement': new_rsrp - old_rsrp, 'success': success
    }
    st.session_state.handover_events.append(handover_event)
    st.session_state.network_metrics['total_handovers'] += 1
    if success:
        st.session_state.network_metrics['successful_handovers'] += 1
    else:
        st.session_state.network_metrics['failed_handovers'] += 1

def update_network_metrics():
    """Оновлення мережевих метрик"""
    active_users_list = [u for u in st.session_state.users if u['active']]
    st.session_state.network_metrics['active_users'] = len(active_users_list)

    if active_users_list:
        avg_rsrp_val = np.mean([u['rsrp'] for u in active_users_list if u['rsrp'] is not None])
        avg_throughput_val = np.mean([u['throughput'] for u in active_users_list if u['throughput'] is not None])
        st.session_state.network_metrics['average_rsrp'] = float(avg_rsrp_val) if not np.isnan(avg_rsrp_val) else -120.0
        st.session_state.network_metrics['network_throughput'] = float(avg_throughput_val * len(active_users_list)) if not np.isnan(avg_throughput_val) else 0.0
    else:
        st.session_state.network_metrics['average_rsrp'] = -120.0
        st.session_state.network_metrics['network_throughput'] = 0.0


    for bs in st.session_state.base_stations:
        users_on_bs = len([u for u in active_users_list if u['serving_bs'] == bs['id']])
        bs['users'] = users_on_bs
        # Спрощена модель навантаження: кожні 5 користувачів = 10% навантаження, максимум 100%
        bs['load'] = min(100, users_on_bs * 10) # Наприклад, кожні 5 користувачів дають 10% навантаження

# Головний інтерфейс
st.title("🌐 LTE Network Simulator")
st.markdown("### Інтерактивний симулятор мережі LTE в реальному часі")

# Sidebar управління
st.sidebar.header("🎛️ Управління симуляцією")

if st.sidebar.button("🚀 Запустити мережу" if not st.session_state.network_active else "⏹️ Зупинити мережу"):
    st.session_state.network_active = not st.session_state.network_active
    if not st.session_state.network_active: # При зупинці очищаємо деякі метрики
        st.session_state.users = []
        st.session_state.handover_events = []
        st.session_state.network_metrics.update({
            'total_handovers': 0, 'successful_handovers': 0, 'failed_handovers': 0,
            'average_rsrp': -85.0, 'network_throughput': 0.0, 'active_users': 0
        })
        for bs_reset in st.session_state.base_stations: # Скидаємо користувачів і навантаження БС
            bs_reset['users'] = 0
            bs_reset['load'] = 0


if st.session_state.network_active:
    st.sidebar.success("✅ Мережа активна")
else:
    st.sidebar.info("⏸️ Мережа зупинена")

st.sidebar.subheader("⚙️ Параметри")
max_users = st.sidebar.slider("Максимум користувачів", 5, 50, 20)
# user_spawn_interval_seconds = st.sidebar.slider("Інтервал появи користувачів (сек)", 1.0, 10.0, 2.0, 0.5)
# Для еквіваленту user_spawn_rate 0.1-2.0, де 0.5 було типовим
# Якщо user_spawn_rate це ймовірність за крок симуляції (наприклад, 2 сек)
# Тоді інтервал = 1 / (user_spawn_rate / simulation_step_interval)
# Або простіше: менше значення = частіше
user_spawn_chance = st.sidebar.slider("Шанс появи користувача (за крок)", 0.05, 1.0, 0.25, 0.05) # 0.25 ~ кожні 4 кроки (8 сек)

if st.sidebar.button("➕ Додати користувача вручну"):
    if len(st.session_state.users) < max_users:
        new_user = generate_new_user()
        st.session_state.users.append(new_user)
        st.experimental_rerun()

if st.sidebar.button("🗑️ Очистити всіх користувачів"):
    st.session_state.users = []
    st.session_state.handover_events = []
    st.experimental_rerun()

# Основний контент
col1, col2 = st.columns([2, 1])

with col1:
    st.subheader("🗺️ Карта мережі")
    # Створюємо базову карту один раз (кешовану)
    base_map = create_network_map_cached()
    # Додаємо динамічні елементи на кожному оновленні
    current_map_with_elements = add_map_elements(base_map)
    map_placeholder = st.empty() # Використовуємо placeholder для карти
    map_placeholder.folium_static(current_map_with_elements, width=700, height=500)


with col2:
    st.subheader("📊 Метрики мережі")
    update_network_metrics() # Оновлюємо перед відображенням
    metrics = st.session_state.network_metrics
    st.metric("Активні користувачі", metrics['active_users'])
    st.metric("Всього хендоверів", metrics['total_handovers'])
    if metrics['total_handovers'] > 0:
        success_rate = (metrics['successful_handovers'] / metrics['total_handovers']) * 100
        st.metric("Успішність хендоверів", f"{success_rate:.1f}%")
    else:
        st.metric("Успішність хендоверів", "N/A")
    st.metric("Середня RSRP", f"{metrics['average_rsrp']:.1f} дБм")
    st.metric("Пропускна здатність", f"{metrics['network_throughput']:.1f} Мбіт/с")

st.subheader("📡 Статус базових станцій")
bs_data_display = []
for bs_item in st.session_state.base_stations:
    bs_data_display.append({
        'ID': bs_item['id'], 'Назва': bs_item['name'], 'Потужність (дБм)': bs_item['power'],
        'Користувачі': bs_item['users'], 'Навантаження (%)': f"{bs_item['load']:.1f}"
    })
st.dataframe(pd.DataFrame(bs_data_display), use_container_width=True)

if st.session_state.handover_events:
    st.subheader("🔄 Останні хендовери")
    recent_handovers_display = st.session_state.handover_events[-5:]
    ho_data_display = []
    for ho_item in reversed(recent_handovers_display):
        ho_data_display.append({
            'Час': ho_item['timestamp'].strftime('%H:%M:%S'), 'Користувач': ho_item['user_id'],
            'Від': ho_item['old_bs'], 'До': ho_item['new_bs'],
            'Покращення (дБ)': f"{ho_item.get('improvement', 0.0):.1f}", # Використовуємо .get для безпеки
            'Статус': '✅ Успішно' if ho_item['success'] else '❌ Невдало'
        })
    if ho_data_display:
        st.dataframe(pd.DataFrame(ho_data_display), use_container_width=True)

# Автоматичне оновлення, якщо мережа активна
simulation_interval_seconds = 2.0 # Інтервал симуляційного кроку

if st.session_state.network_active:
    # Додавання нових користувачів з заданим шансом
    if len(st.session_state.users) < max_users and np.random.random() < user_spawn_chance:
        new_user = generate_new_user()
        st.session_state.users.append(new_user)

    simulate_user_movement()
    update_network_metrics() # Оновлюємо метрики після руху/хендоверів

    # Для оновлення UI
    time.sleep(simulation_interval_seconds) # Затримка перед rerun
    st.experimental_rerun() # Перезапускаємо скрипт для оновлення UI

# Інформаційна панель
with st.expander("ℹ️ Про симулятор"):
    st.markdown("""
    ### Функції симулятора:
    **🌐 Реальна мережа LTE** - 5 базових станцій з різними характеристиками
    **👥 Динамічні користувачі** - автоматична генерація та рух користувачів
    **📡 Реалтайм хендовери** - автоматичне переключення між станціями
    **📊 Живі метрики** - моніторинг ефективності мережі в реальному часі
    **🗺️ Інтерактивна карта** - візуалізація всіх елементів мережі (з Mapbox)
    **⚙️ Налаштування** - контроль параметрів симуляції
    ### Алгоритм хендовера:
    - Користувач переключається на нову BS, якщо RSRP покращується > 5 дБ (гістерезис)
    - Враховується відстань та потужність передавачів для розрахунку RSRP
    - Автоматичний розрахунок успішності хендовера
    """)

