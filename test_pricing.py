#!/usr/bin/env python3
"""
Тест новой системы ценообразования
"""

from config import BASE_PLANS, DEVICE_PLANS, calculate_price, VPN_PLANS

def test_pricing():
    """Тестирование системы ценообразования"""
    
    print("Тестирование новой системы ценообразования\n")
    
    # Тест 1: Базовые планы
    print("1. Базовые планы:")
    for period_id, period in BASE_PLANS.items():
        print(f"   {period_id}: {period['name']} - {period['base_price']} руб. ({period['days']} дней)")
    
    # Тест 2: Планы устройств
    print("\n2. Планы устройств:")
    for device_count, device in DEVICE_PLANS.items():
        print(f"   {device_count}: {device['name']} - +{device['extra_price']} руб.")
    
    # Тест 3: Расчет цен
    print("\n3. Примеры расчета цен:")
    examples = [
        ("1month", 1),
        ("1month", 2),
        ("3months", 1),
        ("3months", 3),
        ("6months", 2),
        ("1year", 5)
    ]
    
    for period_id, device_count in examples:
        period = BASE_PLANS[period_id]
        device = DEVICE_PLANS[device_count]
        total = calculate_price(period_id, device_count)
        
        print(f"   {period['name']} + {device['name']}")
        print(f"   = {period['base_price']} + {device['extra_price']} = {total} руб.")
        print()
    
    # Тест 4: Совместимость со старым форматом
    print("4. Совместимость (VPN_PLANS):")
    for plan_id, plan in list(VPN_PLANS.items())[:5]:  # Показываем первые 5
        print(f"   {plan_id}: {plan['name']} - {plan['price']} руб.")
    
    print(f"\nВсего сгенерировано планов: {len(VPN_PLANS)}")

if __name__ == "__main__":
    test_pricing()