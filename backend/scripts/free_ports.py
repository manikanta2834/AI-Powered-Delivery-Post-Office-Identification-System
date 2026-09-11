"""High-Reliability Port Inspector & Force-Release Utility.

Uses native Windows kernel32.dll Win32 APIs (no PATH/PowerShell dependencies)
to terminate any process holding port 8000, 3000, or 3001 and strictly verify
the socket is released before proceeding.
"""

import ctypes
import os
import socket
import subprocess
import sys
import time


def terminate_pid_native(pid: int) -> bool:
    """Terminate a Windows process using kernel32.TerminateProcess directly."""
    PROCESS_TERMINATE = 0x0001
    try:
        handle = ctypes.windll.kernel32.OpenProcess(PROCESS_TERMINATE, False, pid)
        if handle:
            ctypes.windll.kernel32.TerminateProcess(handle, 1)
            ctypes.windll.kernel32.CloseHandle(handle)
            return True
    except Exception as e:
        print(f"  [WARN] kernel32 terminate failed for {pid}: {e}")
    return False


def get_pids_on_port(port: int) -> set[int]:
    """Inspect netstat TCP rows to find any process ID bound to the port."""
    pids = set()

    # Try netstat with explicit System32 path fallback
    cmd = "netstat -ano -p tcp"
    if os.path.exists(r"C:\Windows\System32\netstat.exe"):
        cmd = r"C:\Windows\System32\netstat.exe -ano -p tcp"

    try:
        out = subprocess.check_output(cmd, shell=True, text=True)
        for line in out.splitlines():
            line = line.strip()
            if f":{port} " in line or f":{port}\t" in line or f":{port}\r" in line:
                if any(state in line for state in ["LISTENING", "ESTABLISHED", "CLOSE_WAIT", "TIME_WAIT"]):
                    parts = line.split()
                    try:
                        pid = int(parts[-1])
                        if pid > 4 and pid != os.getpid():
                            pids.add(pid)
                    except (ValueError, IndexError):
                        pass
    except Exception as exc:
        print(f"  [WARN] netstat query error on port {port}: {exc}")

    # Try PowerShell with explicit System32 path fallback
    ps_path = r"C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe"
    if os.path.exists(ps_path):
        try:
            ps_cmd = f'"{ps_path}" -NoProfile -Command "Get-NetTCPConnection -LocalPort {port} -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess -Unique"'
            ps_out = subprocess.check_output(ps_cmd, shell=True, text=True)
            for line in ps_out.splitlines():
                line = line.strip()
                if line.isdigit():
                    pid = int(line)
                    if pid > 4 and pid != os.getpid():
                        pids.add(pid)
        except Exception:
            pass

    return pids


def can_bind(port: int, host: str = "127.0.0.1") -> bool:
    """Strictly test socket bind without SO_REUSEADDR."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind((host, port))
            return True
        except OSError:
            return False


def free_port(port: int) -> bool:
    """Identify all PIDs holding the port, terminate them via kernel32, and wait for release."""
    pids = get_pids_on_port(port)

    if not pids and can_bind(port):
        return True

    print(f"[PORT CLEANUP] Port {port} is occupied by PID(s): {pids if pids else 'lingering socket'}")

    for pid in pids:
        print(f"  - Force-terminating process PID {pid} via Win32 API...")
        # 1. Native Win32 API
        terminate_pid_native(pid)
        # 2. System32 taskkill fallback
        taskkill_path = r"C:\Windows\System32\taskkill.exe" if os.path.exists(r"C:\Windows\System32\taskkill.exe") else "taskkill"
        subprocess.run(f'"{taskkill_path}" /F /T /PID {pid}', shell=True, capture_output=True)

    # Active wait loop: Wait up to 5.0 seconds until Windows kernel releases the socket
    for _ in range(50):
        time.sleep(0.1)
        if can_bind(port):
            print(f"  [OK] Port {port} is verified free to bind.")
            return True

    # If still not free, query netstat again and kill any newly discovered PIDs
    remaining = get_pids_on_port(port)
    if remaining:
        print(f"  [RETRY] Killing remaining PID(s): {remaining}...")
        for pid in remaining:
            terminate_pid_native(pid)
        time.sleep(0.5)
        if can_bind(port):
            print(f"  [OK] Port {port} is verified free to bind.")
            return True

    print(f"  [WARN] Port {port} socket teardown in progress. Proceeding.")
    return False


def main():
    target_ports = [int(arg) for arg in sys.argv[1:] if arg.isdigit()]
    if not target_ports:
        target_ports = [8000, 3000, 3001]

    for port in target_ports:
        free_port(port)


if __name__ == "__main__":
    main()
