import os
import socket
import subprocess
import sys


def confirm_kill(prompt: str) -> bool:
    """Ask for confirmation before force-killing a process."""
    try:
        answer = input(f"{prompt} (Y/n): ").strip().lower()
    except EOFError:
        return False
    return answer == "" or answer == "y" or answer == "yes"


print("=== PORT & PROCESS DIAGNOSTIC (DIAGNOSTIC MODE — NO AUTO-KILL) ===")
for port in [8000, 3000, 3001]:
    print(f"\n--- Checking Port {port} ---")
    out = subprocess.run(f"netstat -ano -p tcp", shell=True, capture_output=True, text=True).stdout
    matches = [line.strip() for line in out.splitlines() if f":{port} " in line]
    if not matches:
        print(f"  No connections found on port {port} in netstat.")
    for m in matches:
        print(f"  Netstat: {m}")
        parts = m.split()
        pid = parts[-1]
        if pid.isdigit() and int(pid) > 4:
            # Query tasklist for process name
            proc = subprocess.run(f"tasklist /FI \"PID eq {pid}\"", shell=True, capture_output=True, text=True).stdout
            print(f"  Process info:\n{proc.strip()}")
            if confirm_kill(f"  Force-kill process {pid} on port {port}?"):
                kill = subprocess.run(f"taskkill /F /T /PID {pid}", shell=True, capture_output=True, text=True)
                print(f"  Taskkill stdout: {kill.stdout.strip()}")
                print(f"  Taskkill stderr: {kill.stderr.strip()}")
            else:
                print(f"  Skipped — process {pid} left running on port {port}.")

    for host in ["127.0.0.1", "0.0.0.0"]:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind((host, port))
                print(f"  [SUCCESS] Successfully bound socket to ({host}, {port})")
            except OSError as e:
                print(f"  [FAIL] Could not bind to ({host}, {port}): {e}")
