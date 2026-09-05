from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from google import genai


BASE_DIR = Path(__file__).resolve().parents[3]
load_dotenv(BASE_DIR / ".env")

DEFAULT_MODEL = "gemini-2.5-flash"

MODEL_FIELDS = {
    "order_category",
    "order_value",
    "item_value",
    "quantity",
    "time_to_return_request_hours",
    "refund_amount",
    "returned_item_match",
    "item_condition_score",
    "package_weight_delta_pct",
    "vision_confidence_score",
    "account_age_days",
    "lifetime_order_count",
    "lifetime_return_count",
    "total_spent",
    "return_rate",
    "return_velocity_30d",
    "return_velocity_48h",
    "shared_device_count",
    "shared_address_count",
    "shared_payment_fingerprint_count",
    "device_return_velocity_7d",
    "address_return_velocity_7d",
    "payment_return_velocity_7d",
    "cluster_return_velocity_7d",
    "order_category",
    "return_reason",
}

IDENTITY_FIELDS = {
    "user_id",
    "customer_id",
    "account_id",
    "buyer_id",
    "user",
    "email",
    "phone",
    "mobile",
    "order_id",
    "return_id",
    "device_fingerprint",
    "address_hash",
    "payment_fingerprint",
}


class LLMDataUnderstandingService:
    """
    Converts arbitrary raw return/customer data into structured fields
    that can be consumed by the existing RiskGuard ML pipeline.

    This service does NOT:
    - predict risk
    - calculate risk scores
    - make ALLOW/REVIEW/BLOCK decisions
    - invent missing behavioral/model features
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

    def understand(self, raw_data: dict[str, Any]) -> dict[str, Any]:
        """
        Understand raw input and return normalized structured data.

        The LLM is used only for semantic field identification/mapping.
        """

        if not isinstance(raw_data, dict):
            raise ValueError("Raw input must be an object.")

        if not self.available:
            return self._fallback_understanding(raw_data)

        prompt = self._build_prompt(raw_data)

        try:
            response = self.client.models.generate_content(
                model=self.model,
                contents=prompt,
            )

            return self._parse_response(response, raw_data)

        except Exception as exc:
            print(
                "[LLMDataUnderstandingService] "
                f"Request failed: {type(exc).__name__}"
            )
            return self._fallback_understanding(raw_data)

    @staticmethod
    def _build_prompt(raw_data: dict[str, Any]) -> str:
        serialized = json.dumps(
            raw_data,
            ensure_ascii=False,
            default=str,
        )

        return f"""
You are the RiskGuard AI data-understanding layer.

Your ONLY responsibility is to understand raw return/customer/order data
and map fields to the canonical RiskGuard input schema.

You are NOT the risk model.

Do NOT:
- predict fraud or abuse
- calculate a risk score
- decide ALLOW, REVIEW, or BLOCK
- classify the customer as risky
- invent missing values
- estimate missing behavioral metrics
- fabricate user IDs
- fabricate account/device/address/payment relationships

Existing ML model fields are:

{json.dumps(sorted(MODEL_FIELDS), indent=2)}

Possible identity/reference fields include:

{json.dumps(sorted(IDENTITY_FIELDS), indent=2)}

For every value you map:
- preserve the original value when possible
- normalize obvious representations only when unambiguous
- map different names such as "customer_id" or "buyer_id" to the
  appropriate identity field when the meaning is clear
- leave unavailable fields absent
- never create values that were not present in the input

Return ONLY valid JSON:

{{
  "normalized_data": {{
    "canonical_field": "value"
  }},
  "identity": {{
    "field": "value"
  }},
  "source_mapping": {{
    "canonical_field": "original_field_name"
  }},
  "missing_fields": [
    "field_name"
  ]
}}

Raw input:

{serialized}
"""

    def _parse_response(
        self,
        response: Any,
        raw_data: dict[str, Any],
    ) -> dict[str, Any]:
        text = getattr(response, "text", None)

        if not text:
            return self._fallback_understanding(raw_data)

        try:
            cleaned = text.strip()

            if cleaned.startswith("```"):
                cleaned = cleaned.removeprefix("```json")
                cleaned = cleaned.removeprefix("```")
                cleaned = cleaned.removesuffix("```")
                cleaned = cleaned.strip()

            data = json.loads(cleaned)

            normalized_data = data.get("normalized_data", {})
            identity = data.get("identity", {})
            source_mapping = data.get("source_mapping", {})
            missing_fields = data.get("missing_fields", [])

            if not isinstance(normalized_data, dict):
                normalized_data = {}

            if not isinstance(identity, dict):
                identity = {}

            if not isinstance(source_mapping, dict):
                source_mapping = {}

            if not isinstance(missing_fields, list):
                missing_fields = []

            normalized_data = {
                str(key): value
                for key, value in normalized_data.items()
                if str(key) in MODEL_FIELDS
            }

            identity = {
                str(key): value
                for key, value in identity.items()
                if str(key) in IDENTITY_FIELDS
            }

            return {
                "normalized_data": normalized_data,
                "identity": identity,
                "source_mapping": source_mapping,
                "missing_fields": [
                    str(field)
                    for field in missing_fields
                ],
                "llm_used": True,
            }

        except (json.JSONDecodeError, TypeError, ValueError):
            return self._fallback_understanding(raw_data)

    @staticmethod
    def _fallback_understanding(
        raw_data: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Deterministic fallback.

        Existing canonical fields are preserved directly.
        Nothing missing is fabricated.
        """

        normalized_data = {
            key: value
            for key, value in raw_data.items()
            if key in MODEL_FIELDS
        }

        identity = {
            key: value
            for key, value in raw_data.items()
            if key in IDENTITY_FIELDS
        }

        missing_fields = sorted(
            MODEL_FIELDS - set(normalized_data.keys())
        )

        return {
            "normalized_data": normalized_data,
            "identity": identity,
            "source_mapping": {
                key: key
                for key in normalized_data
            },
            "missing_fields": missing_fields,
            "llm_used": False,
        }


llm_data_understanding_service = LLMDataUnderstandingService()
