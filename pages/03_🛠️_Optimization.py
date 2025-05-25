import streamlit as st
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
from datetime import datetime

st.title("🛠️ Оптимізація мережі")

# Симуляція різних алгоритмів оптимізації
st.subheader("🧠 Алгоритми оптимізації хендовера")

# Параметри оптимізації
st.sidebar.header("⚙️ Параметри оптимізації")

handover_threshold = st.sidebar.slider("Поріг хендовера (дБ)", 1.0, 10.0, 5.0, 0.5)
load_balancing = st.sidebar.checkbox("Балансування навантаження", value=True)
predictive_handover = st.sidebar.checkbox("Предиктивний хендовер", value=False)

# Алгоритми оптимізації
algorithms = {
    "Стандартний": {"threshold": 5.0, "load_factor": 0, "prediction": False},
    "Адаптивний": {"threshold": handover_threshold, "load_factor": 0.3, "prediction": False},
    "Предиктивний": {"threshold": handover_threshold, "load_factor": 0.2, "prediction": True},
    "Гібридний": {"threshold": handover_threshold, "load_factor": 0.5, "prediction": predictive_handover}
}

def simulate_algorithm_performance(algorithm_params, num_simulations=1000):
    """Симуляція ефективності алгоритму"""
    successful = 0
    failed = 0
    unnecessary = 0
    total_improvement = 0
    
    for _ in range(num_simulations):
        # Симуляція початкової RSRP
        initial_rsrp = np.random.uniform(-100, -60)
        
        # Симуляція потенційного покращення
        potential_improvement = np.random.normal(6, 3)
        
        # Симуляція навантаження BS
        source_load = np.random.uniform(0, 100)
        target_load = np.random.uniform(0, 100)
        
        # Поправка на навантаження
        load_penalty = 0
        if algorithm_params["load_factor"] > 0:
            load_penalty = algorithm_params["load_factor"] * (target_load - source_load) * 0.1
        
        # Предиктивна поправка
        prediction_bonus = 0
        if algorithm_params["prediction"]:
            prediction_bonus = np.random.uniform(0, 2)
        
        effective_improvement = potential_improvement - load_penalty + prediction_bonus
        
        # Рішення про хендовер
        if effective_improvement > algorithm_params["threshold"]:
            if potential_improvement > 2:  # Реально корисний хендовер
                successful += 1
                total_improvement += effective_improvement
            else:
                unnecessary += 1  # Непотрібний хендовер
        else:
            if potential_improvement > algorithm_params["threshold"] + 2:
                failed += 1  # Пропущений корисний хендовер
    
    total_handovers = successful + unnecessary
    success_rate = (successful / total_handovers * 100) if total_handovers > 0 else 0
    avg_improvement = total_improvement / successful if successful > 0 else 0
    
    return {
        "success_rate": success_rate,
        "avg_improvement": avg_improvement,
        "unnecessary_rate": (unnecessary / total_handovers * 100) if total_handovers > 0 else 0,
        "missed_opportunities": failed,
        "total_handovers": total_handovers
    }

# Запуск порівняння алгоритмів
if st.button("🚀 Запустити порівняння алгоритмів"):
    with st.spinner("Виконується симуляція..."):
        results = {}
        
        for alg_name, params in algorithms.items():
            results[alg_name] = simulate_algorithm_performance(params)
        
        # Збереження результатів в сесії
        st.session_state.optimization_results = results

# Відображення результатів
if 'optimization_results' in st.session_state:
    results = st.session_state.optimization_results
    
    # Таблиця порівняння
    st.subheader("📊 Порівняння алгоритмів")
    
    comparison_data = []
    for alg_name, metrics in results.items():
        comparison_data.append({
            "Алгоритм": alg_name,
            "Успішність (%)": f"{metrics['success_rate']:.1f}",
            "Середнє покращення (дБ)": f"{metrics['avg_improvement']:.1f}",
            "Непотрібні хендовери (%)": f"{metrics['unnecessary_rate']:.1f}",
            "Пропущені можливості": metrics['missed_opportunities'],
            "Всього хендоверів": metrics['total_handovers']
        })
    
    df_comparison = pd.DataFrame(comparison_data)
    st.dataframe(df_comparison, use_container_width=True)
    
    # Графічне порівняння
    col1, col2 = st.columns(2)
    
    with col1:
        # Успішність алгоритмів
        fig_success = px.bar(
            x=list(results.keys()),
            y=[results[alg]['success_rate'] for alg in results.keys()],
            title="Успішність алгоритмів (%)",
            labels={'x': 'Алгоритм', 'y': 'Успішність (%)'}
        )
        st.plotly_chart(fig_success, use_container_width=True)
    
    with col2:
        # Середнє покращення
        fig_improvement = px.bar(
            x=list(results.keys()),
            y=[results[alg]['avg_improvement'] for alg in results.keys()],
            title="Середнє покращення RSRP (дБ)",
            labels={'x': 'Алгоритм', 'y': 'Покращення (дБ)'}
        )
        st.plotly_chart(fig_improvement, use_container_width=True)

# Оптимізація параметрів
st.subheader("🎯 Автоматична оптимізація параметрів")

optimization_target = st.selectbox(
    "Цільова функція",
    ["Максимальна успішність", "Мінімум непотрібних хендоверів", "Баланс успішності та ефективності"]
)

if st.button("🔍 Знайти оптимальні параметри"):
    with st.spinner("Пошук оптимальних параметрів..."):
        
        best_score = 0
        best_params = None
        optimization_history = []
        
        # Перебір параметрів
        for threshold in np.arange(1.0, 10.1, 0.5):
            for load_factor in np.arange(0, 0.61, 0.1):
                for prediction in [False, True]:
                    
                    params = {
                        "threshold": threshold,
                        "load_factor": load_factor,
                        "prediction": prediction
                    }
                    
                    result = simulate_algorithm_performance(params, 500)
                    
                    # Обчислення оцінки за вибраною функцією
                    if optimization_target == "Максимальна успішність":
                        score = result['success_rate']
                    elif optimization_target == "Мінімум непотрібних хендоверів":
                        score = 100 - result['unnecessary_rate']
                    else:  # Баланс
                        score = result['success_rate'] * 0.7 + (100 - result['unnecessary_rate']) * 0.3
                    
                    optimization_history.append({
                        'threshold': threshold,
                        'load_factor': load_factor,
                        'prediction': prediction,
                        'score': score,
                        'success_rate': result['success_rate'],
                        'unnecessary_rate': result['unnecessary_rate']
                    })
                    
                    if score > best_score:
                        best_score = score
                        best_params = params.copy()
                        best_params['score'] = score
                        best_params['result'] = result
        
        # Відображення результатів оптимізації
        st.success("✅ Оптимізація завершена!")
        
        col3, col4 = st.columns(2)
        
        with col3:
            st.write("**🏆 Оптимальні параметри:**")
            st.write(f"- Поріг хендовера: {best_params['threshold']:.1f} дБ")
            st.write(f"- Коефіцієнт навантаження: {best_params['load_factor']:.1f}")
            st.write(f"- Предиктивний режим: {'Так' if best_params['prediction'] else 'Ні'}")
            st.write(f"- Оцінка: {best_params['score']:.1f}")
        
        with col4:
            st.write("**📈 Очікувана ефективність:**")
            result = best_params['result']
            st.write(f"- Успішність: {result['success_rate']:.1f}%")
            st.write(f"- Середнє покращення: {result['avg_improvement']:.1f} дБ")
            st.write(f"- Непотрібні хендовери: {result['unnecessary_rate']:.1f}%")
            st.write(f"- Всього хендоверів: {result['total_handovers']}")
        
        # 3D візуалізація оптимізації
        df_opt = pd.DataFrame(optimization_history)
        
        fig_3d = go.Figure(data=[go.Scatter3d(
            x=df_opt['threshold'],
            y=df_opt['load_factor'],
            z=df_opt['score'],
            mode='markers',
            marker=dict(
                size=5,
                color=df_opt['score'],
                colorscale='Viridis',
                showscale=True
            ),
            text=[f"Threshold: {row['threshold']}<br>Load Factor: {row['load_factor']}<br>Score: {row['score']:.1f}" 
                  for _, row in df_opt.iterrows()],
            hovertemplate='%{text}<extra></extra>'
        )])
        
        # Додавання оптимальної точки
        fig_3d.add_trace(go.Scatter3d(
            x=[best_params['threshold']],
            y=[best_params['load_factor']],
            z=[best_params['score']],
            mode='markers',
            marker=dict(size=15, color='red', symbol='diamond'),
            name='Оптимум'
        ))
        
        fig_3d.update_layout(
            title="3D простір оптимізації параметрів",
            scene=dict(
                xaxis_title='Поріг хендовера (дБ)',
                yaxis_title='Коефіцієнт навантаження',
                zaxis_title='Оцінка ефективності'
            )
        )
        
        st.plotly_chart(fig_3d, use_container_width=True)

# Симуляція покращень
st.subheader("⚡ Симуляція впровадження покращень")

if st.button("🧪 Запустити симуляцію покращень"):
    with st.spinner("Симуляція покращень мережі..."):
        
        # Поточна ефективність
        current_performance = simulate_algorithm_performance(algorithms["Стандартний"])
        
        # Покращена ефективність
        if 'optimization_results' in st.session_state:
            best_alg = max(st.session_state.optimization_results.items(), 
                          key=lambda x: x[1]['success_rate'])
            improved_performance = best_alg[1]
            best_alg_name = best_alg[0]
        else:
            improved_performance = simulate_algorithm_performance(algorithms["Гібридний"])
            best_alg_name = "Гібридний"
        
        # Порівняння
        col5, col6 = st.columns(2)
        
        with col5:
            st.write("**📊 Поточна ефективність:**")
            st.metric("Успішність", f"{current_performance['success_rate']:.1f}%")
            st.metric("Покращення", f"{current_performance['avg_improvement']:.1f} дБ")
            st.metric("Непотрібні хендовери", f"{current_performance['unnecessary_rate']:.1f}%")
        
        with col6:
            st.write(f"**🚀 Після оптимізації ({best_alg_name}):**")
            success_delta = improved_performance['success_rate'] - current_performance['success_rate']
            improvement_delta = improved_performance['avg_improvement'] - current_performance['avg_improvement']
            unnecessary_delta = improved_performance['unnecessary_rate'] - current_performance['unnecessary_rate']
            
            st.metric("Успішність", f"{improved_performance['success_rate']:.1f}%", 
                     delta=f"{success_delta:+.1f}%")
            st.metric("Покращення", f"{improved_performance['avg_improvement']:.1f} дБ", 
                     delta=f"{improvement_delta:+.1f} дБ")
            st.metric("Непотрібні хендовери", f"{improved_performance['unnecessary_rate']:.1f}%", 
                     delta=f"{unnecessary_delta:+.1f}%")
        
        # Візуалізація покращень
        categories = ['Успішність (%)', 'Покращення RSRP (дБ)', 'Ефективність (%)']
        current_values = [
            current_performance['success_rate'],
            current_performance['avg_improvement'],
            100 - current_performance['unnecessary_rate']
        ]
        improved_values = [
            improved_performance['success_rate'],
            improved_performance['avg_improvement'],
            100 - improved_performance['unnecessary_rate']
        ]
        
        fig_comparison = go.Figure(data=[
            go.Bar(name='Поточний стан', x=categories, y=current_values),
            go.Bar(name='Після оптимізації', x=categories, y=improved_values)
        ])
        
        fig_comparison.update_layout(
            title="Порівняння ефективності до та після оптимізації",
            barmode='group'
        )
        
        st.plotly_chart(fig_comparison, use_container_width=True)

# Рекомендації
st.subheader("💡 Рекомендації по впровадженню")

recommendations = [
    "🔧 **Поетапне впровадження**: Почніть з менш критичних зон мережі",
    "📊 **Моніторинг**: Впровадьте додатковий моніторинг для відстеження ефективності",
    "🎯 **A/B тестування**: Порівняйте нові алгоритми з існуючими на обмежених ділянках",
    "⚙️ **Автоматичне налаштування**: Розгляньте впровадження самонавчальних систем",
    "🔄 **Регулярний перегляд**: Переглядайте параметри щомісячно на основі нових даних"
]

for rec in recommendations:
    st.write(rec)
