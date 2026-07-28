import subprocess
import signal
import sys

processes = []

try:
    # Start exam app
    p1 = subprocess.Popen(
        ["python3", "/mnt/data/project/exam/app.py"]
    )
    processes.append(p1)

    # Start mindmap server
    p2 = subprocess.Popen(
        ["python3", "/mnt/data/project/mindmap/server.py"]
    )
    processes.append(p2)

    print("Both servers started.")

    # Wait for both processes
    for p in processes:
        p.wait()

except KeyboardInterrupt:
    print("\nStopping servers...")
    for p in processes:
        p.send_signal(signal.SIGINT)

    for p in processes:
        p.wait()

    sys.exit(0)