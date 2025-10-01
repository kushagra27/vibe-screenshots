#!/bin/bash

# Simple development server starter for vibe-screenshots
# Uses watchdog for auto-reload (Python's nodemon equivalent)

echo "🚀 Starting vibe-screenshots development servers..."

# Kill any existing processes on our ports
lsof -ti tcp:8000 | xargs kill -9 2>/dev/null || true
lsof -ti tcp:8001 | xargs kill -9 2>/dev/null || true

# Set default token if not provided
if [ -z "$UPLOAD_TOKEN" ]; then
    export UPLOAD_TOKEN="dev-token-123"
    echo "⚠️  Using default development token: 'dev-token-123'"
    echo "   Set UPLOAD_TOKEN environment variable for production"
fi

echo "📸 Gallery server: http://localhost:8000"
echo "📤 Upload server: http://localhost:8001" 
echo "🔑 Upload token: $UPLOAD_TOKEN"
echo ""
echo "💡 Press Ctrl+C to stop both servers"
echo ""

# Function to cleanup on exit
cleanup() {
    echo ""
    echo "🛑 Shutting down servers..."
    lsof -ti tcp:8000 | xargs kill -9 2>/dev/null || true
    lsof -ti tcp:8001 | xargs kill -9 2>/dev/null || true
    exit 0
}

# Set trap for cleanup
trap cleanup SIGINT SIGTERM

# Start gallery server in background
cd source
python3 -m http.server 8000 &
GALLERY_PID=$!
cd ..

# Start upload server with auto-reload using watchdog
watchdog auto-restart --directory=. --pattern="*.py" --recursive -- python3 upload_app.py &
UPLOAD_PID=$!

# Wait for both processes
wait $GALLERY_PID $UPLOAD_PID