import base64
import json
import os
import urllib.error
import urllib.request


TASKS = {
    "tiktok": {
        "title": "Follow us on TikTok",
        "platform": "TikTok",
        "url": "https://www.tiktok.com/@lou_kyasua.aep?is_from_webapp=1&sender_device=pc",
        "reward": 50,
        "instruction": "Follow @lou_kyasua.aep and upload a screenshot showing the completed follow.",
        "criteria": "The screenshot should visibly show TikTok, the target account @lou_kyasua.aep, and evidence that the follow action is completed.",
    },
    "youtube": {
        "title": "Subscribe on YouTube",
        "platform": "YouTube",
        "url": "https://www.youtube.com/@KyasuaLouis-f8u",
        "reward": 30,
        "instruction": "Subscribe to Kyasua Louis and upload a screenshot showing the completed subscription.",
        "criteria": "The screenshot should visibly show YouTube, the Kyasua Louis channel, and evidence that the subscription is completed.",
    },
    "twitter": {
        "title": "Follow us on X",
        "platform": "X",
        "url": "https://x.com/Sephora",
        "reward": 25,
        "instruction": "Follow the linked X account and upload a screenshot showing the completed follow.",
        "criteria": "The screenshot should visibly show X, the linked account, and evidence that the follow action is completed.",
    },
    "facebook": {
        "title": "Follow us on Facebook",
        "platform": "Facebook",
        "url": "https://www.facebook.com/100085446753897/",
        "reward": 20,
        "instruction": "Follow the linked Facebook account and upload a screenshot showing the completed follow.",
        "criteria": "The screenshot should visibly show Facebook, the linked account, and evidence that the follow action is completed.",
    },
    "palmpay": {
        "title": "Join PalmPay",
        "platform": "PalmPay",
        "url": "https://info.palmpay.com/5r3CBVK_",
        "reward": 200,
        "instruction": "Register on PalmPay using referral code LGKJ4521 or the referral link, then upload a screenshot showing the completed registration.",
        "criteria": "The screenshot should visibly show PalmPay and convincing evidence of the requested registration/referral action. Do not treat generic PalmPay screenshots as proof by themselves.",
    },
}


def _image_data(path):
    ext = os.path.splitext(path)[1].lower()
    mime = {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".webp": "image/webp",
    }.get(ext, "application/octet-stream")
    with open(path, "rb") as fh:
        data = base64.b64encode(fh.read()).decode("ascii")
    return mime, data


def _extract_json(text):
    """Extract the verifier JSON even if the model wraps it in a markdown fence."""
    text = (text or "").strip()
    if text.startswith("```"):
        lines = text.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}")
        if start >= 0 and end > start:
            return json.loads(text[start : end + 1])
        raise


def analyze_submission(task_key, proof_path):
    task = TASKS.get(task_key)
    if not task:
        return {
            "status": "needs_review",
            "confidence": 0.0,
            "reason": "Unknown task.",
        }

    # Gemini 2.5 Flash-Lite supports image input and currently has a free API tier.
    # The key is kept server-side in GEMINI_API_KEY; never put it in the browser or repo.
    api_key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not api_key:
        return {
            "status": "needs_review",
            "confidence": 0.0,
            "reason": "AI verifier is not configured; manual admin review required.",
        }

    try:
        mime_type, image_b64 = _image_data(proof_path)
    except (OSError, ValueError) as exc:
        return {
            "status": "needs_review",
            "confidence": 0.0,
            "reason": f"Could not read screenshot; manual review required. ({type(exc).__name__})",
        }

    prompt = (
        "You are an evidence-review assistant for a rewards task. Analyze the screenshot "
        "only for the stated task. Do not assume an uploaded image is genuine just because "
        "it looks plausible. Look for visible UI evidence, target account/channel identity, "
        "and completion state. Never invent evidence. Return JSON only with exactly these keys: "
        "status, confidence, reason. status must be one of verified, rejected, needs_review. "
        "Use verified only when the screenshot clearly shows the requested action and target. "
        "Use rejected when it clearly contradicts the task or is obviously unrelated. "
        "Otherwise use needs_review. confidence must be a number from 0 to 1. Keep reason concise.\n\n"
        f"Task: {task['title']}\n"
        f"Platform: {task['platform']}\n"
        f"Criteria: {task['criteria']}"
    )

    payload = {
        "contents": [
            {
                "role": "user",
                "parts": [
                    {"text": prompt},
                    {
                        "inline_data": {
                            "mime_type": mime_type,
                            "data": image_b64,
                        }
                    },
                ],
            }
        ],
        "generationConfig": {
            "responseMimeType": "application/json",
            "responseSchema": {
                "type": "OBJECT",
                "properties": {
                    "status": {
                        "type": "STRING",
                        "enum": ["verified", "rejected", "needs_review"],
                    },
                    "confidence": {"type": "NUMBER"},
                    "reason": {"type": "STRING"},
                },
                "required": ["status", "confidence", "reason"],
            },
            "temperature": 0,
        },
    }

    model = os.environ.get("NOVA_TASK_AI_MODEL", "gemini-2.5-flash-lite").strip()
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"

    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "x-goog-api-key": api_key,
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=45) as response:
            raw = response.read().decode("utf-8")
        data = json.loads(raw)
        parts = data.get("candidates", [{}])[0].get("content", {}).get("parts", [])
        text = "\n".join(part.get("text", "") for part in parts if part.get("text"))
        result = _extract_json(text)

        status = result.get("status", "needs_review")
        if status not in {"verified", "rejected", "needs_review"}:
            status = "needs_review"
        confidence = float(result.get("confidence", 0.0))
        confidence = max(0.0, min(1.0, confidence))
        reason = str(result.get("reason", "No reason returned."))[:1000]
        return {"status": status, "confidence": confidence, "reason": reason}

    except urllib.error.HTTPError as exc:
        # Do not expose API credentials or the provider's full error body to users.
        return {
            "status": "needs_review",
            "confidence": 0.0,
            "reason": f"AI verification unavailable; manual review required. (HTTP {exc.code})",
        }
    except (urllib.error.URLError, TimeoutError, ValueError, json.JSONDecodeError, OSError, IndexError, TypeError) as exc:
        return {
            "status": "needs_review",
            "confidence": 0.0,
            "reason": f"AI verification failed; manual review required. ({type(exc).__name__})",
        }
