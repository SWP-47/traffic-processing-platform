#!/bin/bash

# ==============================================================================
# CnSS Production Environment Cleanup Script
# Stops and removes all production containers, networks, and volumes.
# WARNING: This will permanently delete all TimescaleDB and Redis data.
# ==============================================================================

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}========================================================${NC}"
echo -e "${YELLOW}WARNING: Full Production Environment Cleanup for CnSS${NC}"
echo -e "${BLUE}========================================================${NC}"
echo ""
echo -e "${RED}This script will perform the following actions:${NC}"
echo "  1. Stop all running production containers."
echo "  2. Remove containers and Docker networks."
echo -e "  3. ${RED}PERMANENTLY DELETE Docker volumes (TimescaleDB & Redis data).${NC}"
echo ""

# Prompt for confirmation
read -p "Are you absolutely sure you want to proceed? (type 'YES' to confirm): " CONFIRM

if [ "$CONFIRM" != "YES" ]; then
    echo -e "${YELLOW}Operation cancelled. No changes were made.${NC}"
    exit 0
fi

echo ""
echo -e "${GREEN}Starting cleanup process...${NC}"

# 1. Stop and remove containers, networks, and volumes
echo -e "${BLUE}[1/3] Stopping and removing containers and volumes...${NC}"
docker compose -f docker-compose.yml down -v --remove-orphans

if [ $? -ne 0 ]; then
    echo -e "${RED}Error during 'docker compose down'. Check logs above.${NC}"
    exit 1
fi

# 2. Clean up dangling images (optional but recommended for a clean server)
echo -e "${BLUE}[2/3] Cleaning up dangling Docker images...${NC}"
docker image prune -f

# 3. Verify cleanup status
echo -e "${BLUE}[3/3] Verifying remaining resources...${NC}"
REMAINING_VOLUMES=$(docker volume ls -q | grep -c "cnss" || true)

if [ "$REMAINING_VOLUMES" -eq 0 ]; then
    echo -e "${GREEN}========================================================${NC}"
    echo -e "${GREEN} Server successfully cleaned from all CnSS data and containers!${NC}"
    echo -e "${GREEN}========================================================${NC}"
else
    echo -e "${YELLOW} Warning: Remaining volumes related to 'cnss' were found.${NC}"
    echo "You can remove them manually with: docker volume rm \$(docker volume ls -q | grep cnss)"
fi