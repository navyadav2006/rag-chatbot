#!/bin/bash

# Navigate to the backend folder and start the FastAPI server
echo "🚀 Starting Backend..."
cd backend
PYTHONPATH=$PYTHONPATH:. uvicorn main:app --host 0.0.0.0 --port 8001 &

# Wait for a few seconds to ensure the backend starts
sleep 5

# Navigate to the frontend folder and start the HTTP server
echo "🌍 Starting Frontend..."
cd ../frontend
python -m http.server 8000 &

# Wait for the frontend to start
sleep 3

# Get the local IP address
IP=$(hostname -I | awk '{print $1}')

# Print instructions
echo "✅ Application is running!"
echo "🔗 Open your browser and go to: http://$IP:8000"
