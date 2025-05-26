import numpy as np
from geopy.distance import geodesic

def calculate_distance(lat1, lon1, lat2, lon2):
    """Розрахунок відстані між двома точками"""
    return geodesic((lat1, lon1), (lat2, lon2)).kilometers

def calculate_path_loss(distance_km, frequency_mhz, environment='urban'):
    """Розрахунок втрат на трасі за моделлю COST-Hata (з роботи)"""
    
    if environment == 'urban':
        # Міська місцевість (модель з роботи)
        if frequency_mhz <= 1000:  # 900 МГц
            path_loss = (69.55 + 26.16*np.log10(frequency_mhz) - 
                        13.82*np.log10(30) + 
                        (44.9 - 6.55*np.log10(30))*np.log10(distance_km + 0.001))
        else:  # 1800/2600 МГц
            path_loss = (46.3 + 33.9*np.log10(frequency_mhz) - 
                        13.82*np.log10(30) + 
                        (44.9 - 6.55*np.log10(30))*np.log10(distance_km + 0.001) + 3)
    
    elif environment == 'suburban':
        # Приміська місцевість
        urban_loss = calculate_path_loss(distance_km, frequency_mhz, 'urban')
        path_loss = urban_loss - 2 * (np.log10(frequency_mhz/28))**2 - 5.4
    
    elif environment == 'rural':
        # Сільська місцевість  
        urban_loss = calculate_path_loss(distance_km, frequency_mhz, 'urban')
        path_loss = urban_loss - 4.78 * (np.log10(frequency_mhz))**2 + 18.33*np.log10(frequency_mhz) - 40.98
    
    else:
        # За замовчуванням - міська місцевість
        path_loss = calculate_path_loss(distance_km, frequency_mhz, 'urban')
    
    return max(path_loss, 30)  # Мінімальні втрати 30 дБ

def add_metrology_error(signal_dbm, error_std=1.0):
    """Додавання метрологічної похибки ±1 дБ (згідно з роботою)"""
    return signal_dbm + np.random.normal(0, error_std)

def optimize_handover_parameters(target_success_rate=95):
    """Оптимізація параметрів хендовера (алгоритм з роботи)"""
    best_params = None
    best_success_rate = 0
    
    # Діапазони параметрів з роботи
    ttt_range = range(40, 1001, 40)  # 40-1000 мс з кроком 40 мс
    hyst_range = range(0, 11, 1)     # 0-10 дБ з кроком 1 дБ
    offset_range = [0]               # Фіксований Offset = 0
    
    results = []
    
    for ttt in ttt_range:
        for hyst in hyst_range:
            for offset in offset_range:
                # Симуляція успішності (спрощена модель з роботи)
                success_rate = simulate_handover_success_rate(ttt, hyst, offset)
                
                if success_rate > best_success_rate:
                    best_success_rate = success_rate
                    best_params = {'ttt': ttt, 'hyst': hyst, 'offset': offset}
                
                results.append({
                    'ttt': ttt,
                    'hyst': hyst,
                    'offset': offset,
                    'success_rate': success_rate
                })
    
    return best_params, best_success_rate, results

def simulate_handover_success_rate(ttt, hyst, offset, num_simulations=1000):
    """Симуляція успішності хендовера (модель з роботи)"""
    successful = 0
    
    for _ in range(num_simulations):
        # Симуляція RSRP з похибкою ±1 дБ
        rsrp_serving = -80 + np.random.normal(0, 1)
        rsrp_target = rsrp_serving + hyst + offset + np.random.normal(0, 1)
        
        # Перевірка умови хендовера
        if rsrp_target > rsrp_serving + hyst:
            # Симуляція часу спрацювання TTT
            actual_trigger_time = ttt * (0.8 + 0.4 * np.random.random())
            
            # Оцінка успішності
            if 0.9 * ttt <= actual_trigger_time <= 1.1 * ttt:
                successful += 1
    
    return (successful / num_simulations) * 100
