#!/bin/bash
# Database restore script

set -e

if [ -z "$1" ]; then
    echo "Usage: $0 <backup_file>"
    echo "Example: $0 postgres_backup_20240105_120000.sql.gz"
    exit 1
fi

BACKUP_FILE="$1"
BACKUP_DIR="/app/backups"
BACKUP_PATH="${BACKUP_DIR}/${BACKUP_FILE}"

if [ ! -f "${BACKUP_PATH}" ]; then
    echo "Error: Backup file not found: ${BACKUP_PATH}"
    exit 1
fi

echo "Starting PostgreSQL restore from ${BACKUP_FILE} at $(date)"

# Drop existing connections
echo "Dropping existing connections..."
PGPASSWORD="${DB_PASSWORD}" psql -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}" -d postgres -c "
SELECT pg_terminate_backend(pid) 
FROM pg_stat_activity 
WHERE datname = '${DB_NAME}' AND pid <> pg_backend_pid();"

# Drop and recreate database
echo "Dropping existing database..."
PGPASSWORD="${DB_PASSWORD}" psql -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}" -d postgres -c "DROP DATABASE IF EXISTS ${DB_NAME};"
PGPASSWORD="${DB_PASSWORD}" psql -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}" -d postgres -c "CREATE DATABASE ${DB_NAME};"

# Restore database
echo "Restoring database..."
gunzip -c "${BACKUP_PATH}" | PGPASSWORD="${DB_PASSWORD}" psql -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}" -d "${DB_NAME}"

if [ $? -eq 0 ]; then
    echo "Database restore completed successfully at $(date)"
else
    echo "Database restore failed!"
    exit 1
fi