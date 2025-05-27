"""
Розширена візуалізація з Mapbox підтримкою
"""

import plotly.graph_objects as go
import plotly.express as px
import numpy as np
import pandas as pd
from typing import Dict, List, Optional
from config.mapbox_config import MAPBOX_CONFIG, COLOR_SCHEME, MAP_ICONS, LINE_STYLES

class MapboxVisualizer:
    """Клас для створення інтерактивних карт з Mapbox"""
    
    def __init__(self):
        self.config = MAPBOX_CONFIG
        self.colors = COLOR_SCHEME
        
    def create_network_map(self, base_stations: Dict, users: Dict, 
                          handover_events: List = None, 
                          show_coverage: bool = True) -> go.Figure:
        """Створення основної карти мережі"""
        
        fig = go.Figure()
        
        # Додавання базових станцій
        self._add_base_stations(fig, base_stations)
        
        # Додавання користувачів
        self._add_users(fig, users)
        
        # Додавання зон покриття
        if show_coverage:
            self._add_coverage_areas(fig, base_stations)
        
        # Додавання подій хендовера
        if handover_events:
            self._add_handover_events(fig, handover_events)
        
        # Налаштування карти
        self._configure_map_layout(fig)
        
        return fig
    
    def _add_base_stations(self, fig: go.Figure, base_stations: Dict):
        """Додавання базових станцій на карту"""
        
        for bs_id, bs_data in base_stations.items():
            operator = bs_data.get('operator', 'Unknown')
            color = self.colors['base_stations'].get(operator, '#000000')
            
            # Розмір маркера залежно від навантаження
            load = bs_data.get('load_percentage', 0)
            size = 15 + (load / 100) * 10  # 15-25 пікселів
            
            # Текст підказки
            hover_text = f"""
            <b>{bs_data.get('name', bs_id)}</b><br>
            Оператор: {operator}<br>
            Потужність: {bs_data.get('power_dbm', 0)} дБм<br>
            Частота: {bs_data.get('frequency_mhz', 0)} МГц<br>
            Користувачі: {bs_data.get('connected_users', 0)}<br>
            Навантаження: {load:.1f}%<br>
            Пропускна здатність: {bs_data.get('throughput_mbps', 0):.1f} Мбіт/с
            """
            
            fig.add_trace(go.Scattermapbox(
                lat=[bs_data['latitude']],
                lon=[bs_data['longitude']],
                mode='markers',
                marker=dict(
                    size=size,
                    color=color,
                    symbol='communications-tower'
                ),
                text=hover_text,
                hovertemplate='%{text}<extra></extra>',
                name=f"BS {operator}",
                showlegend=True
            ))
    
    def _add_users(self, fig: go.Figure, users: Dict):
        """Додавання користувачів на карту"""
        
        for ue_id, ue_data in users.items():
            if not ue_data.get('active', True):
                continue
                
            rsrp = ue_data.get('rsrp', -85)
            
            # Визначення кольору за якістю сигналу
            if rsrp > -70:
                color = self.colors['signal_quality']['excellent']
                quality = 'Відмінно'
            elif rsrp > -85:
                color = self.colors['signal_quality']['good']
                quality = 'Добре'
            elif rsrp > -100:
                color = self.colors['signal_quality']['fair']
                quality = 'Задовільно'
            else:
                color = self.colors['signal_quality']['poor']
                quality = 'Погано'
            
            # Іконка залежно від типу пристрою
            device_type = ue_data.get('device_type', 'smartphone')
            icon_config = MAP_ICONS['user_equipment'].get(device_type, 
                                                         MAP_ICONS['user_equipment']['smartphone'])
            
            # Текст підказки
            hover_text = f"""
            <b>{ue_id}</b><br>
            Тип: {device_type}<br>
            RSRP: {rsrp:.1f} дБм ({quality})<br>
            RSRQ: {ue_data.get('rsrq', -12):.1f} дБ<br>
            Швидкість: {ue_data.get('speed_kmh', 0):.1f} км/год<br>
            Пропускна здатність: {ue_data.get('throughput', 0):.1f} Мбіт/с<br>
            Обслуговуюча BS: {ue_data.get('serving_bs', 'Немає')}
            """
            
            fig.add_trace(go.Scattermapbox(
                lat=[ue_data['latitude']],
                lon=[ue_data['longitude']],
                mode='markers',
                marker=dict(
                    size=icon_config['size'],
                    color=color,
                    symbol=icon_config['symbol']
                ),
                text=hover_text,
                hovertemplate='%{text}<extra></extra>',
                name=f"UE ({quality})",
                showlegend=False
            ))
    
    def _add_coverage_areas(self, fig: go.Figure, base_stations: Dict):
        """Додавання зон покриття базових станцій"""
        
        for bs_id, bs_data in base_stations.items():
            lat = bs_data['latitude']
            lon = bs_data['longitude']
            range_km = bs_data.get('range_km', 2.0)
            
            # Створення кола покриття
            circle_lat, circle_lon = self._create_circle(lat, lon, range_km)
            
            operator = bs_data.get('operator', 'Unknown')
            color = self.colors['base_stations'].get(operator, '#000000')
            
            fig.add_trace(go.Scattermapbox(
                lat=circle_lat,
                lon=circle_lon,
                mode='lines',
                line=dict(
                    color=color,
                    width=2
                ),
                fill='toself',
                fillcolor=f"rgba{tuple(list(bytes.fromhex(color[1:])) + [0.1])}",
                name=f"Покриття {bs_data.get('name', bs_id)}",
                showlegend=False,
                hoverinfo='skip'
            ))
    
    def _add_handover_events(self, fig: go.Figure, handover_events: List):
        """Додавання подій хендовера на карту"""
        
        for event in handover_events[-10:]:  # Останні 10 подій
            ho_type = event.get('type', 'unknown')
            color = self.colors['handover_types'].get(ho_type, '#888888')
            
            # Позиція події (спрощено - центр між старою та новою BS)
            lat = event.get('latitude', 49.23)
            lon = event.get('longitude', 28.48)
            
            improvement = event.get('improvement', 0)
            
            # Іконка залежно від типу
            if ho_type == 'successful':
                symbol = 'arrow-right'
            elif ho_type == 'pingpong':
                symbol = 'arrow-left-right'
            else:
                symbol = 'x'
            
            hover_text = f"""
            <b>Хендовер {ho_type}</b><br>
            Користувач: {event.get('ue_id', 'Unknown')}<br>
            Від: {event.get('old_bs', 'Unknown')}<br>
            До: {event.get('new_bs', 'Unknown')}<br>
            Покращення: {improvement:.1f} дБ<br>
            Час: {event.get('timestamp', 'Unknown')}
            """
            
            fig.add_trace(go.Scattermapbox(
                lat=[lat],
                lon=[lon],
                mode='markers',
                marker=dict(
                    size=12,
                    color=color,
                    symbol=symbol,
                    line=dict(width=2, color='white')
                ),
                text=hover_text,
                hovertemplate='%{text}<extra></extra>',
                name=f"HO {ho_type}",
                showlegend=False
            ))
    
    def _create_circle(self, lat: float, lon: float, radius_km: float, num_points: int = 50):
        """Створення координат кола для зони покриття"""
        
        # Конвертація радіуса в градуси (приблизно)
        lat_radius = radius_km / 111.0
        lon_radius = radius_km / (111.0 * np.cos(np.radians(lat)))
        
        angles = np.linspace(0, 2 * np.pi, num_points)
        circle_lat = lat + lat_radius * np.cos(angles)
        circle_lon = lon + lon_radius * np.sin(angles)
        
        return circle_lat.tolist(), circle_lon.tolist()
    
    def _configure_map_layout(self, fig: go.Figure):
        """Налаштування макету карти"""
        
        fig.update_layout(
            mapbox=dict(
                style=self.config['style'],
                center=dict(
                    lat=self.config['center']['lat'],
                    lon=self.config['center']['lon']
                ),
                zoom=self.config['zoom']
            ),
            height=self.config['height'],
            margin=dict(l=0, r=0, t=0, b=0),
            showlegend=True,
            legend=dict(
                yanchor="top",
                y=0.99,
                xanchor="left",
                x=0.01,
                bgcolor="rgba(255,255,255,0.8)"
            )
        )
    
    def create_handover_analysis_chart(self, handover_events: List) -> go.Figure:
        """Створення діаграми аналізу хендоверів"""
        
        if not handover_events:
            fig = go.Figure()
            fig.add_annotation(
                text="Немає даних для аналізу",
                xref="paper", yref="paper",
                x=0.5, y=0.5, xanchor='center', yanchor='middle',
                showarrow=False, font=dict(size=16)
            )
            return fig
        
        # Підготовка даних
        df = pd.DataFrame(handover_events)
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df['hour'] = df['timestamp'].dt.floor('H')
        
        # Групування по годинах та типах
        hourly_stats = df.groupby(['hour', 'type']).size().unstack(fill_value=0)
        
        fig = go.Figure()
        
        # Додавання стовпців для кожного типу
        for ho_type in hourly_stats.columns:
            color = self.colors['handover_types'].get(ho_type, '#888888')
            
            fig.add_trace(go.Bar(
                x=hourly_stats.index,
                y=hourly_stats[ho_type],
                name=ho_type.title(),
                marker_color=color
            ))
        
        fig.update_layout(
            title="Розподіл хендоверів по часу та типах",
            xaxis_title="Час",
            yaxis_title="Кількість хендоверів",
            barmode='stack',
            height=400
        )
        
        return fig
    
    def create_signal_quality_heatmap(self, users: Dict, base_stations: Dict) -> go.Figure:
        """Створення теплової карти якості сигналу"""
        
        # Створення сітки точок для інтерполяції
        lat_range = np.linspace(49.20, 49.27, 50)
        lon_range = np.linspace(28.42, 28.55, 50)
        
        lat_grid, lon_grid = np.meshgrid(lat_range, lon_range)
        rsrp_grid = np.zeros_like(lat_grid)
        
        # Розрахунок RSRP для кожної точки сітки
        for i in range(lat_grid.shape[0]):
            for j in range(lat_grid.shape[1]):
                lat_point = lat_grid[i, j]
                lon_point = lon_grid[i, j]
                
                max_rsrp = -120
                for bs_data in base_stations.values():
                    rsrp = self._calculate_rsrp_simple(
                        lat_point, lon_point,
                        bs_data['latitude'], bs_data['longitude'],
                        bs_data.get('power_dbm', 43)
                    )
                    max_rsrp = max(max_rsrp, rsrp)
                
                rsrp_grid[i, j] = max_rsrp
        
        fig = go.Figure(data=go.Contour(
            z=rsrp_grid,
            x=lon_range,
            y=lat_range,
            colorscale='RdYlGn',
            contours=dict(
                showlabels=True,
                labelfont=dict(size=10)
            ),
            colorbar=dict(
                title="RSRP (дБм)",
                titleside="right"
            )
        ))
        
        # Додавання базових станцій
        for bs_data in base_stations.values():
            fig.add_trace(go.Scatter(
                x=[bs_data['longitude']],
                y=[bs_data['latitude']],
                mode='markers',
                marker=dict(
                    size=15,
                    color='black',
                    symbol='triangle-up',
                    line=dict(width=2, color='white')
                ),
                name=bs_data.get('name', 'BS'),
                text=bs_data.get('name', 'BS'),
                textposition='top center'
            ))
        
        fig.update_layout(
            title="Теплова карта покриття RSRP",
            xaxis_title="Довгота",
            yaxis_title="Широта",
            height=500
        )
        
        return fig
    
    def _calculate_rsrp_simple(self, ue_lat: float, ue_lon: float, 
                              bs_lat: float, bs_lon: float, 
                              power_dbm: float) -> float:
        """Спрощений розрахунок RSRP для теплової карти"""
        
        from geopy.distance import geodesic
        
        distance_km = geodesic((ue_lat, ue_lon), (bs_lat, bs_lon)).kilometers
        
        # Спрощена модель втрат
        if distance_km == 0:
            distance_km = 0.001
        
        path_loss = 32.44 + 20 * np.log10(1800) + 20 * np.log10(distance_km)
        rsrp = power_dbm - path_loss + 15  # +15 dB antenna gain
        
        return max(-120, min(-40, rsrp))
