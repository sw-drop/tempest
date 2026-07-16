#!/usr/bin/env python3
import os
import sys
import json
import time
import urllib.request
import urllib.parse
import urllib.error
import ssl
import argparse

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
HERMES_HOME = os.environ.get("HERMES_HOME", "/opt/data")
STATE_FILE = os.path.join(HERMES_HOME, ".docker_monitor_state.json")

def main():
    parser = argparse.ArgumentParser(description="Portainer Docker Watchdog")
    parser.add_argument("--status", action="store_true", help="Print current status of all unhealthy containers and exit without saving state")
    args = parser.parse_args()

    portainer_url = os.environ.get("PORTAINER_URL", "https://172.17.0.1:9443")
    portainer_user = os.environ.get("PORTAINER_USER", "agent")
    portainer_pass = os.environ.get("PORTAINER_PASSWORD", "h3rm3s_dash_88!")

    if not portainer_url:
        print("⚠️ Portainer monitoring skipped: PORTAINER_URL not set in environment.", file=sys.stderr)
        sys.exit(0)

    # Normalize URL
    portainer_url = portainer_url.rstrip("/")
    
    # Create unverified SSL context for self-signed certs
    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE

    # Authenticate and get JWT token
    auth_data = json.dumps({"username": portainer_user, "password": portainer_pass}).encode("utf-8")
    req = urllib.request.Request(f"{portainer_url}/api/auth", data=auth_data, headers={"Content-Type": "application/json"})
    
    try:
        with urllib.request.urlopen(req, context=ssl_context, timeout=10) as response:
            auth_resp = json.loads(response.read().decode())
            jwt_token = auth_resp.get("jwt")
    except Exception as e:
        print(f"⚠️ Portainer API Auth Error: {e}", file=sys.stderr)
        sys.exit(1)

    headers = {
        "Authorization": f"Bearer {jwt_token}",
        "Accept": "application/json"
    }

    try:
        req = urllib.request.Request(f"{portainer_url}/api/endpoints", headers=headers)
        with urllib.request.urlopen(req, context=ssl_context, timeout=15) as response:
            endpoints = json.loads(response.read().decode())
    except Exception as e:
        print(f"⚠️ Portainer API Error (Endpoints): {e}", file=sys.stderr)
        sys.exit(1)

    # Load state
    state = {}
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r") as f:
                state = json.load(f)
        except Exception:
            state = {}

    current_bad_containers = {}
    output_message = []

    for endpoint in endpoints:
        env_id = endpoint.get("Id")
        env_name = endpoint.get("Name")
        env_status = endpoint.get("Status") # 1 = up, 2 = down

        if env_status == 2:
            current_bad_containers[f"endpoint_{env_id}"] = {
                "name": f"Endpoint {env_name}",
                "status": "Down/Unreachable",
                "error": "Portainer cannot reach this environment"
            }
            continue

        # Skip non-Docker endpoints if necessary (Type 1=Docker API, 2=Docker Swarm, 4=Docker Edge)
        # We will attempt to hit the docker/containers endpoint
        try:
            req = urllib.request.Request(f"{portainer_url}/api/endpoints/{env_id}/docker/containers/json?all=1", headers=headers)
            with urllib.request.urlopen(req, context=ssl_context, timeout=15) as response:
                if response.getcode() != 200:
                    continue # Skip if it doesn't support the docker api (e.g. Kubernetes)
                containers = json.loads(response.read().decode())
        except Exception as e:
            # We silently skip environments that timeout or fail individually
            continue

        for container in containers:
            c_name = container.get("Names", ["/Unknown"])[0].lstrip("/")
            c_state = container.get("State", "")
            c_status = container.get("Status", "")

            # Identify sick containers
            is_bad = False
            error_msg = c_status

            if c_state.lower() == "exited":
                # Only alert if it exited with a non-zero code. (Sometimes Portainer just shows "Exited (1)")
                if "Exited (0)" not in c_status:
                    is_bad = True
            elif "unhealthy" in c_status.lower() or c_state.lower() == "dead":
                is_bad = True

            if is_bad:
                container_key = f"{env_id}_{c_name}"
                current_bad_containers[container_key] = {
                    "env": env_name,
                    "name": c_name,
                    "status": c_state,
                    "error": c_status
                }

    # Compare current bad containers with state
    new_alerts = []
    resolved_alerts = []

    if args.status:
        if not current_bad_containers:
            print("✅ All Portainer endpoints and containers are perfectly healthy.")
        else:
            print("🚨 **CURRENT SICK CONTAINERS REPORT** 🚨")
            for key, data in current_bad_containers.items():
                if "endpoint_" in key:
                    print(f"- **Docker Host Down**: {data['name']} is unreachable.")
                else:
                    print(f"- **Container Alert** [{data['env']}]: `{data['name']}` is **{data['status']}** ({data['error']})")
        return

    for key, data in current_bad_containers.items():
        if key not in state:
            if "endpoint_" in key:
                new_alerts.append(f"🚨 **Docker Host Down**: {data['name']} is unreachable by Portainer.")
            else:
                new_alerts.append(f"🚨 **Container Alert** [{data['env']}]: `{data['name']}` is **{data['status']}** ({data['error']})")

    for key, data in state.items():
        if key not in current_bad_containers:
            if "endpoint_" in key:
                resolved_alerts.append(f"✅ **Docker Host Recovered**: {data['name']} is reachable again.")
            else:
                resolved_alerts.append(f"✅ **Container Recovered** [{data['env']}]: `{data['name']}` is no longer reporting errors.")

    # Combine messages
    if new_alerts:
        output_message.extend(new_alerts)
    if resolved_alerts:
        output_message.extend(resolved_alerts)

    # Save state
    try:
        with open(STATE_FILE, "w") as f:
            json.dump(current_bad_containers, f, indent=2)
    except Exception as e:
        print(f"⚠️ Failed to write state file: {e}", file=sys.stderr)

    # Print output if there is any (triggers Telegram delivery)
    if output_message:
        print("\n".join(output_message))

if __name__ == "__main__":
    main()
