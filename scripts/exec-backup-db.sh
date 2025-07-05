#!/bin/bash
# Helper script to run database backup

echo "Running database backup..."
docker-compose exec fastapi /app/scripts/backup.sh