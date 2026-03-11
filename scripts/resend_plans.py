"""Re-send plans to Telegram with feedback buttons."""
import json
import os

import httpx

BOT_TOKEN = os.environ["BOT_TOKEN"]
CHAT_ID = os.environ["CHAT_ID"]
BASE_URL = os.environ.get("BASE_URL", "https://reelbot.leadneedleai.com")

REELS = ["DVl7jdQjpT8", "DVjUbasERPI", "DVhhkw0D2Rf", "DVmPZh0EuCq", "DVl9DAAjmxC"]

client = httpx.Client(timeout=15)


def send_telegram(text, keyboard):
    resp = client.post(
        f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
        json={
            "chat_id": CHAT_ID,
            "text": text,
            "parse_mode": "HTML",
            "reply_markup": keyboard,
        },
    )
    return resp.json()


plans_data = client.get(f"{BASE_URL}/plans/").json()
review_plans = plans_data.get("review", [])
plan_index = {p["reel_id"]: p for p in review_plans}

for reel_id in REELS:
    plan_data = client.get(f"{BASE_URL}/plans/{reel_id}").json()
    meta = plan_data.get("metadata", {})
    idx = plan_index.get(reel_id, {})

    title = idx.get("title", "Unknown")
    creator = meta.get("creator", "")
    theme = idx.get("theme", "")
    relevance = idx.get("relevance_score", 0)
    total_hours = idx.get("total_hours", 0)
    cost = idx.get("estimated_cost", 0)
    task_count = idx.get("task_count", 0)

    cb = meta.get("cost_breakdown", {})
    cost_lines = []
    for c in cb.get("calls", []):
        model_short = c["model"].split("/")[-1] if c.get("model") else "?"
        toks = c.get("prompt_tokens", 0) + c.get("completion_tokens", 0)
        cost_lines.append(
            f"  {c['step']}: ${c['cost_usd']:.4f} ({model_short}, {toks:,}tok)"
        )

    view_url = f"{BASE_URL}/plans/{reel_id}/view"
    cost_detail = "\n".join(cost_lines)

    msg = (
        f"<b>{title}</b>\n"
        f"{creator} \u00b7 {relevance:.0%} relevance\n\n"
        f"<i>{theme}</i>\n\n"
        f"<b>{task_count} tasks ({total_hours:.1f}h)</b>\n\n"
        f"<b>Cost:</b> ${cost:.4f}\n<pre>{cost_detail}</pre>"
    )

    keyboard = {
        "inline_keyboard": [
            [
                {"text": "\u2705 Approve", "callback_data": f"approve:{reel_id}"},
                {"text": "\u274c Reject", "callback_data": f"reject:{reel_id}"},
            ],
            [{"text": "\U0001f4c4 View Plan", "url": view_url}],
            [
                {"text": "\U0001f44d Good", "callback_data": f"feedback_good:{reel_id}"},
                {"text": "\U0001f44e Needs Work", "callback_data": f"feedback_bad:{reel_id}"},
                {"text": "\U0001f937 Partial", "callback_data": f"feedback_partial:{reel_id}"},
            ],
        ],
    }

    resp = send_telegram(msg, keyboard)
    ok = resp.get("ok", False)
    print(f"{'OK' if ok else 'FAIL'}: {reel_id} - {title}")
    if not ok:
        print(f"  Error: {resp.get('description', 'unknown')}")
