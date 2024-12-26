import json
import re

def format_value(value):
    """Format a single value into a readable string."""
    if isinstance(value, (dict, list)):
        return json.dumps(value, indent=2)
    return str(value)

def result_formatter(subject: str) -> str:
    """Format the result in a human-readable way without external APIs."""
    try:
        # If subject is a string that might be JSON
        if isinstance(subject, str):
            try:
                data = json.loads(subject)
            except json.JSONDecodeError:
                # If not JSON, return cleaned string
                return re.sub(r'[\n\r]+', '\n', subject).strip()
        else:
            data = subject

        # Format dictionary
        if isinstance(data, dict):
            formatted_parts = []
            for key, value in data.items():
                formatted_key = key.replace('_', ' ').title()
                formatted_value = format_value(value)
                formatted_parts.append(f"{formatted_key}: {formatted_value}")
            return '\n'.join(formatted_parts)
        
        # Format list
        elif isinstance(data, list):
            return '\n'.join(f"- {format_value(item)}" for item in data)
        
        # Format other types
        return str(data)

    except Exception as e:
        # Fallback to original content if formatting fails
        return str(subject)