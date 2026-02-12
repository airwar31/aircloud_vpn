#!/bin/bash

# ═══════════════════════════════════════════════════════════════
# 🚀 СКРИПТ РАЗВЕРТЫВАНИЯ НА ОБА СЕРВЕРА
# ═══════════════════════════════════════════════════════════════

set -e

# Конфигурация серверов
VK_SERVER="89.208.86.167"
NL_SERVER="5.129.224.166"
VK_USER="root"
NL_USER="root"
PROJECT_DIR="aircloud_vpn"

# Цвета для логирования
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[✅ OK]${NC} $1"
}

log_error() {
    echo -e "${RED}[❌ ERROR]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[⚠️  WARN]${NC} $1"
}

# ═══════════════════════════════════════════════════════════════
# ФУНКЦИЯ: Синхронизация на VK сервер
# ═══════════════════════════════════════════════════════════════
deploy_to_vk() {
    log_info "════════════════════════════════════════════════════════"
    log_info "📤 РАЗВЕРТЫВАНИЕ НА VK СЕРВЕР (89.208.86.167)"
    log_info "════════════════════════════════════════════════════════"
    
    log_info "Копирование docker-compose.yml..."
    scp docker-configs/docker-compose.yml ${VK_USER}@${VK_SERVER}:~/${PROJECT_DIR}/docker-compose.yml
    log_success "docker-compose.yml скопирован"
    
    log_info "Копирование .env..."
    scp docker-configs/.env ${VK_USER}@${VK_SERVER}:~/${PROJECT_DIR}/docker-configs/.env
    log_success ".env скопирован"
    
    log_info "Копирование VK конфига..."
    scp docker-configs/vk-server/config.json ${VK_USER}@${VK_SERVER}:~/${PROJECT_DIR}/docker-configs/vk-server/config.json
    log_success "VK config.json скопирован"
    
    log_info "Копирование Dockerfile для VK..."
    scp docker-configs/vk-server/Dockerfile ${VK_USER}@${VK_SERVER}:~/${PROJECT_DIR}/docker-configs/vk-server/Dockerfile
    log_success "VK Dockerfile скопирован"
    
    log_warning "Копирование core_vpn/*..."
    scp -r docker-configs/vk-server/core_vpn/* ${VK_USER}@${VK_SERVER}:~/${PROJECT_DIR}/docker-configs/vk-server/core_vpn/
    log_success "core_vpn/* скопирован"
}

# ═══════════════════════════════════════════════════════════════
# ФУНКЦИЯ: Синхронизация на NL сервер
# ═══════════════════════════════════════════════════════════════
deploy_to_nl() {
    log_info "════════════════════════════════════════════════════════"
    log_info "📤 РАЗВЕРТЫВАНИЕ НА NL СЕРВЕР (5.129.224.166)"
    log_info "════════════════════════════════════════════════════════"
    
    log_info "Копирование docker-compose.yml..."
    scp docker-configs/docker-compose.yml ${NL_USER}@${NL_SERVER}:~/${PROJECT_DIR}/docker-compose.yml
    log_success "docker-compose.yml скопирован"
    
    log_info "Копирование .env..."
    scp docker-configs/.env ${NL_USER}@${NL_SERVER}:~/${PROJECT_DIR}/docker-configs/.env
    log_success ".env скопирован"
    
    log_info "Копирование NL конфига..."
    scp docker-configs/nl-server/config.json ${NL_USER}@${NL_SERVER}:~/${PROJECT_DIR}/docker-configs/nl-server/config.json
    log_success "NL config.json скопирован"
    
    log_info "Копирование Dockerfile для NL..."
    scp docker-configs/nl-server/Dockerfile ${NL_USER}@${NL_SERVER}:~/${PROJECT_DIR}/docker-configs/nl-server/Dockerfile
    log_success "NL Dockerfile скопирован"
    
    log_info "Копирование bot_app/*..."
    scp -r docker-configs/nl-server/bot_app/* ${NL_USER}@${NL_SERVER}:~/${PROJECT_DIR}/docker-configs/nl-server/bot_app/
    log_success "bot_app/* скопирован"
    
    log_info "Копирование core_vpn/*..."
    scp -r docker-configs/nl-server/core_vpn/* ${NL_USER}@${NL_SERVER}:~/${PROJECT_DIR}/docker-configs/nl-server/core_vpn/
    log_success "core_vpn/* скопирован"
}

# ═══════════════════════════════════════════════════════════════
# ФУНКЦИЯ: Запуск контейнеров на VK
# ═══════════════════════════════════════════════════════════════
start_vk_containers() {
    log_info "════════════════════════════════════════════════════════"
    log_info "🐳 ЗАПУСК КОНТЕЙНЕРОВ НА VK"
    log_info "════════════════════════════════════════════════════════"
    
    ssh ${VK_USER}@${VK_SERVER} << 'EOF'
        cd ~/${PROJECT_DIR}
        log_info "Остановка старых контейнеров..."
        docker-compose down 2>/dev/null || true
        
        log_info "Сборка VK контейнера..."
        docker-compose build vk-server
        
        log_info "Запуск VK контейнера..."
        docker-compose up -d vk-server
        
        log_info "Проверка статуса..."
        docker ps
        
        log_info "Логи контейнера..."
        docker logs --tail 20 vk-xray-server
EOF

    log_success "VK контейнеры запущены"
}

# ═══════════════════════════════════════════════════════════════
# ФУНКЦИЯ: Запуск контейнеров на NL
# ═══════════════════════════════════════════════════════════════
start_nl_containers() {
    log_info "════════════════════════════════════════════════════════"
    log_info "🐳 ЗАПУСК КОНТЕЙНЕРОВ НА NL"
    log_info "════════════════════════════════════════════════════════"
    
    ssh ${NL_USER}@${NL_SERVER} << 'EOF'
        cd ~/${PROJECT_DIR}
        log_info "Остановка старых контейнеров..."
        docker-compose down 2>/dev/null || true
        
        log_info "Сборка NL контейнера..."
        docker-compose build nl-server vpn-bot
        
        log_info "Запуск NL контейнеров..."
        docker-compose up -d nl-server vpn-bot
        
        log_info "Проверка статуса..."
        docker ps
        
        log_info "Логи nl-server..."
        docker logs --tail 20 nl-xray-server
        
        log_info "Логи bot..."
        docker logs --tail 20 vpn-telegram-bot
EOF

    log_success "NL контейнеры запущены"
}

# ═══════════════════════════════════════════════════════════════
# ГЛАВНОЕ МЕНЮ
# ═══════════════════════════════════════════════════════════════

echo ""
echo -e "${BLUE}╔═══════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║   🚀 СКРИПТ РАЗВЕРТЫВАНИЯ НА ОБА СЕРВЕРА             ║${NC}"
echo -e "${BLUE}╚═══════════════════════════════════════════════════════╝${NC}"
echo ""
echo "Выберите действие:"
echo "1) Развернуть на VK сервер (только копирование файлов)"
echo "2) Развернуть на NL сервер (только копирование файлов)"
echo "3) Запустить контейнеры на VK"
echo "4) Запустить контейнеры на NL"
echo "5) ✅ Полное развертывание (ВСЕ ШАГИ)"
echo "6) ❌ Выход"
echo ""
read -p "Введите номер (1-6): " choice

case $choice in
    1)
        deploy_to_vk
        ;;
    2)
        deploy_to_nl
        ;;
    3)
        start_vk_containers
        ;;
    4)
        start_nl_containers
        ;;
    5)
        deploy_to_vk
        echo ""
        deploy_to_nl
        echo ""
        read -p "Запустить контейнеры на VK? (y/n): " vk_run
        if [ "$vk_run" = "y" ]; then
            start_vk_containers
        fi
        echo ""
        read -p "Запустить контейнеры на NL? (y/n): " nl_run
        if [ "$nl_run" = "y" ]; then
            start_nl_containers
        fi
        log_success "✅ Полное развертывание завершено!"
        ;;
    6)
        log_info "Выход..."
        exit 0
        ;;
    *)
        log_error "Неверный выбор!"
        exit 1
        ;;
esac

echo ""
log_success "════════════════════════════════════════════════════════"
log_success "✅ ОПЕРАЦИЯ ЗАВЕРШЕНА"
log_success "════════════════════════════════════════════════════════"
