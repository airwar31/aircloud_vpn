#!/bin/bash
# AirCloud VPN Bot Entrypoint Script
# Initializes the bot environment and starts the application

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}🚀 AirCloud VPN Bot Starting...${NC}"

# Create necessary directories
echo -e "${YELLOW}📁 Creating data directories...${NC}"
mkdir -p /app/data
mkdir -p /app/logs

# Check if .env exists
if [ ! -f /app/.env ]; then
    echo -e "${RED}❌ .env file not found!${NC}"
    echo -e "${YELLOW}Please create /app/.env using .env.example as template${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Environment file found${NC}"

# Check BOT_TOKEN
if [ -z "$BOT_TOKEN" ]; then
    echo -e "${RED}❌ BOT_TOKEN is not set!${NC}"
    echo -e "${YELLOW}Please set BOT_TOKEN in .env file${NC}"
    exit 1
fi

echo -e "${GREEN}✅ BOT_TOKEN is configured${NC}"

# Check database
if [ ! -f /app/data/users.db ]; then
    echo -e "${YELLOW}🔄 Creating new database...${NC}"
    python3 -c "
import sys
sys.path.insert(0, '/app')
import asyncio
from bot_app.database import Database

async def init_db():
    db = Database('/app/data/users.db')
    await db.init()
    await db.close()

asyncio.run(init_db())
" || {
        echo -e "${RED}❌ Failed to initialize database${NC}"
        exit 1
    }
    echo -e "${GREEN}✅ Database initialized${NC}"
else
    echo -e "${GREEN}✅ Database already exists${NC}"
fi

# Test database connection
echo -e "${YELLOW}🔗 Testing database connection...${NC}"
python3 -c "
import sys
sys.path.insert(0, '/app')
import asyncio
import sqlite3

try:
    conn = sqlite3.connect('/app/data/users.db')
    cursor = conn.cursor()
    cursor.execute('SELECT COUNT(*) FROM users')
    count = cursor.fetchone()[0]
    print(f'✅ Database connected (Users: {count})')
    conn.close()
except Exception as e:
    print(f'❌ Database error: {e}')
    sys.exit(1)
" || exit 1

# Test Xray API connectivity (optional, don't fail if unavailable)
echo -e "${YELLOW}🔗 Testing Xray API connectivity...${NC}"
timeout 5 python3 -c "
import sys
sys.path.insert(0, '/app')
import asyncio
from bot_app.xray_api import XrayAPI

async def test_api():
    try:
        api = XrayAPI(
            host='${XRAY_HOST:-xray-panel}',
            port=${XRAY_PORT:-2053},
            username='${XRAY_USERNAME:-admin}',
            password='${XRAY_PASSWORD:-admin}'
        )
        async with api:
            stats = await api.get_stats()
        print('✅ Xray API connected')
        return True
    except Exception as e:
        print(f'⚠️  Xray API not available yet: {e}')
        print('   Bot will retry when needed')
        return False

asyncio.run(test_api())
" || echo "⚠️  Xray API connection test skipped"

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}✅ All checks passed!${NC}"
echo -e "${GREEN}✅ Starting AirCloud VPN Bot...${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

# Start the bot
exec python3 -m bot_app.bot
