# File: ai_translator/services/ai_api.py
import json
import logging
import os
import re
from typing import Dict, Optional

import requests


class JsonExtractor:
    """Robustly extracts a JSON string from a raw text response."""

    @staticmethod
    def extract(raw_content: str) -> str:
        trimmed = raw_content.strip()
        try:
            json.loads(trimmed)
            return trimmed
        except json.JSONDecodeError:
            pass
        match = re.search(r"```json\s*(\{.*?\})\s*```", trimmed, re.DOTALL)
        if match:
            return match.group(1)
        start_brace = trimmed.find('{')
        end_brace = trimmed.rfind('}')
        if start_brace != -1 and end_brace != -1:
            return trimmed[start_brace:end_brace + 1]
        raise ValueError("Could not extract a valid JSON block from the response.")


def call_ai_translation_api(
        source_text: str, system_prompt: str, model_name: str
) -> Optional[Dict[str, str]]:
    """Call the local AI API and parse the response."""
    api_url = os.getenv("AI_API_URL")
    if not api_url:
        logging.error("AI_API_URL environment variable must be set.")
        return None

    headers = {"Content-Type": "application/json"}
    payload = {
        "model": model_name,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"{source_text} /no_think"},
        ],
        "temperature": 0.2, "max_tokens": 8192, "stream": False,
    }

    response_text = ""
    try:
        response = requests.post(api_url, headers=headers, json=payload, timeout=180)
        response_text = response.text
        response.raise_for_status()

        raw_content = response.json()["choices"][0]["message"]["content"]
        json_string = JsonExtractor.extract(raw_content)
        translations = json.loads(json_string)

        pretty_json = json.dumps(translations, indent=2, ensure_ascii=False)
        logging.debug(f"Successfully parsed AI response:\n{pretty_json}")

        return translations

    except requests.exceptions.RequestException as e:
        logging.error(f"API request failed: {e}")
    except (KeyError, IndexError, json.JSONDecodeError, ValueError, TypeError) as e:
        logging.error(f"Failed to parse API response: {e}. Raw content: {response_text}")

    return None