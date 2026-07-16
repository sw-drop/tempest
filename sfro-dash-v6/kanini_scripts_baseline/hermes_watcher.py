#!/usr/bin/env python3
"""
hermes_watcher.py — DISABLED
Replaced by Hermes Agent (Antigravity) on 2026-07-06.
New pipeline: see Docs/local/obsidian-ingestion-report.md Section 8.
The systemd service should be stopped: systemctl stop hermes-watcher && systemctl disable hermes-watcher
"""
import sys
print("hermes_watcher.py is DISABLED. New pipeline handles Obsidian ingestion via Hermes Agent.", file=sys.stderr)
sys.exit(0)

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

def extract_concepts(concepts_dir):
    if not os.path.isdir(concepts_dir):
        logging.warning(f"Concepts directory {concepts_dir} not found. Skipping linking.")
        return []
    concept_files = [f for f in os.listdir(concepts_dir) if f.endswith(".md")]
    return [f[:-3] for f in concept_files]

def get_status(file_content):
    for line in file_content.splitlines():
        if line.startswith("## Status:"):
            return line.replace("## Status:", "").strip()
    return None

def surgically_link_file(content, concept_names):
    lines = content.splitlines(keepends=True)
    parsed_blocks = []
    in_code_block = False
    
    frontmatter_start = -1
    frontmatter_end = -1
    for i, line in enumerate(lines):
        if line.strip() == "---":
            if frontmatter_start == -1:
                if all(not l.strip() for l in lines[:i]):
                    frontmatter_start = i
            elif frontmatter_end == -1:
                frontmatter_end = i
                break
                
    for idx, line in enumerate(lines):
        if frontmatter_start != -1 and frontmatter_start <= idx <= frontmatter_end:
            parsed_blocks.append({"type": "metadata", "text": line})
            continue
            
        if line.strip().startswith("```"):
            in_code_block = not in_code_block
            parsed_blocks.append({"type": "code_block_marker", "text": line})
            continue
        
        if in_code_block:
            parsed_blocks.append({"type": "code", "text": line})
            continue
            
        stripped = line.strip()
        if (stripped.startswith("#") or 
            stripped.startswith("## Status:") or 
            stripped.startswith("## Tags:") or 
            stripped == "___" or 
            stripped == "---"):
            parsed_blocks.append({"type": "metadata", "text": line})
            continue
            
        parsed_blocks.append({"type": "plain", "text": line})
        
    placeholders = []
    placeholder_counter = 0
    protect_pattern = re.compile(r'(`[^`\n]+`|\[\[[^\]\n]+\]\]|\[[^\]\n]+\]\([^)\n]+\))')
    
    for block in parsed_blocks:
        if block["type"] == "plain":
            text = block["text"]
            def replace_match(match):
                nonlocal placeholder_counter
                ph = f"\ue000{placeholder_counter}\ue001"
                placeholders.append((ph, match.group(0)))
                placeholder_counter += 1
                return ph
            block["processed_text"] = protect_pattern.sub(replace_match, text)
            
    linked_concepts = set()
    sorted_concepts = sorted(concept_names, key=len, reverse=True)
    
    for concept in sorted_concepts:
        concept_regex = re.compile(rf'\b{re.escape(concept)}\b', re.IGNORECASE)
        replaced = False
        for block in parsed_blocks:
            if replaced:
                break
            if block["type"] == "plain":
                text = block["processed_text"]
                match = concept_regex.search(text)
                if match:
                    start, end = match.span()
                    matched_word = match.group(0)
                    new_text = text[:start] + f"[[{matched_word}]]" + text[end:]
                    block["processed_text"] = new_text
                    replaced = True
                    linked_concepts.add(concept)
                    
    for block in parsed_blocks:
        if block["type"] == "plain":
            text = block["processed_text"]
            for ph, original in reversed(placeholders):
                text = text.replace(ph, original)
            block["final_text"] = text
        else:
            block["final_text"] = block["text"]
            
    return "".join(b["final_text"] for b in parsed_blocks), linked_concepts

def process_file(file_path, notes_dir, concepts_dir):
    filename = os.path.basename(file_path)
    
    # Wait a short duration to ensure file is completely written by host/client
    time.sleep(0.5)

    try:
        if not os.path.exists(file_path):
            logging.info(f"File {filename} disappeared before processing.")
            return True

        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        status = get_status(content)
        if status in ["Delete", "Ephemeral"]:
            logging.info(f"Skipping processing of {filename} due to status: {status}")
            os.remove(file_path)
            logging.info(f"Deleted {filename} from inbox.")
            return True

        concepts = extract_concepts(concepts_dir)
        processed_content, linked = surgically_link_file(content, concepts)
        
        if linked:
            logging.info(f"Surgically linked {len(linked)} concepts in {filename}: {list(linked)}")
        else:
            logging.info(f"No new concepts found to link in {filename}")

        target_path = os.path.join(notes_dir, filename)
        with open(target_path, "w", encoding="utf-8") as f:
            f.write(processed_content)
        logging.info(f"Moved and processed note to: {target_path}")

        if os.path.exists(file_path):
            os.remove(file_path)
            logging.info(f"Cleaned up {filename} from inbox.")
            
        return True

    except Exception as e:
        logging.error(f"Error processing file {filename}: {str(e)}")
        return False

def main():
    parser = argparse.ArgumentParser(description="Hermes Inbox Watcher Daemon")
    parser.add_argument("--inbox-dir", default="/workspace/vault/New", help="Directory to monitor (Inbox)")
    parser.add_argument("--notes-dir", default="/workspace/vault/_Notes", help="Directory to save processed notes")
    parser.add_argument("--concepts-dir", default="/workspace/vault/_Concepts", help="Directory containing concepts")
    args = parser.parse_args()

    os.makedirs(args.inbox_dir, exist_ok=True)
    os.makedirs(args.notes_dir, exist_ok=True)
    os.makedirs(args.concepts_dir, exist_ok=True)

    logging.info("Starting Hermes Custom Polling Watcher...")
    logging.info(f"  - Monitoring Inbox: {args.inbox_dir}")
    logging.info(f"  - Target Notes: {args.notes_dir}")
    logging.info(f"  - Concept Source: {args.concepts_dir}")
    logging.info("  - Polling Interval: 20 seconds")

    last_mtimes = {}

    while True:
        try:
            current_filepaths = []
            if os.path.exists(args.inbox_dir):
                for filename in os.listdir(args.inbox_dir):
                    if not filename.endswith(".md"):
                        continue
                        
                    file_path = os.path.join(args.inbox_dir, filename)
                    current_filepaths.append(file_path)
                    
                    if not os.path.exists(file_path):
                        continue
                        
                    try:
                        mtime = os.path.getmtime(file_path)
                    except OSError:
                        continue
                        
                    if mtime > last_mtimes.get(file_path, 0):
                        current_time = time.time()
                        time_since_modified = current_time - mtime
                        
                        if time_since_modified > 300:
                            logging.info(f"Note '{filename}' has been idle for {int(time_since_modified/60)} minutes. Processing...")
                            # Update mtime immediately so we don't retry repeatedly if it permanently fails
                            last_mtimes[file_path] = mtime
                            
                            success = process_file(file_path, args.notes_dir, args.concepts_dir)
                            if success:
                                # If it was moved/deleted successfully, it won't be in the dir next sweep
                                pass
                        else:
                            # Wait until 5 minutes have passed since the last modification
                            pass
                            
            # Clean up tracking dict for files that are no longer in the inbox
            for fp in list(last_mtimes.keys()):
                if fp not in current_filepaths:
                    del last_mtimes[fp]

        except Exception as e:
            logging.error(f"Error in main polling loop: {str(e)}")

        time.sleep(20)

if __name__ == "__main__":
    main()
