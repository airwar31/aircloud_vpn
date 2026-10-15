#!/bin/bash
# AirCloud VPN VK Server Setup
# Initializes Reality inbound for double tunnel support

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}"
echo "╔════════════════════════════════════════╗"
echo "║   AirCloud VPN VK Server Setup v2.0    ║"
echo "║   Reality Obfuscation Entry Point      ║"
echo "╚════════════════════════════════════════╝"
echo -e "${NC}"
echo ""

# Check if running on correct directory
if [ ! -f "docker-compose.yml" ]; then
    echo -e "${RED}❌ Error: docker-compose.yml not found!${NC}"
    echo -e "${YELLOW}Please run this script from vk-server directory${NC}"
    exit 1
fi

echo ""
echo -e "${BLUE}=== Step 1: Environment Configuration ===${NC}"
echo ""

# Check if .env exists
if [ ! -f ".env" ]; then
    echo -e "${YELLOW}Creating empty .env file...${NC}"
    touch .env
    echo -e "${GREEN}✅ .env created${NC}"
    echo ""
    echo -e "${YELLOW}Recommended settings for VK Server:${NC}"
    echo "  VK_XRAY_HOST: $(hostname -I | awk '{print $1}') (your VK server IP)"
    echo "  VK_XRAY_USERNAME: your panel username"
    echo "  VK_XRAY_PASSWORD: your panel password"
else
    echo -e "${GREEN}✅ .env already exists${NC}"
fi

echo ""
echo -e "${BLUE}=== Step 2: Docker Image Preparation ===${NC}"
echo ""

echo -e "${YELLOW}Pulling 3xui image (ghcr.io/mhsanaei/3x-ui:latest)...${NC}"
docker pull ghcr.io/mhsanaei/3x-ui:latest
echo -e "${GREEN}✅ 3xui image ready${NC}"

echo ""
echo -e "${BLUE}=== Step 3: Service Startup ===${NC}"
echo ""

echo -e "${YELLOW}Starting xray-panel service...${NC}"
docker-compose down --remove-orphans 2>/dev/null || true
docker-compose up -d xray-panel

echo -e "${GREEN}✅ Service started${NC}"
echo ""

# Wait for xray-panel to be ready
echo -e "${YELLOW}⏳ Waiting for xray-panel to be ready...${NC}"

max_attempts=60
attempt=0

while [ $attempt -lt $max_attempts ]; do
    if docker-compose logs xray-panel 2>/dev/null | grep -q "start success" || \
       docker exec $(docker-compose ps -q xray-panel 2>/dev/null) curl -s http://localhost:2053/panel/ > /dev/null 2>&1; then
        echo -e "${GREEN}✅ xray-panel is ready!${NC}"
        break
    fi
    
    attempt=$((attempt + 1))
    echo -n "."
    sleep 1
done

if [ $attempt -eq $max_attempts ]; then
    echo -e "${YELLOW}⚠️  xray-panel startup check timed out${NC}"
fi

echo ""
echo -e "${BLUE}=== Step 4: Configuration Instructions ===${NC}"
echo ""

# Get server IP
SERVER_IP=$(hostname -I | awk '{print $1}')

echo -e "${GREEN}VK Server Information:${NC}"
echo "  Server IP: $SERVER_IP"
echo "  🌐 Web Panel: http://$SERVER_IP:54321"
echo "  🔐 Default: admin / admin"
echo ""

echo -e "${YELLOW}Manual Configuration Required:${NC}"
echo ""
echo "1. Access the 3xui panel:"
echo "   http://$SERVER_IP:54321"
echo ""
echo "2. Login with admin/admin"
echo ""
echo "3. Configure Reality Protocol on Port 443:"
echo "   - Go to: Inbound Settings"
echo "   - Create new inbound:"
echo "     * Port: 443"
echo "     * Protocol: VLESS"
echo "     * Security: Reality"
echo "     * Settings:"
echo "       - Generate new reality keypair"
echo "       - Fingerprint: chrome"
echo "       - ServerName (SNI): dl.google.com"
echo "       - Public Key: [copy to NL server config]"
echo "       - Short ID: [save for reference]"
echo ""
echo "4. Configure outbound to NL server:"
echo "   - Add outbound pointing to your NL exit server (${NL_SERVER_IP:-<NL_SERVER_IP>}:443)"
echo "   - This chains Double Tunnel traffic to NL exit point"
echo ""

echo -e "${YELLOW}For Double Tunnel Support:${NC}"
echo "  - Copy Reality public key from VK panel"
echo "  - Store in NL server's config.py REALITY_PARAMS"
echo "  - Bot will use these credentials for double tunnel clients"
echo ""

echo -e "${GREEN}Useful Commands:${NC}"
echo "  View logs: docker-compose logs -f"
echo "  Restart service: docker-compose restart"
echo "  Stop service: docker-compose down"
echo "  Service status: docker-compose ps"
echo ""

echo -e "${BLUE}=== Setup Complete! ===${NC}"
echo ""
echo -e "${GREEN}✅ VK Server is ready for configuration!${NC}"
echo ""

# Show service status
echo -e "${BLUE}Current Service Status:${NC}"
docker-compose ps

echo ""
echo -e "${YELLOW}⚠️  IMPORTANT NEXT STEPS:${NC}"
echo "1. Log in to 3xui panel and configure Reality inbound"
echo "2. Copy the Reality public key to NL server config"
echo "3. Restart NL server bot to use new Reality parameters"
echo ""
echo -e "${YELLOW}For support, visit: https://github.com/yourusername/aircloud_vpn${NC}"
