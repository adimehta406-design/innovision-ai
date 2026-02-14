import os
import sys
import time
import threading
import uvicorn
from pyngrok import ngrok, conf

# --- Configuration ---
PORT = 8000
# Ensure ngrok is installed in the system path or virtualenv
# You might need to authenticate: ngrok config add-authtoken <TOKEN>

def run_server():
    """Runs the Uvicorn server in a separate thread."""
    uvicorn.run("main:app", host="127.0.0.1", port=PORT, log_level="info")

def start_tunnel():
    """Starts the Ngrok tunnel."""
    try:
        # Connect to the local port
        public_url = ngrok.connect(PORT).public_url
        print(f"\n{'='*60}")
        print(f"   TRUTHLENS IS LIVE! 🚀")
        print(f"   Public URL: {public_url}")
        print(f"{'='*60}\n")
        
        # Write URL to file
        with open("ngrok_url.txt", "w") as f:
            f.write(public_url)
        
        # Keep the main thread alive to keep the tunnel open
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\nShutting down tunnel...")
            ngrok.disconnect(public_url)
            ngrok.kill()
            sys.exit(0)
            
    except Exception as e:
        print(f"\n[ERROR] Ngrok failed to start: {e}")
        if "authentication" in str(e).lower() or "ERR_NGROK_4018" in str(e):
            print("\n>>> CRITICAL: You need to authenticate Ngrok!")
            print(">>> 1. Sign up at https://dashboard.ngrok.com/signup")
            print(">>> 2. Get your authtoken from https://dashboard.ngrok.com/get-started/your-authtoken")
            print(">>> 3. Run: ngrok config add-authtoken <YOUR_TOKEN>")
        sys.exit(1)

if __name__ == "__main__":
    print(f"Starting TruthLens on port {PORT}...")
    
    # Start FastAPI in a daemon thread
    server_thread = threading.Thread(target=run_server)
    server_thread.daemon = True
    server_thread.start()

    # Wait a moment for server to boot
    time.sleep(2)
    
    # Start Ngrok in the main thread
    start_tunnel()
