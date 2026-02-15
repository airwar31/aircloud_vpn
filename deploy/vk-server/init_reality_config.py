#!/usr/bin/env python3
"""
Скрипт для автоматического получения Reality конфигурации из 3xui панели
и обновления .env файла
"""

import os
import sys
import json
import asyncio
import aiohttp
from pathlib import Path
from urllib.parse import urljoin
import argparse
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class XrayRealityConfigurator:
    """Получает Reality конфигурацию из 3xui и обновляет .env"""
    
    def __init__(self, host: str, port: int, username: str, password: str, env_path: str = ".env"):
        """
        Инициализация конфигуратора
        
        Args:
            host: IP адрес 3xui панели
            port: Порт 3xui панели
            username: Логин админа
            password: Пароль админа
            env_path: Путь к .env файлу
        """
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.env_path = env_path
        self.base_url = f"http://{host}:{port}"
        self.session: aiohttp.ClientSession = None
        self.token = None
    
    async def __aenter__(self):
        """Контекстный менеджер - вход"""
        self.session = aiohttp.ClientSession()
        await self.login()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Контекстный менеджер - выход"""
        if self.session:
            await self.session.close()
    
    async def login(self):
        """Авторизоваться в 3xui панели"""
        try:
            login_url = urljoin(self.base_url, "/api/login")
            data = {
                "username": self.username,
                "password": self.password
            }
            
            logger.info(f"Подключение к 3xui панели: {self.base_url}")
            
            async with self.session.post(login_url, json=data, verify_ssl=False) as resp:
                if resp.status != 200:
                    raise Exception(f"Ошибка авторизации: {resp.status}")
                
                result = await resp.json()
                
                if not result.get("success"):
                    raise Exception(f"Ошибка входа: {result.get('msg', 'Неизвестная ошибка')}")
                
                self.token = result.get("obj")
                logger.info("✅ Успешная авторизация в 3xui")
        
        except Exception as e:
            logger.error(f"❌ Ошибка авторизации: {e}")
            raise
    
    async def get_inbound_config(self, inbound_id: int = 1):
        """
        Получить конфигурацию inbound (содержит Reality параметры)
        
        Args:
            inbound_id: ID inbound'а (обычно 1 для входной точки)
        
        Returns:
            Словарь с конфигурацией
        """
        try:
            config_url = urljoin(self.base_url, f"/api/inbounds/get/{inbound_id}")
            
            headers = {"Authorization": self.token} if self.token else {}
            
            logger.info(f"Получение конфигурации inbound {inbound_id}...")
            
            async with self.session.get(config_url, headers=headers, verify_ssl=False) as resp:
                if resp.status != 200:
                    raise Exception(f"Ошибка получения конфига: {resp.status}")
                
                result = await resp.json()
                
                if not result.get("success"):
                    raise Exception(f"Ошибка: {result.get('msg')}")
                
                inbound_data = result.get("obj", {})
                logger.info("✅ Конфигурация получена")
                
                return inbound_data
        
        except Exception as e:
            logger.error(f"❌ Ошибка получения конфигурации: {e}")
            raise
    
    async def extract_reality_config(self, inbound_config: dict) -> dict:
        """
        Извлечь Reality параметры из конфигурации inbound'а
        
        Args:
            inbound_config: Конфигурация inbound'а
        
        Returns:
            Словарь с Reality параметрами
        """
        try:
            # Структура в 3xui для Reality:
            # streamSettings -> realitySettings
            stream_settings = inbound_config.get("streamSettings", {})
            reality_settings = stream_settings.get("realitySettings", {})
            
            if not reality_settings:
                logger.warning("⚠️  Reality конфигурация не найдена")
                return {}
            
            config = {
                "publicKey": reality_settings.get("publicKey", ""),
                "shortIds": reality_settings.get("shortIds", []),
                "fingerprint": stream_settings.get("tlsSettings", {}).get("fingerprint", "chrome"),
                "serverName": stream_settings.get("realitySettings", {}).get("serverName", "dl.google.com"),
            }
            
            # Из shortIds берем первый или генерируем
            if config["shortIds"]:
                config["shortId"] = config["shortIds"][0] if isinstance(config["shortIds"], list) else config["shortIds"]
            else:
                config["shortId"] = "SHORT_ID"
            
            logger.info("✅ Reality параметры извлечены")
            logger.info(f"   Public Key: {config['publicKey'][:20]}...")
            logger.info(f"   Short ID: {config['shortId']}")
            
            return config
        
        except Exception as e:
            logger.error(f"❌ Ошибка извлечения Reality параметров: {e}")
            raise
    
    def update_env_file(self, reality_config: dict):
        """
        Обновить .env файл с Reality параметрами
        
        Args:
            reality_config: Словарь с Reality параметрами
        """
        try:
            env_path = Path(self.env_path)
            
            if not env_path.exists():
                logger.warning(f"⚠️  Файл {self.env_path} не найден, создаю новый...")
                env_path.touch()
            
            # Читаем существующий .env
            env_content = env_path.read_text(encoding='utf-8') if env_path.exists() else ""
            
            # Обновляем значения
            updates = {
                "REALITY_PUBLIC_KEY": reality_config.get("publicKey", ""),
                "REALITY_SHORT_ID": reality_config.get("shortId", ""),
                "REALITY_FINGERPRINT": reality_config.get("fingerprint", "chrome"),
                "REALITY_SNI": reality_config.get("serverName", "dl.google.com"),
            }
            
            # Обновляем или добавляем строки
            lines = env_content.split('\n')
            updated_lines = []
            updated_keys = set()
            
            for line in lines:
                updated = False
                for key, value in updates.items():
                    if line.startswith(f"{key}="):
                        updated_lines.append(f"{key}={value}")
                        updated_keys.add(key)
                        updated = True
                        break
                
                if not updated:
                    updated_lines.append(line)
            
            # Добавляем отсутствующие ключи
            for key, value in updates.items():
                if key not in updated_keys:
                    updated_lines.append(f"{key}={value}")
            
            # Пишем обновленный .env
            env_path.write_text('\n'.join(updated_lines), encoding='utf-8')
            
            logger.info(f"✅ .env файл обновлен: {self.env_path}")
            logger.info(f"   REALITY_PUBLIC_KEY={updates['REALITY_PUBLIC_KEY'][:20]}...")
            logger.info(f"   REALITY_SHORT_ID={updates['REALITY_SHORT_ID']}")
            logger.info(f"   REALITY_FINGERPRINT={updates['REALITY_FINGERPRINT']}")
            logger.info(f"   REALITY_SNI={updates['REALITY_SNI']}")
        
        except Exception as e:
            logger.error(f"❌ Ошибка обновления .env: {e}")
            raise
    
    async def configure(self, inbound_id: int = 1):
        """
        Основной метод: получить конфиг и обновить .env
        
        Args:
            inbound_id: ID inbound'а для получения конфигурации
        """
        try:
            logger.info("🔄 Запуск конфигурации Reality...")
            
            # Получаем конфигурацию inbound'а
            inbound_config = await self.get_inbound_config(inbound_id)
            
            # Извлекаем Reality параметры
            reality_config = await self.extract_reality_config(inbound_config)
            
            if not reality_config:
                logger.error("❌ Не удалось получить Reality конфигурацию")
                return False
            
            # Обновляем .env файл
            self.update_env_file(reality_config)
            
            logger.info("✅ Конфигурация Reality успешно завершена!")
            return True
        
        except Exception as e:
            logger.error(f"❌ Ошибка конфигурации: {e}")
            return False


async def main():
    """Главная функция"""
    
    parser = argparse.ArgumentParser(
        description="Автоматически получить Reality конфиг из 3xui и обновить .env"
    )
    
    parser.add_argument(
        "--host",
        default=os.getenv("VK_XRAY_HOST", "89.208.86.167"),
        help="IP адрес 3xui панели (по умолчанию из .env)"
    )
    
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.getenv("VK_XRAY_PORT", "54321")),
        help="Порт 3xui панели"
    )
    
    parser.add_argument(
        "--username",
        default=os.getenv("VK_XRAY_USERNAME"),
        help="Логин администратора 3xui"
    )
    
    parser.add_argument(
        "--password",
        default=os.getenv("VK_XRAY_PASSWORD"),
        help="Пароль администратора 3xui"
    )
    
    parser.add_argument(
        "--env",
        default=".env",
        help="Путь к .env файлу"
    )
    
    parser.add_argument(
        "--inbound-id",
        type=int,
        default=1,
        help="ID inbound'а для получения конфигурации (по умолчанию 1)"
    )
    
    args = parser.parse_args()
    
    # Проверяем обязательные параметры
    if not args.username or not args.password:
        logger.error("❌ Необходимо указать username и password")
        logger.error("   Используйте --username и --password")
        logger.error("   Или установите VK_XRAY_USERNAME и VK_XRAY_PASSWORD в .env")
        sys.exit(1)
    
    logger.info("=" * 60)
    logger.info("АВТОМАТИЧЕСКАЯ КОНФИГУРАЦИЯ REALITY")
    logger.info("=" * 60)
    logger.info(f"Host: {args.host}:{args.port}")
    logger.info(f"Inbound ID: {args.inbound_id}")
    logger.info(f".env файл: {args.env}")
    logger.info("=" * 60)
    
    try:
        async with XrayRealityConfigurator(
            host=args.host,
            port=args.port,
            username=args.username,
            password=args.password,
            env_path=args.env
        ) as configurator:
            success = await configurator.configure(inbound_id=args.inbound_id)
            
            if success:
                logger.info("\n✅ Готово!")
                logger.info("Теперь вы можете использовать значения из .env")
                sys.exit(0)
            else:
                logger.error("\n❌ Скрипт завершился с ошибкой")
                sys.exit(1)
    
    except Exception as e:
        logger.error(f"\n❌ Критическая ошибка: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
