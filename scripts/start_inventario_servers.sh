#!/usr/bin/env bash
# Start PocketBase + ngrok for Inventário Florestal
set -euo pipefail

echo "========================================"
echo "  Starting Inventário Florestal Servers"
echo "========================================"

SERVIDOR_DIR="/mnt/hdold/orca/servidorbadger"
POCKETBASE_PORT="8090"

# Check if already running
if pgrep -f "pocketbase serve" > /dev/null; then
    echo "[!] PocketBase already running"
else
    echo "[+] Starting PocketBase on port $POCKETBASE_PORT..."
    cd "$SERVIDOR_DIR"
    ./pocketbase serve &
    sleep 3
    echo "[✓] PocketBase started!"
    echo "    Local: http://127.0.0.1:$POCKETBASE_PORT"
    echo "    Admin: http://127.0.0.1:$POCKETBASE_PORT/_/"
fi

if pgrep -f "ngrok http" > /dev/null; then
    echo "[!] ngrok already running"
else
    echo ""
    echo "[+] Starting ngrok tunnel..."
    cd "$SERVIDOR_DIR"
    ./ngrok http $POCKETBASE_PORT &
    sleep 5
    echo "[✓] ngrok started!"
    echo ""
    echo "Fetching public URL..."
    sleep 2
    curl -s http://127.0.0.1:4040/api/tunnels | grep -o '"public_url":"[^"]*"' | head -1
fi

echo ""
echo "========================================"
echo "  Servers Ready!"
echo "========================================"
echo ""
echo "PocketBase Admin UI: http://127.0.0.1:${POCKETBASE_PORT}/_/"
echo ""
echo "To view ngrok public URL:"
echo "  curl http://127.0.0.1:4040/api/tunnels"
echo ""
echo "To stop servers:"
echo "  pkill -f 'pocketbase serve'"
echo "  pkill -f 'ngrok http'"
