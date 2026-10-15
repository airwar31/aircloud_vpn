#!/usr/bin/env python3
"""
Скрипт для автоматического получения TLS конфигурации из 3xui панели NL сервера
и обновления .env файла
"""

import os
import sys
import asyncio
import aiohttp
from pathlib import Path
from urllib.parse import urljoin
import argparse
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class XrayTLSConfigurator:
    """Получает TLS конфигурацию из 3xui и обновляет .env"""
    
    def __init__(self, host: str, port: int, username: str, password: str, env_path: str = ".env"):
        """
        Инициализация конфигуратора
        
        Args:
            host: IP адрес 3xui панели NL
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
            
            logger.info(f"Подключение к 3xui панели NL: {self.base_url}")
            
            async with self.session.post(login_url, json=data, verify_ssl=False) as resp:
                if resp.status != 200:
                    raise Exception(f"Ошибка авторизации: {resp.status}")
                
                result = await resp.json()
                
                if not result.get("success"):
                    raise Exception(f"Ошибка входа: {result.get('msg', 'Неизвестная ошибка')}")
                
                self.token = result.get("obj")
                logger.info("✅ Успешная авторизация в 3xui NL")
        
        except Exception as e:
            logger.error(f"❌ Ошибка авторизации: {e}")
            raise
    
    async def get_inbound_config(self, inbound_id: int = 0):
        """
        Получить конфигурацию inbound'а (содержит TLS параметры)
        
        Args:
            inbound_id: ID inbound'а (обычно 0 для TLS входной точки NL)
        
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
    
    async def extract_tls_config(self, inbound_config: dict) -> dict:
        """
        Извлечь TLS параметры из конфигурации inbound'а
        
        Args:
            inbound_config: Конфигурация inbound'а
        
        Returns:
            Словарь с TLS параметрами
        """
        try:
            # Структура в 3xui для TLS:
            # streamSettings -> tlsSettings
            stream_settings = inbound_config.get("streamSettings", {})
            tls_settings = stream_settings.get("tlsSettings", {})
            
            if not tls_settings:
                logger.warning("⚠️  TLS конфигурация не найдена")
                return {}
            
            # Пытаемся получить сертификат и ключ
            certs = tls_settings.get("certificates", [])
            
            config = {
                "certificate": "",
                "key": "",
                "serverName": tls_settings.get("serverName", "example.com"),
                "alpn": ",".join(tls_settings.get("alpn", ["h2", "http/1.1"])) if tls_settings.get("alpn") else "h2,http/1.1",
            }
            
            # Извлекаем сертификат и ключ, если есть
            if certs and len(certs) > 0:
                cert = certs[0]
                config["certificate"] = cert.get("certificateFile", "")
                config["key"] = cert.get("keyFile", "")
                
                logger.info(f"✅ TLS параметры найдены")
                logger.info(f"   Server Name: {config['serverName']}")
                logger.info(f"   ALPN: {config['alpn']}")
            else:
                logger.warning("⚠️  Сертификаты не найдены в конфигурации")
            
            return config
        
        except Exception as e:
            logger.error(f"❌ Ошибка извлечения TLS параметров: {e}")
            raise
    
    def update_env_file(self, tls_config: dict):
        """
        Обновить .env файл с TLS параметрами
        
        Args:
            tls_config: Словарь с TLS параметрами
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
                "NL_TLS_SERVER_NAME": tls_config.get("serverName", "example.com"),
                "NL_TLS_ALPN": tls_config.get("alpn", "h2,http/1.1"),
            }
            
            if tls_config.get("certificate"):
                updates["NL_TLS_CERTIFICATE_FILE"] = tls_config["certificate"]
            
            if tls_config.get("key"):
                updates["NL_TLS_KEY_FILE"] = tls_config["key"]
            
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
            for key, value in updates.items():
                logger.info(f"   {key}={value}")
        
        except Exception as e:
            logger.error(f"❌ Ошибка обновления .env: {e}")
            raise
    
    async def configure(self, inbound_id: int = 0):
        """
        Основной метод: получить конфиг и обновить .env
        
        Args:
            inbound_id: ID inbound'а для получения конфигурации
        """
        try:
            logger.info("🔄 Запуск конфигурации TLS NL сервера...")
            
            # Получаем конфигурацию inbound'а
            inbound_config = await self.get_inbound_config(inbound_id)
            
            # Извлекаем TLS параметры
            tls_config = await self.extract_tls_config(inbound_config)
            
            if not tls_config:
                logger.error("❌ Не удалось получить TLS конфигурацию")
                return False
            
            # Обновляем .env файл
            self.update_env_file(tls_config)
            
            logger.info("✅ Конфигурация TLS успешно завершена!")
            return True
        
        except Exception as e:
            logger.error(f"❌ Ошибка конфигурации: {e}")
            return False


async def main():
    """Главная функция"""
    
    parser = argparse.ArgumentParser(
        description="Автоматически получить TLS конфиг из 3xui NL и обновить .env"
    )
    
    parser.add_argument(
        "--host",
        default=os.getenv("NL_SERVER_IP", "127.0.0.1"),
        help="IP адрес 3xui панели NL (по умолчанию из .env)"
    )
    
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.getenv("NL_SERVER_PORT", "8443")),
        help="Порт 3xui панели"
    )
    
    parser.add_argument(
        "--username",
        default=os.getenv("NL_SERVER_USERNAME"),
        help="Логин администратора 3xui"
    )
    
    parser.add_argument(
        "--password",
        default=os.getenv("NL_SERVER_PASSWORD"),
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
        default=0,
        help="ID inbound'а для получения конфигурации (по умолчанию 0)"
    )
    
    args = parser.parse_args()
    
    # Проверяем обязательные параметры
    if not args.username or not args.password:
        logger.error("❌ Необходимо указать username и password")
        logger.error("   Используйте --username и --password")
        logger.error("   Или установите NL_SERVER_USERNAME и NL_SERVER_PASSWORD в .env")
        sys.exit(1)
    
    logger.info("=" * 60)
    logger.info("АВТОМАТИЧЕСКАЯ КОНФИГУРАЦИЯ TLS (NL СЕРВЕР)")
    logger.info("=" * 60)
    logger.info(f"Host: {args.host}:{args.port}")
    logger.info(f"Inbound ID: {args.inbound_id}")
    logger.info(f".env файл: {args.env}")
    logger.info("=" * 60)
    
    try:
        async with XrayTLSConfigurator(
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
