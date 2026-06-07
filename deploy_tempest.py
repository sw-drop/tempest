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
    ssh_host = "Eadu"
    remote_dir = "/docker/script-host"
    host_port = "8081"
    
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

    # 3. Build the docker image on Eadu
    print("\nStep 3: Building docker image on Eadu...")
    build_cmd = f"cd {remote_dir} && docker build -t script-host ."
    run_remote(ssh_host, build_cmd)

    # 4. Stop and remove existing container if running
    print("\nStep 4: Stopping old container (if any)...")
    run_remote(ssh_host, "docker stop script-host || true", check=False)
    run_remote(ssh_host, "docker rm script-host || true", check=False)

    # 5. Run the new container
    # Mapping port 8085 on Eadu host to port 80 inside container
    # Volume mount: /docker/script-host/extra_scripts to /app/extra_scripts for future python scripts
    print(f"\nStep 5: Launching new container on port {host_port}...")
    run_cmd = (
        f"docker run -d "
        f"--name script-host "
        f"--restart unless-stopped "
        f"-p {host_port}:80 "
        f"-v {remote_dir}/extra_scripts:/app/extra_scripts "
        f"-e TEMPEST_STATION_ID=174867 "
        f"script-host"
    )
    run_remote(ssh_host, run_cmd)

    print("\n==================================================")
    print("Deployment completed successfully!")
    print(f"Weather Monitor Dashboard is now live at: http://192.168.1.70:{host_port}/")
    print(f"API endpoint is now live at: http://192.168.1.70:{host_port}/api/observations")
    print("Waiting 3 seconds to print container status...")
    time.sleep(3)
    run_remote(ssh_host, "docker ps -f name=script-host")

if __name__ == "__main__":
    main()
