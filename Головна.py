import streamlit as st
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

# Налаштування сторінки
st.set_page_config(
    page_title="LTE Network Simulator - Вінниця",
    page_icon="📡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ✅ КРИТИЧНО: Правильна ініціалізація всіх атрибутів session_state
def initialize_session_state():
    """Ініціалізація стану сесії - ОБОВ'ЯЗКОВО викликати першою"""
    
    if 'network_active' not in st.session_state:
        st.session_state.network_active = False
    
    if 'users' not in st.session_state:
        st.session_state.users = []
    
    if 'base_stations' not in st.session_state:
        # Базові станції як список словників (оригінальна структура)
        st.session_state.base_stations = [
            {
                'id': 'eNodeB_001', 'name': 'Центр (Соборна)', 
                'lat': 49.2328, 'lon': 28.4810, 'power': 43,
                'frequency': 1800, 'operator': 'Київстар', 'color': 'blue',
                'users': 0, 'load': 0, 'range_km': 2.5
            },
            {
                'id': 'eNodeB_002', 'name': 'Вишенька',
                'lat': 49.2510, 'lon': 28.4590, 'power': 40,
                'frequency': 2600, 'operator': 'Vodafone', 'color': 'red',
                'users': 0, 'load': 0, 'range_km': 1.8
            },
            {
                'id': 'eNodeB_003', 'name': 'Замостя',
                'lat': 49.2180, 'lon': 28.5120, 'power': 41,
                'frequency': 1800, 'operator': 'lifecell', 'color': 'green',
                'users': 0, 'load': 0, 'range_km': 2.2
            },
            {
                'id': 'eNodeB_004', 'name': 'Пирогово',
                'lat': 49.2450, 'lon': 28.5280, 'power': 38,
                'frequency': 2600, 'operator': 'Київстар', 'color': 'blue',
                'users': 0, 'load': 0, 'range_km': 1.5
            },
            {
                'id': 'eNodeB_005', 'name': 'Старе місто',
                'lat': 49.2290, 'lon': 28.4650, 'power': 42,
                'frequency': 900, 'operator': 'Vodafone', 'color': 'red',
                'users': 0, 'load': 0, 'range_km': 3.0
            },
            {
                'id': 'eNodeB_006', 'name': 'Військове містечко',
                'lat': 49.2150, 'lon': 28.4420, 'power': 39,
                'frequency': 1800, 'operator': 'lifecell', 'color': 'green',
                'users': 0, 'load': 0, 'range_km': 2.0
            }
        ]
    
    if 'handover_events' not in st.session_state:
        st.session_state.handover_events = []
    
    if 'network_metrics' not in st.session_state:
        st.session_state.network_metrics = {
            'total_handovers': 0,
            'successful_handovers': 0,
            'failed_handovers': 0,
            'pingpong_handovers': 0,
            'average_rsrp': -85.0,
            'network_throughput': 0.0,
            'active_users': 0,
            'simulation_time': 0.0
        }
    
    # Ініціалізація параметрів хендовера
    if 'handover_params' not in st.session_state:
        st.session_state.handover_params = {
            'ttt': 280,
            'hyst': 4.0,
            'offset': 0.0,
            'metrology_error': 1.0,
            'calibration_factor': 1.0
        }

# 🚨 ОБОВ'ЯЗКОВО: Викликаємо ініціалізацію ПЕРШОЮ
initialize_session_state()

# Функції розрахунків
def calculate_rsrp(user_lat, user_lon, bs_lat, bs_lon, bs_power, frequency=1800, metrology_error=1.0):
    """Розрахунок RSRP з метрологічною похибкою"""
    distance = geodesic((user_lat, user_lon), (bs_lat, bs_lon)).kilometers
    if distance == 0:
        distance = 0.001
    
    # Модель COST-Hata
    if frequency <= 1000:
        path_loss = (69.55 + 26.16*np.log10(frequency) - 
                    13.82*np.log10(30) + 
                    (44.9 - 6.55*np.log10(30))*np.log10(distance))
    else:
        path_loss = (46.3 + 33.9*np.log10(frequency) - 
                    13.82*np.log10(30) + 
                    (44.9 - 6.55*np.log10(30))*np.log10(distance) + 3)
    
    rsrp = bs_power - path_loss + 15  # antenna gain
    rsrp += np.random.normal(0, metrology_error)  # метрологічна похибка
    rsrp += np.random.normal(0, 2)  # fading
    
    return max(-120, min(-40, rsrp))

def find_best_bs(user_lat, user_lon, base_stations):
    """Знаходження найкращої базової станції"""
    best_bs = None
    best_rsrp = -999
    
    for bs in base_stations:
        rsrp = calculate_rsrp(
            user_lat, user_lon, bs['lat'], bs['lon'], 
            bs['power'], bs['frequency']
        )
        if rsrp > best_rsrp:
            best_rsrp = rsrp
            best_bs = bs
    
    return best_bs, best_rsrp

# Заголовок
st.title("📡 LTE Network Simulator - м. Вінниця")
st.markdown("""
**Симуляція мережі LTE з алгоритмами хендовера та метрологічним забезпеченням**
""")

# Бічна панель
with st.sidebar:
    st.header("🎛️ Управління симуляцією")
    
    # Кнопки управління
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🚀 Старт", type="primary"):
            st.session_state.network_active = True
            st.success("Мережу запущено!")
    
    with col2:
        if st.button("⏸️ Стоп"):
            st.session_state.network_active = False
            st.warning("Мережу зупинено!")
    
    if st.button("🔄 Скинути"):
        st.session_state.network_active = False
        st.session_state.users.clear()
        st.session_state.handover_events.clear()
        for bs in st.session_state.base_stations:
            bs['users'] = 0
            bs['load'] = 0
        st.info("Симуляцію скинуто!")
        st.rerun()
    
    st.divider()
    
    # Параметри хендовера
    st.subheader("🔄 Параметри хендовера")
    
    ttt = st.slider("Time-to-Trigger (мс)", 40, 1000, 
                   st.session_state.handover_params['ttt'], 40)
    hyst = st.slider("Hysteresis (дБ)", 0.0, 10.0, 
                    st.session_state.handover_params['hyst'], 0.5)
    offset = st.slider("Offset (дБ)", -10.0, 10.0, 
                      st.session_state.handover_params['offset'], 0.5)
    
    # Оновлення параметрів
    st.session_state.handover_params.update({
        'ttt': ttt, 'hyst': hyst, 'offset': offset
    })
    
    st.divider()
    
    # Метрологічні параметри
    st.subheader("🔬 Метрологія")
    
    metrology_error = st.slider("Похибка RSRP (σ)", 0.1, 3.0, 
                               st.session_state.handover_params['metrology_error'], 0.1)
    calibration_factor = st.slider("Калібрування", 0.95, 1.05, 
                                  st.session_state.handover_params['calibration_factor'], 0.01)
    
    st.session_state.handover_params.update({
        'metrology_error': metrology_error,
        'calibration_factor': calibration_factor
    })
    
    st.divider()
    
    # Користувачі
    st.subheader("👥 Користувачі")
    max_users = st.slider("Максимум UE", 1, 50, 10)
    
    if st.button("➕ Додати користувача"):
        if len(st.session_state.users) < max_users:
            user_id = f'UE_{len(st.session_state.users)+1:03d}'
            user = {
                'id': user_id,
                'lat': random.uniform(49.20, 49.27),
                'lon': random.uniform(28.42, 28.55),
                'speed': random.uniform(5, 80),
                'direction': random.uniform(0, 360),
                'active': True,
                'serving_bs': None,
                'rsrp': -85,
                'rsrq': -12,
                'throughput': 0,
                'handover_count': 0,
                'last_handover': None
            }
            
            # Знаходження найкращої BS
            best_bs, best_rsrp = find_best_bs(user['lat'], user['lon'], st.session_state.base_stations)
            if best_bs:
                user['serving_bs'] = best_bs['name']
                user['rsrp'] = best_rsrp
                best_bs['users'] += 1
                best_bs['load'] = min(100, (best_bs['users'] / 100) * 100)
            
            st.session_state.users.append(user)
            st.success(f"Додано {user_id}")
            st.rerun()
        else:
            st.warning(f"Досягнуто ліміт ({max_users} UE)")

# Основний інтерфейс
tab1, tab2, tab3 = st.tabs(["🗺️ Карта мережі", "📊 Метрики", "🔄 Хендовери"])

with tab1:
    st.subheader("Мережа LTE м. Вінниця")
    
    # Створення карти
    center = [49.2328, 28.4810]
    m = folium.Map(location=center, zoom_start=12)
    
    # Додавання базових станцій
    for bs in st.session_state.base_stations:
        color = 'green' if bs['load'] < 30 else 'orange' if bs['load'] < 70 else 'red'
        
        folium.Marker(
            [bs['lat'], bs['lon']],
            popup=f"""
            <b>{bs['name']}</b><br>
            Оператор: {bs['operator']}<br>
            Потужність: {bs['power']} дБм<br>
            Частота: {bs['frequency']} МГц<br>
            Користувачі: {bs['users']}<br>
            Навантаження: {bs['load']:.1f}%
            """,
            tooltip=bs['name'],
            icon=folium.Icon(color=color, icon='tower-cell', prefix='fa')
        ).add_to(m)
        
        # Зона покриття
        folium.Circle(
            [bs['lat'], bs['lon']],
            radius=bs['range_km'] * 1000,
            color=bs['color'],
            fillColor=bs['color'],
            fillOpacity=0.1,
            weight=1,
            opacity=0.3
        ).add_to(m)
    
    # Додавання користувачів
    for user in st.session_state.users:
        if user['active']:
            # Колір за якістю сигналу
            if user['rsrp'] > -70:
                marker_color = 'green'
            elif user['rsrp'] > -85:
                marker_color = 'orange'
            else:
                marker_color = 'red'
            
            folium.Marker(
                [user['lat'], user['lon']],
                popup=f"""
                <b>{user['id']}</b><br>
                RSRP: {user['rsrp']:.1f} дБм<br>
                BS: {user['serving_bs']}<br>
                Швидкість: {user['speed']:.1f} км/год<br>
                Хендовери: {user['handover_count']}
                """,
                tooltip=user['id'],
                icon=folium.Icon(color=marker_color, icon='mobile', prefix='fa')
            ).add_to(m)
    
    # Відображення карти
    map_data = st_folium(m, width=700, height=500)

with tab2:
    st.subheader("📈 Метрики в реальному часі")
    
    # KPI
    col1, col2, col3, col4 = st.columns(4)
    
    active_users = len([u for u in st.session_state.users if u['active']])
    total_handovers = st.session_state.network_metrics['total_handovers']
    successful_handovers = st.session_state.network_metrics['successful_handovers']
    avg_rsrp = np.mean([u['rsrp'] for u in st.session_state.users]) if st.session_state.users else -85
    
    with col1:
        st.metric("Активні UE", active_users)
    
    with col2:
        success_rate = (successful_handovers / total_handovers * 100) if total_handovers > 0 else 0
        st.metric("Успішність HO", f"{success_rate:.1f}%")
    
    with col3:
        st.metric("Середня RSRP", f"{avg_rsrp:.1f} дБм")
    
    with col4:
        total_load = sum([bs['load'] for bs in st.session_state.base_stations])
        avg_load = total_load / len(st.session_state.base_stations)
        st.metric("Навантаження", f"{avg_load:.1f}%")
    
    # Графіки
    if st.session_state.users:
        # RSRP користувачів
        user_data = []
        for user in st.session_state.users:
            if user['active']:
                user_data.append({
                    'Користувач': user['id'],
                    'RSRP': user['rsrp'],
                    'BS': user['serving_bs']
                })
        
        if user_data:
            df = pd.DataFrame(user_data)
            fig = px.bar(df, x='Користувач', y='RSRP', color='BS',
                        title="RSRP користувачів")
            st.plotly_chart(fig, use_container_width=True)

with tab3:
    st.subheader("🔄 Журнал хендоверів")
    
    if st.session_state.handover_events:
        # Таблиця подій
        ho_data = []
        for ho in st.session_state.handover_events[-20:]:  # Останні 20
            ho_data.append({
                'Час': ho['timestamp'].strftime('%H:%M:%S'),
                'UE': ho['user_id'],
                'Від → До': f"{ho['old_bs']} → {ho['new_bs']}",
                'Покращення': f"{ho['improvement']:.1f} дБ",
                'Тип': ho['type'],
                'Успіх': '✅' if ho['success'] else '❌'
            })
        
        if ho_data:
            df_ho = pd.DataFrame(ho_data)
            st.dataframe(df_ho, use_container_width=True, hide_index=True)
        
        # Статистика
        success_count = len([ho for ho in st.session_state.handover_events if ho['success']])
        total_count = len(st.session_state.handover_events)
        
        col5, col6, col7 = st.columns(3)
        with col5:
            st.metric("Загалом", total_count)
        with col6:
            success_rate = (success_count / total_count * 100) if total_count > 0 else 0
            st.metric("Успішність", f"{success_rate:.1f}%")
        with col7:
            avg_improvement = np.mean([ho['improvement'] for ho in st.session_state.handover_events])
            st.metric("Покращення", f"{avg_improvement:.1f} дБ")
    else:
        st.info("Хендовери ще не зафіксовано")

# Автоматичне оновлення при активній мережі
if st.session_state.network_active:
    # Симуляція руху користувачів та хендоверів
    for user in st.session_state.users:
        if user['active']:
            # Рух користувача
            speed_ms = user['speed'] * 1000 / 3600
            distance_m = speed_ms * 1.0  # 1 секунда
            
            lat_change = (distance_m * np.cos(np.radians(user['direction']))) / 111111
            lon_change = (distance_m * np.sin(np.radians(user['direction']))) / \
                        (111111 * np.cos(np.radians(user['lat'])))
            
            user['lat'] = np.clip(user['lat'] + lat_change, 49.20, 49.27)
            user['lon'] = np.clip(user['lon'] + lon_change, 28.42, 28.55)
            
            # Перевірка хендовера
            current_bs = next((bs for bs in st.session_state.base_stations 
                             if bs['name'] == user['serving_bs']), None)
            if current_bs:
                current_rsrp = calculate_rsrp(
                    user['lat'], user['lon'], current_bs['lat'], current_bs['lon'],
                    current_bs['power'], current_bs['frequency'], metrology_error
                )
                user['rsrp'] = current_rsrp
                
                # Знаходження кращої BS
                best_bs, best_rsrp = find_best_bs(user['lat'], user['lon'], st.session_state.base_stations)
                
                # Умова хендовера
                if best_bs and best_bs['name'] != user['serving_bs']:
                    if best_rsrp > current_rsrp + hyst + offset:
                        # Виконання хендовера
                        old_bs_name = user['serving_bs']
                        improvement = best_rsrp - current_rsrp
                        
                        # Оновлення користувача
                        current_bs['users'] -= 1
                        best_bs['users'] += 1
                        user['serving_bs'] = best_bs['name']
                        user['rsrp'] = best_rsrp
                        user['handover_count'] += 1
                        user['last_handover'] = datetime.now()
                        
                        # Оновлення навантаження
                        current_bs['load'] = min(100, (current_bs['users'] / 100) * 100)
                        best_bs['load'] = min(100, (best_bs['users'] / 100) * 100)
                        
                        # Тип хендовера
                        ho_type = 'successful' if improvement >= 3 else 'failed'
                        
                        # Запис події
                        handover_event = {
                            'timestamp': datetime.now(),
                            'user_id': user['id'],
                            'old_bs': old_bs_name,
                            'new_bs': best_bs['name'],
                            'improvement': improvement,
                            'type': ho_type,
                            'success': improvement >= 0
                        }
                        
                        st.session_state.handover_events.append(handover_event)
                        st.session_state.network_metrics['total_handovers'] += 1
                        
                        if ho_type == 'successful':
                            st.session_state.network_metrics['successful_handovers'] += 1
    
    # Оновлення кожні 2 секунди
    time.sleep(2)
    st.rerun()

# Футер
st.markdown("---")
st.markdown("**LTE Network Simulator v2.0** | ВНТУ, 2025")
