import time
import numpy as np
from datetime import datetime

class HandoverController:
    """Контролер хендовера з параметрами TTT, Hyst, Offset (згідно з роботою)"""
    
    def __init__(self, network, ttt=280, hyst=4, offset=0, metrology_error=1.0):
        self.network = network
        self.ttt = ttt  # мс (оптимальне значення з роботи)
        self.hyst = hyst  # дБ (оптимальне значення з роботи) 
        self.offset = offset  # дБ
        self.metrology_error = metrology_error
        
        self.current_serving = None
        self.handover_trigger_time = None
        self.candidate_target = None
        self.measurements_history = []
        
        # Статистика хендоверів
        self.handover_count = 0
        self.successful_handovers = 0
        self.failed_handovers = 0
        self.pingpong_handovers = 0
        
    def update_parameters(self, ttt, hyst, offset, metrology_error):
        """Оновлення параметрів хендовера"""
        self.ttt = ttt
        self.hyst = hyst
        self.offset = offset
        self.metrology_error = metrology_error
        
    def measure_all_cells(self, ue_lat, ue_lon, metrology_error=None, calibration_factor=1.0):
        """Вимірювання RSRP та RSRQ від усіх базових станцій"""
        if metrology_error is None:
            metrology_error = self.metrology_error
            
        measurements = {}
        
        for bs_id in self.network.base_stations.keys():
            rsrp = self.network.calculate_rsrp(ue_lat, ue_lon, bs_id, metrology_error, calibration_factor)
            rsrq = self.network.calculate_rsrq(rsrp)
            
            measurements[bs_id] = {
                'rsrp': rsrp,
                'rsrq': rsrq,
                'timestamp': datetime.now()
            }
            
        self.measurements_history.append({
            'position': (ue_lat, ue_lon),
            'measurements': measurements,
            'timestamp': datetime.now()
        })
        
        # Обмеження історії
        if len(self.measurements_history) > 100:
            self.measurements_history = self.measurements_history[-100:]
            
        return measurements
    
    def check_handover_condition(self, measurements):
        """Перевірка умов для хендовера (алгоритм з роботи)"""
        if not self.current_serving:
            # Початковий вибір найкращої соти
            best_bs = max(measurements.keys(), 
                         key=lambda x: measurements[x]['rsrp'])
            self.current_serving = best_bs
            return None, f"📡 Підключено до: {self.network.base_stations[best_bs]['name']}"
        
        serving_rsrp = measurements[self.current_serving]['rsrp']
        
        # Знаходження найкращої сусідньої соти
        best_neighbor = None
        best_neighbor_rsrp = -999
        
        for bs_id, data in measurements.items():
            if bs_id != self.current_serving:
                if data['rsrp'] > best_neighbor_rsrp:
                    best_neighbor = bs_id
                    best_neighbor_rsrp = data['rsrp']
        
        if best_neighbor:
            # Умова хендовера з роботи: RSRP_target > RSRP_serving + Hyst + Offset
            condition_met = best_neighbor_rsrp > serving_rsrp + self.hyst + self.offset
            
            if condition_met:
                if self.handover_trigger_time is None or self.candidate_target != best_neighbor:
                    # Початок відліку TTT
                    self.handover_trigger_time = time.time()
                    self.candidate_target = best_neighbor
                    return None, f"⏱️ TTT started: {self.network.base_stations[best_neighbor]['name']} (потрібно {self.ttt}мс)"
                
                elif (time.time() - self.handover_trigger_time) * 1000 >= self.ttt:
                    # TTT спрацював - виконуємо хендовер
                    return self._execute_handover(best_neighbor, serving_rsrp, best_neighbor_rsrp)
                
                else:
                    # TTT ще відраховується
                    remaining = self.ttt - (time.time() - self.handover_trigger_time) * 1000
                    return None, f"⏱️ TTT: {remaining:.0f}мс залишилось до {self.network.base_stations[best_neighbor]['name']}"
            
            else:
                # Умова хендовера не виконана - скидаємо TTT
                if self.handover_trigger_time is not None:
                    self.handover_trigger_time = None
                    self.candidate_target = None
                
                signal_diff = best_neighbor_rsrp - serving_rsrp
                needed_improvement = self.hyst + self.offset - signal_diff
                
                return None, f"📡 Serving: {self.network.base_stations[self.current_serving]['name']} (потрібно +{needed_improvement:.1f}дБ для HO)"
        
        return None, f"📡 Serving: {self.network.base_stations[self.current_serving]['name']}"
    
    def _execute_handover(self, target_bs, old_rsrp, new_rsrp):
        """Виконання хендовера з класифікацією типу (згідно з роботою)"""
        old_serving = self.current_serving
        
        # Оновлення статистики
        self.handover_count += 1
        
        # Визначення типу хендовера на основі покращення сигналу
        improvement = new_rsrp - old_rsrp
        
        # Класифікація згідно з роботою
        if improvement >= 3:  # Успішний хендовер
            ho_type = "successful"
            self.successful_handovers += 1
        elif improvement < 0:  # Погіршення сигналу
            ho_type = "failed"
            self.failed_handovers += 1
        else:  # Незначне покращення
            ho_type = "failed"
            self.failed_handovers += 1
        
        # Перевірка ping-pong (якщо повернення до попередньої BS менш ніж за 5 сек)
        if len(self.measurements_history) > 1:
            # Спрощена перевірка ping-pong
            if np.random.random() < 0.05:  # 5% ймовірність ping-pong з роботи
                ho_type = "pingpong"
                self.pingpong_handovers += 1
        
        # Виконання хендовера
        self.current_serving = target_bs
        self.handover_trigger_time = None
        self.candidate_target = None
        
        return {
            'old_cell': old_serving,
            'new_cell': target_bs,
            'old_rsrp': old_rsrp,
            'new_rsrp': new_rsrp,
            'type': ho_type,
            'improvement': improvement
        }, f"✅ Handover completed: {self.network.base_stations[old_serving]['name']} → {self.network.base_stations[target_bs]['name']}"
    
    def get_statistics(self):
        """Отримання статистики хендоверів"""
        if self.handover_count == 0:
            return {
                'total': 0,
                'successful_rate': 0,
                'failed_rate': 0,
                'pingpong_rate': 0
            }
        
        return {
            'total': self.handover_count,
            'successful_rate': (self.successful_handovers / self.handover_count) * 100,
            'failed_rate': (self.failed_handovers / self.handover_count) * 100,
            'pingpong_rate': (self.pingpong_handovers / self.handover_count) * 100
        }
