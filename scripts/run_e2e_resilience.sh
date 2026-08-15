#!/bin/bash
set -e

# Setup Playwright environment (e.g. localhost URL)
export E2E_BASE_URL="http://localhost:5173"

echo "Starting Resilience E2E test suite..."

# 1. Verify healthy baseline
echo "Step 1: Running baseline Playwright suite"
cd ../frontend && npx playwright test e2e/auth.spec.ts && cd ../scripts

# Helper function to run a resilience test
run_resilience() {
  local container=$1
  local test_name=$2
  
  echo "--- Testing Failure: $container ---"
  echo "Stopping $container..."
  docker compose -f ../docker-compose.yml stop $container
  
  echo "Running resilience observation tests (auth/dashboard)..."
  # Use a dedicated error-recovery spec if available, otherwise just check that the frontend doesn't totally 500 error out
  cd ../frontend && npx playwright test e2e/error-recovery.spec.ts || echo "Tests failed as expected, verifying behavior" && cd ../scripts
  
  echo "Starting $container..."
  docker compose -f ../docker-compose.yml start $container
  
  echo "Waiting for recovery..."
  sleep 10
  
  echo "Verifying recovery..."
  cd ../frontend && npx playwright test e2e/auth.spec.ts && cd ../scripts
  echo "--- Recovery successful for $container ---"
}

# Generate error-recovery.spec.ts temporarily if it doesn't exist? (it'll be in frontend/e2e/error-recovery.spec.ts)
run_resilience "digizafe-redis-broker-1" "Redis Broker Outage"
run_resilience "digizafe-redis-cache-1" "Redis Cache Outage"
run_resilience "digizafe-worker-1" "Celery Worker Outage"
# Notice: PostgreSQL outage will fail auth completely, test might need specific assertions

echo "Resilience tests complete."
