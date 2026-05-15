#!/usr/bin/env bash
# ============================================
# Aqar.ai - Fresh Database Reset
# ============================================
# Drops all data and re-runs migrations.
# Run from the repo root: bash infra/scripts/reset-db.sh
# ============================================

set -e

echo "⚠️  This will DROP ALL DATA and reset the database."
echo "    Press Ctrl+C to cancel, Enter to continue..."
read -r

echo "🔄 Stopping services..."
docker compose down

echo "🗑️  Removing database volume..."
docker volume rm aqar-ai_pgdata 2>/dev/null || true

echo "🚀 Starting services..."
docker compose up -d db redis meilisearch
sleep 5

echo "🏗️  Starting API for migrations..."
docker compose up -d api
sleep 3

echo "📦 Running migration..."
docker compose exec api alembic -c apps/api/alembic.ini upgrade head

echo "🚀 Starting remaining services..."
docker compose up -d

echo ""
echo "✅ Database reset complete!"
echo "   The system is running with a clean database."
echo "   Use the admin UI to discover and add channels."
echo ""
