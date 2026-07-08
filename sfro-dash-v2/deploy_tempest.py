import subprocess
import sys
import time

def run_local(cmd, check=True):
    print(f"\n[LOCAL] Executing: {' '.join(cmd)}")
    res = subprocess.run(cmd, capture_output=False)
    if check and res.returncode != 0:
        print(f"[ERROR] Local command failed with code {res.returncode}")
        sys.exit(res.returncode)
    return res.returncode

def run_remote(ssh_host, remote_cmd, check=True):
    cmd = ["ssh", ssh_host, remote_cmd]
    print(f"\n[REMOTE @ {ssh_host}] Executing: {remote_cmd}")
    res = subprocess.run(cmd, capture_output=False)
    if check and res.returncode != 0:
        print(f"[ERROR] Remote command failed with code {res.returncode}")
        sys.exit(res.returncode)
    return res.returncode

def main():
    ssh_host = "Pi5-1"
    remote_dir = "/docker/sfro-dash"
    host_port = "8023"
    
    print("==================================================")
    # 1. Create target directories on Eadu
    print(f"Step 1: Preparing remote directory {remote_dir} on Eadu...")
    run_remote(ssh_host, f"mkdir -p {remote_dir}/extra_scripts")

    # 2. Sync local files to Eadu (excluding scripts and temp files)
    print("\nStep 2: Syncing codebase to Eadu...")
    exclude_list = [
        ".git",
        "*.pyc",
        "__pycache__",
        "deploy_tempest.py",
        "probe_eadu.py",
        "run.py",
        "test_fetch.py"
    ]
    rsync_cmd = ["rsync", "-avz"]
    for pattern in exclude_list:
        rsync_cmd.extend(["--exclude", pattern])
    
    rsync_cmd.extend([".", f"{ssh_host}:{remote_dir}/"])
    run_local(rsync_cmd)

    # 3. Stop existing services using docker compose down & remove legacy standalone container if exists
    print("\nStep 3: Stopping old services and cleaning legacy containers...")
    run_remote(ssh_host, "docker rm -f sfro-dash-v2 || true", check=False)
    run_remote(ssh_host, f"cd {remote_dir} && docker compose down", check=False)

    # 4. Build and start services using docker compose up
    print(f"\nStep 4: Building and launching services on port {host_port} with docker compose...")
    run_remote(ssh_host, f"cd {remote_dir} && docker compose up --build -d")

    print("\n==================================================")
    print("Deployment completed successfully!")
    print(f"Weather Monitor Dashboard is now live at: http://{ssh_host}:{host_port}/")
    print(f"API endpoint is now live at: http://{ssh_host}:{host_port}/api/observations")
    print("Waiting 3 seconds to print container status...")
    time.sleep(3)
    run_remote(ssh_host, "docker ps -f name=sfro-dash-v2")

if __name__ == "__main__":
    main()
