#!/bin/bash

# Colors for better output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}Starting LLMgine Log Visualizer...${NC}"

# Start the custom development server that includes API endpoints
npm run dev:server