import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import numpy as np
from datetime import datetime

st.title("🌐 Живий моніторинг мережі")

# ✅ Перевірка ініціалізації з правильною обробкою помилок
def check_initialization():
    required_keys = ['handover_events', 'users', 'base_stations', 'network_metrics']
    missing_keys = [key for key in required_keys if key not in st.session_state]
    
    if missing_keys:
        st.error(f"❌ Не ініціалізовано: {', '.join(missing_keys)}")
        st.warning("🔄 Спочатку запустіть головну сторінку симулятора!")
        st.stop()

# Перевірка ініціалізації
check_initialization()

# Основний код сторінки
col1, col2 = st.columns(2)

with col1:
    st.subheader("📈 RSRP користувачів")
    
    if st.session_state.users:
        user_data = []
        for user in st.session_state.users:
            if user.get('active', True):
                user_data.append({
                    'Користувач': user['id'],
                    'RSRP': user.get('rsrp', -85),
                    'BS': user.get('serving_bs', 'Немає'),
                    'Швидкість': user.get('speed', 0)
                })
        
        if user_data:
            df = pd.DataFrame(user_data)
            fig = px.bar(df, x='Користувач', y='RSRP', color='BS',
                        title="Поточна RSRP користувачів")
            
            # Порогові лінії
            fig.add_hline(y=-70, line_dash="dash", line_color="green",
                         annotation_text="Відмінно (-70 дБм)")
            fig.add_hline(y=-85, line_dash="dash", line_color="orange",
                         annotation_text="Добре (-85 дБм)")
            fig.add_hline(y=-100, line_dash="dash", line_color="red",
                         annotation_text="Критично (-100 дБм)")
            
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Немає активних користувачів")
    else:
        st.info("Користувачі не знайдені")

with col2:
    st.subheader("📊 Розподіл навантаження")
    
    if st.session_state.base_stations:
        bs_data = []
        for bs in st.session_state.base_stations:
            bs_data.append({
                'BS': bs['name'],
                'Користувачі': bs.get('users', 0),
                'Навантаження (%)': bs.get('load', 0)
            })
        
        if bs_data:
            df_bs = pd.DataFrame(bs_data)
            fig_load = px.pie(df_bs, values='Користувачі', names='BS',
                             title="Розподіл користувачів по BS")
            st.plotly_chart(fig_load, use_container_width=True)

# Часовий графік хендоверів
st.subheader("🔄 Часовий графік хендоверів")

if st.session_state.handover_events:
    ho_data = []
    for ho in st.session_state.handover_events[-50:]:
        ho_data.append({
            'Час': ho['timestamp'],
            'Покращення': ho.get('improvement', 0),
            'Успішність': 'Успішно' if ho.get('success', False) else 'Невдало',
            'Користувач': ho.get('user_id', 'Unknown')
        })
    
    if ho_data:
        df_ho = pd.DataFrame(ho_data)
        fig_time = px.scatter(df_ho, x='Час', y='Покращення',
                             color='Успішність',
                             hover_data=['Користувач'],
                             title="Покращення RSRP при хендоверах")
        fig_time.add_hline(y=0, line_dash="solid", line_color="gray")
        st.plotly_chart(fig_time, use_container_width=True)
        
        # Статистика
        success_count = df_ho['Успішність'].value_counts()
        col3, col4, col5 = st.columns(3)
        
        with col3:
            st.metric("Всього хендоверів", len(df_ho))
        
        with col4:
            if 'Успішно' in success_count:
                success_rate = (success_count['Успішно'] / len(df_ho)) * 100
                st.metric("Успішність", f"{success_rate:.1f}%")
        
        with col5:
            avg_improvement = df_ho['Покращення'].mean()
            st.metric("Середнє покращення", f"{avg_improvement:.1f} дБ")
else:
    st.info("Хендовери ще не відбулися")

# Детальна таблиця користувачів
st.subheader("👥 Детальна інформація")

if st.session_state.users:
    user_details = []
    for user in st.session_state.users:
        if user.get('active', True):
            user_details.append({
                'ID': user['id'],
                'RSRP (дБм)': f"{user.get('rsrp', -85):.1f}",
                'BS': user.get('serving_bs', 'Немає'),
                'Швидкість (км/год)': user.get('speed', 0),
                'Хендовери': user.get('handover_count', 0),
                'Останній HO': user.get('last_handover', 'Немає')
            })
    
    if user_details:
        st.dataframe(pd.DataFrame(user_details), use_container_width=True)

# Автооновлення
if st.session_state.get('network_active', False):
    time.sleep(3)
    st.rerun()
