import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from geopy.distance import geodesic
import random
from typing import Dict, List, Tuple, Optional
import time

class LTENetworkEngine:
    """Основний движок симуляції LTE мережі"""
    
    def __init__(self):
        self.base_stations = {}
        self.users = {}
        self.handover_events = []
        self.network_metrics = {}
        self.simulation_running = False
        self.simulation_time = 0.0
        self.time_step = 1.0  # секунди
        
    def initialize_network(self, base_stations_config: List[Dict]) -> bool:
        """Ініціалізація мережі з базовими станціями"""
        try:
            for bs_config in base_stations_config:
                self.add_base_station(bs_config)
            
            self.network_metrics = {
                'total_handovers': 0,
                'successful_handovers': 0,
                'failed_handovers': 0,
                'pingpong_handovers': 0,
                'average_rsrp': -85.0,
                'network_throughput': 0.0,
                'active_users': 0,
                'last_update': datetime.now()
            }
            
            return True
        except Exception as e:
            print(f"Помилка ініціалізації мережі: {e}")
            return False
    
    def add_base_station(self, config: Dict) -> bool:
        """Додавання базової станції"""
        from .base_station import BaseStation
        
        try:
            bs = BaseStation(
                bs_id=config['id'],
                name=config['name'],
                latitude=config['lat'],
                longitude=config['lon'],
                power_dbm=config['power'],
                frequency_mhz=config.get('frequency', 1800),
                operator=config.get('operator', 'Unknown'),
                max_users=config.get('max_users', 100)
            )
            
            self.base_stations[config['id']] = bs
            return True
        except Exception as e:
            print(f"Помилка додавання BS {config.get('id', 'Unknown')}: {e}")
            return False
    
    def add_user(self, user_config: Dict) -> bool:
        """Додавання користувача"""
        from .user_equipment import UserEquipment
        
        try:
            ue = UserEquipment(
                ue_id=user_config['id'],
                latitude=user_config['lat'],
                longitude=user_config['lon'],
                speed_kmh=user_config.get('speed', 20),
                direction=user_config.get('direction', random.uniform(0, 360)),
                device_type=user_config.get('device_type', 'smartphone')
            )
            
            # Знаходження найкращої базової станції
            best_bs = self.find_best_base_station(ue.latitude, ue.longitude)
            if best_bs:
                ue.serving_bs = best_bs.bs_id
                ue.rsrp = self.calculate_rsrp(ue.latitude, ue.longitude, best_bs)
                best_bs.add_user(ue.ue_id)
            
            self.users[user_config['id']] = ue
            return True
        except Exception as e:
            print(f"Помилка додавання UE {user_config.get('id', 'Unknown')}: {e}")
            return False
    
    def remove_user(self, ue_id: str) -> bool:
        """Видалення користувача"""
        try:
            if ue_id in self.users:
                ue = self.users[ue_id]
                if ue.serving_bs and ue.serving_bs in self.base_stations:
                    self.base_stations[ue.serving_bs].remove_user(ue_id)
                del self.users[ue_id]
                return True
            return False
        except Exception as e:
            print(f"Помилка видалення UE {ue_id}: {e}")
            return False
    
    def calculate_rsrp(self, ue_lat: float, ue_lon: float, base_station, 
                      metrology_error: float = 1.0) -> float:
        """Розрахунок RSRP з урахуванням метрологічної похибки"""
        # Відстань між UE та BS
        distance_km = geodesic((ue_lat, ue_lon), 
                              (base_station.latitude, base_station.longitude)).kilometers
        
        # Модель затухання COST-Hata для міської місцевості
        frequency = base_station.frequency_mhz
        
        if frequency <= 1000:  # 900 МГц
            path_loss = (69.55 + 26.16 * np.log10(frequency) - 
                        13.82 * np.log10(30) + 
                        (44.9 - 6.55 * np.log10(30)) * np.log10(distance_km + 0.001))
        else:  # 1800/2600 МГц
            path_loss = (46.3 + 33.9 * np.log10(frequency) - 
                        13.82 * np.log10(30) + 
                        (44.9 - 6.55 * np.log10(30)) * np.log10(distance_km + 0.001) + 3)
        
        # RSRP = Потужність - Втрати + Gain антени
        rsrp = base_station.power_dbm - path_loss + 15  # 15 dB antenna gain
        
        # Додавання метрологічної похибки та федингу
        rsrp += np.random.normal(0, metrology_error)
        rsrp += np.random.normal(0, 4)  # Rayleigh fading
        
        return max(-120, min(-40, rsrp))
    
    def calculate_rsrq(self, rsrp: float, interference_level: float = 5.0) -> float:
        """Розрахунок RSRQ"""
        rssi = rsrp + np.random.uniform(0, interference_level)
        rsrq = rsrp - rssi
        return max(-20, min(-3, rsrq))
    
    def find_best_base_station(self, ue_lat: float, ue_lon: float):
        """Знаходження найкращої базової станції"""
        best_bs = None
        best_rsrp = -999
        
        for bs in self.base_stations.values():
            if not bs.is_overloaded():
                rsrp = self.calculate_rsrp(ue_lat, ue_lon, bs)
                if rsrp > best_rsrp:
                    best_rsrp = rsrp
                    best_bs = bs
        
        return best_bs
    
    def step_simulation(self, delta_time: float = 1.0) -> Dict:
        """Один крок симуляції"""
        if not self.simulation_running:
            return {}
        
        self.simulation_time += delta_time
        step_events = []
        
        # Оновлення позицій користувачів
        for ue in self.users.values():
            if ue.active:
                ue.update_position(delta_time)
                
                # Перевірка хендовера
                handover_event = self.check_handover_for_user(ue)
                if handover_event:
                    step_events.append(handover_event)
        
        # Оновлення метрик базових станцій
        for bs in self.base_stations.values():
            bs.update_metrics()
        
        # Оновлення загальних метрик мережі
        self.update_network_metrics()
        
        return {
            'simulation_time': self.simulation_time,
            'events': step_events,
            'active_users': len([u for u in self.users.values() if u.active]),
            'total_handovers': self.network_metrics['total_handovers']
        }
    
    def check_handover_for_user(self, ue) -> Optional[Dict]:
        """Перевірка необхідності хендовера для користувача"""
        from .handover_algorithm import HandoverAlgorithm
        
        if not ue.serving_bs or ue.serving_bs not in self.base_stations:
            return None
        
        current_bs = self.base_stations[ue.serving_bs]
        current_rsrp = self.calculate_rsrp(ue.latitude, ue.longitude, current_bs)
        
        # Вимірювання від усіх BS
        measurements = {}
        for bs_id, bs in self.base_stations.items():
            rsrp = self.calculate_rsrp(ue.latitude, ue.longitude, bs)
            rsrq = self.calculate_rsrq(rsrp)
            measurements[bs_id] = {
                'rsrp': rsrp,
                'rsrq': rsrq,
                'distance': geodesic((ue.latitude, ue.longitude), 
                                   (bs.latitude, bs.longitude)).kilometers
            }
        
        # Оновлення RSRP поточної BS
        ue.rsrp = current_rsrp
        ue.rsrq = measurements[ue.serving_bs]['rsrq']
        
        # Перевірка хендовера
        ho_algorithm = HandoverAlgorithm()
        handover_decision = ho_algorithm.check_handover_condition(
            current_bs_id=ue.serving_bs,
            measurements=measurements,
            ttt=280,  # мс
            hyst=4,   # дБ
            offset=0  # дБ
        )
        
        if handover_decision['execute_handover']:
            return self.execute_handover(ue, handover_decision['target_bs'])
        
        return None
    
    def execute_handover(self, ue, target_bs_id: str) -> Dict:
        """Виконання хендовера"""
        if target_bs_id not in self.base_stations:
            return {'success': False, 'reason': 'Target BS not found'}
        
        old_bs_id = ue.serving_bs
        old_bs = self.base_stations[old_bs_id] if old_bs_id else None
        target_bs = self.base_stations[target_bs_id]
        
        # Перевірка доступності цільової BS
        if target_bs.is_overloaded():
            self.network_metrics['failed_handovers'] += 1
            return {
                'success': False,
                'reason': 'Target BS overloaded',
                'ue_id': ue.ue_id,
                'old_bs': old_bs_id,
                'target_bs': target_bs_id
            }
        
        # Виконання хендовера
        old_rsrp = ue.rsrp
        new_rsrp = self.calculate_rsrp(ue.latitude, ue.longitude, target_bs)
        
        # Оновлення користувача
        if old_bs:
            old_bs.remove_user(ue.ue_id)
        
        target_bs.add_user(ue.ue_id)
        ue.serving_bs = target_bs_id
        ue.rsrp = new_rsrp
        ue.handover_count += 1
        ue.last_handover = datetime.now()
        
        # Визначення типу хендовера
        improvement = new_rsrp - old_rsrp
        if improvement >= 3:
            ho_type = 'successful'
            self.network_metrics['successful_handovers'] += 1
        else:
            ho_type = 'failed'
            self.network_metrics['failed_handovers'] += 1
        
        # Перевірка ping-pong
        if ue.handover_count >= 2 and (datetime.now() - ue.last_handover).total_seconds() < 5:
            ho_type = 'pingpong'
            self.network_metrics['pingpong_handovers'] += 1
        
        self.network_metrics['total_handovers'] += 1
        
        # Створення події хендовера
        handover_event = {
            'timestamp': datetime.now(),
            'ue_id': ue.ue_id,
            'old_bs': old_bs_id,
            'new_bs': target_bs_id,
            'old_rsrp': old_rsrp,
            'new_rsrp': new_rsrp,
            'improvement': improvement,
            'type': ho_type,
            'success': True
        }
        
        self.handover_events.append(handover_event)
        
        return handover_event
    
    def update_network_metrics(self):
        """Оновлення метрик мережі"""
        active_users = [u for u in self.users.values() if u.active]
        self.network_metrics['active_users'] = len(active_users)
        
        if active_users:
            avg_rsrp = np.mean([u.rsrp for u in active_users])
            total_throughput = sum([u.throughput for u in active_users])
            
            self.network_metrics['average_rsrp'] = avg_rsrp
            self.network_metrics['network_throughput'] = total_throughput
        
        self.network_metrics['last_update'] = datetime.now()
    
    def start_simulation(self):
        """Запуск симуляції"""
        self.simulation_running = True
        self.simulation_time = 0.0
    
    def stop_simulation(self):
        """Зупинка симуляції"""
        self.simulation_running = False
    
    def reset_simulation(self):
        """Скидання симуляції"""
        self.stop_simulation()
        self.users.clear()
        self.handover_events.clear()
        for bs in self.base_stations.values():
            bs.reset()
        self.simulation_time = 0.0
    
    def get_network_state(self) -> Dict:
        """Отримання поточного стану мережі"""
        return {
            'simulation_time': self.simulation_time,
            'simulation_running': self.simulation_running,
            'base_stations': {bs_id: bs.get_state() for bs_id, bs in self.base_stations.items()},
            'users': {ue_id: ue.get_state() for ue_id, ue in self.users.items()},
            'network_metrics': self.network_metrics.copy(),
            'recent_handovers': self.handover_events[-10:] if self.handover_events else []
        }
