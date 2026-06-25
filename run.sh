#!/bin/bash
# EPU MIS System - Linux Launcher
cd "$(dirname "$0")"

# Kill any existing instance on port 5000
fuser -k 5000/tcp 2>/dev/null

# Activate virtual environment
source venv/bin/activate

# Start Flask in background briefly then open browser
echo "========================================"
echo "  EPU MIS System - Development Server"
echo "========================================"
echo ""
echo "  URL: http://localhost:5000"
echo "  Press Ctrl+C to stop the server"
echo ""

# Open browser after 2 seconds
(sleep 2 && xdg-open http://localhost:5000) &

# Start Flask (logs show here in terminal)
python app.py
