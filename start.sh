#!/bin/bash

# 设置端口变量
export PORT=${PORT:-5005}

echo "Starting Rasa Action Server on port 5055..."
rasa run actions --port 5055 &

echo "Starting Rasa Main Server on port $PORT..."
rasa run --enable-api --cors "*" --port $PORT

# 保持容器运行
wait