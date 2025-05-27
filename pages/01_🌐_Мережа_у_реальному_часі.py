import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

st.title("🌐 Живий моніторинг мережі")

# Перевірка ініціалізації
if 'handover_events' not in st.session_state:
    st.warning("Спочатку запустіть головну сторінку симулятора!")
    st.stop()

# Графіки в реальному часі
col1, col2 = st.columns(2)

with col1:
    st.subheader("📈 RSRP користувачів")
    
    if st.session_state.users:
        # Підготовка даних для графіка
        user_data = []
        for user in st.session_state.users:
            if user['active']:
                user_data.append({
                    'Користувач': user['id'],
                    'RSRP': user['rsrp'],
                    'BS': user['serving_bs'],
                    'Швидкість': user['speed']
                })
        
        if user_data:
            df = pd.DataFrame(user_data)
            
            fig = px.bar(df, x='Користувач', y='RSRP', 
                        color='BS', 
                        title="Поточна RSRP користувачів",
                        labels={'RSRP': 'RSRP (дБм)'})
            
            # Додавання порогових ліній
            fig.add_hline(y=-70, line_dash="dash", line_color="green", 
                         annotation_text="Відмінно (-70 дБм)")
            fig.add_hline(y=-85, line_dash="dash", line_color="orange", 
                         annotation_text="Добре (-85 дБм)")
            fig.add_hline(y=-100, line_dash="dash", line_color="red", 
                         annotation_text="Критично (-100 дБм)")
            
            st.plotly_chart(fig, use_container_width=True)

with col2:
    st.subheader("📊 Розподіл навантаження")
    
    # Підготовка даних про BS
    bs_data = []
    for bs in st.session_state.base_stations:
        bs_data.append({
            'BS': bs['name'],
            'Користувачі': bs['users'],
            'Навантаження (%)': bs['load']
        })
    
    if bs_data:
        df_bs = pd.DataFrame(bs_data)
        
        fig_load = px.pie(df_bs, values='Користувачі', names='BS',
                         title="Розподіл користувачів по BS")
        st.plotly_chart(fig_load, use_container_width=True)

# Часовий графік хендоверів
st.subheader("🔄 Часовий графік хендоверів")

if st.session_state.handover_events:
    # Підготовка даних
    ho_data = []
    for ho in st.session_state.handover_events[-50:]:  # Останні 50
        ho_data.append({
            'Час': ho['timestamp'],
            'Покращення': ho['improvement'],
            'Успішність': 'Успішно' if ho['success'] else 'Невдало',
            'Користувач': ho['user_id']
        })
    
    df_ho = pd.DataFrame(ho_data)
    
    fig_time = px.scatter(df_ho, x='Час', y='Покращення', 
                         color='Успішність',
                         hover_data=['Користувач'],
                         title="Покращення RSRP при хендоверах у часі")
    
    fig_time.add_hline(y=0, line_dash="solid", line_color="gray")
    
    st.plotly_chart(fig_time, use_container_width=True)
    
    # Статистика хендоверів
    success_count = df_ho['Успішність'].value_counts()
    
    col3, col4, col5 = st.columns(3)
    
    with col3:
        total_ho = len(df_ho)
        st.metric("Всього хендоверів", total_ho)
    
    with col4:
        if 'Успішно' in success_count:
            success_rate = (success_count['Успішно'] / total_ho) * 100
            st.metric("Успішність", f"{success_rate:.1f}%")
    
    with col5:
        avg_improvement = df_ho['Покращення'].mean()
        st.metric("Середнє покращення", f"{avg_improvement:.1f} дБ")

else:
    st.info("Хендовери ще не відбулися. Зачекайте або додайте більше користувачів.")

# Деталі користувачів
st.subheader("👥 Детальна інформація про користувачів")

if st.session_state.users:
    user_details = []
    for user in st.session_state.users:
        if user['active']:
            user_details.append({
                'ID': user['id'],
                'RSRP (дБм)': f"{user['rsrp']:.1f}",
                'Обслуговуюча BS': user['serving_bs'],
                'Швидкість (км/год)': user['speed'],
                'Throughput (Мбіт/с)': f"{user['throughput']:.1f}",
                'Кількість хендоверів': user['handover_count'],
                'Останній хендовер': user['last_handover'].strftime('%H:%M:%S') if user['last_handover'] else 'Немає'
            })
    
    if user_details:
        st.dataframe(pd.DataFrame(user_details), use_container_width=True)

# Автоматичне оновлення
if st.session_state.network_active:
    st.rerun()
