#!/usr/bin/env python3
"""
Start script for the Podcast Clips Generator full-stack application.
Starts both the FastAPI backend and React frontend.
"""

import subprocess
import sys
import os
import time
from pathlib import Path

def start_backend():
    """Start the FastAPI backend server"""
    print("🚀 Starting FastAPI backend...")
    
    # Install backend dependencies
    try:
        subprocess.run([sys.executable, "-m", "pip", "install", "-r", "backend/requirements.txt"], 
                      check=True, capture_output=True)
        print("✅ Backend dependencies installed")
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to install backend dependencies: {e}")
        return None
    
    # Start backend (run as a module so relative imports in backend/ work correctly)
    backend_process = subprocess.Popen([
        sys.executable, "-m", "uvicorn", "backend.main:app",
        "--host", "0.0.0.0", "--port", "8000"
    ], cwd=Path.cwd())
    
    print("✅ Backend started on http://localhost:8000")
    return backend_process

def start_frontend():
    """Start the React frontend development server"""
    print("🎨 Starting React frontend...")
    
    frontend_dir = Path("frontend")
    
    # Install frontend dependencies
    try:
        subprocess.run(["npm", "install"], cwd=frontend_dir, check=True, capture_output=True)
        print("✅ Frontend dependencies installed")
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to install frontend dependencies: {e}")
        return None
    
    # Start frontend
    frontend_process = subprocess.Popen([
        "npm", "start"
    ], cwd=frontend_dir)
    
    print("✅ Frontend started on http://localhost:3000")
    return frontend_process

def main():
    """Main function to start the application"""
    print("🎬 Starting Podcast Clips Generator...")
    print("=" * 50)
    
    # Check if required directories exist
    if not Path("backend").exists():
        print("❌ Backend directory not found!")
        sys.exit(1)
    
    if not Path("frontend").exists():
        print("❌ Frontend directory not found!")
        sys.exit(1)
    
    # Start backend
    backend_process = start_backend()
    if not backend_process:
        sys.exit(1)
    
    # Wait a moment for backend to start
    time.sleep(3)
    
    # Start frontend
    frontend_process = start_frontend()
    if not frontend_process:
        backend_process.terminate()
        sys.exit(1)
    
    print("\n" + "=" * 50)
    print("🎉 Application started successfully!")
    print("📱 Frontend: http://localhost:3000")
    print("🔧 Backend API: http://localhost:8000")
    print("📚 API Docs: http://localhost:8000/docs")
    print("\nPress Ctrl+C to stop both servers")
    print("=" * 50)
    
    try:
        # Wait for processes
        backend_process.wait()
        frontend_process.wait()
    except KeyboardInterrupt:
        print("\n🛑 Shutting down...")
        backend_process.terminate()
        frontend_process.terminate()
        print("✅ Application stopped")

if __name__ == "__main__":
    main() 