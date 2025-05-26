import plotly.graph_objects as go
import plotly.express as px
import numpy as np
import pandas as pd

def create_realtime_plot(measurements_log, network, serving_bs, metric='rsrp'):
    """Створення графіка реального часу для RSRP/RSRQ"""
    
    if len(measurements_log) < 2:
        return go.Figure()
    
    # Підготовка даних
    times = [entry['timestamp'] for entry in measurements_log[-20:]]  # Останні 20 записів
    
    fig = go.Figure()
    
    # Додавання ліній для кожної базової станції
    for bs_id, bs_data in network.base_stations.items():
        values = []
        for entry in measurements_log[-20:]:
            if bs_id in entry['measurements']:
                values.append(entry['measurements'][bs_id][metric])
            else:
                values.append(None)
        
        # Визначення стилю лінії
        line_width = 4 if bs_id == serving_bs else 2
        line_dash = None if bs_id == serving_bs else 'dash'
        
        fig.add_trace(go.Scatter(
            x=times,
            y=values,
            mode='lines+markers',
            name=f"{bs_data['name']} ({bs_data['operator']})",
            line=dict(
                color=bs_data['color'], 
                width=line_width,
                dash=line_dash
            ),
            marker=dict(size=8 if bs_id == serving_bs else 5),
            showlegend=True
        ))
    
    # Налаштування графіка
    title = f"{'RSRP (дБм)' if metric == 'rsrp' else 'RSRQ (дБ)'} у реальному часі"
    
    fig.update_layout(
        title=title,
        xaxis_title="Час",
        yaxis_title=f"{'RSRP (дБм)' if metric == 'rsrp' else 'RSRQ (дБ)'}",
        height=300,
        showlegend=True,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        ),
        margin=dict(t=50, b=50, l=50, r=50)
    )
    
    # Додавання порогових ліній
    if metric == 'rsrp':
        fig.add_hline(y=-70, line_dash="dot", line_color="green", 
                     annotation_text="Відмінно (-70 дБм)")
        fig.add_hline(y=-85, line_dash="dot", line_color="orange", 
                     annotation_text="Добре (-85 дБм)")
        fig.add_hline(y=-100, line_dash="dot", line_color="red", 
                     annotation_text="Мінімум (-100 дБм)")
    
    return fig
