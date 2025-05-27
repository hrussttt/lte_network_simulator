"""
Конфігурація для Mapbox візуалізації
"""

# Mapbox налаштування
MAPBOX_CONFIG = {
    'access_token': 'pk.eyJ1IjoiaHJ1c3N0dHQiLCJhIjoiY21iNnR0OXh1MDJ2ODJsczk3emdhdDh4ayJ9.CNygw7kmAPb6JGd0CFvUBg',  # Замініть на ваш токен
    'style': 'open-street-map',  # Використовуємо відкрите джерело
    'center': {
        'lat': 49.2328,
        'lon': 28.4810
    },
    'zoom': 12,
    'height': 600
}

# Кольорова схема для різних елементів
COLOR_SCHEME = {
    'base_stations': {
        'Київстар': '#0066CC',
        'Vodafone': '#CC0000',
        'lifecell': '#00CC66'
    },
    'signal_quality': {
        'excellent': '#00FF00',  # > -70 дБм
        'good': '#FFFF00',       # -70 до -85 дБм
        'fair': '#FFA500',       # -85 до -100 дБм
        'poor': '#FF0000',       # < -100 дБм
        'no_signal': '#808080'   # Немає сигналу
    },
    'handover_types': {
        'successful': '#00FF00',
        'failed': '#FF0000',
        'pingpong': '#FF8800'
    },
    'coverage_areas': {
        'primary': 'rgba(100, 150, 255, 0.3)',
        'secondary': 'rgba(100, 150, 255, 0.2)',
        'overlap': 'rgba(255, 100, 100, 0.3)'
    }
}

# Іконки для карти
MAP_ICONS = {
    'base_station': {
        'symbol': 'communications-tower',
        'size': 15,
        'color': '#000000'
    },
    'user_equipment': {
        'smartphone': {'symbol': 'mobile-phone', 'size': 8},
        'tablet': {'symbol': 'tablet', 'size': 10},
        'laptop': {'symbol': 'computer', 'size': 12},
        'car': {'symbol': 'car', 'size': 10},
        'iot': {'symbol': 'circle', 'size': 6}
    }
}

# Стилі ліній для траєкторій та зв'язків
LINE_STYLES = {
    'user_trajectory': {
        'color': '#0066FF',
        'width': 2,
        'dash': 'solid'
    },
    'handover_connection': {
        'color': '#FF6600',
        'width': 3,
        'dash': 'dash'
    },
    'coverage_boundary': {
        'color': '#888888',
        'width': 1,
        'dash': 'dot'
    }
}
