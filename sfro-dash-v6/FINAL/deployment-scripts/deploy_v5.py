#!/usr/bin/env python3
import subprocess
import sys
import time
import os

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
    remote_dir = "/docker/sfro-dash-v5"
    host_port = "8025"
    
    print("==================================================")
    print(f"Starting Deployment Pipeline to {ssh_host}...")
    print("==================================================")
    
    # 1. Create target directories on remote host
    print(f"\nStep 1: Preparing remote directory {remote_dir} on {ssh_host}...")
    run_remote(ssh_host, f"mkdir -p {remote_dir}")

    # 2. Sync codebase using rsync (targeting contents of docker_deploy)
    print(f"\nStep 2: Syncing codebase bundle to {ssh_host}...")
    exclude_list = [
        "data/",
        ".env",
        "*.db",
        "*.db-journal",
        "__pycache__",
        ".DS_Store"
    ]
    
    rsync_cmd = ["rsync", "-avz", "--progress"]
    for pattern in exclude_list:
        rsync_cmd.extend(["--exclude", pattern])
    
    # Sync contents of docker_deploy folder to remote directory
    rsync_cmd.extend(["docker_deploy/", f"{ssh_host}:{remote_dir}/"])
    run_local(rsync_cmd)

    # 3. Stop existing services if running on the host
    print("\nStep 3: Cleaning up any existing containers on the host...")
    run_remote(ssh_host, f"cd {remote_dir} && docker compose down || true", check=False)

    # 4. Ensure the remote data directory exists and has correct permissions
    print("\nStep 4: Aligning remote directory data and script folder permissions to 1000:1000...")
    remote_align_cmd = (
        f"mkdir -p {remote_dir}/data {remote_dir}/dash-scripts {remote_dir}/images && "
        f"sudo chown -R 1000:1000 {remote_dir}/data {remote_dir}/dash-scripts {remote_dir}/images && "
        f"sudo chmod -R 775 {remote_dir}/data {remote_dir}/dash-scripts {remote_dir}/images"
    )
    run_remote(ssh_host, remote_align_cmd, check=False)
    
    # 4b. Migrate .env from V3 if present
    print("\nStep 4b: Migrating .env configuration from V3 database...")
    run_remote(ssh_host, f"[ ! -f {remote_dir}/.env ] && [ -f /docker/sfro-dash-v3/.env ] && cp /docker/sfro-dash-v3/.env {remote_dir}/.env || true", check=False)

    # 5. Build and start services using docker-compose
    print(f"\nStep 5: Building and starting V5 Docker services on port {host_port}...")
    run_remote(ssh_host, f"cd {remote_dir} && docker compose up --build -d")

    print("\n==================================================")
    print("Deployment completed successfully!")
    print(f"V5 Dashboard is now live at: http://{ssh_host}:{host_port}/index.html")
    print("Waiting 3 seconds to print container status...")
    time.sleep(3)
    run_remote(ssh_host, "docker ps -f name=sfro-dash-v5-")
    print("==================================================")

if __name__ == "__main__":
    main()
