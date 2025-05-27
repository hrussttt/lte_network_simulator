import streamlit as st
import pydeck as pdk
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
    page_title="LTE Network Simulator - Вінниця",
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
    # Реальні базові станції Вінниці з роботи
    st.session_state.base_stations = [
        {
            'id': 'eNodeB_001', 'name': 'Центр (Соборна)', 'lat': 49.2328, 'lon': 28.4810, 
            'power': 43, 'frequency': 1800, 'operator': 'Київстар', 'users': 0, 'load': 0,
            'color': [0, 100, 255, 180], 'range_km': 2.5
        },
        {
            'id': 'eNodeB_002', 'name': 'Вишенька', 'lat': 49.2510, 'lon': 28.4590,
            'power': 40, 'frequency': 2600, 'operator': 'Vodafone', 'users': 0, 'load': 0,
            'color': [255, 50, 50, 180], 'range_km': 1.8
        },
        {
            'id': 'eNodeB_003', 'name': 'Замостя', 'lat': 49.2180, 'lon': 28.5120,
            'power': 41, 'frequency': 1800, 'operator': 'lifecell', 'users': 0, 'load': 0,
            'color': [50, 255, 50, 180], 'range_km': 2.2
        },
        {
            'id': 'eNodeB_004', 'name': 'Пирогово', 'lat': 49.2450, 'lon': 28.5280,
            'power': 38, 'frequency': 2600, 'operator': 'Київстар', 'users': 0, 'load': 0,
            'color': [0, 100, 255, 180], 'range_km': 1.5
        },
        {
            'id': 'eNodeB_005', 'name': 'Старе місто', 'lat': 49.2290, 'lon': 28.4650,
            'power': 42, 'frequency': 900, 'operator': 'Vodafone', 'users': 0, 'load': 0,
            'color': [255, 50, 50, 180], 'range_km': 3.0
        },
        {
            'id': 'eNodeB_006', 'name': 'Військове містечко', 'lat': 49.2150, 'lon': 28.4420,
            'power': 39, 'frequency': 1800, 'operator': 'lifecell', 'users': 0, 'load': 0,
            'color': [50, 255, 50, 180], 'range_km': 2.0
        }
    ]

if 'handover_events' not in st.session_state:
    st.session_state.handover_events = []
if 'network_metrics' not in st.session_state:
    st.session_state.network_metrics = {
        'total_handovers': 0,
        'successful_handovers': 0,
        'failed_handovers': 0,
        'early_handovers': 0,
        'late_handovers': 0,
        'pingpong_handovers': 0,
        'average_rsrp': -85,
        'network_throughput': 0,
        'active_users': 0
    }
if 'handover_timers' not in st.session_state:
    st.session_state.handover_timers = {}

# Функції симуляції згідно з бакалаврською роботою
def calculate_rsrp_cost_hata(user_lat, user_lon, bs, metrology_error=1.0):
    """Розрахунок RSRP за моделлю COST-Hata з роботи"""
    distance_km = geodesic((user_lat, user_lon), (bs['lat'], bs['lon'])).kilometers
    if distance_km == 0:
        distance_km = 0.001
    
    frequency = bs['frequency']
    h_bs = 30  # висота антени БС, м
    
    # Модель COST-Hata для міської місцевості (з роботи)
    if frequency <= 1000:  # 900 МГц
        path_loss = (69.55 + 26.16*np.log10(frequency) - 
                    13.82*np.log10(h_bs) + 
                    (44.9 - 6.55*np.log10(h_bs))*np.log10(distance_km))
    else:  # 1800/2600 МГц
        path_loss = (46.3 + 33.9*np.log10(frequency) - 
                    13.82*np.log10(h_bs) + 
                    (44.9 - 6.55*np.log10(h_bs))*np.log10(distance_km) + 3)
    
    # RSRP = Потужність - Втрати + Gain антени
    rsrp = bs['power'] - path_loss + 15  # 15 dB antenna gain
    
    # Метрологічна похибка ±1 дБ (з роботи)
    rsrp += np.random.normal(0, metrology_error)
    
    # Rayleigh fading
    rsrp += np.random.normal(0, 4)
    
    return max(-120, min(-40, rsrp))

def check_handover_condition_advanced(user, base_stations, ttt=280, hyst=4, offset=0):
    """Розширений алгоритм хендовера з роботи з різними типами результатів"""
    if not user['serving_bs']:
        return None, None
    
    # Поточна обслуговуюча BS
    serving_bs = next((bs for bs in base_stations if bs['id'] == user['serving_bs']), None)
    if not serving_bs:
        return None, None
    
    # Вимірювання RSRP від всіх BS
    measurements = {}
    for bs in base_stations:
        rsrp = calculate_rsrp_cost_hata(user['lat'], user['lon'], bs)
        measurements[bs['id']] = rsrp
    
    serving_rsrp = measurements[user['serving_bs']]
    user['rsrp'] = serving_rsrp
    
    # Знаходження найкращої цільової BS
    best_target = None
    best_rsrp = -999
    
    for bs_id, rsrp in measurements.items():
        if bs_id != user['serving_bs'] and rsrp > best_rsrp:
            best_rsrp = rsrp
            best_target = bs_id
    
    if not best_target:
        return None, None
    
    # Умова хендовера з роботи: RSRP_target > RSRP_serving + Hyst + Offset
    condition_met = best_rsrp > serving_rsrp + hyst + offset
    
    user_id = user['id']
    current_time = time.time() * 1000  # мс
    
    if condition_met:
        # Перевірка TTT таймера
        if user_id not in st.session_state.handover_timers:
            # Початок TTT
            st.session_state.handover_timers[user_id] = {
                'start_time': current_time,
                'target_bs': best_target,
                'target_rsrp': best_rsrp
            }
            return None, f"TTT почато для {best_target}"
        
        timer_info = st.session_state.handover_timers[user_id]
        elapsed = current_time - timer_info['start_time']
        
        # Перевірка зміни цільової BS
        if timer_info['target_bs'] != best_target:
            # Перезапуск TTT
            st.session_state.handover_timers[user_id] = {
                'start_time': current_time,
                'target_bs': best_target,
                'target_rsrp': best_rsrp
            }
            return None, f"TTT перезапущено для {best_target}"
        
        if elapsed >= ttt:
            # TTT спрацював - виконуємо хендовер
            del st.session_state.handover_timers[user_id]
            return execute_handover_realistic(user, serving_bs, best_target, serving_rsrp, best_rsrp, elapsed, ttt)
        else:
            remaining = ttt - elapsed
            return None, f"TTT: {remaining:.0f}мс до {best_target}"
    
    else:
        # Умова не виконана - скидаємо TTT
        if user_id in st.session_state.handover_timers:
            del st.session_state.handover_timers[user_id]
        
        improvement_needed = serving_rsrp + hyst + offset - best_rsrp
        return None, f"Serving: {serving_bs['name']} (потрібно +{improvement_needed:.1f}дБ)"

def execute_handover_realistic(user, old_bs, new_bs_id, old_rsrp, new_rsrp, elapsed_time, ttt):
    """Реалістичне виконання хендовера з різними типами згідно з роботою"""
    new_bs = next((bs for bs in st.session_state.base_stations if bs['id'] == new_bs_id), None)
    if not new_bs:
        return None, "Помилка: цільова BS не знайдена"
    
    # Визначення типу хендовера згідно з роботою
    improvement = new_rsrp - old_rsrp
    speed = user['speed']
    
    # Логіка класифікації з роботи
    ho_type = "successful"
    
    # Передчасний хендовер (< 0.8 * TTT)
    if elapsed_time < 0.8 * ttt:
        ho_type = "early"
        st.session_state.network_metrics['early_handovers'] += 1
    
    # Запізнілий хендовер (> 1.2 * TTT) 
    elif elapsed_time > 1.2 * ttt:
        ho_type = "late"
        st.session_state.network_metrics['late_handovers'] += 1
    
    # Ping-pong (швидкий рух або мале покращення)
    elif improvement < 3 or (speed > 60 and improvement < 5):
        ho_type = "pingpong"
        st.session_state.network_metrics['pingpong_handovers'] += 1
    
    # Невдалий хендовер (погіршення сигналу)
    elif improvement < 0:
        ho_type = "failed"
        st.session_state.network_metrics['failed_handovers'] += 1
    
    # Успішний хендовер
    else:
        ho_type = "successful"
        st.session_state.network_metrics['successful_handovers'] += 1
    
    # Оновлення користувача
    old_bs['users'] = max(0, old_bs['users'] - 1)
    new_bs['users'] += 1
    
    user['serving_bs'] = new_bs_id
    user['rsrp'] = new_rsrp
    user['handover_count'] += 1
    user['last_handover'] = datetime.now()
    
    # Збереження події
    handover_event = {
        'timestamp': datetime.now(),
        'user_id': user['id'],
        'old_bs': old_bs['id'],
        'new_bs': new_bs_id,
        'old_rsrp': old_rsrp,
        'new_rsrp': new_rsrp,
        'improvement': improvement,
        'type': ho_type,
        'elapsed_time': elapsed_time,
        'success': ho_type == "successful"
    }
    
    st.session_state.handover_events.append(handover_event)
    st.session_state.network_metrics['total_handovers'] += 1
    
    # Статус повідомлення
    type_names = {
        'successful': '✅ Успішний',
        'early': '⚡ Передчасний', 
        'late': '⏰ Запізнілий',
        'pingpong': '🏓 Ping-pong',
        'failed': '❌ Невдалий'
    }
    
    status = f"{type_names[ho_type]} хендовер: {old_bs['name']} → {new_bs['name']} (+{improvement:.1f}дБ)"
    
    return handover_event, status

def create_3d_lte_map():
    """Створення 3D карти мережі LTE без миготіння"""
    
    # Підготовка даних базових станцій
    bs_data = []
    for bs in st.session_state.base_stations:
        # Висота залежно від потужності та навантаження
        height = (bs['power'] - 30) * 10 + bs['load'] * 2
        
        # Колір залежно від навантаження
        if bs['load'] < 30:
            color = [0, 255, 0, 200]  # Зелений
        elif bs['load'] < 70:
            color = [255, 165, 0, 200]  # Помаранчевий
        else:
            color = [255, 0, 0, 200]  # Червоний
        
        bs_data.append({
            'lat': bs['lat'],
            'lon': bs['lon'],
            'elevation': height,
            'radius': bs['range_km'] * 1000,  # в метрах
            'name': bs['name'],
            'operator': bs['operator'],
            'power': bs['power'],
            'users': bs['users'],
            'load': bs['load'],
            'color': color
        })
    
    # Підготовка даних користувачів
    users_data = []
    for user in st.session_state.users:
        if user.get('active', True):
            rsrp = user.get('rsrp', -85)
            
            # Колір залежно від якості сигналу
            if rsrp > -70:
                user_color = [0, 255, 0, 255]  # Зелений
            elif rsrp > -85:
                user_color = [255, 165, 0, 255]  # Помаранчевий  
            elif rsrp > -100:
                user_color = [255, 0, 0, 255]  # Червоний
            else:
                user_color = [128, 0, 128, 255]  # Фіолетовий
            
            # Розмір залежно від швидкості
            size = 50 + user['speed'] * 2
            
            users_data.append({
                'lat': user['lat'],
                'lon': user['lon'],
                'elevation': 20,
                'rsrp': rsrp,
                'speed': user['speed'],
                'user_id': user['id'],
                'serving_bs': user.get('serving_bs', 'None'),
                'color': user_color,
                'size': size
            })
    
    # Створення шарів для 3D карти
    layers = []
    
    # Шар зон покриття (кола на землі)
    if bs_data:
        layers.append(pdk.Layer(
            'ScatterplotLayer',
            data=bs_data,
            get_position='[lon, lat]',
            get_radius='radius',
            get_fill_color='color',
            pickable=True,
            filled=True,
            radius_scale=1,
            radius_min_pixels=10
        ))
        
        # Шар 3D башт базових станцій
        layers.append(pdk.Layer(
            'ColumnLayer',
            data=bs_data,
            get_position='[lon, lat]',
            get_elevation='elevation',
            elevation_scale=1,
            radius=100,
            get_fill_color='color',
            pickable=True,
            extruded=True
        ))
    
    # Шар користувачів
    if users_data:
        layers.append(pdk.Layer(
            'ScatterplotLayer',
            data=users_data,
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
        pitch=45,  # Нахил для 3D ефекту
        bearing=0
    )
    
    # Tooltip для інтерактивності
    tooltip = {
        "html": """
        <div style="background-color: rgba(0,0,0,0.8); color: white; padding: 10px; border-radius: 5px; font-size: 12px;">
            <b>{name}</b><br/>
            <b>Оператор:</b> {operator}<br/>
            <b>Потужність:</b> {power} дБм<br/>
            <b>Користувачі:</b> {users}<br/>
            <b>Навантаження:</b> {load:.1f}%<br/>
            <b>RSRP:</b> {rsrp:.1f} дБм<br/>
            <b>Швидкість:</b> {speed} км/год<br/>
            <b>ID:</b> {user_id}
        </div>
        """,
        "style": {"color": "white"}
    }
    
    return pdk.Deck(
        layers=layers,
        initial_view_state=view_state,
        tooltip=tooltip,
        map_style='light'  # Використовуємо світлий стиль без потреби в mapbox token
    )

def find_best_bs(user_lat, user_lon, base_stations):
    """Знаходження найкращої базової станції"""
    best_bs = None
    best_rsrp = -999
    
    for bs in base_stations:
        rsrp = calculate_rsrp_cost_hata(user_lat, user_lon, bs)
        if rsrp > best_rsrp:
            best_rsrp = rsrp
            best_bs = bs
    
    return best_bs, best_rsrp

def generate_new_user():
    """Генерація нового користувача"""
    user_id = f"UE{len(st.session_state.users)+1:03d}"
    
    # Випадкова позиція в межах Вінниці
    lat = 49.2328 + np.random.uniform(-0.03, 0.03)
    lon = 28.4810 + np.random.uniform(-0.05, 0.05)
    
    # Знаходження найкращої BS для початкового підключення
    best_bs, rsrp = find_best_bs(lat, lon, st.session_state.base_stations)
    
    user = {
        'id': user_id,
        'lat': lat,
        'lon': lon,
        'serving_bs': best_bs['id'] if best_bs else None,
        'rsrp': rsrp,
        'speed': np.random.choice([5, 20, 40, 60, 90]),  # км/год
        'direction': np.random.uniform(0, 360),  # градуси
        'throughput': np.random.uniform(10, 100),  # Мбіт/с
        'active': True,
        'handover_count': 0,
        'last_handover': None
    }
    
    if best_bs:
        best_bs['users'] += 1
        best_bs['load'] = min(100, (best_bs['users'] / 20) * 100)  # 20 користувачів = 100%
    
    return user

def simulate_user_movement():
    """Симуляція руху користувачів"""
    for user in st.session_state.users:
        if not user['active']:
            continue
        
        # Розрахунок нової позиції
        speed_ms = user['speed'] * 1000 / 3600  # м/с
        distance = speed_ms * 1  # за 1 секунду
        
        # Конвертація в градуси
        lat_change = (distance * np.cos(np.radians(user['direction']))) / 111111
        lon_change = (distance * np.sin(np.radians(user['direction']))) / (111111 * np.cos(np.radians(user['lat'])))
        
        user['lat'] += lat_change
        user['lon'] += lon_change
        
        # Обмеження межами Вінниці
        user['lat'] = np.clip(user['lat'], 49.20, 49.27)
        user['lon'] = np.clip(user['lon'], 28.42, 28.55)
        
        # Випадкова зміна напряму
        if np.random.random() < 0.05:
            user['direction'] = np.random.uniform(0, 360)

def update_network_metrics():
    """Оновлення мережевих метрик"""
    active_users = [u for u in st.session_state.users if u['active']]
    st.session_state.network_metrics['active_users'] = len(active_users)
    
    if active_users:
        avg_rsrp = np.mean([u['rsrp'] for u in active_users])
        avg_throughput = np.mean([u['throughput'] for u in active_users])
        st.session_state.network_metrics['average_rsrp'] = avg_rsrp
        st.session_state.network_metrics['network_throughput'] = avg_throughput * len(active_users)
    
    # Оновлення навантаження BS
    for bs in st.session_state.base_stations:
        bs['users'] = len([u for u in active_users if u.get('serving_bs') == bs['id']])
        bs['load'] = min(100, (bs['users'] / 20) * 100)

# Головний інтерфейс
st.title("🏗️ Симулятор хендовера LTE в мережі м. Вінниця")
st.markdown("### Архітектурні принципи та оптимізація функціонування мережі LTE з метрологічними аспектами")
st.markdown("**Бакалаврська робота - Хрустовський А.А. | Керівник: Савицький А.Ю.**")

# Sidebar управління згідно з роботою
st.sidebar.header("⚙️ Параметри хендовера")
ttt = st.sidebar.slider("Time-to-Trigger (мс)", 40, 1000, 280, 40)
hyst = st.sidebar.slider("Hysteresis (дБ)", 0, 10, 4, 1)
offset = st.sidebar.slider("Offset (дБ)", -10, 10, 0, 1)

st.sidebar.header("🔬 Метрологічні параметри")
metrology_error = st.sidebar.slider("Похибка RSRP (дБ)", 0.1, 3.0, 1.0, 0.1)

st.sidebar.header("🚶 Управління користувачами")
max_users = st.sidebar.slider("Максимум користувачів", 5, 50, 20)

# Основний інтерфейс
col1, col2 = st.columns([2.5, 1.5])

with col1:
    st.subheader("🗺️ 3D Карта мережі LTE Вінниці")
    
    # Створення та відображення 3D карти БЕЗ миготіння
    deck = create_3d_lte_map()
    
    # Використання ключа для стабільного відображення
    map_placeholder = st.empty()
    with map_placeholder.container():
        st.pydeck_chart(deck, use_container_width=True, height=500)

with col2:
    st.subheader("📊 Поточний стан системи")
    
    # Кнопки керування
    col_btn1, col_btn2 = st.columns(2)
    with col_btn1:
        if st.button("▶️ Старт", use_container_width=True):
            st.session_state.network_active = True
    with col_btn2:
        if st.button("⏸️ Стоп", use_container_width=True):
            st.session_state.network_active = False
    
    # Кнопка додавання користувача
    if st.button("➕ Додати користувача", use_container_width=True):
        if len(st.session_state.users) < max_users:
            new_user = generate_new_user()
            st.session_state.users.append(new_user)
    
    # Кнопка очищення
    if st.button("🗑️ Очистити користувачів", use_container_width=True):
        st.session_state.users = []
        st.session_state.handover_events = []
        for bs in st.session_state.base_stations:
            bs['users'] = 0
            bs['load'] = 0
    
    # Оновлення метрик
    update_network_metrics()
    
    # Відображення метрик згідно з роботою
    metrics = st.session_state.network_metrics
    
    st.metric("Активні користувачі", metrics['active_users'])
    st.metric("Всього хендоверів", metrics['total_handovers'])
    
    if metrics['total_handovers'] > 0:
        success_rate = (metrics['successful_handovers'] / metrics['total_handovers']) * 100
        st.metric("Успішність хендоверів", f"{success_rate:.1f}%")
    
    st.metric("Середня RSRP", f"{metrics['average_rsrp']:.1f} дБм")

# Статистика хендоверів згідно з роботою
if st.session_state.handover_events:
    st.subheader("🔄 Статистика хендоверів")
    
    total = metrics['total_handovers']
    col3, col4, col5, col6, col7 = st.columns(5)
    
    with col3:
        st.metric("✅ Успішні", f"{metrics['successful_handovers']}")
    with col4:
        st.metric("⚡ Передчасні", f"{metrics['early_handovers']}")
    with col5:
        st.metric("⏰ Запізнілі", f"{metrics['late_handovers']}")
    with col6:
        st.metric("🏓 Ping-pong", f"{metrics['pingpong_handovers']}")
    with col7:
        failed_total = metrics['failed_handovers'] + metrics['early_handovers'] + metrics['late_handovers'] + metrics['pingpong_handovers']
        st.metric("❌ Невдалі сумарно", f"{failed_total}")

# Таблиця останніх хендоверів
if st.session_state.handover_events:
    st.subheader("📋 Останні хендовери")
    
    recent_handovers = st.session_state.handover_events[-10:]  # Останні 10
    ho_data = []
    
    type_icons = {
        'successful': '✅',
        'early': '⚡',
        'late': '⏰', 
        'pingpong': '🏓',
        'failed': '❌'
    }
    
    for ho in reversed(recent_handovers):
        old_bs_name = next((bs['name'] for bs in st.session_state.base_stations if bs['id'] == ho['old_bs']), ho['old_bs'])
        new_bs_name = next((bs['name'] for bs in st.session_state.base_stations if bs['id'] == ho['new_bs']), ho['new_bs'])
        
        ho_data.append({
            'Час': ho['timestamp'].strftime('%H:%M:%S'),
            'Користувач': ho['user_id'],
            'Від': old_bs_name,
            'До': new_bs_name,
            'RSRP до': f"{ho['old_rsrp']:.1f} дБм",
            'RSRP після': f"{ho['new_rsrp']:.1f} дБм",
            'Покращення': f"{ho['improvement']:+.1f} дБ",
            'Тип': f"{type_icons.get(ho['type'], '❓')} {ho['type'].title()}"
        })
    
    if ho_data:
        st.dataframe(pd.DataFrame(ho_data), use_container_width=True, hide_index=True)

# Автоматичне оновлення симуляції
if st.session_state.network_active:
    # Автоматичне додавання користувачів
    if len(st.session_state.users) < max_users and np.random.random() < 0.1:
        new_user = generate_new_user()
        st.session_state.users.append(new_user)
    
    # Симуляція руху
    simulate_user_movement()
    
    # Перевірка хендоверів для всіх користувачів
    for user in st.session_state.users:
        if user['active']:
            handover_event, status = check_handover_condition_advanced(
                user, st.session_state.base_stations, ttt, hyst, offset
            )
    
    # Оновлення через 2 секунди
    time.sleep(2)
    st.rerun()

# Інформаційна панель про роботу
with st.expander("ℹ️ Про реалістичну симуляцію хендовера"):
    st.markdown("""
    ### 🎯 Реалізовані типи хендоверів згідно з бакалаврською роботою:
    
    **✅ Успішні хендовери** - виконані вчасно з покращенням сигналу ≥3дБ
    
    **⚡ Передчасні хендовери** - виконані занадто рано (< 0.8×TTT)
    
    **⏰ Запізнілі хендовери** - виконані із затримкою (> 1.2×TTT)
    
    **🏓 Ping-pong хендовери** - при малому покращенні або високій швидкості
    
    **❌ Невдалі хендовери** - з погіршенням якості сигналу
    
    ### 📡 Модель COST-Hata для міської місцевості
    
    **🗺️ 3D Візуалізація:**
    - Висота веж залежить від потужності та навантаження
    - Кольори BS: зелений (низьке навантаження), помаранчевий (середнє), червоний (високе)
    - Розмір UE залежить від швидкості руху
    - Карта не миготить при оновленні даних
    
    ### ⚙️ Оптимальні параметри з роботи:
    - **TTT**: 280 мс (оптимальне значення)
    - **Hysteresis**: 4 дБ (баланс між ping-pong та затримкою)
    - **Offset**: 0 дБ (без зсуву)
    - **Метрологічна похибка**: ±1 дБ (реалістична точність)
    """)
