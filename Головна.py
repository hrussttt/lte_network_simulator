import streamlit as st
import pydeck as pdk
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
import time
import random
from geopy.distance import geodesic

# Конфігурація сторінки
st.set_page_config(
    page_title="📡 LTE Network Simulator | ВНТУ",
    page_icon="📡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Кастомний CSS для покращення дизайну
st.markdown("""
<style>
    .main-header {
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        padding: 1rem;
        border-radius: 10px;
        color: white;
        text-align: center;
        margin-bottom: 2rem;
    }
    .metric-card {
        background: white;
        padding: 1rem;
        border-radius: 8px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        border-left: 4px solid #667eea;
    }
    .status-success { color: #28a745; font-weight: bold; }
    .status-warning { color: #ffc107; font-weight: bold; }
    .status-danger { color: #dc3545; font-weight: bold; }
    .sidebar .sidebar-content {
        background: #f8f9fa;
    }
    .stButton > button {
        width: 100%;
        border-radius: 20px;
        border: none;
        padding: 0.5rem 1rem;
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)

# Ініціалізація стану сесії
if 'network_active' not in st.session_state:
    st.session_state.network_active = False
if 'users' not in st.session_state:
    st.session_state.users = []
if 'base_stations' not in st.session_state:
    st.session_state.base_stations = [
        {
            'id': 'BS001', 'name': 'Центр (Соборна)', 'lat': 49.2328, 'lon': 28.4810,
            'power': 43, 'frequency': 1800, 'operator': 'Київстар', 'users': 0, 'load': 0,
            'color': [30, 144, 255, 200], 'range_km': 2.5, 'height': 50
        },
        {
            'id': 'BS002', 'name': 'Вишенька', 'lat': 49.2510, 'lon': 28.4590,
            'power': 40, 'frequency': 2600, 'operator': 'Vodafone', 'users': 0, 'load': 0,
            'color': [255, 69, 0, 200], 'range_km': 1.8, 'height': 45
        },
        {
            'id': 'BS003', 'name': 'Замостя', 'lat': 49.2180, 'lon': 28.5120,
            'power': 41, 'frequency': 1800, 'operator': 'lifecell', 'users': 0, 'load': 0,
            'color': [50, 205, 50, 200], 'range_km': 2.2, 'height': 47
        },
        {
            'id': 'BS004', 'name': 'Пирогово', 'lat': 49.2450, 'lon': 28.5280,
            'power': 38, 'frequency': 2600, 'operator': 'Київстар', 'users': 0, 'load': 0,
            'color': [30, 144, 255, 200], 'range_km': 1.5, 'height': 42
        },
        {
            'id': 'BS005', 'name': 'Старе місто', 'lat': 49.2290, 'lon': 28.4650,
            'power': 42, 'frequency': 900, 'operator': 'Vodafone', 'users': 0, 'load': 0,
            'color': [255, 69, 0, 200], 'range_km': 3.0, 'height': 48
        },
        {
            'id': 'BS006', 'name': 'Військове містечко', 'lat': 49.2150, 'lon': 28.4420,
            'power': 39, 'frequency': 1800, 'operator': 'lifecell', 'users': 0, 'load': 0,
            'color': [50, 205, 50, 200], 'range_km': 2.0, 'height': 44
        }
    ]

if 'handover_events' not in st.session_state:
    st.session_state.handover_events = []
if 'network_metrics' not in st.session_state:
    st.session_state.network_metrics = {
        'total_handovers': 0, 'successful_handovers': 0, 'failed_handovers': 0,
        'early_handovers': 0, 'late_handovers': 0, 'pingpong_handovers': 0,
        'average_rsrp': -85, 'network_throughput': 0, 'active_users': 0
    }
if 'handover_timers' not in st.session_state:
    st.session_state.handover_timers = {}
if 'selected_scenario' not in st.session_state:
    st.session_state.selected_scenario = "Навчальний режим"

# Заголовок
st.markdown("""
<div class="main-header">
    <h1>📡 LTE Network Simulator</h1>
    <h3>Інтерактивний симулятор мережі LTE для навчання</h3>
    <p><strong>Вінницький національний технічний університет</strong> | Кафедра ІРТС</p>
</div>
""", unsafe_allow_html=True)

# Функції симуляції
def calculate_rsrp_cost_hata(user_lat, user_lon, bs, metrology_error=1.0):
    """Розрахунок RSRP за моделлю COST-Hata"""
    distance_km = geodesic((user_lat, user_lon), (bs['lat'], bs['lon'])).kilometers
    if distance_km == 0:
        distance_km = 0.001
    
    frequency = bs['frequency']
    h_bs = 30  # висота антени БС
    
    # Модель COST-Hata для міської місцевості
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
    
    # Метрологічна похибка
    rsrp += np.random.normal(0, metrology_error)
    rsrp += np.random.normal(0, 4)  # Rayleigh fading
    
    return max(-120, min(-40, rsrp))

def check_handover_condition_educational(user, base_stations, ttt=280, hyst=4, offset=0):
    """Освітній алгоритм хендовера з детальними поясненнями"""
    if not user['serving_bs']:
        return None, None, {"step": "initial", "explanation": "Початкове підключення до мережі"}
    
    serving_bs = next((bs for bs in base_stations if bs['id'] == user['serving_bs']), None)
    if not serving_bs:
        return None, None, {"step": "error", "explanation": "Обслуговуюча БС не знайдена"}
    
    # Крок 1: Вимірювання RSRP
    measurements = {}
    for bs in base_stations:
        rsrp = calculate_rsrp_cost_hata(user['lat'], user['lon'], bs)
        measurements[bs['id']] = rsrp
    
    serving_rsrp = measurements[user['serving_bs']]
    user['rsrp'] = serving_rsrp
    
    # Крок 2: Знаходження найкращої цільової БС
    best_target = None
    best_rsrp = -999
    
    for bs_id, rsrp in measurements.items():
        if bs_id != user['serving_bs'] and rsrp > best_rsrp:
            best_rsrp = rsrp
            best_target = bs_id
    
    if not best_target:
        return None, None, {"step": "no_target", "explanation": "Не знайдено підходящих сусідніх БС"}
    
    # Крок 3: Перевірка умови хендовера
    condition_met = best_rsrp > serving_rsrp + hyst + offset
    improvement = best_rsrp - serving_rsrp
    
    explanation_data = {
        "step": "condition_check",
        "serving_rsrp": serving_rsrp,
        "target_rsrp": best_rsrp,
        "improvement": improvement,
        "threshold": hyst + offset,
        "condition_met": condition_met,
        "formula": f"{best_rsrp:.1f} > {serving_rsrp:.1f} + {hyst} + {offset} = {serving_rsrp + hyst + offset:.1f}"
    }
    
    user_id = user['id']
    current_time = time.time() * 1000
    
    if condition_met:
        if user_id not in st.session_state.handover_timers:
            # Початок TTT
            st.session_state.handover_timers[user_id] = {
                'start_time': current_time,
                'target_bs': best_target,
                'target_rsrp': best_rsrp
            }
            explanation_data.update({
                "step": "ttt_started",
                "explanation": f"Розпочато відлік TTT ({ttt} мс) для переходу до {best_target}"
            })
            return None, f"⏱️ TTT розпочато ({ttt} мс)", explanation_data
        
        timer_info = st.session_state.handover_timers[user_id]
        elapsed = current_time - timer_info['start_time']
        
        if elapsed >= ttt:
            # Виконуємо хендовер
            del st.session_state.handover_timers[user_id]
            return execute_handover_educational(user, serving_bs, best_target, serving_rsrp, best_rsrp, elapsed, ttt, explanation_data)
        else:
            remaining = ttt - elapsed
            explanation_data.update({
                "step": "ttt_counting",
                "remaining_time": remaining,
                "explanation": f"Очікування TTT: {remaining:.0f} мс залишилось"
            })
            return None, f"⏱️ TTT: {remaining:.0f} мс", explanation_data
    
    else:
        # Умова не виконана
        if user_id in st.session_state.handover_timers:
            del st.session_state.handover_timers[user_id]
        
        explanation_data.update({
            "step": "condition_failed",
            "explanation": f"Умова хендовера не виконана. Потрібно покращення на {(serving_rsrp + hyst + offset - best_rsrp):.1f} дБ"
        })
        return None, f"📡 Обслуговує: {serving_bs['name']}", explanation_data

def execute_handover_educational(user, old_bs, new_bs_id, old_rsrp, new_rsrp, elapsed_time, ttt, explanation_data):
    """Виконання хендовера з освітніми поясненнями"""
    new_bs = next((bs for bs in st.session_state.base_stations if bs['id'] == new_bs_id), None)
    if not new_bs:
        return None, "Помилка: цільова БС не знайдена", explanation_data
    
    improvement = new_rsrp - old_rsrp
    speed = user['speed']
    
    # Освітня класифікація хендовера
    ho_type = "successful"
    ho_explanation = ""
    
    if elapsed_time < 0.8 * ttt:
        ho_type = "early"
        ho_explanation = "Передчасний хендовер - виконано занадто швидко"
        st.session_state.network_metrics['early_handovers'] += 1
    elif elapsed_time > 1.2 * ttt:
        ho_type = "late"
        ho_explanation = "Запізнілий хендовер - виконано з затримкою"
        st.session_state.network_metrics['late_handovers'] += 1
    elif improvement < 3 or (speed > 60 and improvement < 5):
        ho_type = "pingpong"
        ho_explanation = "Ping-pong хендовер - ризик швидких переключень"
        st.session_state.network_metrics['pingpong_handovers'] += 1
    elif improvement < 0:
        ho_type = "failed"
        ho_explanation = "Невдалий хендовер - погіршення якості сигналу"
        st.session_state.network_metrics['failed_handovers'] += 1
    else:
        ho_type = "successful"
        ho_explanation = "Успішний хендовер - покращення якості зв'язку"
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
        'success': ho_type == "successful",
        'explanation': ho_explanation
    }
    
    st.session_state.handover_events.append(handover_event)
    st.session_state.network_metrics['total_handovers'] += 1
    
    explanation_data.update({
        "step": "handover_executed",
        "type": ho_type,
        "explanation": ho_explanation,
        "improvement": improvement,
        "elapsed_time": elapsed_time
    })
    
    type_icons = {
        'successful': '✅', 'early': '⚡', 'late': '⏰',
        'pingpong': '🏓', 'failed': '❌'
    }
    
    status = f"{type_icons[ho_type]} {ho_explanation}"
    return handover_event, status, explanation_data

def create_mapbox_lte_map():
    """Створення красивої Mapbox карти мережі LTE"""
    
    # Підготовка даних базових станцій для 3D візуалізації
    bs_data = []
    coverage_data = []
    
    for bs in st.session_state.base_stations:
        # Динамічна висота залежно від навантаження
        height = bs['height'] + (bs['load'] * 2)
        
        # Колір залежно від навантаження
        if bs['load'] < 30:
            tower_color = [0, 255, 0, 220]  # Зелений
        elif bs['load'] < 70:
            tower_color = [255, 165, 0, 220]  # Помаранчевий
        else:
            tower_color = [255, 0, 0, 220]  # Червоний
        
        bs_data.append({
            'lat': bs['lat'],
            'lon': bs['lon'],
            'elevation': height,
            'name': bs['name'],
            'operator': bs['operator'],
            'power': bs['power'],
            'users': bs['users'],
            'load': bs['load'],
            'color': tower_color
        })
        
        # Зона покриття
        coverage_data.append({
            'lat': bs['lat'],
            'lon': bs['lon'],
            'radius': bs['range_km'] * 1000,  # в метрах
            'color': bs['color']
        })
    
    # Підготовка даних користувачів
    users_data = []
    connections_data = []
    
    for user in st.session_state.users:
        if user.get('active', True):
            rsrp = user.get('rsrp', -85)
            
            # Колір залежно від якості сигналу
            if rsrp > -70:
                user_color = [0, 255, 0, 255]
            elif rsrp > -85:
                user_color = [255, 165, 0, 255]
            elif rsrp > -100:
                user_color = [255, 69, 0, 255]
            else:
                user_color = [255, 0, 0, 255]
            
            users_data.append({
                'lat': user['lat'],
                'lon': user['lon'],
                'elevation': 5,
                'rsrp': rsrp,
                'speed': user['speed'],
                'user_id': user['id'],
                'serving_bs': user.get('serving_bs', 'None'),
                'color': user_color,
                'size': 30 + user['speed']
            })
            
            # Лінія з'єднання до обслуговуючої БС
            serving_bs = user.get('serving_bs')
            if serving_bs:
                bs = next((bs for bs in st.session_state.base_stations if bs['id'] == serving_bs), None)
                if bs:
                    connections_data.append({
                        'source_lat': user['lat'],
                        'source_lon': user['lon'],
                        'target_lat': bs['lat'],
                        'target_lon': bs['lon'],
                        'color': user_color[:3] + [100]  # Прозорість
                    })
    
    # Створення шарів карти
    layers = []
    
    # Шар зон покриття
    if coverage_data:
        layers.append(pdk.Layer(
            'ScatterplotLayer',
            data=coverage_data,
            get_position='[lon, lat]',
            get_radius='radius',
            get_fill_color='color',
            pickable=False,
            filled=True,
            radius_scale=1,
            radius_min_pixels=5
        ))
    
    # Шар 3D веж базових станцій
    if bs_data:
        layers.append(pdk.Layer(
            'ColumnLayer',
            data=bs_data,
            get_position='[lon, lat]',
            get_elevation='elevation',
            elevation_scale=1,
            radius=80,
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
    
    # Шар з'єднань
    if connections_data:
        layers.append(pdk.Layer(
            'LineLayer',
            data=connections_data,
            get_source_position='[source_lon, source_lat]',
            get_target_position='[target_lon, target_lat]',
            get_color='color',
            get_width=2,
            pickable=False
        ))
    
    # Налаштування камери
    view_state = pdk.ViewState(
        latitude=49.2328,
        longitude=28.4810,
        zoom=11.5,
        pitch=50,
        bearing=0
    )
    
    # Tooltip для інтерактивності
    tooltip = {
        "html": """
        <div style="background: rgba(0,0,0,0.8); color: white; padding: 12px; border-radius: 8px; font-size: 12px; max-width: 250px;">
            <b style="color: #00d4ff;">{name}</b><br/>
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
        map_style='mapbox://styles/mapbox/dark-v10'  # Темний стиль Mapbox
    )

# Бічна панель для навчальних сценаріїв
with st.sidebar:
    st.markdown("### 🎓 Навчальні сценарії")
    
    scenario = st.selectbox(
        "Оберіть сценарій навчання:",
        [
            "Навчальний режим",
            "Дослідження TTT",
            "Вплив Hysteresis",
            "Ping-pong ефект",
            "Метрологічні похибки",
            "Мобільність користувачів"
        ]
    )
    st.session_state.selected_scenario = scenario
    
    st.markdown("---")
    st.markdown("### ⚙️ Параметри хендовера")
    
    if scenario == "Дослідження TTT":
        st.info("🔬 Дослідження впливу Time-to-Trigger")
        ttt = st.slider("Time-to-Trigger (мс)", 40, 1000, 280, 40)
        hyst = 4  # Фіксований
        offset = 0
    elif scenario == "Вплив Hysteresis":
        st.info("🔬 Дослідження впливу Hysteresis")
        ttt = 280  # Фіксований
        hyst = st.slider("Hysteresis (дБ)", 0, 10, 4, 1)
        offset = 0
    else:
        ttt = st.slider("Time-to-Trigger (мс)", 40, 1000, 280, 40)
        hyst = st.slider("Hysteresis (дБ)", 0, 10, 4, 1)
        offset = st.slider("Offset (дБ)", -10, 10, 0, 1)
    
    st.markdown("### 🔬 Метрологія")
    metrology_error = st.slider("Похибка RSRP (дБ)", 0.1, 3.0, 1.0, 0.1)
    
    st.markdown("### 👥 Користувачі")
    max_users = st.slider("Максимум користувачів", 5, 30, 15)
    
    if st.button("🚀 Запустити симуляцію", type="primary"):
        st.session_state.network_active = True
    
    if st.button("⏸️ Зупинити"):
        st.session_state.network_active = False
    
    if st.button("🔄 Скинути"):
        st.session_state.users = []
        st.session_state.handover_events = []
        for bs in st.session_state.base_stations:
            bs['users'] = 0
            bs['load'] = 0

# Основний інтерфейс
col1, col2 = st.columns([2.5, 1.5])

with col1:
    st.markdown("### 🗺️ Інтерактивна карта мережі LTE (Вінниця)")
    
    # Відображення Mapbox карти
    deck = create_mapbox_lte_map()
    selected_data = st.pydeck_chart(deck, use_container_width=True, height=500)
    
    # Освітні підказки під картою
    with st.expander("📚 Як читати карту", expanded=False):
        st.markdown("""
        **🏗️ Базові станції (3D вежі):**
        - 🟢 Зелені: низьке навантаження (<30%)
        - 🟡 Жовті: середнє навантаження (30-70%)
        - 🔴 Червоні: високе навантаження (>70%)
        
        **📱 Користувачі (точки):**
        - 🟢 Зелені: відмінний сигнал (RSRP > -70 дБм)
        - 🟡 Жовті: хороший сигнал (-85 до -70 дБм)
        - 🔴 Червоні: слабкий сигнал (< -85 дБм)
        
        **🔗 Лінії з'єднання:** показують активні підключення користувачів до базових станцій
        """)

with col2:
    st.markdown("### 📊 Панель управління")
    
    # Швидкі дії
    col_a, col_b = st.columns(2)
    with col_a:
        if st.button("➕ Додати UE"):
            if len(st.session_state.users) < max_users:
                user_id = f"UE{len(st.session_state.users)+1:02d}"
                lat = 49.2328 + np.random.uniform(-0.03, 0.03)
                lon = 28.4810 + np.random.uniform(-0.05, 0.05)
                
                # Знаходження найкращої БС
                best_bs = None
                best_rsrp = -999
                for bs in st.session_state.base_stations:
                    rsrp = calculate_rsrp_cost_hata(lat, lon, bs)
                    if rsrp > best_rsrp:
                        best_rsrp = rsrp
                        best_bs = bs
                
                user = {
                    'id': user_id,
                    'lat': lat, 'lon': lon,
                    'serving_bs': best_bs['id'] if best_bs else None,
                    'rsrp': best_rsrp,
                    'speed': np.random.choice([5, 20, 40, 60]),
                    'direction': np.random.uniform(0, 360),
                    'active': True,
                    'handover_count': 0,
                    'last_handover': None
                }
                
                if best_bs:
                    best_bs['users'] += 1
                    best_bs['load'] = min(100, (best_bs['users'] / 20) * 100)
                
                st.session_state.users.append(user)
                st.rerun()
    
    with col_b:
        if st.button("🗑️ Очистити"):
            st.session_state.users = []
            for bs in st.session_state.base_stations:
                bs['users'] = 0
                bs['load'] = 0
            st.rerun()
    
    # Поточні метрики
    metrics = st.session_state.network_metrics
    
    col_m1, col_m2 = st.columns(2)
    with col_m1:
        st.metric("Активні UE", len([u for u in st.session_state.users if u.get('active', True)]))
        st.metric("Всього HO", metrics['total_handovers'])
    
    with col_m2:
        if metrics['total_handovers'] > 0:
            success_rate = (metrics['successful_handovers'] / metrics['total_handovers']) * 100
            st.metric("Успішність", f"{success_rate:.1f}%")
        else:
            st.metric("Успішність", "N/A")
        
        avg_rsrp = np.mean([u.get('rsrp', -85) for u in st.session_state.users]) if st.session_state.users else -85
        st.metric("Середня RSRP", f"{avg_rsrp:.1f} дБм")

# Освітня панель пояснень
if st.session_state.selected_scenario != "Навчальний режим":
    st.markdown("---")
    st.markdown(f"### 🎓 Активний сценарій: {st.session_state.selected_scenario}")
    
    scenario_info = {
        "Дослідження TTT": {
            "icon": "⏱️",
            "description": "Дослідження впливу параметра Time-to-Trigger на якість хендоверів",
            "theory": "TTT запобігає передчасним хендоверам через короткочасні флуктуації сигналу. Збільшення TTT зменшує ping-pong, але може спричинити запізнілі хендовери.",
            "task": f"Поточне значення TTT: {ttt} мс. Спостерігайте за частотою хендоверів при зміні цього параметра."
        },
        "Вплив Hysteresis": {
            "icon": "🔄",
            "description": "Дослідження впливу гістерезису на стабільність мережі",
            "theory": "Hysteresis створює 'буферну зону' між рішеннями про хендовер, запобігаючи ping-pong ефекту.",
            "task": f"Поточне значення Hyst: {hyst} дБ. Порівняйте кількість ping-pong хендоверів при різних значеннях."
        },
        "Ping-pong ефект": {
            "icon": "🏓",
            "description": "Вивчення проблеми частих переключень між базовими станціями",
            "theory": "Ping-pong виникає при недостатньому гістерезисі або в зонах рівного покриття двох БС.",
            "task": "Спостерігайте за користувачами на межі зон покриття. Як параметри впливають на ping-pong?"
        }
    }
    
    if st.session_state.selected_scenario in scenario_info:
        info = scenario_info[st.session_state.selected_scenario]
        
        col_theory, col_task = st.columns(2)
        with col_theory:
            st.info(f"**{info['icon']} Теорія:** {info['theory']}")
        with col_task:
            st.success(f"**📋 Завдання:** {info['task']}")

# Таблиця останніх хендоверів (спрощена для освітніх цілей)
if st.session_state.handover_events:
    st.markdown("### 🔄 Останні хендовери")
    
    recent_events = st.session_state.handover_events[-5:]  # Тільки останні 5
    ho_data = []
    
    type_icons = {'successful': '✅', 'early': '⚡', 'late': '⏰', 'pingpong': '🏓', 'failed': '❌'}
    
    for ho in reversed(recent_events):
        old_bs_name = next((bs['name'] for bs in st.session_state.base_stations if bs['id'] == ho['old_bs']), ho['old_bs'])
        new_bs_name = next((bs['name'] for bs in st.session_state.base_stations if bs['id'] == ho['new_bs']), ho['new_bs'])
        
        ho_data.append({
            'Час': ho['timestamp'].strftime('%H:%M:%S'),
            'Користувач': ho['user_id'],
            'Напрямок': f"{old_bs_name} → {new_bs_name}",
            'Покращення': f"{ho['improvement']:+.1f} дБ",
            'Результат': f"{type_icons.get(ho['type'], '❓')} {ho.get('explanation', ho['type']).title()}"
        })
    
    if ho_data:
        st.dataframe(pd.DataFrame(ho_data), use_container_width=True, hide_index=True)

# Автоматичне оновлення симуляції
if st.session_state.network_active:
    # Симуляція руху користувачів
    for user in st.session_state.users:
        if user['active']:
            # Простий рух
            speed_ms = user['speed'] * 1000 / 3600
            distance = speed_ms * 1  # за 1 секунду
            
            lat_change = (distance * np.cos(np.radians(user['direction']))) / 111111
            lon_change = (distance * np.sin(np.radians(user['direction']))) / (111111 * np.cos(np.radians(user['lat'])))
            
            user['lat'] += lat_change
            user['lon'] += lon_change
            
            # Обмеження межами Вінниці
            user['lat'] = np.clip(user['lat'], 49.20, 49.27)
            user['lon'] = np.clip(user['lon'], 28.42, 28.55)
            
            if np.random.random() < 0.05:
                user['direction'] = np.random.uniform(0, 360)
            
            # Перевірка хендовера
            handover_event, status, explanation = check_handover_condition_educational(
                user, st.session_state.base_stations, ttt, hyst, offset
            )
    
    # Автоматичне додавання користувачів
    if len(st.session_state.users) < max_users and np.random.random() < 0.1:
        # Код додавання нового користувача (аналогічно кнопці)
        pass
    
    time.sleep(2)
    st.rerun()

# Футер з інформацією
st.markdown("---")
st.markdown("""
<div style="text-align: center; color: #666; font-size: 12px;">
    <p>📡 <strong>LTE Network Simulator</strong> | Розроблено для освітніх цілей</p>
    <p>🏛️ <strong>ВНТУ</strong> | Кафедра ІРТС | Бакалаврська робота Хрустовського А.А.</p>
    <p>🎯 Архітектурні принципи та оптимізація функціонування мережі LTE</p>
</div>
""", unsafe_allow_html=True)
