#!/usr/bin/env bash
# MINOVA MinIO bucket bootstrap
# Run after MinIO is healthy. Requires mc (MinIO Client) on PATH or passed as $MC.

set -euo pipefail

MINIO_ENDPOINT="${MINIO_ENDPOINT:-http://localhost:9000}"
MINIO_USER="${MINIO_ROOT_USER:-minova_minio}"
MINIO_PASS="${MINIO_ROOT_PASSWORD:-minova_minio_2026}"
MC="${MC:-mc}"

echo "Configuring MinIO alias 'minova'..."
$MC alias set minova "$MINIO_ENDPOINT" "$MINIO_USER" "$MINIO_PASS" --api S3v4

BUCKETS=(documents attachments exports reports)
for bucket in "${BUCKETS[@]}"; do
  if $MC ls "minova/$bucket" >/dev/null 2>&1; then
    echo "Bucket '$bucket' already exists."
  else
    echo "Creating bucket '$bucket'..."
    $MC mb "minova/$bucket"
  fi
done

# Enable versioning on documents bucket (audit trail for uploads)
$MC version enable "minova/documents"
$MC version enable "minova/attachments"

echo "MinIO bootstrap complete."
echo "Buckets: ${BUCKETS[*]}"
