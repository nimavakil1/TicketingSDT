#!/bin/bash
cd /home/ai/TicketingSDT

# Load environment variables and export them
set -a
source /home/ai/TicketingSDT/.env
set +a

# Execute python with the environment
exec python3 main.py
