#!/usr/bin/env python
"""Quick script to check if the backend server is accessible"""
import sys
import socket

def check_port(host, port):
    """Check if a port is open"""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(2)
        result = sock.connect_ex((host, port))
        sock.close()
        return result == 0
    except Exception as e:
        print(f"Error checking port: {e}")
        return False

def main():
    host = 'localhost'
    port = 8000
    
    print(f"Checking if backend server is running on {host}:{port}...")
    
    if check_port(host, port):
        print(f"[OK] Port {port} is open - server appears to be running")
        print(f"Try accessing: http://{host}:{port}/health")
        print(f"API docs: http://{host}:{port}/docs")
    else:
        print(f"[ERROR] Port {port} is not accessible")
        print("\nTo start the server:")
        print("  cd backend")
        print("  python -m uvicorn main:app --reload")
        print("  or")
        print("  start.bat (Windows)")
        sys.exit(1)

if __name__ == "__main__":
    main()

