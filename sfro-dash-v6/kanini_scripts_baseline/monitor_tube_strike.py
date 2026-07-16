from hermes_tools import web_search, send_message

def main():
    # Perform search for current London tube strike status
    result = web_search(query="London tube strike", limit=5)
    
    strike_found = False
    for item in result.get("web", []):
        title = item.get("title", "").lower()
        description = item.get("description", "").lower()
        # Look for indications of an active strike
        if "strike" in title or "strike" in description:
            # Heuristic: include references to current time or ongoing
            if any(
                phrase in description 
                for phrase in ["midnight", "00:01", "00:00", "today", "now", "ongoing"]
            ):
                strike_found = True
                break

    if strike_found:
        # Send Telegram alert
        send_message(
            action="send",
            target="telegram:1461012131",
            message="⚠️ London tube strike detected! Check TfL for details."
        )

if __name__ == "__main__":
    main()