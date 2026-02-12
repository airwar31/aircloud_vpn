"""
Утилиты для работы с двойным туннелем VPN
Упрощает интеграцию в существующий бот
"""

import json
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, Tuple
from config import VPN_PLANS
from tunnel_manager import TunnelManager
from xray_double_tunnel import XrayDoubleTunnelConfig

logger = logging.getLogger(__name__)


class DoubleTunnelHelper:
    """Вспомогательный класс для работы с двойным туннелем"""
    
    @staticmethod
    def is_double_tunnel_plan(plan_id: str) -> bool:
        """Проверяет, является ли план двойным туннелем"""
        plan = VPN_PLANS.get(plan_id)
        if not plan:
            return False
        return plan.get('tunnel_type') == 'double'
    
    @staticmethod
    def get_tunnel_type(plan_id: str) -> str:
        """Получает тип туннеля для плана"""
        plan = VPN_PLANS.get(plan_id)
        if not plan:
            return 'single'
        return plan.get('tunnel_type', 'single')
    
    @staticmethod
    def get_tunnel_route(plan_id: str) -> str:
        """Получает маршрут туннеля для плана"""
        plan = VPN_PLANS.get(plan_id)
        if not plan:
            return ''
        return plan.get('route', '')
    
    @staticmethod
    def get_plan_info(plan_id: str) -> Dict[str, Any]:
        """Получает полную информацию о плане"""
        plan = VPN_PLANS.get(plan_id)
        if not plan:
            return {}
        
        tunnel_type = plan.get('tunnel_type', 'single')
        route = plan.get('route', '')
        tunnel_info = TunnelManager.get_tunnel_info(tunnel_type, route)
        
        return {
            **plan,
            "plan_id": plan_id,
            "tunnel_info": tunnel_info,
            "is_double": tunnel_type == 'double'
        }
    
    @staticmethod
    def generate_vpn_config(plan_id: str, user_id: int, client_id: str,
                           email: str, expires_at: datetime) -> Dict[str, Any]:
        """
        Генерирует конфигурацию VPN для пользователя
        
        Args:
            plan_id: ID плана подписки
            user_id: ID пользователя
            client_id: UUID клиента
            email: Email для конфигурации
            expires_at: Дата истечения подписки
            
        Returns:
            Словарь с конфигурацией и метаданными
        """
        try:
            plan = VPN_PLANS.get(plan_id)
            if not plan:
                logger.error(f"План {plan_id} не найден")
                return {}
            
            tunnel_type = plan.get('tunnel_type', 'single')
            route = plan.get('route', '')
            
            # Генерируем конфигурацию
            if tunnel_type == 'double':
                config = TunnelManager.generate_double_tunnel_config(
                    email=email,
                    client_id=client_id,
                    expires_at=expires_at,
                    route=route
                )
                config_str = json.dumps(config, ensure_ascii=False, indent=2)
            else:
                config_str = TunnelManager.generate_single_tunnel_config(
                    email=email,
                    client_id=client_id,
                    expires_at=expires_at
                )
            
            return {
                "plan_id": plan_id,
                "user_id": user_id,
                "email": email,
                "client_id": client_id,
                "tunnel_type": tunnel_type,
                "tunnel_route": route,
                "config": config_str,
                "expires_at": expires_at,
                "plan_info": plan
            }
            
        except Exception as e:
            logger.error(f"Ошибка генерации конфигурации: {e}")
            return {}
    
    @staticmethod
    def format_config_for_display(config: Dict[str, Any]) -> str:
        """
        Форматирует конфигурацию для отображения пользователю
        
        Args:
            config: Словарь конфигурации
            
        Returns:
            Красивый текст для отправки пользователю
        """
        tunnel_type = config.get('tunnel_type', 'single')
        tunnel_route = config.get('tunnel_route', '')
        plan_info = config.get('plan_info', {})
        expires_at = config.get('expires_at')
        
        if tunnel_type == 'double':
            emoji = "🔗"
            type_name = "Двойной туннель"
            route_info = f" ({TunnelManager.DOUBLE_TUNNEL_ROUTES.get(tunnel_route, {}).get('name', '')})"
        else:
            emoji = "🌐"
            type_name = "Обычный VPN"
            route_info = ""
        
        text = f"""{emoji} <b>{type_name}{route_info}</b>

<b>Информация о подписке:</b>
📦 Тариф: {plan_info.get('name', 'Неизвестный')}
💰 Стоимость: {plan_info.get('price', '?')}₽
⏰ Действует до: {expires_at.strftime('%d.%m.%Y %H:%M') if expires_at else '?'}
🔄 Период: {plan_info.get('days', '?')} дней

<b>Ваша конфигурация:</b>
<code>{config.get('config', '')}</code>

<b>Как подключиться:</b>
📱 Для Android: V2RayNG или ClashMeta
💻 Для ПК: Clash for Windows / ClashX
🍎 Для iOS: Shadowrocket или Quantumult X

✅ Инструкция: /help"""
        
        return text
    
    @staticmethod
    def format_plan_for_menu(plan_id: str) -> str:
        """
        Форматирует название плана для меню
        
        Args:
            plan_id: ID плана
            
        Returns:
            Красивый текст для кнопки меню
        """
        plan = VPN_PLANS.get(plan_id)
        if not plan:
            return plan_id
        
        tunnel_type = plan.get('tunnel_type', 'single')
        price = plan.get('price', '?')
        name = plan.get('name', plan_id)
        
        if tunnel_type == 'double':
            return f"🔗 {name} - {price}₽"
        else:
            return f"🌐 {name} - {price}₽"
    
    @staticmethod
    def get_plan_description(plan_id: str) -> str:
        """Получает описание плана для отображения"""
        plan_info = DoubleTunnelHelper.get_plan_info(plan_id)
        if not plan_info:
            return ""
        
        tunnel_info = plan_info.get('tunnel_info', {})
        
        text = f"""
<b>{plan_info.get('name')}</b>

💰 Цена: {plan_info.get('price')}₽
📦 Период: {plan_info.get('days')} дней

<b>Описание:</b>
{tunnel_info.get('description', 'Нет описания')}

<b>Включено:</b>
"""
        
        if plan_info.get('is_double'):
            text += """✅ Двойное шифрование
✅ IP Нидерландов
✅ Выход через два сервера
✅ Максимальная приватность
⚠️ Скорость: 50-70% от обычного VPN"""
        else:
            text += """✅ Один сервер
✅ Быстрое соединение
✅ Стандартное шифрование
✅ Хорошее соотношение скорости и приватности"""
        
        return text
    
    @staticmethod
    def compare_plans() -> str:
        """Создает таблицу сравнения планов"""
        single_plans = {pid: p for pid, p in VPN_PLANS.items() if p.get('tunnel_type') == 'single'}
        double_plans = {pid: p for pid, p in VPN_PLANS.items() if p.get('tunnel_type') == 'double'}
        
        text = """
<b>📊 Сравнение планов VPN</b>

<code>
ПЕРИОД       ОБЫЧНЫЙ VPN    ДВОЙНОЙ ТУННЕЛЬ    СЭКОНОМИЯ ДОП.
────────────────────────────────────────────────────────────"""
        
        # Сортируем по дням для сравнения
        for days in [30, 90, 180, 365]:
            single = next((p for p in single_plans.values() if p.get('days') == days), None)
            double = next((p for p in double_plans.values() if p.get('days') == days), None)
            
            if single and double:
                price_diff = double.get('price', 0) - single.get('price', 0)
                percent = (price_diff / single.get('price', 1)) * 100
                
                period = f"{days}d" if days < 365 else "1y"
                text += f"\n{period:12} {single.get('price'):4}₽          {double.get('price'):4}₽           +{price_diff}₽ ({percent:.0f}%)"
        
        text += """
────────────────────────────────────────────────────────────
</code>

<b>🌐 Обычный VPN:</b> Быстрый, надежный, хорошее соотношение
<b>🔗 Двойной туннель:</b> Максимальная приватность, скрывает IP провайдера
"""
        return text


class DoubleTunnelUserGuide:
    """Помощник для отправки гайдов пользователям"""
    
    @staticmethod
    def get_quick_start() -> str:
        """Быстрый старт для новичков"""
        from double_tunnel_docs import get_quick_setup_guide
        return get_quick_setup_guide()
    
    @staticmethod
    def get_full_guide() -> str:
        """Полный гайд по использованию"""
        from double_tunnel_docs import get_double_tunnel_documentation
        return get_double_tunnel_documentation()
    
    @staticmethod
    def get_troubleshooting() -> str:
        """Гайд по решению проблем"""
        from double_tunnel_docs import get_troubleshooting_guide
        return get_troubleshooting_guide()
    
    @staticmethod
    def get_setup_instructions(tunnel_type: str, tunnel_route: str = "") -> str:
        """Получает инструкции для конкретного типа туннеля"""
        if tunnel_type == 'double':
            return XrayDoubleTunnelConfig.get_setup_instructions()
        else:
            return """
🌐 <b>Подключение к обычному VPN</b>

1️⃣ <b>Выберите приложение:</b>
   • Android: V2RayNG, Clash for Android
   • Windows: Clash for Windows
   • Mac: ClashX, ClashX Pro
   • iOS: Shadowrocket

2️⃣ <b>Импортируйте конфиг:</b>
   • Скопируйте VLESS ссылку
   • Откройте приложение
   • Нажмите '+' и вставьте ссылку

3️⃣ <b>Подключитесь:</b>
   • Выберите конфигурацию
   • Нажмите "Connect" / "Подключиться"

4️⃣ <b>Проверьте IP:</b>
   • Откройте ipinfo.io
   • Должен быть IP вашего сервера
"""
