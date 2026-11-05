"""
LikePilot Silent Launcher
Starts the farm.py script as a detached background process.
Allows you to close this terminal window while the bot continues running.
"""

import subprocess
import sys
import os
import time

def main():
    print("=" * 50)
    print("  LikePilot - Silent Background Launcher")
    print("=" * 50)
    print()
    
    # Get the absolute path to farm.py
    script_dir = os.path.dirname(os.path.abspath(__file__))
    farm_path = os.path.join(script_dir, "farm.py")
    
    if not os.path.exists(farm_path):
        print(f"[ERROR] Could not find farm.py at: {farm_path}")
        input("Press Enter to exit...")
        return

    print("Starting LikePilot automation engine...")
    print("Dashboard will be available at: http://localhost:5000")
    print()
    print("[OK] Launching in detached process...")
    print("[INFO] You can safely close this window now.")
    print("[INFO] To stop the bot: Close Chrome windows or end 'python.exe' in Task Manager.")
    print()

    try:
        # Start the process completely detached from this terminal
        # DETACHED_PROCESS: The created process does not inherit its parent's console.
        # CREATE_NEW_PROCESS_GROUP: Creates a new process group for the child process.
        subprocess.Popen(
            [sys.executable, farm_path],
            cwd=script_dir,
            creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            stdin=subprocess.DEVNULL
        )
        
        # Wait briefly to ensure process started
        time.sleep(2)
        
        print()
        print("=" * 50)
        print("  LikePilot is now running in background!")
        print("=" * 50)
        print()
        print("Press Enter to close this launcher...")
        input()
        
    except Exception as e:
        print(f"[ERROR] Failed to start background process: {e}")
        print("Falling back to standard mode...")
        time.sleep(2)
        # Fallback to normal run if detached mode fails
        os.system(f"python {farm_path}")

if __name__ == "__main__":
    main()
