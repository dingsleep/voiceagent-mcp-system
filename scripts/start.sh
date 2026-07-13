#!/bin/bash
# Start all microservices for the dialogue system

echo "=== Starting Dialogue Agent Services ==="

# 0. Redis
redis-cli ping > /dev/null 2>&1 || { echo "Please start Redis first"; exit 1; }

# 1. Reject service (port 8007)
cd train
nohup python reject_infer.py > /dev/null 2>&1 &
echo "[1/4] Reject service started (port 8007)"
sleep 3

# 2. Intent service (port 8008)
nohup python intent_infer.py > /dev/null 2>&1 &
echo "[2/4] Intent service started (port 8008)"
sleep 3

# 3. NLU service (port 8009)
cd ../function_call
nohup python chatnlu_infer.py > /dev/null 2>&1 &
echo "[3/4] NLU service started (port 8009)"
sleep 5

# 4. Gateway (port 8080)
cd ..
nohup python start.py > /dev/null 2>&1 &
echo "[4/4] Gateway started (port 8080)"

echo "=== All services running ==="
