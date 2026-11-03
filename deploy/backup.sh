#!/usr/bin/env bash
set -euo pipefail

backup_bucket="pulse-start-deploy-124310609508"
backup_stamp="$(date -u +%Y%m%dT%H%M%SZ)"
backup_file="$(mktemp /tmp/techwatch-backup.XXXXXXXX.dump)"
trap 'rm -f "$backup_file"' EXIT
chmod 600 "$backup_file"

docker exec techwatch-db-1 pg_dump -U techwatch -d techwatch \
  --format=custom --no-owner --no-acl > "$backup_file"
test -s "$backup_file"

backup_key="techwatch/backups/techwatch-${backup_stamp}.dump"
aws s3 cp "$backup_file" "s3://${backup_bucket}/${backup_key}" \
  --sse AES256 --only-show-errors
aws s3api head-object --bucket "$backup_bucket" --key "$backup_key" \
  --query ContentLength --output text | grep -Eq '^[1-9][0-9]*$'

echo "TechWatch backup uploaded: s3://${backup_bucket}/${backup_key}"
