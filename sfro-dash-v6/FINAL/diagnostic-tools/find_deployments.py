import subprocess
import sys

hosts = ["Pi5-1", "Eadu", "Pi4-3", "Pi4-1"]

def run_ssh(host, cmd):
    try:
        res = subprocess.run(["ssh", host, cmd], capture_output=True, text=True, timeout=10)
        return res.returncode, res.stdout, res.stderr
    except Exception as e:
        return -1, "", str(e)

print("Checking directories on hosts...")
for host in hosts:
    print(f"\n--- Host: {host} ---")
    
    # Check for docker compose containers
    code, out, err = run_ssh(host, "docker ps -a --format 'table {{.Names}}\t{{.Image}}\t{{.Ports}}'")
    if code == 0:
        print("[Containers]")
        print(out.strip())
    else:
        print(f"[Containers Error] {err.strip()}")
        
    # Check filesystem for sfro-dash-v5 or similar
    code, out, err = run_ssh(host, "find /docker /opt -maxdepth 3 -name '*v5*' -o -name '*v4*' 2>/dev/null")
    if code == 0:
        print("[Filesystem matches]")
        print(out.strip())
    else:
        print(f"[Filesystem Error] {err.strip()}")
