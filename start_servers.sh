#!/bin/bash
echo "啟動 Rasa 動作伺服器 (埠 5055)..."
rasa run actions > actions.log 2>&1 &

echo "啟動 Rasa 核心伺服器 (埠 5005)..."
rasa run --enable-api --cors "*" --endpoints endpoints.yml > core.log 2>&1 &

echo "伺服器已啟動！檢查 log: actions.log, core.log"
echo "Web UI: 在另一終端跑 python3 -m http.server 8000"