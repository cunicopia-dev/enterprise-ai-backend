#!/bin/bash
# Database backup script for Docker container

set -e

# Configuration
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/app/backups"
BACKUP_FILE="postgres_backup_${TIMESTAMP}.sql.gz"
BACKUP_PATH="${BACKUP_DIR}/${BACKUP_FILE}"

# Ensure backup directory exists
mkdir -p "${BACKUP_DIR}"

echo "Starting PostgreSQL backup at $(date)"

# Perform database dump
echo "Dumping database..."
PGPASSWORD="${DB_PASSWORD}" pg_dump -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}" -d "${DB_NAME}" | gzip > "${BACKUP_PATH}"

if [ $? -eq 0 ]; then
    echo "Database backup completed: ${BACKUP_FILE}"
    
    # Calculate backup size
    BACKUP_SIZE=$(du -h "${BACKUP_PATH}" | cut -f1)
    echo "Backup size: ${BACKUP_SIZE}"
    
    # Upload to S3 if configured
    if [ ! -z "${S3_BUCKET}" ] && [ ! -z "${AWS_ACCESS_KEY_ID}" ]; then
        echo "Uploading to S3 bucket: ${S3_BUCKET}"
        aws s3 cp "${BACKUP_PATH}" "s3://${S3_BUCKET}/postgres-backups/${BACKUP_FILE}"
        
        if [ $? -eq 0 ]; then
            echo "S3 upload completed"
            
            # Remove local backup after S3 upload if configured
            if [ "${REMOVE_LOCAL_AFTER_S3}" = "true" ]; then
                rm "${BACKUP_PATH}"
                echo "Local backup removed after S3 upload"
            fi
        else
            echo "S3 upload failed, keeping local backup"
        fi
    fi
    
    # Clean up old local backups (keep last 7 days)
    echo "Cleaning up old backups..."
    find "${BACKUP_DIR}" -name "postgres_backup_*.sql.gz" -mtime +7 -delete
    
    echo "Backup process completed at $(date)"
else
    echo "Database backup failed!"
    exit 1
fi