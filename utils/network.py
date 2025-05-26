import numpy as np
from geopy.distance import geodesic
import random
from datetime import datetime

class VinnytsiaLTENetwork:
    """Клас для моделювання мережі LTE у м. Вінниця"""
    
    def __init__(self):
        # Базові станції в різних районах Вінниці (реальні координати)
        self.base_stations = {
            'eNodeB_001': {
                'name': 'Центр (Соборна)',
                'lat': 49.2328,
                'lon': 28.4810,
                'power': 43,  # дБм
                'frequency': 1800,  # МГц
                'operator': 'Київстар',
                'color': 'blue',
                'users': 0,
                'load': 0,
                'range_km': 2.5
            },
            'eNodeB_002': {
                'name': 'Вишенька',
                'lat': 49.2510,
                'lon': 28.4590,
                'power': 40,
                'frequency': 2600,
                'operator': 'Vodafone',
                'color': 'red',
                'users': 0,
                'load': 0,
                'range_km': 1.8
            },
            'eNodeB_003': {
                'name': 'Замостя',
                'lat': 49.2180,
                'lon': 28.5120,
                'power': 41,
                'frequency': 1800,
                'operator': 'lifecell',
                'color': 'green',
                'users': 0,
                'load': 0,
                'range_km': 2.2
            },
            'eNodeB_004': {
                'name': 'Пирогово',
                'lat': 49.2450,
                'lon': 28.5280,
                'power': 38,
                'frequency': 2600,
                'operator': 'Київстар',
                'color': 'blue',
                'users': 0,
                'load': 0,
                'range_km': 1.5
            },
            'eNodeB_005': {
                'name': 'Старе місто',
                'lat': 49.2290,
                'lon': 28.4650,
                'power': 42,
                'frequency': 900,
                'operator': 'Vodafone',
                'color': 'red',
                'users': 0,
                'load': 0,
                'range_km': 3.0
            },
            'eNodeB_006': {
                'name': 'Військове містечко',
                'lat': 49.2150,
                'lon': 28.4420,
                'power': 39,
                'frequency': 1800,
                'operator': 'lifecell',
                'color': 'green',
                'users': 0,
                'load': 0,
                'range_km': 2.0
            }
        }
    
    def calculate_rsrp(self, ue_lat, ue_lon, bs_id, metrology_error=1.0, calibration_factor=1.0):
        """Розрахунок RSRP з урахуванням метрологічної похибки (згідно з роботою)"""
        bs = self.base_stations[bs_id]
        
        # Відстань між UE та базовою станцією
        distance_km = geodesic((ue_lat, ue_lon), (bs['lat'], bs['lon'])).kilometers
        
        # Модель затухання COST-Hata для міської місцевості (з роботи)
        frequency = bs['frequency']
        
        if frequency <= 1000:  # 900 МГц
            path_loss = (69.55 + 26.16*np.log10(frequency) - 
                        13.82*np.log10(30) + 
                        (44.9 - 6.55*np.log10(30))*np.log10(distance_km + 0.001))
        else:  # 1800/2600 МГц
            path_loss = (46.3 + 33.9*np.log10(frequency) - 
                        13.82*np.log10(30) + 
                        (44.9 - 6.55*np.log10(30))*np.log10(distance_km + 0.001) + 3)
        
        # RSRP = Потужність передачі - Втрати + Gain антени
        rsrp = bs['power'] - path_loss + 15  # 15 dB antenna gain
        
        # Додавання метрологічної похибки ±1 дБ (з роботи)
        rsrp = rsrp * calibration_factor + np.random.normal(0, metrology_error)
        
        # Додавання випадкового федингу (Rayleigh fading)
        fading = np.random.normal(0, 4)
        rsrp += fading
        
        # Обмеження реалістичними значеннями
        return max(-120, min(-40, rsrp))
    
    def calculate_rsrq(self, rsrp, interference_level=5):
        """Розрахунок RSRQ на основі RSRP та рівня інтерференції"""
        # RSRQ = RSRP - RSSI (спрощена модель)
        rssi = rsrp + np.random.uniform(0, interference_level)
        rsrq = rsrp - rssi
        return max(-20, min(-3, rsrq))
    
    def get_best_server(self, ue_lat, ue_lon, metrology_error=1.0, calibration_factor=1.0):
        """Знаходження базової станції з найкращим сигналом"""
        best_bs = None
        best_rsrp = -999
        
        for bs_id in self.base_stations.keys():
            rsrp = self.calculate_rsrp(ue_lat, ue_lon, bs_id, metrology_error, calibration_factor)
            if rsrp > best_rsrp:
                best_rsrp = rsrp
                best_bs = bs_id
                
        return best_bs, best_rsrp
    
    def update_load(self, bs_id, users_count):
        """Оновлення навантаження базової станції"""
        if bs_id in self.base_stations:
            self.base_stations[bs_id]['users'] = users_count
            # Припустимо максимум 100 користувачів на BS
            self.base_stations[bs_id]['load'] = min(100, (users_count / 100) * 100)
