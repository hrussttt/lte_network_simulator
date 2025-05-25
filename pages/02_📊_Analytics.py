import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import numpy as np
from collections import defaultdict

st.title("📊 Аналітика мережі")

# Перевірка даних
if 'handover_events' not in st.session_state:
    st.warning("Спочатку запустіть симулятор!")
    st.stop()

# Фільтри
st.sidebar.header("🔍 Фільтри аналізу")

# Вибір періоду
time_filter = st.sidebar.selectbox(
    "Період аналізу",
    ["Останні 5 хвилин", "Останні 15 хвилин", "Остання година", "Весь час"]
)

# Конвертація періоду
now = pd.Timestamp.now()
if time_filter == "Останні 5 хвилин":
    start_time = now - pd.Timedelta(minutes=5)
elif time_filter == "Останні 15 хвилин":
    start_time = now - pd.Timedelta(minutes=15)
elif time_filter == "Остання година":
    start_time = now - pd.Timedelta(hours=1)
else:
    start_time = None

# Фільтрація подій
filtered_events = st.session_state.handover_events
if start_time:
    filtered_events = [e for e in filtered_events if pd.Timestamp(e['timestamp']) >= start_time]

if not filtered_events:
    st.warning("Немає даних для аналізу в обраному періоді")
    st.stop()

# Основна аналітика
st.subheader("📈 Загальна статистика")

col1, col2, col3, col4 = st.columns(4)

total_handovers = len(filtered_events)
successful_handovers = len([e for e in filtered_events if e['success']])
failed_handovers = total_handovers - successful_handovers
avg_improvement = np.mean([e['improvement'] for e in filtered_events])

with col1:
    st.metric("Всього хендоверів", total_handovers)

with col2:
    success_rate = (successful_handovers / total_handovers * 100) if total_handovers > 0 else 0
    st.metric("Успішність", f"{success_rate:.1f}%")

with col3:
    st.metric("Невдалі хендовери", failed_handovers)

with col4:
    st.metric("Середнє покращення", f"{avg_improvement:.1f} дБ")

# Детальний аналіз
tab1, tab2, tab3, tab4 = st.tabs(["📊 Тренди", "🔄 Хендовери по BS", "⚡ Ефективність", "🎯 Прогнози"])

with tab1:
    st.subheader("Тренди хендоверів у часі")
    
    # Групування по часу
    df_events = pd.DataFrame(filtered_events)
    df_events['timestamp'] = pd.to_datetime(df_events['timestamp'])
    df_events['hour'] = df_events['timestamp'].dt.floor('H')
    
    # Аналіз по годинах
    hourly_stats = df_events.groupby('hour').agg({
        'success': ['count', 'sum'],
        'improvement': 'mean'
    }).round(2)
    
    hourly_stats.columns = ['Всього', 'Успішних', 'Середнє покращення']
    hourly_stats['Успішність (%)'] = (hourly_stats['Успішних'] / hourly_stats['Всього'] * 100).round(1)
    
    # Графік трендів
    fig_trend = go.Figure()
    
    fig_trend.add_trace(go.Scatter(
        x=hourly_stats.index,
        y=hourly_stats['Всього'],
        mode='lines+markers',
        name='Всього хендоверів',
        line=dict(color='blue')
    ))
    
    fig_trend.add_trace(go.Scatter(
        x=hourly_stats.index,
        y=hourly_stats['Успішних'],
        mode='lines+markers',
        name='Успішні хендовери',
        line=dict(color='green')
    ))
    
    fig_trend.update_layout(
        title="Динаміка хендоверів по годинах",
        xaxis_title="Час",
        yaxis_title="Кількість хендоверів"
    )
    
    st.plotly_chart(fig_trend, use_container_width=True)

with tab2:
    st.subheader("Аналіз хендоверів по базових станціях")
    
    # Статистика по BS
    bs_stats = defaultdict(lambda: {'from': 0, 'to': 0, 'total': 0})
    
    for event in filtered_events:
        bs_stats[event['old_bs']]['from'] += 1
        bs_stats[event['new_bs']]['to'] += 1
        bs_stats[event['old_bs']]['total'] += 1
        bs_stats[event['new_bs']]['total'] += 1
    
    # Створення DataFrame
    bs_data = []
    for bs_id, stats in bs_stats.items():
        bs_name = next((bs['name'] for bs in st.session_state.base_stations if bs['id'] == bs_id), bs_id)
        bs_data.append({
            'BS': bs_name,
            'ID': bs_id,
            'Вихідні хендовери': stats['from'],
            'Вхідні хендовери': stats['to'],
            'Баланс': stats['to'] - stats['from']
        })
    
    df_bs = pd.DataFrame(bs_data)
    
    # Графік балансу хендоверів
    fig_balance = px.bar(
        df_bs, 
        x='BS', 
        y='Баланс',
        color='Баланс',
        color_continuous_scale='RdYlGn',
        title="Баланс хендоверів (вхідні - вихідні)"
    )
    
    fig_balance.add_hline(y=0, line_dash="solid", line_color="black")
    st.plotly_chart(fig_balance, use_container_width=True)
    
    # Таблиця статистики
    st.dataframe(df_bs, use_container_width=True)

with tab3:
    st.subheader("Ефективність хендоверів")
    
    # Розподіл покращень RSRP
    improvements = [e['improvement'] for e in filtered_events]
    
    fig_hist = px.histogram(
        x=improvements,
        nbins=20,
        title="Розподіл покращень RSRP при хендоверах",
        labels={'x': 'Покращення RSRP (дБ)', 'y': 'Кількість'}
    )
    
    fig_hist.add_vline(x=0, line_dash="dash", line_color="red", annotation_text="Без покращення")
    fig_hist.add_vline(x=np.mean(improvements), line_dash="dash", line_color="green", annotation_text="Середнє")
    
    st.plotly_chart(fig_hist, use_container_width=True)
    
    # Кореляційний аналіз
    st.subheader("📊 Кореляційний аналіз")
    
    # Створення DataFrame для кореляції
    corr_data = []
    for event in filtered_events:
        user = next((u for u in st.session_state.users if u['id'] == event['user_id']), None)
        if user:
            corr_data.append({
                'Покращення RSRP': event['improvement'],
                'Початкова RSRP': event['old_rsrp'],
                'Швидкість користувача': user['speed'],
                'Успішність': 1 if event['success'] else 0
            })
    
    if corr_data:
        df_corr = pd.DataFrame(corr_data)
        correlation_matrix = df_corr.corr()
        
        fig_corr = px.imshow(
            correlation_matrix,
            color_continuous_scale='RdBu',
            aspect='auto',
            title="Кореляційна матриця параметрів хендовера"
        )
        
        st.plotly_chart(fig_corr, use_container_width=True)

with tab4:
    st.subheader("🎯 Прогнози та рекомендації")
    
    # Прогноз навантаження
    current_users = len([u for u in st.session_state.users if u['active']])
    avg_handovers_per_user = total_handovers / max(current_users, 1)
    
    st.write("**📈 Прогноз навантаження:**")
    
    future_users = st.slider("Прогнозована кількість користувачів", 1, 100, current_users)
    predicted_handovers = future_users * avg_handovers_per_user
    
    col5, col6 = st.columns(2)
    
    with col5:
        st.metric("Поточні користувачі", current_users)
        st.metric("Середньо хендоверів/користувач", f"{avg_handovers_per_user:.2f}")
    
    with col6:
        st.metric("Прогнозовані користувачі", future_users)
        st.metric("Прогноз хендоверів", f"{predicted_handovers:.0f}")
    
    # Рекомендації
    st.write("**💡 Рекомендації для оптимізації:**")
    
    recommendations = []
    
    if success_rate < 80:
        recommendations.append("🔧 Низька успішність хендоверів - розгляньте збільшення порогу покращення")
    
    if avg_improvement < 3:
        recommendations.append("⚡ Мале середнє покращення - оптимізуйте розташування базових станцій")
    
    # Аналіз балансу навантаження
    bs_loads = [bs['load'] for bs in st.session_state.base_stations]
    load_std = np.std(bs_loads)
    
    if load_std > 20:
        recommendations.append("⚖️ Велика різниця в навантаженні BS - впровадіть балансування навантаження")
    
    if len([bs for bs in st.session_state.base_stations if bs['load'] > 80]) > 0:
        recommendations.append("🚨 Деякі BS перевантажені - додайте нові базові станції")
    
    if not recommendations:
        recommendations.append("✅ Мережа працює оптимально!")
    
    for rec in recommendations:
        st.write(f"- {rec}")
    
    # Оцінка якості мережі
    quality_score = (success_rate + max(0, 100 - load_std)) / 2
    
    st.subheader("📊 Загальна оцінка якості мережі")
    
    if quality_score >= 90:
        st.success(f"🌟 Відмінно: {quality_score:.1f}/100")
    elif quality_score >= 70:
        st.warning(f"⚠️ Добре: {quality_score:.1f}/100")
    else:
        st.error(f"❌ Потребує покращення: {quality_score:.1f}/100")
