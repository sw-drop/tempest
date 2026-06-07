# Git & GitHub Project Setup Guide

This guide outlines the exact steps required to initialize a local Git repository, configure user identity, link it to a remote GitHub repository under the `sw-drop` organization, and push your code. You can reuse this workflow for future projects.

---

## Prerequisites
Ensure Git is installed on your local machine and your SSH keys (or HTTPS credentials) are configured and associated with your GitHub account:
* To check if Git is installed: `git --version`
* To verify your SSH connection to GitHub: `ssh -T git@github.com`

---

## Step-by-Step Setup Pipeline

### 1. Initialize Local Git Repository
Navigate to the root directory of your project and initialize a clean repository:
```bash
git init
```

### 2. Configure Git User Identity (Project Level)
Set up your commit signature. Using the `--local` flag ensures these settings apply only to this specific project, which is useful if you manage multiple GitHub identities on the same machine:
```bash
git config --local user.name "sw-drop"
git config --local user.email "gary@pillay.net"
```

*Note: If you want these credentials to apply to **all** projects on your computer, omit `--local` and use `--global` instead.*

### 3. Create a `.gitignore` File
Create a `.gitignore` file in your project root to exclude temporary, virtual environment, and system-specific files from being tracked. A typical template for Python/Docker projects:
```text
# Python bytecode and caches
__pycache__/
*.pyc
*.pyo
*.pyd
.ipynb_checkpoints/

# Virtual environments
venv/
.venv/
env/

# System / IDE files
.DS_Store
.vscode/
.idea/

# Local configuration overrides
.env
```

### 4. Create a New GitHub Repository
1. Go to [GitHub - New Repository](https://github.com/new).
2. Set the repository name (e.g. `tempest`).
3. Set the visibility (Public or Private).
4. **Important**: Leave "Initialize this repository with" unchecked (do not add a README, `.gitignore`, or License on GitHub, since we will push them from local).
5. Click **Create repository**.

### 5. Stage and Commit Files Locally
Add all project files to the Git staging index and make your initial commit:
```bash
git add .
git commit -m "Initial commit: Setup project files"
```

### 6. Link to GitHub and Push

#### Rename Default Branch to `main`
Ensure your local default branch is named `main` (matching GitHub's modern default):
```bash
git branch -M main
```

#### Add the Remote Origin URL
Link your local repository to the remote GitHub repository. Replace `<repo-name>` with your actual repository name:
```bash
# Using SSH (Recommended)
git remote add origin git@github.com:sw-drop/<repo-name>.git

# OR using HTTPS (if SSH keys are not set up)
git remote add origin https://github.com/sw-drop/<repo-name>.git
```

#### Push to GitHub
Push the `main` branch to GitHub and set it as the default upstream tracking branch:
```bash
git push -u origin main
```
*Subsequent pushes can be done simply with `git push`.*

---

## Quick Setup Script (Automation)
For future projects, you can copy this one-liner template into a file called `git_setup.sh` in the root of your new project directory to automate the configuration:

```bash
#!/bin/bash
set -e

REPO_NAME="your-new-repo-name"

git init
git config --local user.name "sw-drop"
git config --local user.email "gary@pillay.net"

# Create standard gitignore
cat <<EOT > .gitignore
__pycache__/
*.pyc
.DS_Store
venv/
.venv/
.env
EOT

git add .
git commit -m "Initial commit"
git branch -M main
git remote add origin git@github.com:sw-drop/${REPO_NAME}.git
git push -u origin main
```
Make the script executable with `chmod +x git_setup.sh` and run it once you've created the empty repository on GitHub.
