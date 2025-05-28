import time
import numpy as np
from datetime import datetime

class HandoverController:
    """Контролер хендовера з реалістичними типами результатів"""
    
    def __init__(self, network, ttt=280, hyst=4, offset=0, metrology_error=1.0):
        self.network = network
        self.ttt = ttt
        self.hyst = hyst
        self.offset = offset
        self.metrology_error = metrology_error
        
        self.current_serving = None
        self.handover_trigger_time = None
        self.candidate_target = None
        self.measurements_history = []
        
        # Статистика хендоверів за типами
        self.handover_count = 0
        self.successful_handovers = 0
        self.failed_handovers = 0
        self.early_handovers = 0
        self.late_handovers = 0
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
        """ОНОВЛЕНО: Перевірка умов з реалістичними типами хендоверів"""
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
            # Умова хендовера: RSRP_target > RSRP_serving + Hyst + Offset
            condition_met = best_neighbor_rsrp > serving_rsrp + self.hyst + self.offset

            if condition_met:
                if self.handover_trigger_time is None or self.candidate_target != best_neighbor:
                    # Початок відліку TTT
                    self.handover_trigger_time = time.time()
                    self.candidate_target = best_neighbor
                    return None, f"⏱️ TTT started: {self.network.base_stations[best_neighbor]['name']}"

                elif (time.time() - self.handover_trigger_time) * 1000 >= self.ttt:
                    # TTT спрацював - виконуємо хендовер
                    elapsed_time = (time.time() - self.handover_trigger_time) * 1000
                    return self._execute_realistic_handover(
                        best_neighbor, serving_rsrp, best_neighbor_rsrp, elapsed_time
                    )

                else:
                    # TTT ще відраховується
                    remaining = self.ttt - (time.time() - self.handover_trigger_time) * 1000
                    return None, f"⏱️ TTT: {remaining:.0f}мс"

            else:
                # Умова хендовера не виконана - скидаємо TTT
                if self.handover_trigger_time is not None:
                    self.handover_trigger_time = None
                    self.candidate_target = None

                signal_diff = best_neighbor_rsrp - serving_rsrp
                needed_improvement = self.hyst + self.offset - signal_diff

                return None, f"📡 Serving: {self.network.base_stations[self.current_serving]['name']}"

        return None, f"📡 Serving: {self.network.base_stations[self.current_serving]['name']}"

    def _execute_realistic_handover(self, target_bs, old_rsrp, new_rsrp, elapsed_time):
        """НОВИНКА: Реалістичне виконання хендовера з різними типами"""
        old_serving = self.current_serving
        
        # Оновлення статистики
        self.handover_count += 1
        
        # НОВИНКА: Визначення реалістичного типу хендовера
        improvement = new_rsrp - old_rsrp
        
        # Передчасний хендовер (< 0.8 * TTT)
        if elapsed_time < 0.8 * self.ttt:
            ho_type = "early"
            self.early_handovers += 1
        
        # Запізнілий хендовер (> 1.2 * TTT) 
        elif elapsed_time > 1.2 * self.ttt:
            ho_type = "late"
            self.late_handovers += 1
        
        # Ping-pong (мале покращення)
        elif improvement < 3:
            ho_type = "pingpong"
            self.pingpong_handovers += 1
        
        # Невдалий хендовер (погіршення сигналу)
        elif improvement < 0:
            ho_type = "failed"
            self.failed_handovers += 1
        
        # Успішний хендовер
        else:
            ho_type = "successful"
            self.successful_handovers += 1
        
        # Виконання хендовера
        self.current_serving = target_bs
        self.handover_trigger_time = None
        self.candidate_target = None
        
        # НОВИНКА: Розширена подія з типом
        handover_event = {
            'old_cell': old_serving,
            'new_cell': target_bs,
            'old_rsrp': old_rsrp,
            'new_rsrp': new_rsrp,
            'type': ho_type,
            'improvement': improvement,
            'elapsed_time': elapsed_time,
            'timestamp': datetime.now()
        }
        
        # Статус повідомлення з типом
        type_names = {
            'successful': '✅ Успішний',
            'early': '⚡ Передчасний', 
            'late': '⏰ Запізнілий',
            'pingpong': '🏓 Ping-pong',
            'failed': '❌ Невдалий'
        }
        
        status = f"{type_names[ho_type]} хендовер: {self.network.base_stations[old_serving]['name']} → {self.network.base_stations[target_bs]['name']}"
        
        return handover_event, status

    def get_statistics(self):
        """ОНОВЛЕНО: Статистика з усіма типами хендоверів"""
        if self.handover_count == 0:
            return {
                'total': 0, 'successful_rate': 0, 'failed_rate': 0, 'pingpong_rate': 0,
                'early_rate': 0, 'late_rate': 0
            }
        
        return {
            'total': self.handover_count,
            'successful_rate': (self.successful_handovers / self.handover_count) * 100,
            'failed_rate': (self.failed_handovers / self.handover_count) * 100,
            'pingpong_rate': (self.pingpong_handovers / self.handover_count) * 100,
            'early_rate': (self.early_handovers / self.handover_count) * 100,
            'late_rate': (self.late_handovers / self.handover_count) * 100
        }
