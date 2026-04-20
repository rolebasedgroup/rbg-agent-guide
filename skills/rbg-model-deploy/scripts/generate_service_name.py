#!/usr/bin/env python3
"""
Generate K8s DNS-1035 compliant service name from model_id.

Usage:
    python generate_service_name.py <model_id>

Examples:
    python generate_service_name.py Qwen/Qwen3.5-0.8B
    # Output: qwen-qwen3-5-0-8b

    python generate_service_name.py THUDM/chatglm3-6b
    # Output: thudm-chatglm3-6b
"""

import re
import sys


def generate_service_name(model_id: str) -> str:
    """
    Generate K8s DNS-1035 compliant service name from model_id.

    Rules:
    - Only lowercase alphanumeric characters and '-'
    - Must start with an alphabetic character
    - Must end with an alphanumeric character
    - Regex: [a-z]([-a-z0-9]*[a-z0-9])?
    """
    # Replace common separators with hyphens
    name = model_id.lower()
    name = re.sub(r'[/_.]', '-', name)
    name = re.sub(r'[^a-z0-9-]', '', name)  # Remove invalid chars
    name = re.sub(r'-+', '-', name)  # Collapse multiple hyphens
    name = name.strip('-')  # Remove leading/trailing hyphens

    # Ensure starts with letter
    if name and not name[0].isalpha():
        name = 'model-' + name

    # Ensure ends with alphanumeric
    if name and not name[-1].isalnum():
        name = name + '-model'

    return name or 'default-model'


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python generate_service_name.py <model_id>", file=sys.stderr)
        sys.exit(1)

    model_id = sys.argv[1]
    print(generate_service_name(model_id))
