import plotly.graph_objects as go
import plotly.express as px
import folium
from folium import plugins
import numpy as np
import pandas as pd
from typing import Dict, List, Any, Tuple
from datetime import datetime, timedelta

def create_network_map(base_stations: Dict, users: Dict, 
                      center_coords: Tuple[float, float] = (49.2328, 28.4810),
                      zoom: int = 12) -> folium.Map:
    """Створення інтерактивної карти мережі LTE"""
    
    # Створення базової карти
    m = folium.Map(
        location=center_coords,
        zoom_start=zoom,
        tiles='OpenStreetMap'
    )
    
    # Додавання базових станцій
    for bs_id, bs_data in base_stations.items():
        # Визначення кольору залежно від навантаження
        load = bs_data.get('load_percentage', 0)
        if load < 30:
            color = 'green'
            load_status = 'Низьке навантаження'
        elif load < 70:
            color = 'orange' 
            load_status = 'Середнє навантаження'
        else:
            color = 'red'
            load_status = 'Високе навантаження'
        
        # Іконка базової станції
        folium.Marker(
            [bs_data['latitude'], bs_data['longitude']],
            popup=folium.Popup(f"""
            <div style="font-family: Arial; font-size: 12px; width: 250px;">
                <h4 style="color: {color};">{bs_data['name']}</h4>
                <b>ID:</b> {bs_id}<br>
                <b>Оператор:</b> {bs_data.get('operator', 'Unknown')}<br>
                <b>Потужність:</b> {bs_data.get('power_dbm', 0)} дБм<br>
                <b>Частота:</b> {bs_data.get('frequency_mhz', 0)} МГц<br>
                <b>Користувачі:</b> {bs_data.get('connected_users', 0)}/{bs_data.get('max_users', 100)}<br>
                <b>Навантаження:</b> {load:.1f}%<br>
                <b>Throughput:</b> {bs_data.get('throughput_mbps', 0):.1f} Мбіт/с<br>
                <b>Статус:</b> {load_status}
            </div>
            """, max_width=300),
            tooltip=f"{bs_data['name']} ({load:.1f}%)",
            icon=folium.Icon(
                color=color, 
                icon='tower-broadcast', 
                prefix='fa'
            )
        ).add_to(m)
        
        # Зона покриття
        folium.Circle(
            location=[bs_data['latitude'], bs_data['longitude']],
            radius=bs_data.get('range_km', 2) * 1000,  # в метрах
            color=color,
            fillColor=color,
            fillOpacity=0.1,
            weight=2,
            popup=f"Зона покриття {bs_data['name']}"
        ).add_to(m)
    
    # Додавання користувачів
    for ue_id, ue_data in users.items():
        if not ue_data.get('active', True):
            continue
            
        # Визначення кольору залежно від якості сигналу
        rsrp = ue_data.get('rsrp', -85)
        if rsrp > -70:
            ue_color = 'green'
            signal_quality = 'Відмінно'
        elif rsrp > -85:
            ue_color = 'orange'
            signal_quality = 'Добре'
        elif rsrp > -100:
            ue_color = 'red'
            signal_quality = 'Задовільно'
        else:
            ue_color = 'darkred'
            signal_quality = 'Погано'
        
        # Визначення іконки залежно від типу пристрою
        device_icons = {
            'smartphone': 'mobile',
            'tablet': 'tablet',
            'laptop': 'laptop',
            'car': 'car',
            'iot_device': 'microchip'
        }
        
        device_type = ue_data.get('device_type', 'smartphone')
        icon_name = device_icons.get(device_type, 'mobile')
        
        folium.Marker(
            [ue_data['latitude'], ue_data['longitude']],
            popup=folium.Popup(f"""
            <div style="font-family: Arial; font-size: 12px; width: 200px;">
                <h4>📱 {ue_id}</h4>
                <b>Тип:</b> {device_type}<br>
                <b>RSRP:</b> {rsrp:.1f} дБм<br>
                <b>RSRQ:</b> {ue_data.get('rsrq', -12):.1f} дБ<br>
                <b>Якість:</b> <span style="color: {ue_color};">{signal_quality}</span><br>
                <b>Швидкість:</b> {ue_data.get('speed_kmh', 0)} км/год<br>
                <b>Throughput:</b> {ue_data.get('throughput', 0):.1f} Мбіт/с<br>
                <b>Serving BS:</b> {ue_data.get('serving_bs', 'None')}<br>
                <b>Хендоверів:</b> {ue_data.get('handover_count', 0)}
            </div>
            """, max_width=250),
            tooltip=f"{ue_id} (RSRP: {rsrp:.1f} дБм)",
            icon=folium.Icon(
                color=ue_color,
                icon=icon_name,
                prefix='fa'
            )
        ).add_to(m)
        
        # Лінія зв'язку до обслуговуючої БС
        serving_bs = ue_data.get('serving_bs')
        if serving_bs and serving_bs in base_stations:
            bs_data = base_stations[serving_bs]
            folium.PolyLine(
                locations=[
                    [ue_data['latitude'], ue_data['longitude']],
                    [bs_data['latitude'], bs_data['longitude']]
                ],
                color=ue_color,
                weight=2,
                opacity=0.6,
                popup=f"З'єднання: {ue_id} ↔ {bs_data['name']}"
            ).add_to(m)
    
    # Додавання легенди
    legend_html = '''
    <div style="position: fixed; 
                top: 10px; right: 10px; width: 220px; height: 200px; 
                background-color: white; border:2px solid grey; z-index:9999; 
                font-size:12px; padding: 10px;
                border-radius: 5px;">
    <h4>📡 Легенда мережі LTE</h4>
    <p><i class="fa fa-tower-broadcast" style="color:green"></i> БС (низьке навантаження)</p>
    <p><i class="fa fa-tower-broadcast" style="color:orange"></i> БС (середнє навантаження)</p>
    <p><i class="fa fa-tower-broadcast" style="color:red"></i> БС (високе навантаження)</p>
    <hr>
    <p><i class="fa fa-mobile" style="color:green"></i> UE (відмінний сигнал)</p>
    <p><i class="fa fa-mobile" style="color:orange"></i> UE (добрий сигнал)</p>
    <p><i class="fa fa-mobile" style="color:red"></i> UE (слабкий сигнал)</p>
    </div>
    '''
    m.get_root().html.add_child(folium.Element(legend_html))
    
    return m

def create_realtime_rsrp_plot(measurements_log: List[Dict], network_data: Dict) -> go.Figure:
    """Створення графіка RSRP в реальному часі"""
    
    if not measurements_log:
        return go.Figure().add_annotation(
            text="Недостатньо даних для відображення",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False
        )
    
    fig = go.Figure()
    
    # Підготовка даних
    recent_data = measurements_log[-50:]  # Останні 50 записів
    times = [entry['timestamp'] for entry in recent_data]
    
    # Додавання ліній для кожної базової станції
    base_stations = network_data.get('base_stations', {})
    
    for bs_id, bs_data in base_stations.items():
        rsrp_values = []
        
        for entry in recent_data:
            measurements = entry.get('measurements', {})
            if bs_id in measurements:
                rsrp_values.append(measurements[bs_id]['rsrp'])
            else:
                rsrp_values.append(None)
        
        # Визначення стилю лінії
        serving_bs = None
        for ue_data in network_data.get('users', {}).values():
            if ue_data.get('serving_bs') == bs_id:
                serving_bs = bs_id
                break
        
        line_style = dict(
            width=4 if serving_bs else 2,
            dash=None if serving_bs else 'dash'
        )
        
        operator_colors = {
            'Київстар': '#1f77b4',
            'Vodafone': '#ff7f0e', 
            'lifecell': '#2ca02c'
        }
        
        color = operator_colors.get(bs_data.get('operator', 'Unknown'), '#d62728')
        
        fig.add_trace(go.Scatter(
            x=times,
            y=rsrp_values,
            mode='lines+markers',
            name=f"{bs_data.get('name', bs_id)} ({bs_data.get('operator', '')})",
            line=dict(color=color, **line_style),
            marker=dict(size=6 if serving_bs else 4),
            connectgaps=False
        ))
    
    # Додавання порогових ліній
    fig.add_hline(y=-70, line_dash="dot", line_color="green", 
                 annotation_text="Відмінно (-70 дБм)", annotation_position="bottom right")
    fig.add_hline(y=-85, line_dash="dot", line_color="orange", 
                 annotation_text="Добре (-85 дБм)", annotation_position="bottom right")
    fig.add_hline(y=-100, line_dash="dot", line_color="red", 
                 annotation_text="Критично (-100 дБм)", annotation_position="bottom right")
    
    fig.update_layout(
        title="RSRP в реальному часі",
        xaxis_title="Час",
        yaxis_title="RSRP (дБм)",
        height=400,
        hovermode='x unified',
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        )
    )
    
    return fig

def create_handover_analysis_chart(handover_events: List[Dict]) -> go.Figure:
    """Створення графіка аналізу хендоверів"""
    
    if not handover_events:
        return go.Figure().add_annotation(
            text="Хендовери ще не відбулися",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False
        )
    
    # Підготовка даних
    df = pd.DataFrame(handover_events)
    
    # Групування по типах хендоверів
    type_counts = df['type'].value_counts()
    
    # Кольори для різних типів
    colors = {
        'successful': '#2E8B57',
        'failed': '#DC143C',
        'pingpong': '#FF8C00'
    }
    
    fig = go.Figure(data=[
        go.Bar(
            x=type_counts.index,
            y=type_counts.values,
            marker_color=[colors.get(t, '#708090') for t in type_counts.index],
            text=type_counts.values,
            textposition='auto'
        )
    ])
    
    fig.update_layout(
        title="Аналіз типів хендоверів",
        xaxis_title="Тип хендовера",
        yaxis_title="Кількість",
        height=300
    )
    
    return fig

def create_throughput_heatmap(base_stations: Dict, users: Dict) -> go.Figure:
    """Створення теплової карти пропускної здатності"""
    
    # Створення сітки координат
    lats = [bs['latitude'] for bs in base_stations.values()]
    lons = [bs['longitude'] for bs in base_stations.values()]
    
    if not lats or not lons:
        return go.Figure()
    
    lat_min, lat_max = min(lats) - 0.01, max(lats) + 0.01
    lon_min, lon_max = min(lons) - 0.01, max(lons) + 0.01
    
    # Створення сітки
    lat_grid = np.linspace(lat_min, lat_max, 20)
    lon_grid = np.linspace(lon_min, lon_max, 20)
    
    throughput_grid = np.zeros((len(lat_grid), len(lon_grid)))
    
    # Розрахунок пропускної здатності для кожної точки сітки
    for i, lat in enumerate(lat_grid):
        for j, lon in enumerate(lon_grid):
            # Знаходження найближчої БС
            min_dist = float('inf')
            best_throughput = 0
            
            for bs_data in base_stations.values():
                dist = np.sqrt((lat - bs_data['latitude'])**2 + 
                             (lon - bs_data['longitude'])**2)
                if dist < min_dist:
                    min_dist = dist
                    # Спрощена модель: throughput зменшується з відстанню
                    best_throughput = bs_data.get('throughput_mbps', 0) * \
                                    np.exp(-dist * 100)
            
            throughput_grid[i, j] = best_throughput
    
    fig = go.Figure(data=go.Heatmap(
        z=throughput_grid,
        x=lon_grid,
        y=lat_grid,
        colorscale='Viridis',
        colorbar=dict(title="Throughput (Мбіт/с)")
    ))
    
    # Додавання позицій БС
    for bs_data in base_stations.values():
        fig.add_trace(go.Scatter(
            x=[bs_data['longitude']],
            y=[bs_data['latitude']],
            mode='markers',
            marker=dict(size=10, color='red', symbol='star'),
            name=bs_data.get('name', 'BS'),
            showlegend=False
        ))
    
    fig.update_layout(
        title="Карта пропускної здатності мережі",
        xaxis_title="Довгота",
        yaxis_title="Широта",
        height=500
    )
    
    return fig

def create_network_performance_dashboard(network_metrics: Dict) -> List[go.Figure]:
    """Створення дашборду показників мережі"""
    
    figures = []
    
    # 1. Круговa діаграма типів хендоверів
    ho_data = [
        network_metrics.get('successful_handovers', 0),
        network_metrics.get('failed_handovers', 0),
        network_metrics.get('pingpong_handovers', 0)
    ]
    
    if sum(ho_data) > 0:
        fig_pie = go.Figure(data=[go.Pie(
            labels=['Успішні', 'Невдалі', 'Ping-pong'],
            values=ho_data,
            marker_colors=['#2E8B57', '#DC143C', '#FF8C00'],
            hole=0.3
        )])
        
        fig_pie.update_layout(
            title="Розподіл хендоверів",
            height=300
        )
        figures.append(fig_pie)
    
    # 2. Історія активних користувачів
    if 'user_history' in network_metrics:
        times = [entry['time'] for entry in network_metrics['user_history']]
        counts = [entry['count'] for entry in network_metrics['user_history']]
        
        fig_users = go.Figure(data=[
            go.Scatter(x=times, y=counts, mode='lines+markers', name='Активні користувачі')
        ])
        
        fig_users.update_layout(
            title="Динаміка кількості користувачів",
            xaxis_title="Час",
            yaxis_title="Кількість UE",
            height=300
        )
        figures.append(fig_users)
    
    # 3. Середня RSRP по мережі
    if 'rsrp_history' in network_metrics:
        times = [entry['time'] for entry in network_metrics['rsrp_history']]
        rsrp_values = [entry['avg_rsrp'] for entry in network_metrics['rsrp_history']]
        
        fig_rsrp = go.Figure(data=[
            go.Scatter(x=times, y=rsrp_values, mode='lines', name='Середня RSRP',
                      line=dict(color='blue', width=3))
        ])
        
        fig_rsrp.add_hline(y=-85, line_dash="dash", line_color="orange", 
                          annotation_text="Поріг якості")
        
        fig_rsrp.update_layout(
            title="Середня RSRP по мережі",
            xaxis_title="Час", 
            yaxis_title="RSRP (дБм)",
            height=300
        )
        figures.append(fig_rsrp)
    
    return figures

def create_3d_optimization_surface(optimization_results: Dict) -> go.Figure:
    """Створення 3D поверхні оптимізації"""
    
    if not optimization_results:
        return go.Figure()
    
    # Розпакування результатів
    ttt_range = optimization_results.get('ttt_range', [])
    hyst_range = optimization_results.get('hyst_range', [])
    success_matrix = optimization_results.get('success_matrix', [])
    
    if not all([ttt_range, hyst_range, success_matrix]):
        return go.Figure()
    
    # Створення сіток
    X, Y = np.meshgrid(ttt_range, hyst_range)
    Z = np.array(success_matrix)
    
    fig = go.Figure(data=[go.Surface(
        x=X, y=Y, z=Z,
        colorscale='Viridis',
        colorbar=dict(title="Успішність (%)")
    )])
    
    # Знаходження та відображення оптимуму
    if 'optimal_point' in optimization_results:
        opt_point = optimization_results['optimal_point']
        fig.add_trace(go.Scatter3d(
            x=[opt_point['ttt']],
            y=[opt_point['hyst']],
            z=[opt_point['success_rate']],
            mode='markers',
            marker=dict(size=15, color='red', symbol='diamond'),
            name=f"Оптимум: TTT={opt_point['ttt']}мс, Hyst={opt_point['hyst']}дБ"
        ))
    
    fig.update_layout(
        title="3D поверхня оптимізації параметрів хендовера",
        scene=dict(
            xaxis_title='TTT (мс)',
            yaxis_title='Hysteresis (дБ)',
            zaxis_title='Успішність (%)'
        ),
        height=600
    )
    
    return fig
