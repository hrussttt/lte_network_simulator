import numpy as np
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass

@dataclass
class HandoverParameters:
    """Параметри алгоритму хендовера"""
    ttt: int = 280  # Time-to-Trigger в мс
    hyst: float = 4.0  # Hysteresis в дБ
    offset: float = 0.0  # Offset в дБ
    measurement_gap: float = 40.0  # Інтервал вимірювань в мс
    min_trigger_count: int = 3  # Мінімальна кількість спрацювань

class HandoverAlgorithm:
    """Алгоритм прийняття рішень про хендовер"""
    
    def __init__(self):
        self.trigger_timers = {}  # Таймери TTT для кожного UE
        self.measurement_history = {}  # Історія вимірювань
        self.handover_statistics = {
            'total_attempts': 0,
            'successful': 0,
            'failed': 0,
            'pingpong': 0,
            'too_early': 0,
            'too_late': 0
        }
        
    def check_handover_condition(self, current_bs_id: str, measurements: Dict,
                                ttt: int = 280, hyst: float = 4.0, 
                                offset: float = 0.0, ue_id: str = None) -> Dict:
        """Основна функція перевірки умов хендовера"""
        
        if not current_bs_id or current_bs_id not in measurements:
            return {'execute_handover': False, 'reason': 'Invalid current BS'}
        
        current_rsrp = measurements[current_bs_id]['rsrp']
        
        # Знаходження найкращої сусідньої БС
        best_neighbor = None
        best_rsrp = -999
        
        for bs_id, data in measurements.items():
            if bs_id != current_bs_id:
                adjusted_rsrp = data['rsrp'] + offset
                if adjusted_rsrp > best_rsrp:
                    best_rsrp = adjusted_rsrp
                    best_neighbor = bs_id
        
        if not best_neighbor:
            return {'execute_handover': False, 'reason': 'No neighbor BS found'}
        
        # Основна умова хендовера: RSRP_target > RSRP_serving + Hyst
        handover_condition = best_rsrp > current_rsrp + hyst
        
        if not handover_condition:
            # Скидання таймера, якщо умова не виконується
            if ue_id and ue_id in self.trigger_timers:
                del self.trigger_timers[ue_id]
            
            return {
                'execute_handover': False,
                'reason': f'Condition not met: {best_rsrp:.1f} <= {current_rsrp + hyst:.1f}',
                'serving_rsrp': current_rsrp,
                'best_neighbor_rsrp': best_rsrp,
                'required_improvement': current_rsrp + hyst - best_rsrp
            }
        
        # Обробка TTT таймера
        current_time = time.time() * 1000  # в мілісекундах
        
        if ue_id:
            if ue_id not in self.trigger_timers:
                # Початок відліку TTT
                self.trigger_timers[ue_id] = {
                    'start_time': current_time,
                    'target_bs': best_neighbor,
                    'trigger_count': 1
                }
                return {
                    'execute_handover': False,
                    'reason': f'TTT started for {best_neighbor}',
                    'ttt_remaining': ttt,
                    'target_bs': best_neighbor
                }
            else:
                timer_info = self.trigger_timers[ue_id]
                elapsed = current_time - timer_info['start_time']
                
                # Перевірка зміни цільової БС
                if timer_info['target_bs'] != best_neighbor:
                    # Перезапуск таймера для нової цільової БС
                    self.trigger_timers[ue_id] = {
                        'start_time': current_time,
                        'target_bs': best_neighbor,
                        'trigger_count': 1
                    }
                    return {
                        'execute_handover': False,
                        'reason': f'TTT restarted for {best_neighbor}',
                        'ttt_remaining': ttt,
                        'target_bs': best_neighbor
                    }
                
                # Збільшення лічильника спрацювань
                timer_info['trigger_count'] += 1
                
                if elapsed >= ttt:
                    # TTT спрацював - виконуємо хендовер
                    del self.trigger_timers[ue_id]
                    
                    # Додаткова перевірка якості цільової БС
                    target_quality = self._assess_target_quality(
                        measurements[best_neighbor], measurements[current_bs_id]
                    )
                    
                    self.handover_statistics['total_attempts'] += 1
                    
                    return {
                        'execute_handover': True,
                        'target_bs': best_neighbor,
                        'reason': 'TTT expired',
                        'elapsed_time': elapsed,
                        'serving_rsrp': current_rsrp,
                        'target_rsrp': best_rsrp,
                        'improvement': best_rsrp - current_rsrp,
                        'quality_assessment': target_quality,
                        'trigger_count': timer_info['trigger_count']
                    }
                else:
                    # TTT ще відраховується
                    remaining = ttt - elapsed
                    return {
                        'execute_handover': False,
                        'reason': f'TTT in progress: {remaining:.0f}ms remaining',
                        'ttt_remaining': remaining,
                        'target_bs': best_neighbor,
                        'elapsed_time': elapsed,
                        'trigger_count': timer_info['trigger_count']
                    }
        
        # Якщо UE ID не вказано, виконуємо негайний хендовер
        return {
            'execute_handover': True,
            'target_bs': best_neighbor,
            'reason': 'Immediate handover (no TTT)',
            'serving_rsrp': current_rsrp,
            'target_rsrp': best_rsrp,
            'improvement': best_rsrp - current_rsrp
        }
    
    def _assess_target_quality(self, target_measurements: Dict, serving_measurements: Dict) -> Dict:
        """Оцінка якості цільової базової станції"""
        target_rsrp = target_measurements['rsrp']
        target_rsrq = target_measurements.get('rsrq', -12)
        
        serving_rsrp = serving_measurements['rsrp']
        serving_rsrq = serving_measurements.get('rsrq', -12)
        
        # Розрахунок покращень
        rsrp_improvement = target_rsrp - serving_rsrp
        rsrq_improvement = target_rsrq - serving_rsrq
        
        # Оцінка якості
        quality_score = 0
        
        # RSRP оцінка
        if target_rsrp > -70:
            quality_score += 30  # Відмінний сигнал
        elif target_rsrp > -85:
            quality_score += 20  # Хороший сигнал
        elif target_rsrp > -100:
            quality_score += 10  # Задовільний сигнал
        
        # RSRQ оцінка
        if target_rsrq > -9:
            quality_score += 20
        elif target_rsrq > -12:
            quality_score += 15
        elif target_rsrq > -15:
            quality_score += 10
        
        # Покращення оцінка
        if rsrp_improvement >= 5:
            quality_score += 25
        elif rsrp_improvement >= 3:
            quality_score += 15
        elif rsrp_improvement >= 1:
            quality_score += 10
        
        return {
            'quality_score': quality_score,
            'rsrp_improvement': rsrp_improvement,
            'rsrq_improvement': rsrq_improvement,
            'target_rsrp_level': self._get_signal_level(target_rsrp),
            'recommendation': 'proceed' if quality_score >= 40 else 'caution'
        }
    
    def _get_signal_level(self, rsrp: float) -> str:
        """Визначення рівня сигналу"""
        if rsrp > -70:
            return 'excellent'
        elif rsrp > -85:
            return 'good'
        elif rsrp > -100:
            return 'fair'
        elif rsrp > -110:
            return 'poor'
        else:
            return 'very_poor'
    
    def detect_pingpong(self, ue_id: str, handover_history: List[Dict], 
                       window_seconds: int = 60) -> bool:
        """Виявлення ping-pong ефекту"""
        if len(handover_history) < 2:
            return False
        
        current_time = datetime.now()
        recent_handovers = []
        
        # Фільтрація хендоверів за останній період
        for ho in reversed(handover_history):
            ho_time = ho.get('timestamp')
            if isinstance(ho_time, str):
                ho_time = datetime.fromisoformat(ho_time)
            
            if (current_time - ho_time).total_seconds() <= window_seconds:
                recent_handovers.append(ho)
            else:
                break
        
        if len(recent_handovers) < 2:
            return False
        
        # Перевірка зворотних переходів
        for i in range(len(recent_handovers) - 1):
            ho1 = recent_handovers[i]
            ho2 = recent_handovers[i + 1]
            
            if (ho1.get('new_bs') == ho2.get('old_bs') and 
                ho1.get('old_bs') == ho2.get('new_bs')):
                return True
        
        return False
    
    def adaptive_parameter_adjustment(self, ue_mobility_state: str, 
                                    network_load: float, 
                                    interference_level: float) -> HandoverParameters:
        """Адаптивне налаштування параметрів хендовера"""
        base_params = HandoverParameters()
        
        # Коригування на основі мобільності
        if ue_mobility_state == "high_mobility":
            base_params.ttt = max(160, base_params.ttt - 80)  # Швидший хендовер
            base_params.hyst = max(2, base_params.hyst - 1)
        elif ue_mobility_state == "stationary":
            base_params.ttt = min(480, base_params.ttt + 120)  # Повільніший хендовер
            base_params.hyst = min(6, base_params.hyst + 1)
        
        # Коригування на основі навантаження мережі
        if network_load > 0.8:  # Високе навантаження
            base_params.hyst += 1  # Зменшення кількості хендоверів
            base_params.ttt += 40
        elif network_load < 0.3:  # Низьке навантаження
            base_params.hyst = max(1, base_params.hyst - 0.5)
            base_params.ttt = max(120, base_params.ttt - 40)
        
        # Коригування на основі інтерференції
        if interference_level > 5:
            base_params.hyst += 0.5
            base_params.offset += 1
        
        return base_params
    
    def get_handover_statistics(self) -> Dict:
        """Отримання статистики хендоверів"""
        total = self.handover_statistics['total_attempts']
        if total == 0:
            return self.handover_statistics
        
        stats = self.handover_statistics.copy()
        stats['success_rate'] = (stats['successful'] / total) * 100
        stats['failure_rate'] = (stats['failed'] / total) * 100
        stats['pingpong_rate'] = (stats['pingpong'] / total) * 100
        
        return stats
    
    def reset_statistics(self):
        """Скидання статистики"""
        self.handover_statistics = {
            'total_attempts': 0,
            'successful': 0,
            'failed': 0,
            'pingpong': 0,
            'too_early': 0,
            'too_late': 0
        }
        self.trigger_timers.clear()
        self.measurement_history.clear()
    
    def optimize_parameters(self, historical_data: List[Dict], 
                          target_success_rate: float = 95.0) -> HandoverParameters:
        """Оптимізація параметрів на основі історичних даних"""
        best_params = HandoverParameters()
        best_score = 0
        
        # Діапазони для оптимізації
        ttt_range = range(120, 481, 40)
        hyst_range = [h/2 for h in range(2, 11)]  # 1.0, 1.5, 2.0, ..., 5.0
        
        for ttt in ttt_range:
            for hyst in hyst_range:
                # Симуляція з тестовими параметрами
                score = self._evaluate_parameters(historical_data, ttt, hyst)
                
                if score > best_score:
                    best_score = score
                    best_params.ttt = ttt
                    best_params.hyst = hyst
        
        return best_params
    
    def _evaluate_parameters(self, data: List[Dict], ttt: int, hyst: float) -> float:
        """Оцінка якості параметрів"""
        if not data:
            return 0
        
        successful_count = 0
        total_count = len(data)
        
        for entry in data:
            # Спрощена симуляція рішення з новими параметрами
            serving_rsrp = entry.get('serving_rsrp', -85)
            target_rsrp = entry.get('target_rsrp', -80)
            
            if target_rsrp > serving_rsrp + hyst:
                # Симуляція TTT
                simulated_delay = np.random.uniform(0.8, 1.2) * ttt
                if 0.9 * ttt <= simulated_delay <= 1.1 * ttt:
                    successful_count += 1
        
        success_rate = (successful_count / total_count) * 100 if total_count > 0 else 0
        
        # Оцінка якості: близькість до цільового показника
        score = max(0, 100 - abs(success_rate - 95))
        
        return score
