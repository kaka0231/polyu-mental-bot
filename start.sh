#!/bin/bash
echo "Starting Rasa Action Server..."
rasa run actions --port 5055 &

echo "Starting Rasa Main Server..."
rasa run --enable-api --cors "*" --port $PORT --endpoints endpoints.yml

# 保持容器运行
wait