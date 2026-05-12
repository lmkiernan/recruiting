"""
On-demand candidate summarization via Google Gemini.

Called interactively when a user clicks "Summarize with Gemini" on a
candidate who was not included in the bulk OpenAI evaluation run.

Uses the Gemini REST API via httpx — no extra SDK dependency required.
"""

import json
import logging
import time

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

GEMINI_MODEL = "gemini-2.5-flash"
GEMINI_URL = (
    f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent"
)

_SYSTEM_INSTRUCTION = (
    "You are an expert technical recruiter evaluating GitHub developer profiles. "
    "Be specific, evidence-based, and focus only on what is observable from the "
    "public profile data provided. Do not invent information not present in the profile."
)


def summarize_candidate(profile: dict, job_description: str) -> dict:
    """
    Ask Gemini to score and summarize a single candidate against a job description.

    Returns a dict with keys:
        ai_score  (int 0–100)
        summary   (str)
        strengths (list[str])
        concerns  (list[str])

    Raises httpx.HTTPStatusError on HTTP errors or ValueError if the
    response JSON is missing required fields.
    """
    if not settings.GEMINI_API_KEY:
        raise ValueError("GEMINI_API_KEY is not configured")

    prompt = f"""Evaluate this GitHub developer profile against the job description below.

Return a JSON object with exactly these fields:
- "ai_score": integer 0-100 (role-specific fit; be honest and calibrated)
- "summary": string (2-3 sentences, specific to this role, evidence-backed)
- "strengths": array of 2-4 strings (specific strengths relevant to the JD)
- "concerns": array of 1-3 strings (honest gaps for this specific role)

Job Description:
{job_description}

Candidate Profile:
{json.dumps(profile, indent=2)}"""

    payload = {
        "system_instruction": {"parts": [{"text": _SYSTEM_INSTRUCTION}]},
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {
            "responseMimeType": "application/json",
            "temperature": 0.3,
        },
    }

    last_exc: Exception | None = None
    for attempt in range(3):
        try:
            resp = httpx.post(
                GEMINI_URL,
                params={"key": settings.GEMINI_API_KEY},
                json=payload,
                timeout=30,
            )
            resp.raise_for_status()
            break
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code < 500:
                raise
            last_exc = exc
            logger.warning("Gemini attempt %d returned %d, retrying", attempt + 1, exc.response.status_code)
            time.sleep(2 ** attempt)
    else:
        raise last_exc  # type: ignore[misc]

    data = resp.json()
    try:
        text = data["candidates"][0]["content"]["parts"][0]["text"]
        result = json.loads(text)
    except (KeyError, IndexError, json.JSONDecodeError) as exc:
        raise ValueError(f"Unexpected Gemini response shape: {exc}") from exc

    for required in ("ai_score", "summary", "strengths", "concerns"):
        if required not in result:
            raise ValueError(f"Gemini response missing field '{required}'")

    return result
