import subprocess
import sys
import signal
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
python = sys.executable

processes = [
    subprocess.Popen([python, str(BASE_DIR / "exam" / "app.py")]),
    subprocess.Popen([python, str(BASE_DIR / "mindmap" / "server.py")]),
]

print("Both servers started.")

try:
    for p in processes:
        p.wait()
except KeyboardInterrupt:
    print("\nStopping servers...")
    for p in processes:
        p.send_signal(signal.SIGINT)
    for p in processes:
        p.wait()
        
except KeyboardInterrupt:
    print("\nStopping servers...")
    for p in processes:
        p.send_signal(signal.SIGINT)

    for p in processes:
        p.wait()

    sys.exit(0)