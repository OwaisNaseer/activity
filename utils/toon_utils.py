"""Simple TOON (Token-Oriented Object Notation) utilities for LLM communication.

Simple JSON ↔ TOON conversion for token-efficient LLM communication.

TOON Format Specification: https://github.com/toon-format/spec
Python Library: https://github.com/toon-format/toon

TOON Format Examples:
- Simple object: {"name": "Alice", "age": 30} → "name: Alice\nage: 30"
- Array of objects: users[2]{id,name,role}:\n  1,Alice,admin\n  2,Bob,user
"""
import json
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

# Lazy import of toon library
_toon = None

def _get_toon():
    """Lazy import of toon library."""
    global _toon
    if _toon is None:
        try:
            import toon
            _toon = toon
            logger.info("TOON library loaded successfully")
        except ImportError as e:
            logger.warning(f"TOON library not available: {e}. Using fallback implementation.")
            logger.warning("For better performance, install with: pip install toon-llm")
            # Use fallback implementation
            _toon = _FallbackToon()
    return _toon


class _FallbackToon:
    """Fallback TOON encoder/decoder when the toon library is not available.
    
    Simple implementation that converts dicts to a basic TOON-like format.
    """
    @staticmethod
    def encode(data: Dict[str, Any]) -> str:
        """Simple TOON encoding fallback."""
        lines = []
        for key, value in data.items():
            if isinstance(value, str) and (',' in value or ':' in value or '\n' in value):
                lines.append(f'{key}: "{value}"')
            elif isinstance(value, (list, dict)):
                lines.append(f'{key}: {json.dumps(value)}')
            else:
                lines.append(f'{key}: {value}')
        return '\n'.join(lines)
    
    @staticmethod
    def decode(toon_string: str) -> Dict[str, Any]:
        """Simple TOON decoding fallback - converts back to dict."""
        import json
        result = {}
        for line in toon_string.strip().split('\n'):
            if ':' not in line:
                continue
            key, value = line.split(':', 1)
            key = key.strip()
            value = value.strip()
            # Try to parse as JSON if it looks like JSON
            if value.startswith('{') or value.startswith('['):
                try:
                    result[key] = json.loads(value)
                except:
                    result[key] = value
            # Remove quotes if present
            elif value.startswith('"') and value.endswith('"'):
                result[key] = value[1:-1]
            # Try to parse as number
            elif value.isdigit():
                result[key] = int(value)
            elif value.replace('.', '', 1).isdigit():
                result[key] = float(value)
            else:
                result[key] = value
        return result


def json_to_toon(data: Dict[str, Any]) -> str:
    """Convert Python dict (JSON) to TOON format string.
    
    Args:
        data: Dictionary to encode
        
    Returns:
        TOON-formatted string
    """
    toon_lib = _get_toon()
    return toon_lib.encode(data)


def toon_to_json(toon_string: str) -> Dict[str, Any]:
    """Convert TOON format string to Python dict (JSON).
    
    Args:
        toon_string: TOON-formatted string
        
    Returns:
        Python dictionary
    """
    toon_lib = _get_toon()
    # Clean the response (remove markdown code fences if present)
    cleaned = toon_string.strip()
    if cleaned.startswith("```"):
        lines = cleaned.split("\n")
        start_idx = 1 if lines[0].strip().startswith("```") else 0
        end_idx = len(lines)
        for i in range(start_idx, len(lines)):
            if lines[i].strip().startswith("```"):
                end_idx = i
                break
        cleaned = "\n".join(lines[start_idx:end_idx])
    
    return toon_lib.decode(cleaned)
