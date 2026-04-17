#!/bin/bash
set -e

# MongoDB: harici (Atlas) kullanılıyor — yerel mongod başlatılmıyor.
# MONGO_URL ortam değişkeninden okunur.
echo "Using external MongoDB from MONGO_URL"

# Start Redis if not running
if ! pgrep -x redis-server > /dev/null 2>&1; then
  echo "Starting Redis..."
  redis-server --port 6379 --daemonize yes --logfile /tmp/redis.log
  sleep 1
  echo "Redis started"
else
  echo "Redis already running"
fi

echo "Starting FastAPI backend on port 8000..."
# Cookies must be SameSite=None;Secure for cross-site iframe (Replit preview proxy).
export AUTH_COOKIE_SAMESITE="${AUTH_COOKIE_SAMESITE:-none}"
export AUTH_COOKIE_SECURE="${AUTH_COOKIE_SECURE:-true}"
cd backend
exec uvicorn server:app --host localhost --port 8000
