#!/usr/bin/env python3
"""
Development server runner for vibe-screenshots
Starts both the gallery and upload servers with auto-reload
"""

import os
import sys
import subprocess
import signal
import time
from pathlib import Path

def kill_processes():
    """Kill any existing processes on our ports"""
    ports = [8000, 8001]
    for port in ports:
        try:
            subprocess.run(
                ["lsof", "-ti", f"tcp:{port}"], 
                capture_output=True, 
                check=False
            )
            subprocess.run(
                ["pkill", "-f", f":{port}"], 
                capture_output=True, 
                check=False
            )
        except:
            pass

def signal_handler(sig, frame):
    """Handle Ctrl+C gracefully"""
    print("\n🛑 Shutting down servers...")
    kill_processes()
    sys.exit(0)

def main():
    # Set up signal handler for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)
    
    # Kill any existing processes
    kill_processes()
    time.sleep(1)
    
    # Set default upload token if not provided
    if not os.getenv("UPLOAD_TOKEN"):
        os.environ["UPLOAD_TOKEN"] = "dev-token-123"
        print("⚠️  Using default development token: 'dev-token-123'")
        print("   Set UPLOAD_TOKEN environment variable for production")
    
    print("🚀 Starting vibe-screenshots development servers...")
    print(f"📸 Gallery server: http://localhost:8000")
    print(f"📤 Upload server: http://localhost:8001")
    print(f"🔑 Upload token: {os.getenv('UPLOAD_TOKEN')}")
    print("\n💡 Press Ctrl+C to stop both servers\n")
    
    try:
        # Start gallery server (static file server in source directory)
        gallery_process = subprocess.Popen(
            [sys.executable, "-m", "http.server", "8000"],
            cwd="source",
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        # Start upload server with auto-reload
        upload_process = subprocess.Popen(
            ["watchdog", "auto-restart", "--directory=.", "--pattern=*.py", "--recursive", "--", 
             sys.executable, "upload_app.py"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        # Wait for processes and handle output
        while True:
            time.sleep(1)
            
            # Check if processes are still running
            if gallery_process.poll() is not None:
                print("❌ Gallery server stopped unexpectedly")
                break
            if upload_process.poll() is not None:
                print("❌ Upload server stopped unexpectedly")
                break
                
    except KeyboardInterrupt:
        signal_handler(signal.SIGINT, None)
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        # Clean up processes
        try:
            gallery_process.terminate()
            upload_process.terminate()
        except:
            pass
        kill_processes()

if __name__ == "__main__":
    main()