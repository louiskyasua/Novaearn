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


def _data_url(path):
    ext = os.path.splitext(path)[1].lower()
    mime = {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".webp": "image/webp",
    }.get(ext, "application/octet-stream")
    with open(path, "rb") as fh:
        data = base64.b64encode(fh.read()).decode("ascii")
    return f"data:{mime};base64,{data}"


def analyze_submission(task_key, proof_path):
    task = TASKS.get(task_key)
    if not task:
        return {
            "status": "needs_review",
            "confidence": 0.0,
            "reason": "Unknown task.",
        }

    api_key = os.environ.get("OPENAI_API_KEY", "").strip()
    if not api_key:
        return {
            "status": "needs_review",
            "confidence": 0.0,
            "reason": "AI verifier is not configured; manual admin review required.",
        }

    payload = {
        "model": os.environ.get("NOVA_TASK_AI_MODEL", "gpt-5.6-luna"),
        "input": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "input_text",
                        "text": (
                            "You are an evidence-review assistant for a rewards task. "
                            "Analyze the screenshot only for the stated task. Do not assume "
                            "that an uploaded image is genuine just because it looks plausible. "
                            "Return JSON only with keys: status, confidence, reason. "
                            "status must be one of verified, rejected, needs_review. "
                            "Use verified only when the screenshot clearly shows the requested "
                            "action and target. Use rejected when it clearly contradicts the task. "
                            "Otherwise use needs_review. Confidence must be a number from 0 to 1.\n\n"
                            f"Task: {task['title']}\n"
                            f"Platform: {task['platform']}\n"
                            f"Criteria: {task['criteria']}"
                        ),
                    },
                    {
                        "type": "input_image",
                        "image_url": _data_url(proof_path),
                        "detail": "high",
                    },
                ],
            }
        ],
    }

    request = urllib.request.Request(
        "https://api.openai.com/v1/responses",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=45) as response:
            raw = response.read().decode("utf-8")
        data = json.loads(raw)
        text = data.get("output_text", "").strip()
        result = json.loads(text)
        status = result.get("status", "needs_review")
        if status not in {"verified", "rejected", "needs_review"}:
            status = "needs_review"
        confidence = float(result.get("confidence", 0.0))
        confidence = max(0.0, min(1.0, confidence))
        reason = str(result.get("reason", "No reason returned."))[:1000]
        return {"status": status, "confidence": confidence, "reason": reason}
    except (urllib.error.URLError, TimeoutError, ValueError, json.JSONDecodeError, OSError) as exc:
        return {
            "status": "needs_review",
            "confidence": 0.0,
            "reason": f"AI verification failed; manual review required. ({type(exc).__name__})",
        }
