#!/bin/bash
# Database migration script for CabinPython v2

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${GREEN}CabinPython v2 Database Migration${NC}"
echo "===================================="
echo

# Check for .env file
if [ ! -f "../.env" ]; then
    echo -e "${RED}Error: .env file not found${NC}"
    echo "Please create .env with database credentials"
    exit 1
fi

# Load environment variables
set -a
source ../.env
set +a

# Check for required variables
if [ -z "$DB_PASSWORD" ]; then
    echo -e "${RED}Error: DB_PASSWORD not set in .env${NC}"
    exit 1
fi

# Database connection info
DB_USER="${DB_USER:-cabinpi}"
DB_NAME="${DB_NAME:-cabinpi}"
DB_HOST="${DB_HOST:-localhost}"

echo -e "${YELLOW}Database: ${DB_NAME}@${DB_HOST}${NC}"
echo -e "${YELLOW}User: ${DB_USER}${NC}"
echo

# Test database connection
echo -e "${YELLOW}Testing database connection...${NC}"
if ! mysql -h"$DB_HOST" -u"$DB_USER" -p"$DB_PASSWORD" "$DB_NAME" -e "SELECT 1;" > /dev/null 2>&1; then
    echo -e "${RED}Error: Cannot connect to database${NC}"
    echo "Please check database credentials in .env"
    exit 1
fi
echo -e "${GREEN}✓ Database connection successful${NC}"
echo

# Run migrations
echo -e "${YELLOW}Running migrations...${NC}"
echo

for migration in *.sql; do
    if [ -f "$migration" ]; then
        echo -e "${YELLOW}Applying $migration...${NC}"
        mysql -h"$DB_HOST" -u"$DB_USER" -p"$DB_PASSWORD" "$DB_NAME" < "$migration"
        echo -e "${GREEN}✓ $migration applied${NC}"
        echo
    fi
done

echo -e "${GREEN}All migrations completed successfully!${NC}"
echo

# Verify tables
echo -e "${YELLOW}Verifying tables...${NC}"
mysql -h"$DB_HOST" -u"$DB_USER" -p"$DB_PASSWORD" "$DB_NAME" -e "SHOW TABLES;"
echo

echo -e "${GREEN}Migration complete!${NC}"
