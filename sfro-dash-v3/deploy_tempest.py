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
    remote_dir = "/docker/sfro-dash-v3"
    old_remote_dir = "/docker/sfro-dash"
    host_port = "8023"
    
    print("==================================================")
    # 1. Stop existing v2 services (to free up port 8023)
    print("Step 1: Stopping existing sfro-dash-v2 services...")
    run_remote(ssh_host, "docker rm -f sfro-dash-v2 || true", check=False)
    run_remote(ssh_host, f"cd {old_remote_dir} && docker compose down || true", check=False)
    
    # 2. Create target directories on Pi5-1
    print(f"\nStep 2: Preparing remote directory {remote_dir} on {ssh_host}...")
    run_remote(ssh_host, f"mkdir -p {remote_dir}")

    # 3. Sync local files to Pi5-1 (excluding git and test scripts)
    print(f"\nStep 3: Syncing codebase to {ssh_host}...")
    exclude_list = [
        ".git",
        "*.pyc",
        "__pycache__",
        "deploy_tempest.py",
        "deploy.sh",
        "*.fits"
    ]
    rsync_cmd = ["rsync", "-avz"]
    for pattern in exclude_list:
        rsync_cmd.extend(["--exclude", pattern])
    
    rsync_cmd.extend([".", f"{ssh_host}:{remote_dir}/"])
    run_local(rsync_cmd)

    # 4. Stop existing v3 services if running
    print("\nStep 4: Cleaning up any existing v3 container...")
    run_remote(ssh_host, "docker rm -f sfro-dash-v3 || true", check=False)
    run_remote(ssh_host, f"cd {remote_dir} && docker compose down || true", check=False)

    # 5. Build and start services using docker compose up
    print(f"\nStep 5: Building and launching sfro-dash-v3 on port {host_port}...")
    run_remote(ssh_host, f"cd {remote_dir} && docker compose up --build -d")

    print("\n==================================================")
    print("Deployment completed successfully!")
    print(f"Weather Monitor Dashboard is now live at: http://{ssh_host}:{host_port}/")
    print("Waiting 3 seconds to print container status...")
    time.sleep(3)
    run_remote(ssh_host, "docker ps -f name=sfro-dash-v3")

if __name__ == "__main__":
    main()
