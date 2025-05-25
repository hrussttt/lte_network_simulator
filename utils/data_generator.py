import numpy as np
import random
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
from geopy.distance import geodesic
import uuid

class LTEDataGenerator:
    """Генератор даних для симуляції LTE мережі"""
    
    def __init__(self, city_bounds: Dict[str, Tuple[float, float]] = None):
        if city_bounds is None:
            # За замовчуванням - межі Вінниці
            self.city_bounds = {
                'lat_min': 49.20,
                'lat_max': 49.27,
                'lon_min': 28.42,
                'lon_max': 28.55
            }
        else:
            self.city_bounds = city_bounds
        
        # Профілі користувачів
        self.user_profiles = {
            'pedestrian': {'speed_range': (3, 8), 'device_types': ['smartphone', 'tablet']},
            'cyclist': {'speed_range': (10, 25), 'device_types': ['smartphone']},
            'car': {'speed_range': (30, 80), 'device_types': ['smartphone', 'car']},
            'public_transport': {'speed_range': (20, 60), 'device_types': ['smartphone', 'tablet']},
            'high_speed': {'speed_range': (80, 150), 'device_types': ['smartphone', 'laptop']}
        }
        
        # Оператори та їх характеристики
        self.operators = {
            'Київстар': {'color': 'blue', 'frequency_bands': [900, 1800, 2600]},
            'Vodafone': {'color': 'red', 'frequency_bands': [900, 1800, 2600]},
            'lifecell': {'color': 'green', 'frequency_bands': [900, 1800, 2100]}
        }
    
    def generate_base_stations(self, count: int = 6, 
                             operators: Optional[List[str]] = None) -> List[Dict]:
        """Генерація базових станцій"""
        if operators is None:
            operators = list(self.operators.keys())
        
        base_stations = []
        
        # Предвизначені локації для реалістичності (основні райони Вінниці)
        predefined_locations = [
            {'name': 'Центр (Соборна)', 'lat': 49.2328, 'lon': 28.4810},
            {'name': 'Вишенька', 'lat': 49.2510, 'lon': 28.4590},
            {'name': 'Замостя', 'lat': 49.2180, 'lon': 28.5120},
            {'name': 'Пирогово', 'lat': 49.2450, 'lon': 28.5280},
            {'name': 'Старе місто', 'lat': 49.2290, 'lon': 28.4650},
            {'name': 'Військове містечко', 'lat': 49.2150, 'lon': 28.4420},
            {'name': 'Електромережа', 'lat': 49.2380, 'lon': 28.5050},
            {'name': 'Тяжилів', 'lat': 49.2200, 'lon': 28.4900}
        ]
        
        for i in range(min(count, len(predefined_locations))):
            location = predefined_locations[i]
            operator = operators[i % len(operators)]
            operator_info = self.operators[operator]
            
            bs = {
                'id': f'eNodeB_{i+1:03d}',
                'name': location['name'],
                'lat': location['lat'],
                'lon': location['lon'],
                'power': random.randint(38, 46),  # дБм
                'frequency': random.choice(operator_info['frequency_bands']),
                'operator': operator,
                'color': operator_info['color'],
                'range_km': random.uniform(1.5, 3.0),
                'max_users': random.randint(80, 120),
                'users': 0,
                'load': 0,
                'azimuth_angles': [0, 120, 240],  # 3 сектори
                'antenna_gain': 15,  # дБ
                'bandwidth_mhz': random.choice([10, 15, 20]),
                'technology': random.choice(['LTE', 'LTE-A', 'LTE-A Pro'])
            }
            
            base_stations.append(bs)
        
        # Якщо потрібно більше станцій, генеруємо випадкові
        for i in range(len(predefined_locations), count):
            operator = operators[i % len(operators)]
            operator_info = self.operators[operator]
            
            bs = {
                'id': f'eNodeB_{i+1:03d}',
                'name': f'БС-{i+1}',
                'lat': random.uniform(self.city_bounds['lat_min'], self.city_bounds['lat_max']),
                'lon': random.uniform(self.city_bounds['lon_min'], self.city_bounds['lon_max']),
                'power': random.randint(38, 46),
                'frequency': random.choice(operator_info['frequency_bands']),
                'operator': operator,
                'color': operator_info['color'],
                'range_km': random.uniform(1.5, 3.0),
                'max_users': random.randint(80, 120),
                'users': 0,
                'load': 0,
                'azimuth_angles': [0, 120, 240],
                'antenna_gain': 15,
                'bandwidth_mhz': random.choice([10, 15, 20]),
                'technology': random.choice(['LTE', 'LTE-A', 'LTE-A Pro'])
            }
            
            base_stations.append(bs)
        
        return base_stations
    
    def generate_users(self, count: int, base_stations: List[Dict] = None) -> List[Dict]:
        """Генерація користувачів"""
        users = []
        
        for i in range(count):
            # Вибір профілю користувача
            profile_name = random.choice(list(self.user_profiles.keys()))
            profile = self.user_profiles[profile_name]
            
            # Генерація базових параметрів
            user = {
                'id': f'UE_{i+1:03d}',
                'lat': random.uniform(self.city_bounds['lat_min'], self.city_bounds['lat_max']),
                'lon': random.uniform(self.city_bounds['lon_min'], self.city_bounds['lon_max']),
                'speed': random.uniform(*profile['speed_range']),
                'direction': random.uniform(0, 360),
                'device_type': random.choice(profile['device_types']),
                'profile': profile_name,
                'active': True,
                'connected': False,
                'serving_bs': None,
                'rsrp': -85.0,
                'rsrq': -12.0,
                'sinr': 10.0,
                'throughput': 0.0,
                'handover_count': 0,
                'last_handover': None,
                'session_start': datetime.now(),
                'total_data_mb': 0.0
            }
            
            # Додаткові характеристики на основі типу пристрою
            device_characteristics = self._get_device_characteristics(user['device_type'])
            user.update(device_characteristics)
            
            users.append(user)
        
        return users
    
    def _get_device_characteristics(self, device_type: str) -> Dict:
        """Отримання характеристик пристрою"""
        characteristics = {
            'smartphone': {
                'category': random.choice([4, 6, 9]),
                'max_throughput': random.uniform(50, 150),
                'power_class': 3,  # 23 дБм
                'battery_sensitive': True
            },
            'tablet': {
                'category': random.choice([6, 9, 12]),
                'max_throughput': random.uniform(100, 300),
                'power_class': 3,
                'battery_sensitive': True
            },
            'laptop': {
                'category': random.choice([9, 12, 16]),
                'max_throughput': random.uniform(200, 600),
                'power_class': 2,  # 26 дБм
                'battery_sensitive': False
            },
            'car': {
                'category': random.choice([12, 16]),
                'max_throughput': random.uniform(100, 400),
                'power_class': 2,
                'battery_sensitive': False
            },
            'iot_device': {
                'category': 1,
                'max_throughput': random.uniform(1, 10),
                'power_class': 3,
                'battery_sensitive': True
            }
        }
        
        return characteristics.get(device_type, characteristics['smartphone'])
    
    def generate_traffic_patterns(self, users: List[Dict], 
                                time_of_day: str = 'peak') -> List[Dict]:
        """Генерація шаблонів трафіку"""
        traffic_patterns = []
        
        # Коефіцієнти активності залежно від часу доби
        activity_multipliers = {
            'morning': 0.8,
            'peak': 1.0,
            'evening': 0.9,
            'night': 0.3,
            'weekend': 0.6
        }
        
        multiplier = activity_multipliers.get(time_of_day, 1.0)
        
        for user in users:
            # Базовий шаблон використання даних
            base_usage = self._get_base_data_usage(user['device_type'], user['profile'])
            
            # Застосування множника часу
            current_usage = base_usage * multiplier
            
            # Додавання випадковості
            usage_variation = random.uniform(0.5, 2.0)
            final_usage = current_usage * usage_variation
            
            pattern = {
                'user_id': user['id'],
                'expected_throughput': min(user['max_throughput'], final_usage),
                'session_type': random.choice(['web', 'video', 'social', 'gaming', 'voip']),
                'qos_requirements': self._get_qos_requirements(user['device_type']),
                'priority': random.randint(1, 9),
                'data_usage_mb_per_hour': final_usage / 8  # Конвертація в МБ/год
            }
            
            traffic_patterns.append(pattern)
        
        return traffic_patterns
    
    def _get_base_data_usage(self, device_type: str, profile: str) -> float:
        """Базове використання даних (Мбіт/с)"""
        # Базові значення використання даних
        base_usage = {
            'smartphone': {'pedestrian': 2, 'cyclist': 3, 'car': 5, 'public_transport': 4, 'high_speed': 8},
            'tablet': {'pedestrian': 8, 'cyclist': 10, 'car': 15, 'public_transport': 12, 'high_speed': 20},
            'laptop': {'pedestrian': 25, 'cyclist': 30, 'car': 50, 'public_transport': 40, 'high_speed': 80},
            'car': {'car': 10, 'high_speed': 15},
            'iot_device': {'pedestrian': 0.1, 'cyclist': 0.1, 'car': 0.2, 'public_transport': 0.1, 'high_speed': 0.3}
        }
        
        return base_usage.get(device_type, {}).get(profile, 5)
    
    def _get_qos_requirements(self, device_type: str) -> Dict:
        """QoS вимоги для різних типів пристроїв"""
        qos_requirements = {
            'smartphone': {'latency_ms': 50, 'jitter_ms': 10, 'loss_rate': 0.01},
            'tablet': {'latency_ms': 100, 'jitter_ms': 20, 'loss_rate': 0.02},
            'laptop': {'latency_ms': 30, 'jitter_ms': 5, 'loss_rate': 0.005},
            'car': {'latency_ms': 20, 'jitter_ms': 3, 'loss_rate': 0.001},
            'iot_device': {'latency_ms': 1000, 'jitter_ms': 100, 'loss_rate': 0.1}
        }
        
        return qos_requirements.get(device_type, qos_requirements['smartphone'])
    
    def generate_handover_scenarios(self, users: List[Dict], 
                                  base_stations: List[Dict]) -> List[Dict]:
        """Генерація сценаріїв хендовера"""
        scenarios = []
        
        for user in users:
            if not user['active']:
                continue
            
            # Імовірність хендовера залежить від швидкості
            speed = user['speed']
            if speed < 10:
                handover_probability = 0.05  # Низька мобільність
            elif speed < 50:
                handover_probability = 0.15  # Середня мобільність
            else:
                handover_probability = 0.3   # Висока мобільність
            
            if random.random() < handover_probability:
                # Генерація сценарію хендовера
                current_bs = user.get('serving_bs')
                available_bs = [bs for bs in base_stations if bs['id'] != current_bs]
                
                if available_bs:
                    target_bs = random.choice(available_bs)
                    
                    scenario = {
                        'user_id': user['id'],
                        'source_bs': current_bs,
                        'target_bs': target_bs['id'],
                        'trigger_reason': random.choice(['rsrp_threshold', 'load_balancing', 'coverage']),
                        'expected_improvement': random.uniform(3, 10),  # дБ
                        'user_speed': speed,
                        'scenario_type': self._classify_handover_scenario(user, target_bs)
                    }
                    
                    scenarios.append(scenario)
        
        return scenarios
    
    def _classify_handover_scenario(self, user: Dict, target_bs: Dict) -> str:
        """Класифікація сценарію хендовера"""
        speed = user['speed']
        
        # Розрахунок відстані до цільової БС
        distance = geodesic(
            (user['lat'], user['lon']),
            (target_bs['lat'], target_bs['lon'])
        ).kilometers
        
        if speed < 10:
            return 'low_mobility'
        elif speed < 50:
            if distance < 1:
                return 'normal_coverage'
            else:
                return 'extended_coverage'
        else:
            if distance < 0.5:
                return 'high_speed_micro'
            else:
                return 'high_speed_macro'
    
    def generate_measurement_errors(self, measurements: Dict, 
                                  error_std: float = 1.0) -> Dict:
        """Додавання метрологічних похибок до вимірювань"""
        noisy_measurements = measurements.copy()
        
        # Додавання похибки до RSRP
        if 'rsrp' in noisy_measurements:
            noise = np.random.normal(0, error_std)
            noisy_measurements['rsrp'] += noise
        
        # Додавання похибки до RSRQ
        if 'rsrq' in noisy_measurements:
            noise = np.random.normal(0, error_std * 0.5)  # Менша похибка для RSRQ
            noisy_measurements['rsrq'] += noise
        
        # Додавання похибки до інших параметрів
        for param in ['sinr', 'throughput', 'latency']:
            if param in noisy_measurements:
                if param == 'throughput':
                    # Відносна похибка для throughput
                    relative_error = np.random.normal(1, 0.02)  # 2% стандартне відхилення
                    noisy_measurements[param] *= relative_error
                elif param == 'latency':
                    # Абсолютна похибка для latency
                    noise = np.random.normal(0, 0.5)  # 0.5 мс стандартне відхилення
                    noisy_measurements[param] += noise
                else:
                    # Для інших параметрів
                    noise = np.random.normal(0, error_std * 0.3)
                    noisy_measurements[param] += noise
        
        return noisy_measurements
    
    def generate_network_events(self, network_state: Dict, 
                              event_probability: float = 0.1) -> List[Dict]:
        """Генерація мережевих подій"""
        events = []
        current_time = datetime.now()
        
        base_stations = network_state.get('base_stations', {})
        users = network_state.get('users', {})
        
        # Події базових станцій
        for bs_id, bs_data in base_stations.items():
            if random.random() < event_probability:
                event_type = random.choice([
                    'overload', 'maintenance', 'interference', 
                    'power_change', 'configuration_update'
                ])
                
                event = {
                    'timestamp': current_time,
                    'type': event_type,
                    'source': 'base_station',
                    'bs_id': bs_id,
                    'description': self._get_event_description(event_type, bs_data),
                    'severity': random.choice(['low', 'medium', 'high']),
                    'impact': self._estimate_event_impact(event_type, bs_data)
                }
                
                events.append(event)
        
        # Події користувачів
        for ue_id, ue_data in users.items():
            if random.random() < event_probability * 0.5:  # Менша ймовірність
                event_type = random.choice([
                    'poor_signal', 'high_interference', 'mobility_change',
                    'service_request', 'connection_drop'
                ])
                
                event = {
                    'timestamp': current_time,
                    'type': event_type,
                    'source': 'user_equipment',
                    'ue_id': ue_id,
                    'description': self._get_event_description(event_type, ue_data),
                    'severity': random.choice(['low', 'medium']),
                    'impact': self._estimate_event_impact(event_type, ue_data)
                }
                
                events.append(event)
        
        return events
    
    def _get_event_description(self, event_type: str, entity_data: Dict) -> str:
        """Генерація опису події"""
        descriptions = {
            'overload': f"Базова станція перевантажена (навантаження: {entity_data.get('load', 0):.1f}%)",
            'maintenance': "Планове технічне обслуговування базової станції",
            'interference': f"Виявлено підвищений рівень інтерференції",
            'power_change': f"Зміна потужності передавача на {entity_data.get('power', 43)} дБм",
            'configuration_update': "Оновлення конфігурації базової станції",
            'poor_signal': f"Погіршення якості сигналу (RSRP: {entity_data.get('rsrp', -85):.1f} дБм)",
            'high_interference': "Високий рівень інтерференції для користувача",
            'mobility_change': f"Зміна мобільності користувача (швидкість: {entity_data.get('speed', 0):.1f} км/год)",
            'service_request': f"Запит на послугу з високими вимогами QoS",
            'connection_drop': "Втрата з'єднання користувача"
        }
        
        return descriptions.get(event_type, f"Подія типу {event_type}")
    
    def _estimate_event_impact(self, event_type: str, entity_data: Dict) -> Dict:
        """Оцінка впливу події"""
        impact_estimates = {
            'overload': {'affected_users': random.randint(10, 50), 'throughput_degradation': random.uniform(0.2, 0.5)},
            'maintenance': {'downtime_minutes': random.randint(30, 120), 'affected_users': random.randint(20, 100)},
            'interference': {'sinr_degradation': random.uniform(3, 8), 'affected_area_km2': random.uniform(0.5, 2.0)},
            'power_change': {'coverage_change_percent': random.uniform(-10, 15)},
            'configuration_update': {'optimization_improvement': random.uniform(5, 20)},
            'poor_signal': {'throughput_loss_percent': random.uniform(20, 80)},
            'high_interference': {'call_drop_probability': random.uniform(0.05, 0.2)},
            'mobility_change': {'handover_frequency_change': random.uniform(-0.5, 2.0)},
            'service_request': {'additional_bandwidth_mbps': random.uniform(5, 50)},
            'connection_drop': {'reconnection_delay_seconds': random.uniform(1, 10)}
        }
        
        return impact_estimates.get(event_type, {})
