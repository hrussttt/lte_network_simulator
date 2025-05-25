import numpy as np
import random
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple
import uuid

class UserEquipment:
    """Клас для представлення користувацького обладнання (UE)"""
    
    def __init__(self, ue_id: str, latitude: float, longitude: float,
                 speed_kmh: float = 20, direction: float = 0,
                 device_type: str = "smartphone"):
        self.ue_id = ue_id
        self.latitude = latitude
        self.longitude = longitude
        self.speed_kmh = speed_kmh
        self.direction = direction  # градуси (0-360)
        self.device_type = device_type
        
        # Поточний стан з'єднання
        self.serving_bs: Optional[str] = None
        self.rsrp = -85.0  # дБм
        self.rsrq = -12.0  # дБ
        self.sinr = 10.0   # дБ
        self.throughput = 0.0  # Мбіт/с
        
        # Стан активності
        self.active = True
        self.connected = False
        self.last_update = datetime.now()
        
        # Історія хендоверів
        self.handover_count = 0
        self.last_handover: Optional[datetime] = None
        self.handover_history = []
        
        # Параметри руху
        self.movement_pattern = "random"  # random, linear, circular
        self.target_location: Optional[Tuple[float, float]] = None
        self.path_points = []
        
        # Характеристики пристрою
        self.device_category = self._determine_device_category()
        self.max_throughput = self._get_max_throughput()
        self.power_class = self._get_power_class()
        
        # QoS параметри
        self.qci = 9  # QoS Class Identifier (9 = default bearer)
        self.priority = 9
        self.packet_delay_budget = 300  # мс
        self.packet_error_loss_rate = 0.01
        
        # Статистика
        self.total_data_mb = 0.0
        self.session_duration = 0.0
        self.connection_drops = 0
        
    def _determine_device_category(self) -> int:
        """Визначення категорії пристрою LTE"""
        device_categories = {
            "smartphone": random.choice([4, 6, 9, 12]),
            "tablet": random.choice([6, 9, 12]),
            "laptop": random.choice([9, 12, 16]),
            "iot_device": random.choice([1, 4]),
            "car": random.choice([12, 16])
        }
        return device_categories.get(self.device_type, 4)
    
    def _get_max_throughput(self) -> float:
        """Максимальна пропускна здатність на основі категорії"""
        category_throughput = {
            1: 10,    # Мбіт/с
            4: 150,
            6: 300,
            9: 450,
            12: 600,
            16: 979
        }
        return category_throughput.get(self.device_category, 150)
    
    def _get_power_class(self) -> int:
        """Клас потужності пристрою"""
        if self.device_type in ["smartphone", "tablet"]:
            return 3  # 23 дБм
        elif self.device_type in ["laptop", "car"]:
            return 2  # 26 дБм  
        else:
            return 3
    
    def update_position(self, delta_time: float):
        """Оновлення позиції користувача"""
        if not self.active or self.speed_kmh == 0:
            return
        
        # Конвертація швидкості в м/с
        speed_ms = self.speed_kmh * 1000 / 3600
        distance_m = speed_ms * delta_time
        
        # Конвертація в градуси (приблизно)
        lat_change = (distance_m * np.cos(np.radians(self.direction))) / 111111
        lon_change = (distance_m * np.sin(np.radians(self.direction))) / \
                     (111111 * np.cos(np.radians(self.latitude)))
        
        self.latitude += lat_change
        self.longitude += lon_change
        
        # Обмеження координат (для Вінниці)
        self.latitude = np.clip(self.latitude, 49.20, 49.27)
        self.longitude = np.clip(self.longitude, 28.42, 28.55)
        
        # Випадкова зміна напряму (5% ймовірність)
        if random.random() < 0.05:
            self.direction = random.uniform(0, 360)
        
        self.last_update = datetime.now()
    
    def set_movement_pattern(self, pattern: str, **kwargs):
        """Встановлення шаблону руху"""
        self.movement_pattern = pattern
        
        if pattern == "linear":
            self.target_location = kwargs.get('target', None)
        elif pattern == "circular":
            center = kwargs.get('center', (self.latitude, self.longitude))
            radius = kwargs.get('radius', 0.01)  # в градусах
            self._generate_circular_path(center, radius)
        elif pattern == "predefined":
            self.path_points = kwargs.get('path_points', [])
    
    def _generate_circular_path(self, center: Tuple[float, float], radius: float):
        """Генерація кругового маршруту"""
        points = []
        for angle in range(0, 360, 10):
            lat = center[0] + radius * np.cos(np.radians(angle))
            lon = center[1] + radius * np.sin(np.radians(angle))
            points.append((lat, lon))
        self.path_points = points
    
    def update_signal_quality(self, rsrp: float, rsrq: float, sinr: float = None):
        """Оновлення параметрів якості сигналу"""
        self.rsrp = rsrp
        self.rsrq = rsrq
        if sinr is not None:
            self.sinr = sinr
        
        # Розрахунок пропускної здатності на основі SINR
        self.throughput = self._calculate_throughput()
        
        # Оновлення статусу з'єднання
        self.connected = self.rsrp > -110  # мінімальний поріг
    
    def _calculate_throughput(self) -> float:
        """Розрахунок поточної пропускної здатності"""
        if not self.connected or self.rsrp < -110:
            return 0.0
        
        # Спрощена модель на основі SINR
        if self.sinr >= 20:
            efficiency = 0.9
        elif self.sinr >= 10:
            efficiency = 0.7
        elif self.sinr >= 0:
            efficiency = 0.4
        else:
            efficiency = 0.1
        
        # Урахування навантаження та інтерференції
        base_throughput = self.max_throughput * efficiency
        
        # Випадкові флуктуації
        variation = random.uniform(0.8, 1.2)
        
        return min(self.max_throughput, base_throughput * variation)
    
    def execute_handover(self, old_bs: str, new_bs: str, old_rsrp: float, new_rsrp: float):
        """Виконання хендовера"""
        handover_event = {
            'timestamp': datetime.now(),
            'old_bs': old_bs,
            'new_bs': new_bs,
            'old_rsrp': old_rsrp,
            'new_rsrp': new_rsrp,
            'improvement': new_rsrp - old_rsrp,
            'success': new_rsrp > old_rsrp
        }
        
        self.handover_history.append(handover_event)
        self.handover_count += 1
        self.last_handover = datetime.now()
        self.serving_bs = new_bs
        
        return handover_event
    
    def get_mobility_state(self) -> str:
        """Визначення стану мобільності"""
        if self.speed_kmh <= 15:
            return "stationary"
        elif self.speed_kmh <= 50:
            return "normal_mobility"
        elif self.speed_kmh <= 120:
            return "high_mobility"
        else:
            return "very_high_mobility"
    
    def simulate_data_usage(self, delta_time: float):
        """Симуляція використання даних"""
        if not self.connected or self.throughput <= 0:
            return
        
        # Базове використання даних залежно від типу пристрою
        usage_patterns = {
            "smartphone": 0.1,  # МБ/с
            "tablet": 0.2,
            "laptop": 0.5,
            "iot_device": 0.001,
            "car": 0.05
        }
        
        base_usage = usage_patterns.get(self.device_type, 0.1)
        actual_usage = min(base_usage, self.throughput / 8)  # конвертація в МБ/с
        
        self.total_data_mb += actual_usage * delta_time
        self.session_duration += delta_time
    
    def get_qos_requirements(self) -> Dict:
        """Отримання вимог QoS для даного пристрою"""
        qos_profiles = {
            "smartphone": {"qci": 9, "priority": 9, "delay": 300, "loss": 0.01},
            "tablet": {"qci": 9, "priority": 8, "delay": 300, "loss": 0.01},
            "laptop": {"qci": 8, "priority": 7, "delay": 300, "loss": 0.01},
            "iot_device": {"qci": 9, "priority": 9, "delay": 1000, "loss": 0.1},
            "car": {"qci": 4, "priority": 5, "delay": 50, "loss": 0.001}
        }
        
        return qos_profiles.get(self.device_type, qos_profiles["smartphone"])
    
    def check_qos_violation(self) -> Dict:
        """Перевірка порушення QoS"""
        requirements = self.get_qos_requirements()
        
        current_delay = 50 if self.connected else 999  # спрощена модель
        current_loss = self.packet_error_loss_rate
        
        violations = {
            'delay_violation': current_delay > requirements['delay'],
            'loss_violation': current_loss > requirements['loss'],
            'throughput_violation': self.throughput < (self.max_throughput * 0.1),
            'connectivity_violation': not self.connected
        }
        
        return violations
    
    def reset(self):
        """Скидання стану користувача"""
        self.serving_bs = None
        self.rsrp = -85.0
        self.rsrq = -12.0
        self.throughput = 0.0
        self.connected = False
        self.handover_count = 0
        self.last_handover = None
        self.handover_history.clear()
        self.total_data_mb = 0.0
        self.session_duration = 0.0
        self.connection_drops = 0
    
    def get_state(self) -> Dict:
        """Отримання повного стану користувача"""
        return {
            'ue_id': self.ue_id,
            'latitude': self.latitude,
            'longitude': self.longitude,
            'speed_kmh': self.speed_kmh,
            'direction': self.direction,
            'device_type': self.device_type,
            'device_category': self.device_category,
            'serving_bs': self.serving_bs,
            'rsrp': self.rsrp,
            'rsrq': self.rsrq,
            'sinr': self.sinr,
            'throughput': self.throughput,
            'active': self.active,
            'connected': self.connected,
            'handover_count': self.handover_count,
            'last_handover': self.last_handover.isoformat() if self.last_handover else None,
            'mobility_state': self.get_mobility_state(),
            'total_data_mb': self.total_data_mb,
            'session_duration': self.session_duration,
            'qos_violations': self.check_qos_violation()
        }
    
    def __str__(self):
        return (f"UE(id={self.ue_id}, pos=({self.latitude:.4f},{self.longitude:.4f}), "
                f"speed={self.speed_kmh}km/h, rsrp={self.rsrp:.1f}dBm, "
                f"serving={self.serving_bs})")
