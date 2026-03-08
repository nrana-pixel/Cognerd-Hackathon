"""
UTILITY MODULES
Centralized utilities for file I/O, time handling, path resolution, and data parsing.

Created by: Aman Mundra
Date: 2026-02-06

"""

import os
import json
import ast
import logging
from pathlib import Path
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
from typing import Any, Union, List, Dict, Optional

_logger = logging.getLogger(__name__)

def get_project_root() -> Path:
    """Returns the root directory of the project (PyCode)."""
    return Path(__file__).resolve().parent.parent.parent

def read_markdown_file(filename: str) -> str:
    """Reads content from a markdown file, checking standard locations."""
    # 1. Check absolute path or CWD
    if os.path.exists(filename):
        with open(filename, 'r', encoding='utf-8') as f:
            content = f.read()
            _logger.debug("Loaded prompt '%s' from CWD (%d chars)", filename, len(content))
            return content
            
    # 2. Check src/prompts relative to project root (NEW canonical location)
    root = get_project_root()
    prompts_base = root / "src" / "prompts"
    prompt_path = prompts_base / filename
    
    if prompt_path.exists():
        with open(prompt_path, 'r', encoding='utf-8') as f:
            content = f.read()
            _logger.debug("Loaded prompt '%s' from prompts dir (%d chars)", filename, len(content))
            return content

    # 3. Check subdirectories of prompts (e.g. prompts/agents/)
    if prompts_base.exists():
        for match in prompts_base.rglob(filename):
            with open(match, 'r', encoding='utf-8') as f:
                content = f.read()
                _logger.debug("Loaded prompt '%s' from %s (%d chars)", filename, match, len(content))
                return content

    # 4. Fallback: check old location src/intelliwrite/prompts for backward compat
    old_prompts_base = root / "src" / "intelliwrite" / "prompts"
    if old_prompts_base.exists():
        for match in old_prompts_base.rglob(filename):
            with open(match, 'r', encoding='utf-8') as f:
                content = f.read()
                _logger.debug("Loaded prompt '%s' from old location %s (%d chars)", filename, match, len(content))
                return content

    _logger.warning(
        "⚠️ Prompt file '%s' NOT FOUND in any search location! "
        "Agent will have NO instructions. Searched: CWD=%s, prompts_base=%s",
        filename, os.getcwd(), prompts_base,
    )
    return ""


def get_current_utc_iso() -> str:
    """Returns current UTC timestamp in ISO 8601 format."""
    return datetime.now(timezone.utc).isoformat()

def safe_json_parse(input_data: Union[str, List, Dict]) -> Any:
    """Safely parses a string into a JSON object (dict or list)."""
    if isinstance(input_data, (dict, list)):
        return input_data
    
    if not isinstance(input_data, str):
        return None

    cleaned = input_data.strip()
    if not cleaned:
        return None

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass

    try:
        return ast.literal_eval(cleaned)
    except (ValueError, SyntaxError):
        pass

    return None

def get_current_local_iso(tz_name: str = "Asia/Kolkata") -> str:
    """Returns current local timestamp in ISO 8601 format."""
    try:
        tz = ZoneInfo(tz_name)
    except (ZoneInfoNotFoundError, Exception):
        # Fallback to IST if timezone name is not found
        tz = timezone(timedelta(hours=5, minutes=30))
    return datetime.now(tz).isoformat()

def check_openrouter_quota(api_key: str):
    """Checks OpenRouter API key rate limits and remaining credits."""
    import requests
    if not api_key:
        return {"error": "No API key provided"}
        
    try:
        response = requests.get(
            url="https://openrouter.ai/api/v1/key",
            headers={"Authorization": f"Bearer {api_key}"}
        )
        return response.json()
    except Exception as e:
        return {"error": str(e)}
