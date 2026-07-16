# Automated GitHub Backups for Hermes

This guide outlines how to configure and automate backups of the Hermes configuration and architectural files from the **Eadu** server to your private GitHub repository (`git@github.com:sw-drop/Hermes-backup.git`).

---

## 1. The Backup Script

The backup script automatically checks for any changes in `/mnt/ssd/docker/hermes`, stages and commits them using a timestamp, and pushes them to GitHub. It exits silently if no changes are detected.

Create the file `/mnt/ssd/docker/hermes/backup_to_github.sh` with the following content:

```bash
#!/usr/bin/env bash

# Navigate to the repository directory
cd /mnt/ssd/docker/hermes || exit 1

# Ensure path contains common binary locations for cron's execution context
export PATH="/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"

# Check if there are any changes (untracked, modified, or deleted files)
if [ -n "$(git status --porcelain)" ]; then
    echo "$(date +'%Y-%m-%d %H:%M:%S') - Changes detected. Staging files..."
    git add .
    
    echo "Committing changes..."
    git commit -m "Auto-backup: $(date +'%Y-%m-%d %H:%M:%S')"
    
    echo "Pushing to GitHub..."
    git push origin main
    echo "Backup completed successfully."
else
    echo "$(date +'%Y-%m-%d %H:%M:%S') - No changes detected. Skip backup."
fi
```

### Make the Script Executable
Run the following command on Eadu:
```bash
chmod +x /mnt/ssd/docker/hermes/backup_to_github.sh
```

---

## 2. Automating with Cron

To run the backup automatically, add it to root's system cron.

1. Open the crontab editor for the root user:
   ```bash
   crontab -e
   ```
2. Add the following cron expression to the bottom of the file (this runs the backup daily at 2:00 AM and appends output to a log file):
   ```text
   0 2 * * * /mnt/ssd/docker/hermes/backup_to_github.sh >> /var/log/hermes_backup.log 2>&1
   ```

---

## 3. Logs & Troubleshooting

- **Checking logs:** You can check the output history at any time with:
  ```bash
  cat /var/log/hermes_backup.log
  ```
- **Manual Run:** To run the backup manually at any time to verify it:
  ```bash
  /mnt/ssd/docker/hermes/backup_to_github.sh
  ```
- **Credentials:** The script assumes SSH key authentication is set up for the `root` user and that the remote is set to SSH. If you need to re-verify the SSH connection manually:
  ```bash
  ssh -T git@github.com
  ```
- **File Location for the Agent:** For the agent to be able to refer to this document, it is located at `/mnt/ssd/docker/hermes/scripts/github_backup_guide.md` on the host, which mounts inside the agent's main container and sandbox environments at:
  - **`/opt/data/scripts/github_backup_guide.md`**
