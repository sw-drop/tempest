Agent Operating Boundaries & Architecture

1. The Environment (Remote Docker Execution)
You are running natively on a macOS host, but the application runtime is located on a remote Linux server/host. 

File Edits: You must only read and edit files locally on this Mac. Do NOT use ssh, scp, or rsync directly to edit files on the remote server. Use a simple .sh script to push changes to the Mac.

Sync & Deployment:
The remote server is Pi5-1. On the remote server, the deployment of the dashboard is currently at /docker/sfro-dash-v5. As part of this project, we may change that with new versions.
Use only simple .sh scripts with scp or rsync (or similar) to push changes to the server.
There is no automated sync to the server. The project directory structure on the Mac may have sync type naming, but this should not be interpreted as a capability.

Docker & Git Commands: 
- `git` is available directly in your PATH.
- Docker is not installed locally.

2. Strict Coding Baselines (Non-Negotiable)
Surgical Increments: Use strict character-matching and surgical tool calls (e.g., `replace_file_content`). Provide only changes to the exact lines that must be changed. Do not rewrite whole files or make unrequested "optimisations."

UI Lock: Existing HTML/CSS structures are completely locked. Do not make any change that might affect the layout or content other than the specifically requested logic.

Code Presentation: Describe the changes made clearly in your text response. Do not output entire files in your chat responses; show only the relevant code snippets or diff blocks.

3. Compliance Verification
Before concluding any task or /goal, you must explicitly state whether you have complied with these rules, confirm you did not hallucinate any layout changes, and state whether you had all necessary context to complete the request.
