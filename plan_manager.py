import json
import os
from typing import Dict
from config import SUBSCRIPTION_PLANS

class PlanManager:
    def __init__(self, plans_file: str = "plans.json"):
        self.plans_file = plans_file
        self.load_plans()
    
    def load_plans(self):
        """Загрузка планов из файла"""
        if os.path.exists(self.plans_file):
            try:
                with open(self.plans_file, 'r', encoding='utf-8') as f:
                    loaded_plans = json.load(f)
                    # Обновляем глобальные планы
                    SUBSCRIPTION_PLANS.clear()
                    SUBSCRIPTION_PLANS.update(loaded_plans)
            except Exception as e:
                print(f"Ошибка загрузки планов: {e}")
    
    def save_plans(self):
        """Сохранение планов в файл"""
        try:
            with open(self.plans_file, 'w', encoding='utf-8') as f:
                json.dump(SUBSCRIPTION_PLANS, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Ошибка сохранения планов: {e}")
    
    def add_plan(self, plan_id: str, name: str, price: int, duration: int) -> bool:
        """Добавление нового плана"""
        if plan_id in SUBSCRIPTION_PLANS:
            return False
        
        SUBSCRIPTION_PLANS[plan_id] = {
            "name": name,
            "price": price,
            "duration": duration
        }
        
        self.save_plans()
        return True
    
    def update_plan(self, plan_id: str, name: str = None, price: int = None, duration: int = None) -> bool:
        """Обновление существующего плана"""
        if plan_id not in SUBSCRIPTION_PLANS:
            return False
        
        if name is not None:
            SUBSCRIPTION_PLANS[plan_id]["name"] = name
        if price is not None:
            SUBSCRIPTION_PLANS[plan_id]["price"] = price
        if duration is not None:
            SUBSCRIPTION_PLANS[plan_id]["duration"] = duration
        
        self.save_plans()
        return True
    
    def delete_plan(self, plan_id: str) -> bool:
        """Удаление плана"""
        if plan_id not in SUBSCRIPTION_PLANS:
            return False
        
        del SUBSCRIPTION_PLANS[plan_id]
        self.save_plans()
        return True
    
    def get_plan(self, plan_id: str) -> Dict:
        """Получение плана по ID"""
        return SUBSCRIPTION_PLANS.get(plan_id)
    
    def get_all_plans(self) -> Dict:
        """Получение всех планов"""
        return SUBSCRIPTION_PLANS.copy()

# Глобальный экземпляр менеджера планов
plan_manager = PlanManager()