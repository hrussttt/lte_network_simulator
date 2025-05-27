import streamlit as st
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
import time
import random
from geopy.distance import geodesic
import json

# Імпорти локальних модулів
from core.network_engine import LTENetworkEngine
from core.handover_algorithm import HandoverAlgorithm, HandoverParameters
from utils.visualization import MapboxVisualizer
from utils.data_generator import LTEDataGenerator
from config.network_config import VINNYTSIA_BASE_STATIONS, NETWORK_PARAMETERS

# Налаштування сторінки
st.set_page_config(
    page_title="LTE Network Simulator - Вінниця",
    page_icon="📡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Ініціалізація стану сесії
def initialize_session_state():
    """Ініціалізація початкового стану симуляції"""
    if 'network_engine' not in st.session_state:
        st.session_state.network_engine = LTENetworkEngine()
        st.session_state.network_engine.initialize_network(VINNYTSIA_BASE_STATIONS)
    
    if 'handover_algorithm' not in st.session_state:
        st.session_state.handover_algorithm = HandoverAlgorithm()
    
    if 'data_generator' not in st.session_state:
        st.session_state.data_generator = LTEDataGenerator()
    
    if 'visualizer' not in st.session_state:
        st.session_state.visualizer = MapboxVisualizer()
    
    if 'simulation_active' not in st.session_state:
        st.session_state.simulation_active = False
    
    if 'users' not in st.session_state:
        st.session_state.users = []
    
    if 'handover_events' not in st.session_state:
        st.session_state.handover_events = []
    
    if 'simulation_metrics' not in st.session_state:
        st.session_state.simulation_metrics = {
            'total_handovers': 0,
            'successful_handovers': 0,
            'failed_handovers': 0,
            'pingpong_handovers': 0,
            'average_rsrp': -85.0,
            'network_throughput': 0.0,
            'active_users': 0,
            'simulation_time': 0.0
        }

initialize_session_state()

# Заголовок та опис
st.title("📡 LTE Network Simulator - м. Вінниця")
st.markdown("""
**Інтерактивна симуляція мережі LTE з алгоритмами хендовера та метрологічним забезпеченням**

Досліджуйте архітектурні принципи LTE та оптимізуйте параметри мережі для підвищення якості обслуговування користувачів.
""")

# Бічна панель управління
with st.sidebar:
    st.header("🎛️ Параметри симуляції")
    
    # Секція управління симуляцією
    st.subheader("🚀 Управління")
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("▶️ Старт", type="primary", use_container_width=True):
            st.session_state.simulation_active = True
            st.session_state.network_engine.start_simulation()
            st.success("Симуляція запущена!")
    
    with col2:
        if st.button("⏸️ Стоп", type="secondary", use_container_width=True):
            st.session_state.simulation_active = False
            st.session_state.network_engine.stop_simulation()
            st.warning("Симуляція зупинена!")
    
    if st.button("🔄 Скинути", type="secondary", use_container_width=True):
        st.session_state.simulation_active = False
        st.session_state.network_engine.reset_simulation()
        st.session_state.handover_events.clear()
        st.session_state.users.clear()
        st.rerun()
    
    st.divider()
    
    # Параметри хендовера
    st.subheader("🔄 Параметри хендовера")
    
    ttt = st.slider(
        "Time-to-Trigger (TTT)", 
        min_value=40, max_value=1000, value=280, step=40,
        help="Час утримання умови хендовера в мілісекундах"
    )
    
    hyst = st.slider(
        "Hysteresis", 
        min_value=0.0, max_value=10.0, value=4.0, step=0.5,
        help="Гістерезис для запобігання ping-pong ефекту"
    )
    
    offset = st.slider(
        "Offset", 
        min_value=-10.0, max_value=10.0, value=0.0, step=0.5,
        help="Зсув порогу для балансування навантаження"
    )
    
    st.divider()
    
    # Метрологічні параметри
    st.subheader("🔬 Метрологічні параметри")
    
    metrology_error = st.slider(
        "Похибка RSRP (σ)", 
        min_value=0.1, max_value=3.0, value=1.0, step=0.1,
        help="Стандартне відхилення метрологічної похибки"
    )
    
    calibration_factor = st.slider(
        "Коефіцієнт калібрування", 
        min_value=0.95, max_value=1.05, value=1.0, step=0.01,
        help="Систематична похибка калібрування"
    )
    
    st.divider()
    
    # Параметри користувачів
    st.subheader("👥 Користувачі")
    
    max_users = st.slider("Максимум UE", 1, 50, 10)
    
    user_speed = st.selectbox(
        "Швидкість руху",
        ["Пішоходи (5-15 км/год)", "Транспорт (30-80 км/год)", "Змішаний рух", "Статичні"]
    )
    
    auto_generate = st.checkbox("Автоматична генерація UE", value=True)
    
    if st.button("➕ Додати користувача", use_container_width=True):
        add_random_user(max_users)

# Функція додавання користувача
def add_random_user(max_users):
    """Додавання випадкового користувача"""
    if len(st.session_state.users) >= max_users:
        st.warning(f"Досягнуто максимум користувачів ({max_users})")
        return
    
    # Генерація випадкової позиції в межах Вінниці
    lat = random.uniform(49.20, 49.27)
    lon = random.uniform(28.42, 28.55)
    
    # Швидкість залежно від вибраного режиму
    speed_ranges = {
        "Пішоходи (5-15 км/год)": (5, 15),
        "Транспорт (30-80 км/год)": (30, 80),
        "Змішаний рух": (5, 80),
        "Статичні": (0, 1)
    }
    speed_range = speed_ranges[user_speed]
    speed = random.uniform(*speed_range)
    
    user_config = {
        'id': f'UE_{len(st.session_state.users)+1:03d}',
        'lat': lat,
        'lon': lon,
        'speed': speed,
        'direction': random.uniform(0, 360),
        'device_type': random.choice(['smartphone', 'tablet', 'laptop'])
    }
    
    success = st.session_state.network_engine.add_user(user_config)
    if success:
        st.session_state.users.append(user_config)
        st.success(f"Додано користувача {user_config['id']}")

# Основний інтерфейс
tab1, tab2, tab3 = st.tabs(["🗺️ Карта мережі", "📊 Метрики", "🔄 Хендовери"])

with tab1:
    st.subheader("Інтерактивна карта LTE мережі Вінниці")
    
    # Створення карти
    if st.session_state.network_engine.base_stations:
        network_state = st.session_state.network_engine.get_network_state()
        
        # Використання Mapbox для візуалізації
        fig = st.session_state.visualizer.create_network_map(
            base_stations=network_state['base_stations'],
            users=network_state['users'],
            handover_events=st.session_state.handover_events[-10:],  # Останні 10 подій
            show_coverage=True
        )
        
        st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
        
        # Легенда
        with st.expander("📋 Легенда карти"):
            col1, col2, col3 = st.columns(3)
            with col1:
                st.markdown("""
                **Базові станції:**
                - 🔵 Київстар
                - 🔴 Vodafone  
                - 🟢 lifecell
                """)
            with col2:
                st.markdown("""
                **Користувачі:**
                - 🟢 Відмінний сигнал (>-70 дБм)
                - 🟡 Хороший сигнал (-70..-85 дБм)
                - 🔴 Слабкий сигнал (<-85 дБм)
                """)
            with col3:
                st.markdown("""
                **Хендовери:**
                - ➡️ Успішний хендовер
                - ❌ Невдалий хендовер
                - 🔄 Ping-pong хендовер
                """)

with tab2:
    st.subheader("📈 Метрики мережі в реальному часі")
    
    # KPI карточки
    col1, col2, col3, col4 = st.columns(4)
    
    metrics = st.session_state.simulation_metrics
    
    with col1:
        st.metric(
            "Активних користувачів", 
            len([u for u in st.session_state.users if u.get('active', True)]),
            delta=None
        )
    
    with col2:
        total_ho = metrics['total_handovers']
        successful_ho = metrics['successful_handovers']
        success_rate = (successful_ho / total_ho * 100) if total_ho > 0 else 0
        st.metric(
            "Успішність хендоверів", 
            f"{success_rate:.1f}%",
            delta=f"{successful_ho}/{total_ho}"
        )
    
    with col3:
        st.metric(
            "Середня RSRP", 
            f"{metrics['average_rsrp']:.1f} дБм",
            delta=None
        )
    
    with col4:
        st.metric(
            "Пропускна здатність", 
            f"{metrics['network_throughput']:.1f} Мбіт/с",
            delta=None
        )
    
    # Графіки реального часу
    if st.session_state.users:
        col5, col6 = st.columns(2)
        
        with col5:
            # RSRP розподіл
            rsrp_data = []
            for user in st.session_state.users:
                if user.get('active', True):
                    rsrp_data.append({
                        'Користувач': user['id'],
                        'RSRP': user.get('rsrp', -85),
                        'BS': user.get('serving_bs', 'Не підключено')
                    })
            
            if rsrp_data:
                df_rsrp = pd.DataFrame(rsrp_data)
                fig_rsrp = px.bar(
                    df_rsrp, 
                    x='Користувач', 
                    y='RSRP',
                    color='BS',
                    title="Поточна RSRP користувачів",
                    labels={'RSRP': 'RSRP (дБм)'}
                )
                
                # Додавання порогових ліній
                fig_rsrp.add_hline(y=-70, line_dash="dash", line_color="green", 
                                  annotation_text="Відмінно")
                fig_rsrp.add_hline(y=-85, line_dash="dash", line_color="orange", 
                                  annotation_text="Добре")
                fig_rsrp.add_hline(y=-100, line_dash="dash", line_color="red", 
                                  annotation_text="Критично")
                
                st.plotly_chart(fig_rsrp, use_container_width=True)
        
        with col6:
            # Навантаження BS
            bs_data = []
            network_state = st.session_state.network_engine.get_network_state()
            for bs_id, bs_info in network_state['base_stations'].items():
                bs_data.append({
                    'Базова станція': bs_info['name'],
                    'Користувачі': bs_info['connected_users'],
                    'Навантаження': bs_info['load_percentage']
                })
            
            if bs_data:
                df_bs = pd.DataFrame(bs_data)
                fig_load = px.pie(
                    df_bs, 
                    values='Користувачі', 
                    names='Базова станція',
                    title="Розподіл користувачів по BS"
                )
                st.plotly_chart(fig_load, use_container_width=True)

with tab3:
    st.subheader("🔄 Журнал хендоверів")
    
    if st.session_state.handover_events:
        # Фільтри
        col7, col8, col9 = st.columns(3)
        
        with col7:
            ho_types = ["Всі"] + list(set([ho.get('type', 'unknown') for ho in st.session_state.handover_events]))
            selected_type = st.selectbox("Тип хендовера", ho_types)
        
        with col8:
            time_filter = st.selectbox("Період", ["Останні 10", "Останні 50", "Всі"])
        
        with col9:
            if st.button("🗑️ Очистити журнал"):
                st.session_state.handover_events.clear()
                st.rerun()
        
        # Фільтрація подій
        filtered_events = st.session_state.handover_events.copy()
        
        if selected_type != "Всі":
            filtered_events = [ho for ho in filtered_events if ho.get('type') == selected_type]
        
        if time_filter == "Останні 10":
            filtered_events = filtered_events[-10:]
        elif time_filter == "Останні 50":
            filtered_events = filtered_events[-50:]
        
        # Таблиця подій
        if filtered_events:
            ho_df = pd.DataFrame([
                {
                    'Час': ho['timestamp'].strftime('%H:%M:%S'),
                    'Користувач': ho.get('ue_id', 'Unknown'),
                    'Від': ho.get('old_bs', 'Unknown'),
                    'До': ho.get('new_bs', 'Unknown'),
                    'Покращення (дБ)': f"{ho.get('improvement', 0):.1f}",
                    'Тип': ho.get('type', 'unknown'),
                    'Успішно': '✅' if ho.get('success', False) else '❌'
                }
                for ho in filtered_events
            ])
            
            st.dataframe(
                ho_df, 
                use_container_width=True,
                hide_index=True
            )
            
            # Статистика
            st.subheader("📊 Статистика хендоверів")
            
            success_count = len([ho for ho in filtered_events if ho.get('success', False)])
            total_count = len(filtered_events)
            avg_improvement = np.mean([ho.get('improvement', 0) for ho in filtered_events])
            
            col10, col11, col12 = st.columns(3)
            
            with col10:
                st.metric("Загалом", total_count)
            
            with col11:
                success_rate = (success_count / total_count * 100) if total_count > 0 else 0
                st.metric("Успішність", f"{success_rate:.1f}%")
            
            with col12:
                st.metric("Середнє покращення", f"{avg_improvement:.1f} дБ")
        
        else:
            st.info("Хендовери ще не відбулися. Запустіть симуляцію та додайте користувачів.")
    
    else:
        st.info("Хендовери ще не відбулися. Запустіть симуляцію та додайте користувачів.")

# Автоматичне оновлення при активній симуляції
if st.session_state.simulation_active:
    # Автоматична генерація користувачів
    if auto_generate and len(st.session_state.users) < max_users:
        if random.random() < 0.1:  # 10% ймовірність додавання користувача
            add_random_user(max_users)
    
    # Симуляція одного кроку
    network_engine = st.session_state.network_engine
    
    # Оновлення параметрів хендовера
    handover_params = HandoverParameters(ttt=ttt, hyst=hyst, offset=offset)
    st.session_state.handover_algorithm.update_parameters(handover_params)
    
    # Виконання кроку симуляції
    step_result = network_engine.step_simulation(delta_time=1.0)
    
    # Оновлення метрик
    network_state = network_engine.get_network_state()
    st.session_state.simulation_metrics.update(network_state['network_metrics'])
    
    # Додавання нових подій хендовера
    if 'events' in step_result:
        st.session_state.handover_events.extend(step_result['events'])
    
    # Автоматичне оновлення інтерфейсу кожні 2 секунди
    time.sleep(2)
    st.rerun()

# Футер
st.markdown("---")
st.markdown("""
<div style='text-align: center'>
    <strong>LTE Network Simulator v2.0</strong><br>
    Розроблено для дослідження архітектурних принципів та оптимізації LTE мереж<br>
    <em>Автор: Хрустовський А.А. | Керівник: Савицький А.Ю. | ВНТУ, 2025</em>
</div>
""", unsafe_allow_html=True)
