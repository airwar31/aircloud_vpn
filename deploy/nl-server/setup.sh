#!/bin/bash
# AirCloud VPN Setup Script
# Initializes the project with configuration and 3xui panel setup

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}"
echo "╔════════════════════════════════════════╗"
echo "║   AirCloud VPN - Setup Wizard v2.0     ║"
echo "║   Clean Architecture Deployment        ║"
echo "╚════════════════════════════════════════╝"
echo -e "${NC}"
echo ""

# Check if running on correct directory
if [ ! -f "docker-compose.yml" ]; then
    echo -e "${RED}❌ Error: docker-compose.yml not found!${NC}"
    echo -e "${YELLOW}Please run this script from nl-server or vk-server directory${NC}"
    exit 1
fi

# Check if it's NL or VK server
if grep -q "vpn-bot" docker-compose.yml; then
    SERVER_TYPE="nl"
    echo -e "${GREEN}✅ Detected NL Server${NC}"
else
    SERVER_TYPE="vk"
    echo -e "${GREEN}✅ Detected VK Server${NC}"
fi

echo ""
echo -e "${BLUE}=== Step 1: Environment Configuration ===${NC}"
echo ""

# Check if .env exists
if [ ! -f ".env" ]; then
    echo -e "${YELLOW}Creating .env file from .env.example...${NC}"
    cp .env.example .env
    echo -e "${GREEN}✅ .env created${NC}"
    echo ""
    echo -e "${YELLOW}Please edit .env file with your settings:${NC}"
    echo "  - BOT_TOKEN: Get from @BotFather"
    echo "  - ADMIN_IDS: Your Telegram user ID"
    echo "  - Server IPs: Verify NL and VK server addresses"
    echo ""
    read -p "Press Enter after editing .env... " -t 30 || true
else
    echo -e "${GREEN}✅ .env already exists${NC}"
fi

echo ""
echo -e "${BLUE}=== Step 2: Docker Image Preparation ===${NC}"
echo ""

# For NL server, build bot image
if [ "$SERVER_TYPE" = "nl" ]; then
    echo -e "${YELLOW}Building VPN Bot Docker image...${NC}"
    docker build -f Dockerfile.bot -t aircloud-vpn-bot:latest .
    echo -e "${GREEN}✅ Bot image built${NC}"
    echo ""
fi

echo -e "${YELLOW}Pulling 3xui image (ghcr.io/mhsanaei/3x-ui:latest)...${NC}"
docker pull ghcr.io/mhsanaei/3x-ui:latest
echo -e "${GREEN}✅ 3xui image ready${NC}"

echo ""
echo -e "${BLUE}=== Step 3: Service Startup ===${NC}"
echo ""

echo -e "${YELLOW}Starting services with docker-compose...${NC}"
docker-compose down --remove-orphans 2>/dev/null || true
docker-compose up -d

echo -e "${GREEN}✅ Services started${NC}"
echo ""

# Wait for xray-panel to be ready
echo -e "${YELLOW}⏳ Waiting for xray-panel to be ready (this may take 30-60 seconds)...${NC}"

max_attempts=60
attempt=0

while [ $attempt -lt $max_attempts ]; do
    if docker-compose logs xray-panel 2>/dev/null | grep -q "start success" || \
       docker exec $(docker-compose ps -q xray-panel 2>/dev/null) curl -s http://localhost:54321/panel/ > /dev/null 2>&1; then
        echo -e "${GREEN}✅ xray-panel is ready!${NC}"
        break
    fi
    
    attempt=$((attempt + 1))
    echo -n "."
    sleep 1
done

if [ $attempt -eq $max_attempts ]; then
    echo -e "${YELLOW}⚠️  xray-panel startup check timed out${NC}"
    echo -e "${YELLOW}The service may still be initializing. Check logs with:${NC}"
    echo "  docker-compose logs -f xray-panel"
fi

echo ""
echo -e "${BLUE}=== Step 4: Access Information ===${NC}"
echo ""

# Get the current server IP
if [ "$SERVER_TYPE" = "nl" ]; then
    echo -e "${GREEN}NL Server Configuration:${NC}"
    echo "  🌐 Web Panel: http://localhost:54321"
    echo "  🔐 Default: admin / admin"
    echo "  📋 Change password immediately!"
    echo ""
    
    echo -e "${GREEN}Bot Service:${NC}"
    echo "  🤖 Status: Check with 'docker-compose logs vpn-bot'"
    echo "  ℹ️  Bot will connect to xray-panel automatically"
    echo ""
    
    echo -e "${YELLOW}Next steps:${NC}"
    echo "  1. Access the 3xui panel (http://localhost:54321)"
    echo "  2. Change default admin password"
    echo "  3. Verify two inbounds are configured:"
    echo "     - Inbound 0: Port 8443 (Single Tunnel, TLS)"
    echo "     - Inbound 1: Port 443 (Double Tunnel, TLS)"
    echo "  4. Bot will manage clients automatically via API"
    echo ""
else
    echo -e "${GREEN}VK Server Configuration:${NC}"
    echo "  🌐 Web Panel: http://localhost:54321"
    echo "  🔐 Default: admin / admin"
    echo "  📋 Change password immediately!"
    echo ""
    
    echo -e "${YELLOW}Important:${NC}"
    echo "  This server should have Reality protocol configured"
    echo "  for obfuscation. Configure in the 3xui panel."
    echo ""
fi

echo -e "${GREEN}Useful Commands:${NC}"
echo "  View logs: docker-compose logs -f"
echo "  Restart services: docker-compose restart"
echo "  Stop services: docker-compose down"
echo "  Service status: docker-compose ps"
echo ""

echo -e "${BLUE}=== Setup Complete! ===${NC}"
echo ""
echo -e "${GREEN}✅ Your AirCloud VPN deployment is ready!${NC}"
echo ""

# Show service status
echo -e "${BLUE}Current Service Status:${NC}"
docker-compose ps

echo ""
echo -e "${YELLOW}For support, visit: https://github.com/yourusername/aircloud_vpn${NC}"
