import numpy as np
from datetime import datetime
from typing import Dict, List, Set
import uuid

class BaseStation:
    """Клас для представлення базової станції eNodeB"""
    
    def __init__(self, bs_id: str, name: str, latitude: float, longitude: float,
                 power_dbm: float = 43, frequency_mhz: float = 1800,
                 operator: str = "Unknown", max_users: int = 100):
        self.bs_id = bs_id
        self.name = name
        self.latitude = latitude
        self.longitude = longitude
        self.power_dbm = power_dbm
        self.frequency_mhz = frequency_mhz
        self.operator = operator
        self.max_users = max_users
        
        # Поточний стан
        self.connected_users: Set[str] = set()
        self.load_percentage = 0.0
        self.throughput_mbps = 0.0
        self.interference_level = 0.0
        
        # Статистика
        self.total_handovers_in = 0
        self.total_handovers_out = 0
        self.uptime_hours = 0.0
        self.creation_time = datetime.now()
        
        # Технічні параметри
        self.azimuth_angles = [0, 120, 240]  # 3 сектори
        self.antenna_gain_db = 15
        self.range_km = self._calculate_range()
        
        # Метрики якості
        self.average_rsrp = -85.0
        self.average_rsrq = -12.0
        self.packet_loss_rate = 0.01
        
    def _calculate_range(self) -> float:
        """Розрахунок теоретичної дальності покриття"""
        # Спрощена формула на основі потужності та частоти
        if self.frequency_mhz <= 1000:
            return min(5.0, self.power_dbm / 20)
        else:
            return min(3.0, self.power_dbm / 25)
    
    def add_user(self, ue_id: str) -> bool:
        """Додавання користувача до базової станції"""
        if len(self.connected_users) >= self.max_users:
            return False
        
        self.connected_users.add(ue_id)
        self.update_load()
        return True
    
    def remove_user(self, ue_id: str) -> bool:
        """Видалення користувача з базової станції"""
        if ue_id in self.connected_users:
            self.connected_users.remove(ue_id)
            self.update_load()
            return True
        return False
    
    def update_load(self):
        """Оновлення навантаження базової станції"""
        user_count = len(self.connected_users)
        self.load_percentage = min(100.0, (user_count / self.max_users) * 100)
        
        # Симуляція впливу навантаження на throughput
        if user_count == 0:
            self.throughput_mbps = 0.0
        else:
            base_throughput = 100.0  # Мбіт/с
            load_factor = max(0.1, 1.0 - (self.load_percentage / 100) * 0.7)
            self.throughput_mbps = base_throughput * load_factor
        
        # Оновлення інтерференції
        self.interference_level = min(10.0, self.load_percentage / 10)
    
    def is_overloaded(self, threshold: float = 90.0) -> bool:
        """Перевірка перевантаження базової станції"""
        return self.load_percentage >= threshold
    
    def get_sector_for_azimuth(self, azimuth: float) -> int:
        """Визначення сектора для заданого азимута"""
        normalized_azimuth = azimuth % 360
        
        for i, sector_azimuth in enumerate(self.azimuth_angles):
            angle_diff = abs(normalized_azimuth - sector_azimuth)
            if angle_diff <= 60 or angle_diff >= 300:  # ±60° для кожного сектора
                return i
        
        return 0  # За замовчуванням перший сектор
    
    def calculate_antenna_gain(self, azimuth: float) -> float:
        """Розрахунок посилення антени для заданого напряму"""
        sector = self.get_sector_for_azimuth(azimuth)
        sector_azimuth = self.azimuth_angles[sector]
        
        angle_diff = abs(azimuth - sector_azimuth)
        if angle_diff > 180:
            angle_diff = 360 - angle_diff
        
        # Діаграма спрямованості антени (спрощена модель)
        if angle_diff <= 30:  # Головний промінь
            return self.antenna_gain_db
        elif angle_diff <= 60:  # Бічні променя
            return self.antenna_gain_db - 3
        else:  # Задні променя
            return self.antenna_gain_db - 20
    
    def get_quality_metrics(self) -> Dict:
        """Отримання метрик якості обслуговування"""
        # Симуляція метрик на основі навантаження
        base_rsrp = -70.0
        base_rsrq = -8.0
        base_loss = 0.001
        
        load_impact = self.load_percentage / 100
        
        return {
            'average_rsrp': base_rsrp - (load_impact * 15),
            'average_rsrq': base_rsrq - (load_impact * 5),
            'packet_loss_rate': base_loss + (load_impact * 0.02),
            'average_latency_ms': 10 + (load_impact * 40),
            'jitter_ms': 1 + (load_impact * 5)
        }
    
    def update_metrics(self):
        """Оновлення всіх метрик базової станції"""
        self.update_load()
        
        # Оновлення часу роботи
        uptime_delta = (datetime.now() - self.creation_time).total_seconds() / 3600
        self.uptime_hours = uptime_delta
        
        # Оновлення метрик якості
        quality_metrics = self.get_quality_metrics()
        self.average_rsrp = quality_metrics['average_rsrp']
        self.average_rsrq = quality_metrics['average_rsrq']
        self.packet_loss_rate = quality_metrics['packet_loss_rate']
    
    def simulate_failure(self, failure_type: str = "temporary") -> bool:
        """Симуляція відмови базової станції"""
        if failure_type == "temporary":
            # Тимчасова відмова - всі користувачі втрачають зв'язок
            self.connected_users.clear()
            self.load_percentage = 0.0
            self.throughput_mbps = 0.0
            return True
        elif failure_type == "overload":
            # Перевантаження - не приймає нових користувачів
            return self.is_overloaded()
        
        return False
    
    def get_coverage_info(self) -> Dict:
        """Інформація про зону покриття"""
        return {
            'center_lat': self.latitude,
            'center_lon': self.longitude,
            'range_km': self.range_km,
            'sectors': len(self.azimuth_angles),
            'sector_angles': self.azimuth_angles,
            'antenna_gain_db': self.antenna_gain_db
        }
    
    def reset(self):
        """Скидання стану базової станції"""
        self.connected_users.clear()
        self.load_percentage = 0.0
        self.throughput_mbps = 0.0
        self.interference_level = 0.0
        self.total_handovers_in = 0
        self.total_handovers_out = 0
        self.creation_time = datetime.now()
    
    def get_state(self) -> Dict:
        """Отримання повного стану базової станції"""
        return {
            'bs_id': self.bs_id,
            'name': self.name,
            'latitude': self.latitude,
            'longitude': self.longitude,
            'power_dbm': self.power_dbm,
            'frequency_mhz': self.frequency_mhz,
            'operator': self.operator,
            'connected_users': len(self.connected_users),
            'max_users': self.max_users,
            'load_percentage': self.load_percentage,
            'throughput_mbps': self.throughput_mbps,
            'interference_level': self.interference_level,
            'average_rsrp': self.average_rsrp,
            'average_rsrq': self.average_rsrq,
            'packet_loss_rate': self.packet_loss_rate,
            'range_km': self.range_km,
            'uptime_hours': self.uptime_hours,
            'is_overloaded': self.is_overloaded(),
            'total_handovers_in': self.total_handovers_in,
            'total_handovers_out': self.total_handovers_out
        }
    
    def __str__(self):
        return (f"BaseStation(id={self.bs_id}, name={self.name}, "
                f"users={len(self.connected_users)}/{self.max_users}, "
                f"load={self.load_percentage:.1f}%)")
    
    def __repr__(self):
        return self.__str__()
 