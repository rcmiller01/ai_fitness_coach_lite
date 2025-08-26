#!/bin/bash
"""
Database Backup Script for AI Fitness Coach
Automated PostgreSQL backup with rotation and compression
"""

# Configuration
DB_HOST=${DB_HOST:-localhost}
DB_PORT=${DB_PORT:-5432}
DB_NAME=${DB_NAME:-fitness_coach}
DB_USER=${DB_USER:-fitness_user}
BACKUP_DIR=${BACKUP_DIR:-/backup}
RETENTION_DAYS=${BACKUP_RETENTION_DAYS:-30}

# Create backup directory if it doesn't exist
mkdir -p "$BACKUP_DIR"

# Generate backup filename with timestamp
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/fitness_coach_backup_$TIMESTAMP.sql"
COMPRESSED_FILE="$BACKUP_FILE.gz"

echo "🗄️ Starting database backup..."
echo "   Database: $DB_NAME@$DB_HOST:$DB_PORT"
echo "   Backup file: $COMPRESSED_FILE"

# Create database dump
export PGPASSWORD=$DB_PASSWORD
pg_dump \
    --host="$DB_HOST" \
    --port="$DB_PORT" \
    --username="$DB_USER" \
    --dbname="$DB_NAME" \
    --verbose \
    --clean \
    --no-owner \
    --no-privileges \
    --format=custom \
    --file="$BACKUP_FILE"

# Check if backup was successful
if [ $? -eq 0 ]; then
    echo "✅ Database backup completed successfully"
    
    # Compress backup file
    gzip "$BACKUP_FILE"
    
    if [ $? -eq 0 ]; then
        echo "✅ Backup compressed successfully"
        BACKUP_SIZE=$(du -h "$COMPRESSED_FILE" | cut -f1)
        echo "   Backup size: $BACKUP_SIZE"
    else
        echo "⚠️ Backup compression failed, keeping uncompressed file"
        COMPRESSED_FILE="$BACKUP_FILE"
    fi
    
    # Remove old backups
    echo "🧹 Cleaning up old backups (older than $RETENTION_DAYS days)..."
    find "$BACKUP_DIR" -name "fitness_coach_backup_*.sql.gz" -mtime +$RETENTION_DAYS -delete
    find "$BACKUP_DIR" -name "fitness_coach_backup_*.sql" -mtime +$RETENTION_DAYS -delete
    
    echo "✅ Backup process completed successfully!"
    echo "   Final backup: $COMPRESSED_FILE"
    
else
    echo "❌ Database backup failed!"
    rm -f "$BACKUP_FILE"
    exit 1
fi

# Optional: Upload to cloud storage
if [ ! -z "$AWS_S3_BUCKET" ] && command -v aws &> /dev/null; then
    echo "☁️ Uploading backup to S3..."
    aws s3 cp "$COMPRESSED_FILE" "s3://$AWS_S3_BUCKET/backups/" --storage-class STANDARD_IA
    
    if [ $? -eq 0 ]; then
        echo "✅ Backup uploaded to S3 successfully"
    else
        echo "⚠️ S3 upload failed, backup remains local only"
    fi
fi

# Create backup log entry
LOG_FILE="$BACKUP_DIR/backup.log"
echo "$(date '+%Y-%m-%d %H:%M:%S') - Backup completed: $COMPRESSED_FILE" >> "$LOG_FILE"

echo "🎉 Backup process finished!"