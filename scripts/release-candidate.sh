#!/usr/bin/env bash
set -e

echo "========================================="
echo " DigiZafe Release Candidate Gate"
echo "========================================="

echo "[1/6] Running backend linting and static checks..."
cd backend
python -m pip install ruff
ruff check app/
cd ..

echo "[2/6] Verifying Alembic migrations..."
cd backend
alembic heads
# Alembic current requires a running DB, so we skip it here if not available
cd ..

echo "[3/6] Running backend unit and integration tests..."
cd backend
pytest tests/
cd ..

echo "[4/6] Verifying Frontend production build..."
cd frontend
npm install
npm run build
cd ..

echo "[5/6] Building immutable container images..."
docker compose build api worker

echo "[6/6] Release Candidate Gate Passed!"
echo "Next step: Run the smoke test against the built images."
