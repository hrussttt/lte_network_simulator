import streamlit as st
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
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
    """Створення карти мережі з Mapbox"""
    
    # Підготовка даних для базових станцій
    bs_data = []
    for bs in st.session_state.base_stations:
        # Визначення кольору залежно від навантаження
        if bs['load'] < 30:
            color = 'green'
        elif bs['load'] < 70:
            color = 'orange'
        else:
            color = 'red'
            
        bs_data.append({
            'lat': bs['lat'],
            'lon': bs['lon'],
            'name': bs['name'],
            'load': bs['load'],
            'users': bs['users'],
            'power': bs['power'],
            'color': color,
            'type': 'BaseStation'
        })
    
    # Підготовка даних для користувачів
    user_data = []
    for user in st.session_state.users:
        if user['active']:
            # Визначення кольору залежно від RSRP
            if user['rsrp'] > -70:
                color = 'green'
            elif user['rsrp'] > -85:
                color = 'yellow'
            else:
                color = 'red'
                
            user_data.append({
                'lat': user['lat'],
                'lon': user['lon'],
                'id': user['id'],
                'rsrp': user['rsrp'],
                'serving_bs': user['serving_bs'],
                'speed': user['speed'],
                'color': color,
                'type': 'User'
            })
    
    # Створення фігури
    fig = go.Figure()
    
    # Додавання базових станцій
    if bs_data:
        import pandas as pd
        bs_df = pd.DataFrame(bs_data)
        
        for color in ['green', 'orange', 'red']:
            color_data = bs_df[bs_df['color'] == color]
            if not color_data.empty:
                fig.add_trace(go.Scattermapbox(
                    lat=color_data['lat'],
                    lon=color_data['lon'],
                    mode='markers',
                    marker=dict(
                        size=15,
                        color=color,
                        symbol='circle'
                    ),
                    text=color_data['name'],
                    hovertemplate='<b>%{text}</b><br>' +
                                'Навантаження: %{customdata[0]:.1f}%<br>' +
                                'Користувачі: %{customdata[1]}<br>' +
                                'Потужність: %{customdata[2]} дБм<extra></extra>',
                    customdata=color_data[['load', 'users', 'power']].values,
                    name=f'БС ({color})',
                    showlegend=True
                ))
    
    # Додавання користувачів
    if user_data:
        import pandas as pd
        user_df = pd.DataFrame(user_data)
        
        for color in ['green', 'yellow', 'red']:
            color_data = user_df[user_df['color'] == color]
            if not color_data.empty:
                fig.add_trace(go.Scattermapbox(
                    lat=color_data['lat'],
                    lon=color_data['lon'],
                    mode='markers',
                    marker=dict(
                        size=8,
                        color=color,
                        symbol='triangle-up'
                    ),
                    text=color_data['id'],
                    hovertemplate='<b>%{text}</b><br>' +
                                'RSRP: %{customdata[0]:.1f} дБм<br>' +
                                'Обслуговуюча БС: %{customdata[1]}<br>' +
                                'Швидкість: %{customdata[2]} км/год<extra></extra>',
                    customdata=color_data[['rsrp', 'serving_bs', 'speed']].values,
                    name=f'Користувачі ({color})',
                    showlegend=True
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
        legend=dict(
            yanchor="top",
            y=0.99,
            xanchor="left",
            x=0.01,
            bgcolor="rgba(255,255,255,0.8)"
        )
    )
    
    return fig


def generate_new_user():
    """Генерація нового користувача"""
    user_id = f"UE{len(st.session_state.users)+1:03d}"
    
    # Випадкова позиція в межах Вінниці
    lat = 49.2328 + np.random.uniform(-0.03, 0.03)
    lon = 28.4810 + np.random.uniform(-0.05, 0.05)
    
    # Знаходження найкращої BS
    best_bs, rsrp = find_best_bs(lat, lon, st.session_state.base_stations)
    
    user = {
        'id': user_id,
        'lat': lat,
        'lon': lon,
        'serving_bs': best_bs['id'] if best_bs else None,
        'rsrp': rsrp,
        'speed': np.random.choice([5, 20, 60, 90]),  # км/год
        'direction': np.random.uniform(0, 360),  # градуси
        'throughput': np.random.uniform(10, 100),  # Мбіт/с
        'active': True,
        'handover_count': 0,
        'last_handover': None
    }
    
    return user

def simulate_user_movement():
    """Симуляція руху користувачів"""
    for user in st.session_state.users:
        if not user['active']:
            continue
        
        # Розрахунок нової позиції
        speed_ms = user['speed'] * 1000 / 3600  # м/с
        distance = speed_ms * 1  # за 1 секунду
        
        # Конвертація в градуси (приблизно)
        lat_change = (distance * np.cos(np.radians(user['direction']))) / 111111
        lon_change = (distance * np.sin(np.radians(user['direction']))) / (111111 * np.cos(np.radians(user['lat'])))
        
        user['lat'] += lat_change
        user['lon'] += lon_change
        
        # Обмеження межами міста
        user['lat'] = np.clip(user['lat'], 49.20, 49.27)
        user['lon'] = np.clip(user['lon'], 28.42, 28.55)
        
        # Випадкова зміна напряму (5% шанс)
        if np.random.random() < 0.05:
            user['direction'] = np.random.uniform(0, 360)
        
        # Перевірка необхідності хендовера
        check_handover(user)

def check_handover(user):
    """Перевірка необхідності хендовера"""
    current_bs = next((bs for bs in st.session_state.base_stations if bs['id'] == user['serving_bs']), None)
    if not current_bs:
        return
    
    # Розрахунок RSRP від поточної BS
    current_rsrp = calculate_rsrp(user['lat'], user['lon'], current_bs['lat'], current_bs['lon'], current_bs['power'])
    
    # Знаходження найкращої BS
    best_bs, best_rsrp = find_best_bs(user['lat'], user['lon'], st.session_state.base_stations)
    
    # Критерій хендовера: покращення > 5 дБ
    if best_bs and best_bs['id'] != user['serving_bs'] and best_rsrp > current_rsrp + 5:
        # Виконання хендовера
        execute_handover(user, best_bs, current_rsrp, best_rsrp)
    else:
        user['rsrp'] = current_rsrp

def execute_handover(user, new_bs, old_rsrp, new_rsrp):
    """Виконання хендовера"""
    old_bs_id = user['serving_bs']
    
    # Оновлення користувача
    user['serving_bs'] = new_bs['id']
    user['rsrp'] = new_rsrp
    user['handover_count'] += 1
    user['last_handover'] = datetime.now()
    
    # Визначення успішності хендовера
    success = new_rsrp > old_rsrp + 3  # мінімальне покращення 3 дБ
    
    # Збереження події
    handover_event = {
        'timestamp': datetime.now(),
        'user_id': user['id'],
        'old_bs': old_bs_id,
        'new_bs': new_bs['id'],
        'old_rsrp': old_rsrp,
        'new_rsrp': new_rsrp,
        'improvement': new_rsrp - old_rsrp,
        'success': success
    }
    
    st.session_state.handover_events.append(handover_event)
    
    # Оновлення метрик
    st.session_state.network_metrics['total_handovers'] += 1
    if success:
        st.session_state.network_metrics['successful_handovers'] += 1
    else:
        st.session_state.network_metrics['failed_handovers'] += 1

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
        bs['users'] = len([u for u in active_users if u['serving_bs'] == bs['id']])
        bs['load'] = min(100, bs['users'] * 20)  # 20% на користувача

# Головний інтерфейс
st.title("🌐 LTE Network Simulator")
st.markdown("### Інтерактивний симулятор мережі LTE в реальному часі")

# Sidebar управління
st.sidebar.header("🎛️ Управління симуляцією")

# Кнопки управління
if st.sidebar.button("🚀 Запустити мережу" if not st.session_state.network_active else "⏹️ Зупинити мережу"):
    st.session_state.network_active = not st.session_state.network_active

if st.session_state.network_active:
    st.sidebar.success("✅ Мережа активна")
else:
    st.sidebar.info("⏸️ Мережа зупинена")

# Налаштування симуляції
st.sidebar.subheader("⚙️ Параметри")
max_users = st.sidebar.slider("Максимум користувачів", 5, 50, 20)
user_spawn_rate = st.sidebar.slider("Швидкість появи користувачів", 0.1, 2.0, 0.5)

# Кнопка додавання користувача
if st.sidebar.button("➕ Додати користувача"):
    if len(st.session_state.users) < max_users:
        new_user = generate_new_user()
        st.session_state.users.append(new_user)

# Кнопка очищення
if st.sidebar.button("🗑️ Очистити всіх користувачів"):
    st.session_state.users = []
    st.session_state.handover_events = []

# Основний контент
col1, col2 = st.columns([2, 1])

with col1:
    st.subheader("🗺️ Карта мережі")
    
    # Створення та відображення карти
    network_map = create_network_map()
    map_fig = create_network_map()
    st.plotly_chart(map_fig, use_container_width=True, key="network_map")

with col2:
    st.subheader("📊 Метрики мережі")
    
    # Оновлення метрик
    update_network_metrics()
    
    # Відображення метрик
    metrics = st.session_state.network_metrics
    
    st.metric("Активні користувачі", metrics['active_users'])
    st.metric("Всього хендоверів", metrics['total_handovers'])
    
    if metrics['total_handovers'] > 0:
        success_rate = (metrics['successful_handovers'] / metrics['total_handovers']) * 100
        st.metric("Успішність хендоверів", f"{success_rate:.1f}%")
    
    st.metric("Середня RSRP", f"{metrics['average_rsrp']:.1f} дБм")
    st.metric("Пропускна здатність", f"{metrics['network_throughput']:.1f} Мбіт/с")

# Статус базових станцій
st.subheader("📡 Статус базових станцій")

bs_data = []
for bs in st.session_state.base_stations:
    bs_data.append({
        'ID': bs['id'],
        'Назва': bs['name'],
        'Потужність (дБм)': bs['power'],
        'Користувачі': bs['users'],
        'Навантаження (%)': f"{bs['load']:.1f}"
    })

st.dataframe(pd.DataFrame(bs_data), use_container_width=True)

# Останні хендовери
if st.session_state.handover_events:
    st.subheader("🔄 Останні хендовери")
    
    recent_handovers = st.session_state.handover_events[-5:]  # Останні 5
    ho_data = []
    
    for ho in reversed(recent_handovers):
        ho_data.append({
            'Час': ho['timestamp'].strftime('%H:%M:%S'),
            'Користувач': ho['user_id'],
            'Від': ho['old_bs'],
            'До': ho['new_bs'],
            'Покращення (дБ)': f"{ho['improvement']:.1f}",
            'Статус': '✅ Успішно' if ho['success'] else '❌ Невдало'
        })
    
    if ho_data:
        st.dataframe(pd.DataFrame(ho_data), use_container_width=True)

# Автоматичне оновлення
if st.session_state.network_active:
    # Додавання нових користувачів
    if len(st.session_state.users) < max_users and np.random.random() < user_spawn_rate * 0.1:
        new_user = generate_new_user()
        st.session_state.users.append(new_user)
    
    # Симуляція руху
    simulate_user_movement()
    
    # Автоматичне оновлення через 2 секунди
    time.sleep(2)
    st.rerun()

# Інформаційна панель
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
