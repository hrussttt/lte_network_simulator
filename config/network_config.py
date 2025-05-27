"""
Конфігурація мережі LTE для м. Вінниця
Реальні координати базових станцій та параметри мережі
"""

# Базові станції LTE в м. Вінниця
VINNYTSIA_BASE_STATIONS = [
    {
        'id': 'eNodeB_001',
        'name': 'Центр (Соборна)',
        'lat': 49.2328,
        'lon': 28.4810,
        'power': 43,  # дБм
        'frequency': 1800,  # МГц
        'operator': 'Київстар',
        'color': '#0066CC',
        'max_users': 100,
        'bandwidth_mhz': 20,
        'antenna_gain': 15,
        'antenna_height': 30,
        'sector_count': 3,
        'azimuth_angles': [0, 120, 240]
    },
    {
        'id': 'eNodeB_002',
        'name': 'Вишенька',
        'lat': 49.2510,
        'lon': 28.4590,
        'power': 40,
        'frequency': 2600,
        'operator': 'Vodafone',
        'color': '#CC0000',
        'max_users': 90,
        'bandwidth_mhz': 15,
        'antenna_gain': 15,
        'antenna_height': 25,
        'sector_count': 3,
        'azimuth_angles': [0, 120, 240]
    },
    {
        'id': 'eNodeB_003',
        'name': 'Замостя',
        'lat': 49.2180,
        'lon': 28.5120,
        'power': 41,
        'frequency': 1800,
        'operator': 'lifecell',
        'color': '#00CC66',
        'max_users': 95,
        'bandwidth_mhz': 20,
        'antenna_gain': 15,
        'antenna_height': 28,
        'sector_count': 3,
        'azimuth_angles': [0, 120, 240]
    },
    {
        'id': 'eNodeB_004',
        'name': 'Пирогово',
        'lat': 49.2450,
        'lon': 28.5280,
        'power': 38,
        'frequency': 2600,
        'operator': 'Київстар',
        'color': '#0066CC',
        'max_users': 85,
        'bandwidth_mhz': 15,
        'antenna_gain': 15,
        'antenna_height': 22,
        'sector_count': 3,
        'azimuth_angles': [30, 150, 270]
    },
    {
        'id': 'eNodeB_005',
        'name': 'Старе місто',
        'lat': 49.2290,
        'lon': 28.4650,
        'power': 42,
        'frequency': 900,
        'operator': 'Vodafone',
        'color': '#CC0000',
        'max_users': 110,
        'bandwidth_mhz': 10,
        'antenna_gain': 15,
        'antenna_height': 35,
        'sector_count': 3,
        'azimuth_angles': [0, 120, 240]
    },
    {
        'id': 'eNodeB_006',
        'name': 'Військове містечко',
        'lat': 49.2150,
        'lon': 28.4420,
        'power': 39,
        'frequency': 1800,
        'operator': 'lifecell',
        'color': '#00CC66',
        'max_users': 80,
        'bandwidth_mhz': 15,
        'antenna_gain': 15,
        'antenna_height': 20,
        'sector_count': 3,
        'azimuth_angles': [60, 180, 300]
    }
]

# Параметри мережі
NETWORK_PARAMETERS = {
    'handover': {
        'default_ttt': 280,  # мс
        'default_hyst': 4.0,  # дБ
        'default_offset': 0.0,  # дБ
        'measurement_gap': 40,  # мс
        'min_trigger_count': 3
    },
    'metrology': {
        'rsrp_accuracy': 1.0,  # дБ (±1σ)
        'rsrq_accuracy': 0.5,  # дБ (±1σ)
        'calibration_uncertainty': 0.5,  # дБ
        'temperature_coefficient': 0.02,  # дБ/°C
        'aging_drift': 0.1  # дБ/рік
    },
    'propagation': {
        'model': 'COST_HATA_URBAN',
        'environment': 'urban',
        'clutter_height': 15,  # м
        'building_density': 0.7
    },
    'simulation': {
        'time_step': 1.0,  # секунди
        'max_users': 50,
        'auto_handover': True,
        'real_time_update': True
    }
}

# Межі міста Вінниця
VINNYTSIA_BOUNDS = {
    'lat_min': 49.20,
    'lat_max': 49.27,
    'lon_min': 28.42,
    'lon_max': 28.55,
    'center_lat': 49.2328,
    'center_lon': 28.4810
}

# Оператори мобільного зв'язку
OPERATORS = {
    'Київстар': {
        'color': '#0066CC',
        'frequency_bands': [900, 1800, 2600],
        'technology': ['LTE', 'LTE-A', 'LTE-A Pro'],
        'market_share': 0.45
    },
    'Vodafone': {
        'color': '#CC0000',
        'frequency_bands': [900, 1800, 2600],
        'technology': ['LTE', 'LTE-A'],
        'market_share': 0.30
    },
    'lifecell': {
        'color': '#00CC66',
        'frequency_bands': [900, 1800, 2100],
        'technology': ['LTE', 'LTE-A'],
        'market_share': 0.25
    }
}

# QoS профілі
QOS_PROFILES = {
    'voice': {
        'qci': 1,
        'priority': 2,
        'packet_delay_budget': 100,  # мс
        'packet_error_loss_rate': 0.01
    },
    'video': {
        'qci': 2,
        'priority': 4,
        'packet_delay_budget': 150,
        'packet_error_loss_rate': 0.01
    },
    'data': {
        'qci': 9,
        'priority': 9,
        'packet_delay_budget': 300,
        'packet_error_loss_rate': 0.01
    },
    'iot': {
        'qci': 9,
        'priority': 8,
        'packet_delay_budget': 1000,
        'packet_error_loss_rate': 0.1
    }
}
