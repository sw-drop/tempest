#!/usr/bin/env python3
"""
Token Offer Monitor — run by cron job every 12h.
Searches the web for free token / credit offers from AI/LLM providers.
Evaluates quality for Hermes use. Reports new findings only.
Silent (empty stdout) when nothing new is found.
"""

import json
import os
import sys

TRACKING_FILE = os.path.expanduser("~/.hermes/reported_offers.json")

# Known good providers already leveraged by the user
KNOWN_GOOD = {
    "openrouter": "Already configured as primary provider",
    "google gemini": "Already configured (geo-restricted, fails 429 outside US)",
    "deepseek": "Already configured via OpenRouter",
}

# Baseline — providers we know about but aren't worth reporting again
ALREADY_REPORTED = {
    "groq": {"reason": "Free tier known, no recent upgrade"},
    "together": {"reason": "No significant free offering known"},
    "fireworks": {"reason": "No significant free offering known"},
}


def load_tracking():
    os.makedirs(os.path.dirname(TRACKING_FILE), exist_ok=True)
    if os.path.exists(TRACKING_FILE):
        with open(TRACKING_FILE) as f:
            return json.load(f)
    return {"reported_offers": {}, "seen_urls": []}


def save_tracking(data):
    with open(TRACKING_FILE, "w") as f:
        json.dump(data, f, indent=2)


def is_new_offer(offer, tracking):
    """Check if this offer hasn't been reported before."""
    provider_key = offer.get("provider", "").lower().strip()
    url = offer.get("url", "")

    # Skip if provider is already known/configured
    for known in KNOWN_GOOD:
        if known in provider_key:
            return False, f"Already using {known}"

    # Skip if already reported
    if provider_key in tracking["reported_offers"]:
        return False, f"Already reported: {provider_key}"

    if url in tracking["seen_urls"]:
        return False, "URL already seen"

    # Skip known baselines
    for baseline, info in ALREADY_REPORTED.items():
        if baseline in provider_key:
            return False, info["reason"]

    return True, "New offer"


def evaluate_quality(provider, details):
    """
    Quality scoring — is this actually worth using with Hermes?
    Returns (is_good, rating, explanation).
    rating: 0-10
    """
    text = f"{provider} {json.dumps(details)}".lower()
    score = 0
    reasons = []

    # Must be API-accessible (not UI-only)
    if any(kw in text for kw in ["api", "endpoint", "openai-compatible", "api key", "sdk"]):
        score += 3
        reasons.append("API-accessible")
    elif any(kw in text for kw in ["chat only", "web ui", "playground only", "app only"]):
        score -= 2
        reasons.append("UI-only (limited)")

    # Model quality signals
    if any(m in text for m in ["claude", "gpt-4", "gemini", "llama 3", "qwen", "deepseek", "mixtral", "command r", "dbrx"]):
        score += 3
        reasons.append("Good model family")
    if any(m in text for m in ["tiny", "nano", "1b", "pico", "micro"]):
        score -= 1
        reasons.append("Small model")

    # Free tier signals
    if any(kw in text for kw in ["free tier", "free credits", "free tokens", "freemium", "free api"]):
        score += 2
        reasons.append("Has free tier")
    if "rate limit" in text or "requests per day" in text or "rpd" in text:
        score += 1
        reasons.append("Known rate limits")

    # Quantity signals
    for kw, pts in [("unlimited", 2), ("1000 request", 1), ("10000", 1), ("100k", 2), ("1m", 3), ("$10", 1), ("$50", 2), ("$100", 3), ("$200", 3), ("$500", 4), ("$1000", 4)]:
        if kw in text:
            score += pts
            reasons.append(f"Mentioned: {kw}")

    # Sustained vs trial
    if any(kw in text for kw in ["ongoing", "permanent", "always free", "free tier", "forever free"]):
        score += 2
        reasons.append("Sustained free tier")
    elif any(kw in text for kw in ["trial", "7 day", "14 day", "30 day", "limited time"]):
        score -= 1
        reasons.append("Limited-time trial")

    # Return verdict
    is_good = score >= 5
    rating = min(10, score)
    return is_good, rating, reasons


def search_for_offers():
    """
    This function is the data-collection placeholder.
    The actual search + extraction runs via the cron agent prompt
    (web_search + web_extract tools). This script exists so we can
    migrate to no_agent=True later or run deterministic dedup.
    """
    # This script is a companion to the cron LLM prompt.
    # It handles persistent tracking and dedup logic.
    # The actual searching is done by the cron agent with web tools.
    return []


if __name__ == "__main__":
    # When called standalone (no_agent mode), just show what's tracked
    tracking = load_tracking()
    count = len(tracking["reported_offers"])
    print(f"Token Offer Monitor — {count} offers tracked")
    if tracking["reported_offers"]:
        for provider, info in tracking["reported_offers"].items():
            print(f"  - {provider}: {info.get('rating', '?')}/10 — {info.get('url', '')[:80]}")
    print(f"  Seen URLs: {len(tracking['seen_urls'])}")
