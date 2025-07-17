import json
import os
import sys

# Путь к конфигурационному файлу X UI
CONFIG_FILE = "config.json"

def fix_vless_config():
    """Исправляет конфигурацию VLESS, добавляя параметр decryption:none"""
    try:
        # Проверяем существование файла
        if not os.path.exists(CONFIG_FILE):
            print(f"Файл конфигурации не найден: {CONFIG_FILE}")
            print("Пожалуйста, укажите правильный путь к файлу конфигурации X UI.")
            return False
        
        # Читаем текущую конфигурацию
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        # Ищем настройки VLESS и добавляем decryption:none
        modified = False
        
        # Проверяем структуру конфигурации
        if 'inbounds' in config:
            for inbound in config['inbounds']:
                if inbound.get('protocol') == 'vless':
                    # Проверяем settings
                    if 'settings' in inbound:
                        # Если settings равен None, создаем словарь
                        if inbound['settings'] is None:
                            inbound['settings'] = {}
                            
                        # Добавляем decryption:none в settings
                        if 'decryption' not in inbound['settings']:
                            inbound['settings']['decryption'] = 'none'
                            modified = True
                            print(f"Добавлен параметр decryption:none для inbound {inbound.get('tag', 'unknown')}")
                        
                        # Проверяем клиентов
                        if 'clients' in inbound['settings'] and inbound['settings']['clients']:
                            for client in inbound['settings']['clients']:
                                if 'decryption' not in client:
                                    client['decryption'] = 'none'
                                    modified = True
                                    print(f"Добавлен параметр decryption:none для клиента {client.get('id', 'unknown')}")
        
        # Сохраняем изменения, если были модификации
        if modified:
            with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2)
            print("Конфигурация успешно обновлена!")
            return True
        else:
            print("Параметр decryption:none уже присутствует во всех настройках VLESS или VLESS не используется.")
            return False
    
    except Exception as e:
        print(f"Ошибка при обновлении конфигурации: {str(e)}")
        return False

if __name__ == "__main__":
    # Если передан аргумент с путем к файлу конфигурации
    if len(sys.argv) > 1:
        CONFIG_FILE = sys.argv[1]
    
    fix_vless_config()