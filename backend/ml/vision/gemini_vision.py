import json
import os
from typing import Any

from dotenv import load_dotenv
from google import genai
from google.genai import types


# Load project-level .env
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[3]
load_dotenv(BASE_DIR / ".env")

DEFAULT_MODEL = "gemini-2.5-flash"


class GeminiVisionService:
    """
    Optional Vision AI evidence layer.

    Gemini is called only when analyze_image() is explicitly invoked.
    It does not participate in normal risk prediction or risk scoring.
    """

    def __init__(self) -> None:
        self.api_key = os.getenv("GEMINI_API_KEY")
        self.model = os.getenv("GEMINI_MODEL", DEFAULT_MODEL)

        self.client = None

        if self.api_key:
            try:
                self.client = genai.Client(api_key=self.api_key)
            except Exception:
                self.client = None

    @property
    def available(self) -> bool:
        return self.client is not None

    def analyze_image(
        self,
        image_bytes: bytes,
        mime_type: str,
        return_reason: str | None = None,
    ) -> dict[str, Any]:
        """
        Analyze a return image using Gemini Vision.

        This method makes an external Gemini generation request.
        It should only be called explicitly by the Vision endpoint.
        """

        if not self.available:
            return self._unavailable_result(
                "Gemini Vision client is not configured."
            )

        prompt = self._build_prompt(return_reason)

        try:
            response = self.client.models.generate_content(
                model=self.model,
                contents=[
                    types.Part.from_bytes(
                        data=image_bytes,
                        mime_type=mime_type,
                    ),
                    prompt,
                ],
            )

            return self._parse_response(response)

        except Exception as exc:
            print(
               f"[GeminiVisionService] Vision request failed: "
               f"{type(exc).__name__}"
            )

            if hasattr(exc, "code"):
                print(f"[GeminiVisionService] Error code: {exc.code}")

            if hasattr(exc, "message"):
                 print(f"[GeminiVisionService] Error message: {exc.message}")

            return self._unavailable_result(
                 "Vision assessment is temporarily unavailable."
            )

    @staticmethod
    def _build_prompt(return_reason: str | None) -> str:
        reason_text = (
            return_reason.strip()
            if return_reason and return_reason.strip()
            else "Not provided"
        )

        return f"""
You are a return-evidence assessment system.

Inspect the uploaded return image and provide a cautious assessment of
visible physical evidence.

Reported return reason:
{reason_text}

Determine:

1. The visible physical condition of the item/package.
2. Whether the visible evidence supports the reported return reason.
3. The strongest visible evidence.
4. Your confidence in the assessment.

Important restrictions:
- Assess only what is visibly present in the image.
- Do not identify the person.
- Do not infer identity, demographics, intent, criminality, or personality.
- Do not accuse the customer of fraud or abuse.
- Do not make claims about facts that cannot be observed.
- If the image is unclear or insufficient, return an uncertain assessment.
- This is evidence for human review, not an automated fraud determination.

Return ONLY valid JSON using this structure:

{{
  "condition": "CLEAR | DAMAGED | USED | PACKAGING_DAMAGE | UNCLEAR | OTHER",
  "confidence": 0.0,
  "claim_supported": true,
  "evidence": [
    "short visible observation"
  ],
  "message": "short human-readable assessment"
}}

Rules:
- confidence must be between 0.0 and 1.0.
- claim_supported must be true, false, or null.
- Use null when the reported reason cannot be meaningfully assessed.
- evidence must contain only observations visible in the image.
"""

    def _parse_response(self, response: Any) -> dict[str, Any]:
        text = getattr(response, "text", None)

        if not text:
            return self._unavailable_result(
                "Gemini returned an empty response."
            )

        try:
            cleaned = text.strip()

            # Handle ```json ... ``` responses defensively.
            if cleaned.startswith("```"):
                cleaned = cleaned.removeprefix("```json")
                cleaned = cleaned.removeprefix("```")
                cleaned = cleaned.removesuffix("```")
                cleaned = cleaned.strip()

            data = json.loads(cleaned)

            condition = str(
                data.get("condition", "UNCLEAR")
            ).strip() or "UNCLEAR"

            confidence = self._safe_confidence(
                data.get("confidence", 0.0)
            )

            claim_supported = data.get("claim_supported")

            if claim_supported not in (True, False, None):
                claim_supported = None

            evidence = self._safe_evidence(
                data.get("evidence", [])
            )

            message = str(
                data.get(
                    "message",
                    "Vision assessment completed.",
                )
            ).strip()

            return {
                "available": True,
                "condition": condition,
                "confidence": confidence,
                "claim_supported": claim_supported,
                "evidence": evidence,
                "message": message,
            }

        except (json.JSONDecodeError, TypeError, ValueError):
            return self._unavailable_result(
                "Gemini returned an invalid structured response."
            )

    @staticmethod
    def _safe_confidence(value: Any) -> float:
        try:
            confidence = float(value)
        except (TypeError, ValueError):
            return 0.0

        return max(0.0, min(1.0, confidence))

    @staticmethod
    def _safe_evidence(value: Any) -> list[str]:
        if not isinstance(value, list):
            return []

        return [
            str(item).strip()
            for item in value
            if str(item).strip()
        ][:5]

    @staticmethod
    def _unavailable_result(message: str) -> dict[str, Any]:
        return {
            "available": False,
            "condition": "UNKNOWN",
            "confidence": 0.0,
            "claim_supported": None,
            "evidence": [],
            "message": message,
        }