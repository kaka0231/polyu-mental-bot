#!/bin/bash
# 启动 action server 和 main server
rasa run actions --port $((PORT + 1)) &
rasa run --enable-api --cors "*" --port $PORT