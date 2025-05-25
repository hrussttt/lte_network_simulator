import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass, field
import statistics
from geopy.distance import geodesic

@dataclass
class QoSMetrics:
    """Метрики якості обслуговування"""
    throughput_mbps: float = 0.0
    latency_ms: float = 0.0
    packet_loss_rate: float = 0.0
    jitter_ms: float = 0.0
    availability_percent: float = 100.0
    reliability_percent: float = 100.0

@dataclass
class HandoverMetrics:
    """Метрики хендовера"""
    total_handovers: int = 0
    successful_handovers: int = 0
    failed_handovers: int = 0
    pingpong_handovers: int = 0
    average_handover_time_ms: float = 0.0
    handover_success_rate: float = 0.0
    handover_failure_rate: float = 0.0
    pingpong_rate: float = 0.0

@dataclass
class NetworkPerformanceMetrics:
    """Загальні метрики продуктивності мережі"""
    active_users: int = 0
    total_throughput_mbps: float = 0.0
    average_rsrp_dbm: float = -85.0
    average_rsrq_db: float = -12.0
    network_efficiency_percent: float = 0.0
    spectrum_efficiency: float = 0.0
    energy_efficiency: float = 0.0

class MetricsCalculator:
    """Клас для розрахунку різних метрик мережі LTE"""
    
    def __init__(self):
        self.historical_data = []
        self.calculation_window = timedelta(minutes=5)
        
    def calculate_qos_metrics(self, users_data: Dict, time_window: Optional[timedelta] = None) -> QoSMetrics:
        """Розрахунок метрик QoS"""
        if not users_data:
            return QoSMetrics()
        
        active_users = [u for u in users_data.values() if u.get('active', False)]
        if not active_users:
            return QoSMetrics()
        
        # Розрахунок throughput
        total_throughput = sum(u.get('throughput', 0) for u in active_users)
        avg_throughput = total_throughput / len(active_users) if active_users else 0
        
        # Розрахунок latency (спрощена модель на основі RSRP)
        latencies = []
        packet_losses = []
        jitters = []
        
        for user in active_users:
            rsrp = user.get('rsrp', -85)
            
            # Модель затримки на основі якості сигналу
            if rsrp > -70:
                latency = np.random.normal(10, 2)  # Відмінний сигнал
            elif rsrp > -85:
                latency = np.random.normal(20, 5)  # Хороший сигнал
            elif rsrp > -100:
                latency = np.random.normal(50, 10)  # Задовільний сигнал
            else:
                latency = np.random.normal(100, 20)  # Поганий сигнал
            
            latencies.append(max(5, latency))
            
            # Модель втрат пакетів
            if rsrp > -85:
                loss_rate = np.random.uniform(0.001, 0.01)
            else:
                loss_rate = np.random.uniform(0.01, 0.05)
            
            packet_losses.append(loss_rate)
            
            # Модель jitter
            jitter = latency * 0.1 * np.random.uniform(0.5, 1.5)
            jitters.append(jitter)
        
        # Розрахунок доступності
        connected_users = [u for u in active_users if u.get('connected', False)]
        availability = (len(connected_users) / len(active_users) * 100) if active_users else 0
        
        return QoSMetrics(
            throughput_mbps=avg_throughput,
            latency_ms=statistics.mean(latencies) if latencies else 0,
            packet_loss_rate=statistics.mean(packet_losses) if packet_losses else 0,
            jitter_ms=statistics.mean(jitters) if jitters else 0,
            availability_percent=availability,
            reliability_percent=max(0, 100 - statistics.mean(packet_losses) * 1000) if packet_losses else 100
        )
    
    def calculate_handover_metrics(self, handover_events: List[Dict], 
                                  time_window: Optional[timedelta] = None) -> HandoverMetrics:
        """Розрахунок метрик хендовера"""
        if not handover_events:
            return HandoverMetrics()
        
        # Фільтрація за часовим вікном
        if time_window:
            cutoff_time = datetime.now() - time_window
            filtered_events = [
                event for event in handover_events
                if event.get('timestamp', datetime.now()) >= cutoff_time
            ]
        else:
            filtered_events = handover_events
        
        if not filtered_events:
            return HandoverMetrics()
        
        total = len(filtered_events)
        successful = len([e for e in filtered_events if e.get('type') == 'successful'])
        failed = len([e for e in filtered_events if e.get('type') == 'failed'])
        pingpong = len([e for e in filtered_events if e.get('type') == 'pingpong'])
        
        # Розрахунок часу хендовера
        handover_times = []
        for event in filtered_events:
            if 'elapsed_time' in event:
                handover_times.append(event['elapsed_time'])
        
        avg_handover_time = statistics.mean(handover_times) if handover_times else 0
        
        return HandoverMetrics(
            total_handovers=total,
            successful_handovers=successful,
            failed_handovers=failed,
            pingpong_handovers=pingpong,
            average_handover_time_ms=avg_handover_time,
            handover_success_rate=(successful / total * 100) if total > 0 else 0,
            handover_failure_rate=(failed / total * 100) if total > 0 else 0,
            pingpong_rate=(pingpong / total * 100) if total > 0 else 0
        )
    
    def calculate_network_performance(self, network_state: Dict) -> NetworkPerformanceMetrics:
        """Розрахунок загальних метрик продуктивності мережі"""
        users = network_state.get('users', {})
        base_stations = network_state.get('base_stations', {})
        
        active_users_list = [u for u in users.values() if u.get('active', False)]
        active_users_count = len(active_users_list)
        
        # Загальна пропускна здатність
        total_throughput = sum(u.get('throughput', 0) for u in active_users_list)
        
        # Середні RSRP та RSRQ
        if active_users_list:
            avg_rsrp = statistics.mean(u.get('rsrp', -85) for u in active_users_list)
            avg_rsrq = statistics.mean(u.get('rsrq', -12) for u in active_users_list)
        else:
            avg_rsrp = -85.0
            avg_rsrq = -12.0
        
        # Ефективність мережі
        total_capacity = sum(bs.get('throughput_mbps', 0) for bs in base_stations.values())
        network_efficiency = (total_throughput / total_capacity * 100) if total_capacity > 0 else 0
        
        # Спектральна ефективність (спрощена модель)
        total_bandwidth = sum(bs.get('bandwidth_mhz', 20) for bs in base_stations.values())
        spectrum_efficiency = (total_throughput / total_bandwidth) if total_bandwidth > 0 else 0
        
        # Енергетична ефективність (біт/Дж, спрощена модель)
        total_power = sum(bs.get('power_dbm', 43) for bs in base_stations.values())
        energy_efficiency = (total_throughput * 1e6 / total_power) if total_power > 0 else 0
        
        return NetworkPerformanceMetrics(
            active_users=active_users_count,
            total_throughput_mbps=total_throughput,
            average_rsrp_dbm=avg_rsrp,
            average_rsrq_db=avg_rsrq,
            network_efficiency_percent=network_efficiency,
            spectrum_efficiency=spectrum_efficiency,
            energy_efficiency=energy_efficiency
        )
    
    def calculate_bs_load_distribution(self, base_stations: Dict) -> Dict[str, float]:
        """Розрахунок розподілу навантаження по базових станціях"""
        load_distribution = {}
        
        for bs_id, bs_data in base_stations.items():
            load_percentage = bs_data.get('load_percentage', 0)
            load_distribution[bs_id] = load_percentage
        
        return load_distribution
    
    def calculate_interference_metrics(self, network_state: Dict) -> Dict[str, float]:
        """Розрахунок метрик інтерференції"""
        users = network_state.get('users', {})
        base_stations = network_state.get('base_stations', {})
        
        # Спрощена модель розрахунку інтерференції
        interference_levels = []
        sinr_values = []
        
        for user in users.values():
            if not user.get('active', False):
                continue
            
            serving_bs = user.get('serving_bs')
            if not serving_bs or serving_bs not in base_stations:
                continue
            
            user_lat = user.get('latitude', 0)
            user_lon = user.get('longitude', 0)
            
            # Розрахунок інтерференції від інших БС
            interference_power = 0
            serving_power = 0
            
            for bs_id, bs_data in base_stations.items():
                # Спрощений розрахунок потужності сигналу
                distance = self._calculate_distance(
                    user_lat, user_lon,
                    bs_data.get('latitude', 0), bs_data.get('longitude', 0)
                )
                
                # Модель втрат на трасі (спрощена)
                path_loss = 128.1 + 37.6 * np.log10(max(0.001, distance))
                received_power = bs_data.get('power_dbm', 43) - path_loss
                
                if bs_id == serving_bs:
                    serving_power = received_power
                else:
                    interference_power += 10**(received_power / 10)
            
            # Розрахунок SINR
            if interference_power > 0 and serving_power > -120:
                sinr = 10 * np.log10(10**(serving_power / 10) / interference_power)
                sinr_values.append(sinr)
                interference_levels.append(10 * np.log10(interference_power))
        
        # Розрахунок середніх значень
        avg_interference = statistics.mean(interference_levels) if interference_levels else -90
        avg_sinr = statistics.mean(sinr_values) if sinr_values else 10
        max_interference = max(interference_levels) if interference_levels else -90
        min_sinr = min(sinr_values) if sinr_values else 0
        
        return {
            'average_interference_dbm': avg_interference,
            'average_sinr_db': avg_sinr,
            'max_interference_dbm': max_interference,
            'min_sinr_db': min_sinr,
            'interference_limited_users': len([i for i in interference_levels if i > -80]),
            'poor_sinr_users': len([s for s in sinr_values if s < 0])
        }
    
    def _calculate_distance(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Розрахунок відстані між двома точками"""
        try:
            return geodesic((lat1, lon1), (lat2, lon2)).kilometers
        except:
            # Fallback якщо geopy не працює
            return np.sqrt((lat1 - lat2)**2 + (lon1 - lon2)**2) * 111  # приблизно км
    
    def calculate_coverage_metrics(self, network_state: Dict) -> Dict[str, Any]:
        """Розрахунок метрик покриття"""
        users = network_state.get('users', {})
        base_stations = network_state.get('base_stations', {})
        
        total_users = len([u for u in users.values() if u.get('active', False)])
        covered_users = len([u for u in users.values() 
                           if u.get('active', False) and u.get('rsrp', -120) > -110])
        
        coverage_percentage = (covered_users / total_users * 100) if total_users > 0 else 0
        
        # Аналіз якості покриття
        excellent_coverage = len([u for u in users.values() 
                                if u.get('active', False) and u.get('rsrp', -120) > -70])
        good_coverage = len([u for u in users.values() 
                           if u.get('active', False) and -85 < u.get('rsrp', -120) <= -70])
        fair_coverage = len([u for u in users.values() 
                           if u.get('active', False) and -100 < u.get('rsrp', -120) <= -85])
        poor_coverage = len([u for u in users.values() 
                           if u.get('active', False) and -110 < u.get('rsrp', -120) <= -100])
        
        return {
            'total_coverage_percent': coverage_percentage,
            'excellent_coverage_percent': (excellent_coverage / total_users * 100) if total_users > 0 else 0,
            'good_coverage_percent': (good_coverage / total_users * 100) if total_users > 0 else 0,
            'fair_coverage_percent': (fair_coverage / total_users * 100) if total_users > 0 else 0,
            'poor_coverage_percent': (poor_coverage / total_users * 100) if total_users > 0 else 0,
            'coverage_holes': total_users - covered_users,
            'average_signal_strength': statistics.mean([u.get('rsrp', -85) for u in users.values() 
                                                      if u.get('active', False)]) if total_users > 0 else -85
        }
    
    def calculate_mobility_metrics(self, users_data: Dict, handover_events: List[Dict]) -> Dict[str, float]:
        """Розрахунок метрик мобільності"""
        active_users = [u for u in users_data.values() if u.get('active', False)]
        
        if not active_users:
            return {
                'average_speed_kmh': 0,
                'high_mobility_users_percent': 0,
                'handovers_per_user': 0,
                'mobility_related_failures_percent': 0
            }
        
        # Середня швидкість користувачів
        speeds = [u.get('speed_kmh', 0) for u in active_users]
        avg_speed = statistics.mean(speeds) if speeds else 0
        
        # Високомобільні користувачі (>50 км/год)
        high_mobility_count = len([s for s in speeds if s > 50])
        high_mobility_percent = (high_mobility_count / len(active_users) * 100) if active_users else 0
        
        # Хендовери на користувача
        user_handover_counts = {}
        for event in handover_events:
            ue_id = event.get('ue_id', 'unknown')
            user_handover_counts[ue_id] = user_handover_counts.get(ue_id, 0) + 1
        
        avg_handovers_per_user = (sum(user_handover_counts.values()) / 
                                len(active_users)) if active_users else 0
        
        # Відмови пов'язані з мобільністю
        mobility_failures = len([e for e in handover_events 
                               if e.get('type') in ['failed', 'too_late']])
        mobility_failure_percent = (mobility_failures / len(handover_events) * 100) if handover_events else 0
        
        return {
            'average_speed_kmh': avg_speed,
            'high_mobility_users_percent': high_mobility_percent,
            'handovers_per_user': avg_handovers_per_user,
            'mobility_related_failures_percent': mobility_failure_percent
        }
    
    def calculate_optimization_metrics(self, optimization_results: Dict) -> Dict[str, float]:
        """Розрахунок метрик оптимізації"""
        if not optimization_results:
            return {}
        
        # Аналіз результатів оптимізації параметрів
        ttt_optimization = optimization_results.get('ttt_optimization', {})
        hyst_optimization = optimization_results.get('hyst_optimization', {})
        
        metrics = {}
        
        # Ефективність оптимізації TTT
        if 'before' in ttt_optimization and 'after' in ttt_optimization:
            before_failed = ttt_optimization['before'].get('failed_rate', 0)
            after_failed = ttt_optimization['after'].get('failed_rate', 0)
            ttt_improvement = max(0, before_failed - after_failed)
            metrics['ttt_optimization_improvement_percent'] = ttt_improvement
        
        # Ефективність оптимізації Hysteresis
        if 'before' in hyst_optimization and 'after' in hyst_optimization:
            before_pingpong = hyst_optimization['before'].get('pingpong_rate', 0)
            after_pingpong = hyst_optimization['after'].get('pingpong_rate', 0)
            hyst_improvement = max(0, before_pingpong - after_pingpong)
            metrics['hyst_optimization_improvement_percent'] = hyst_improvement
        
        # Загальна ефективність оптимізації
        overall_before = optimization_results.get('baseline_metrics', {})
        overall_after = optimization_results.get('optimized_metrics', {})
        
        if overall_before and overall_after:
            # Покращення success rate
            success_improvement = (overall_after.get('success_rate', 0) - 
                                 overall_before.get('success_rate', 0))
            metrics['overall_success_improvement_percent'] = success_improvement
            
            # Покращення throughput
            throughput_improvement = (overall_after.get('avg_throughput', 0) - 
                                    overall_before.get('avg_throughput', 0))
            metrics['throughput_improvement_mbps'] = throughput_improvement
        
        return metrics
    
    def generate_comprehensive_report(self, network_state: Dict, 
                                    handover_events: List[Dict],
                                    time_window: Optional[timedelta] = None) -> Dict[str, Any]:
        """Генерація комплексного звіту про стан мережі"""
        
        # Розрахунок всіх типів метрик
        qos_metrics = self.calculate_qos_metrics(network_state.get('users', {}), time_window)
        handover_metrics = self.calculate_handover_metrics(handover_events, time_window)
        network_metrics = self.calculate_network_performance(network_state)
        interference_metrics = self.calculate_interference_metrics(network_state)
        coverage_metrics = self.calculate_coverage_metrics(network_state)
        mobility_metrics = self.calculate_mobility_metrics(
            network_state.get('users', {}), handover_events
        )
        
        # Розрахунок загального індексу якості мережі
        network_quality_index = self._calculate_network_quality_index(
            qos_metrics, handover_metrics, network_metrics, coverage_metrics
        )
        
        # Формування рекомендацій
        recommendations = self._generate_recommendations(
            qos_metrics, handover_metrics, network_metrics, 
            interference_metrics, coverage_metrics
        )
        
        report = {
            'timestamp': datetime.now(),
            'qos_metrics': qos_metrics,
            'handover_metrics': handover_metrics,
            'network_performance': network_metrics,
            'interference_analysis': interference_metrics,
            'coverage_analysis': coverage_metrics,
            'mobility_analysis': mobility_metrics,
            'network_quality_index': network_quality_index,
            'recommendations': recommendations,
            'summary': {
                'total_users': network_metrics.active_users,
                'network_efficiency': network_metrics.network_efficiency_percent,
                'handover_success_rate': handover_metrics.handover_success_rate,
                'average_throughput': qos_metrics.throughput_mbps,
                'coverage_quality': coverage_metrics['total_coverage_percent']
            }
        }
        
        return report
    
    def _calculate_network_quality_index(self, qos_metrics: QoSMetrics, 
                                       handover_metrics: HandoverMetrics,
                                       network_metrics: NetworkPerformanceMetrics,
                                       coverage_metrics: Dict) -> float:
        """Розрахунок загального індексу якості мережі (0-100)"""
        
        # Ваги для різних компонентів
        weights = {
            'qos': 0.3,
            'handover': 0.25,
            'performance': 0.25,
            'coverage': 0.2
        }
        
        # Нормалізація QoS метрик (0-100)
        qos_score = min(100, (
            min(100, qos_metrics.throughput_mbps * 2) * 0.4 +  # throughput
            max(0, 100 - qos_metrics.latency_ms / 2) * 0.3 +   # latency
            max(0, 100 - qos_metrics.packet_loss_rate * 1000) * 0.3  # packet loss
        ))
        
        # Нормалізація handover метрик
        handover_score = min(100, handover_metrics.handover_success_rate)
        
        # Нормалізація performance метрик
        performance_score = min(100, network_metrics.network_efficiency_percent)
        
        # Нормалізація coverage метрик
        coverage_score = coverage_metrics.get('total_coverage_percent', 0)
        
        # Зважена сума
        total_score = (
            qos_score * weights['qos'] +
            handover_score * weights['handover'] +
            performance_score * weights['performance'] +
            coverage_score * weights['coverage']
        )
        
        return round(total_score, 2)
    
    def _generate_recommendations(self, qos_metrics: QoSMetrics,
                                handover_metrics: HandoverMetrics,
                                network_metrics: NetworkPerformanceMetrics,
                                interference_metrics: Dict,
                                coverage_metrics: Dict) -> List[str]:
        """Генерація рекомендацій для покращення мережі"""
        recommendations = []
        
        # Рекомендації по QoS
        if qos_metrics.throughput_mbps < 10:
            recommendations.append("🔧 Низька пропускна здатність - розгляньте оптимізацію розподілу ресурсів")
        
        if qos_metrics.latency_ms > 50:
            recommendations.append("⚡ Висока затримка - перевірте конфігурацію мережі та навантаження")
        
        if qos_metrics.packet_loss_rate > 0.02:
            recommendations.append("📦 Високий рівень втрат пакетів - перевірте якість радіоканалу")
        
        # Рекомендації по хендоверу
        if handover_metrics.handover_success_rate < 90:
            recommendations.append("🔄 Низька успішність хендовера - оптимізуйте параметри TTT та Hysteresis")
        
        if handover_metrics.pingpong_rate > 5:
            recommendations.append("🏓 Високий ping-pong ефект - збільште значення Hysteresis")
        
        # Рекомендації по покриттю
        if coverage_metrics.get('total_coverage_percent', 0) < 95:
            recommendations.append("📡 Недостатнє покриття - розгляньте додавання нових базових станцій")
        
        if coverage_metrics.get('poor_coverage_percent', 0) > 10:
            recommendations.append("📶 Багато зон з поганим покриттям - оптимізуйте потужність передавачів")
        
        # Рекомендації по інтерференції
        if interference_metrics.get('interference_limited_users', 0) > network_metrics.active_users * 0.1:
            recommendations.append("🔇 Висока інтерференція - впровадіть координацію між базовими станціями")
        
        # Рекомендації по ефективності
        if network_metrics.network_efficiency_percent < 70:
            recommendations.append("⚙️ Низька ефективність мережі - оптимізуйте балансування навантаження")
        
        if not recommendations:
            recommendations.append("✅ Мережа працює в оптимальному режимі")
        
        return recommendations
