#!/bin/bash
set -e

# Create data directories
mkdir -p /tmp/mongodb-data /tmp/mongodb-logs

# Start MongoDB if not running
if ! pgrep -x mongod > /dev/null 2>&1; then
  echo "Starting MongoDB..."
  mongod --dbpath /tmp/mongodb-data --logpath /tmp/mongodb-logs/mongod.log --bind_ip 127.0.0.1 --port 27017 --fork
  # Wait for MongoDB to be ready
  for i in $(seq 1 15); do
    if mongo --eval "db.runCommand({ping:1})" --quiet 2>/dev/null | grep -q '"ok" : 1'; then
      echo "MongoDB ready"
      break
    fi
    echo "Waiting for MongoDB... ($i)"
    sleep 1
  done
else
  echo "MongoDB already running"
fi

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
cd backend
exec uvicorn server:app --host localhost --port 8000
