#!/bin/bash
# Helper script to restore database

if [ -z "$1" ]; then
    echo "Usage: $0 <backup_file>"
    echo "Available backups:"
    ls -la backups/postgres_backup_*.sql.gz 2>/dev/null || echo "No backups found"
    exit 1
fi

echo "Restoring database from $1..."
docker-compose exec fastapi /app/scripts/restore.sh "$1"