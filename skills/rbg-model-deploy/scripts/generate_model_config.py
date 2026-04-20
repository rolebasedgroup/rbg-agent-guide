#!/usr/bin/env python3
"""
Generate RBG model configuration file.

Usage:
    python generate_model_config.py <model_id> --params <7B|70B> --dtype <bfloat16|float16> \
        --engine <vllm|sglang> --image <image> --gpu-vram <GB> --gpus-per-node <N>

Examples:
    python generate_model_config.py Qwen/Qwen3.5-0.8B --params 0.8B --dtype bfloat16 \
        --engine vllm --image vllm/vllm-openai:0.6.0 --gpu-vram 24 --gpus-per-node 8
    python generate_model_config.py meta-llama/Llama-3.1-70B --params 70B --dtype bfloat16 \
        --engine vllm --image vllm/vllm-openai:nightly --gpu-vram 80 --gpus-per-node 4
"""

import argparse
import json
import math
import os
import re
import sys


def parse_params(param_str: str) -> int:
    """Parse model params string (e.g., 7B, 70B, 0.8B) to number."""
    param_str = param_str.upper().strip()
    match = re.match(r'([\d.]+)(B|M)?', param_str)
    if not match:
        raise ValueError(f"Invalid parameter format: {param_str}")
    value = float(match.group(1))
    unit = match.group(2) or 'B'
    return int(value * 1_000_000_000) if unit == 'B' else int(value * 1_000_000)


def get_dtype_bytes(dtype: str) -> float:
    """Get bytes per parameter for given dtype."""
    dtype_map = {
        'float32': 4, 'fp32': 4,
        'float16': 2, 'fp16': 2,
        'bfloat16': 2, 'bf16': 2,
        'int8': 1, 'fp8': 1,
        'int4': 0.5
    }
    return dtype_map.get(dtype.lower(), 2)


def estimate_kv_cache(params: int) -> float:
    """Estimate KV cache VRAM in GB based on model size."""
    if params < 1_000_000_000:
        return 0.5
    elif params < 10_000_000_000:
        return 2.0
    elif params < 40_000_000_000:
        return 8.0
    elif params < 80_000_000_000:
        return 20.0
    else:
        return 200.0


def calculate_vram(params: int, dtype_bytes: float, kv_cache_gb: float = None, buffer_percent: float = 15) -> dict:
    """Calculate VRAM requirements."""
    weights_vram_gb = (params * dtype_bytes) / (1024 ** 3)
    kv_cache_gb = kv_cache_gb or estimate_kv_cache(params)
    buffer_gb = (weights_vram_gb + kv_cache_gb) * (buffer_percent / 100)
    return {
        'weights_vram_gb': round(weights_vram_gb, 2),
        'kv_cache_gb': round(kv_cache_gb, 2),
        'buffer_gb': round(buffer_gb, 2),
        'total_vram_gb': round(weights_vram_gb + kv_cache_gb + buffer_gb, 2),
    }


def generate_config(model_id: str, engine: str, image: str, gpus: int,
                    gpu_vram: float, gpus_per_node: int, gpu_type: str = "nvidia.com/gpu",
                    params: int = None, dtype: str = None,
                    args: list = None, distributed: bool = False,
                    trust_remote_code: bool = False) -> dict:
    """Generate RBG configuration dictionary."""

    # Calculate memory and CPU
    cpu = gpus * 4
    memory = math.ceil(gpus * gpu_vram * 1.2 / 8) * 8  # Round up to nearest 8Gi

    # Build args list
    config_args = []
    if gpus >= 2:
        config_args.append(f"--tensor-parallel-size={gpus}")
    if trust_remote_code:
        config_args.append("--trust-remote-code")
    if dtype:
        config_args.append(f"--dtype={dtype}")
    if args:
        config_args.extend(args)

    # Check if multi-node needed
    needs_multi_node = gpus > gpus_per_node
    if needs_multi_node:
        node_count = math.ceil(gpus / gpus_per_node)
        shm_size = f"{max(node_count * 4, 16)}Gi"
    else:
        node_count = 1
        shm_size = None

    # Generate config
    if needs_multi_node or distributed:
        # Multi-node config
        config = [{
            "id": model_id,
            "name": model_id.split("/")[-1],
            "modes": [{
                "name": "distributed-vllm-tp",
                "description": "vLLM distributed inference - tensor parallel across nodes",
                "engine": engine,
                "image": image,
                "resources": {
                    gpu_type: str(gpus_per_node),
                    "cpu": str(cpu),
                    "memory": f"{memory}Gi"
                },
                "args": [f"--tensor-parallel-size={gpus}"] + (args or []),
                "distributed": {"size": node_count},
                "shmSize": shm_size,
                "env": [{
                    "name": "CUDA_VISIBLE_DEVICES",
                    "value": ",".join(map(str, range(gpus_per_node)))
                }]
            }]
        }]
    else:
        # Single-node config
        config = [{
            "id": model_id,
            "name": model_id.split("/")[-1],
            "modes": [{
                "name": "standard",
                "description": "Standard mode",
                "engine": engine,
                "image": image,
                "resources": {
                    gpu_type: str(gpus),
                    "cpu": str(cpu),
                    "memory": f"{memory}Gi"
                },
                "args": config_args,
                "env": [{
                    "name": "CUDA_VISIBLE_DEVICES",
                    "value": ",".join(map(str, range(gpus)))
                }]
            }]
        }]

    return config


def to_yaml(config: list, indent: int = 0) -> str:
    """Simple YAML serializer (no external dependency)."""
    lines = []

    for item in config:
        lines.append(" " * indent + "- id: " + str(item["id"]))
        lines.append(" " * (indent + 2) + "name: " + str(item["name"]))
        lines.append(" " * (indent + 2) + "modes:")

        for mode in item["modes"]:
            lines.append(" " * (indent + 4) + "- name: " + str(mode["name"]))
            lines.append(" " * (indent + 6) + "description: \"" + str(mode.get("description", "")) + "\"")
            lines.append(" " * (indent + 6) + "engine: " + str(mode["engine"]))
            lines.append(" " * (indent + 6) + "image: " + str(mode["image"]))
            lines.append(" " * (indent + 6) + "resources:")

            for key, val in mode["resources"].items():
                lines.append(" " * (indent + 8) + key + ": " + str(val))

            if mode.get("args"):
                lines.append(" " * (indent + 6) + "args:")
                for arg in mode["args"]:
                    lines.append(" " * (indent + 8) + "- \"" + str(arg) + "\"")

            if mode.get("distributed"):
                lines.append(" " * (indent + 6) + "distributed:")
                lines.append(" " * (indent + 8) + "size: " + str(mode["distributed"]["size"]))

            if mode.get("shmSize"):
                lines.append(" " * (indent + 6) + "shmSize: " + str(mode["shmSize"]))

            if mode.get("env"):
                lines.append(" " * (indent + 6) + "env:")
                for env in mode["env"]:
                    lines.append(" " * (indent + 8) + "- name: " + str(env["name"]))
                    lines.append(" " * (indent + 10) + "value: \"" + str(env["value"]) + "\"")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description='Generate RBG model config')
    parser.add_argument('model_id', help='Model ID (e.g., Qwen/Qwen3.5-0.8B)')
    parser.add_argument('--params', required=True, help='Model params (e.g., 7B, 70B, 0.8B)')
    parser.add_argument('--dtype', required=True, help='Data type for weights (bfloat16, float16, etc.)')
    parser.add_argument('--engine', required=True, choices=['vllm', 'sglang'], help='Inference engine')
    parser.add_argument('--image', required=True, help='Container image')
    parser.add_argument('--gpu-vram', type=float, required=True, help='Single GPU VRAM in GB')
    parser.add_argument('--gpus-per-node', type=int, required=True, help='GPUs per node')
    parser.add_argument('--gpu-type', default='nvidia.com/gpu', help='GPU type (default: nvidia.com/gpu)')
    parser.add_argument('--args', nargs='*', default=[], help='Additional engine args')
    parser.add_argument('--trust-remote-code', action='store_true', help='Trust remote code')
    parser.add_argument('--distributed', action='store_true', help='Force distributed mode')
    parser.add_argument('--output', '-o', help='Output file (default: ~/.rbg/models/<name>.yaml)')
    parser.add_argument('--stdout', action='store_true', help='Output to stdout only')
    args = parser.parse_args()

    # Calculate VRAM and GPUs needed
    params = parse_params(args.params)
    dtype_bytes = get_dtype_bytes(args.dtype)
    vram = calculate_vram(params, dtype_bytes)
    gpus_needed = math.ceil(vram['total_vram_gb'] / args.gpu_vram)

    # Generate config
    config = generate_config(
        model_id=args.model_id,
        engine=args.engine,
        image=args.image,
        gpus=gpus_needed,
        gpu_vram=args.gpu_vram,
        gpus_per_node=args.gpus_per_node,
        gpu_type=args.gpu_type,
        params=params,
        dtype=args.dtype,
        args=args.args,
        distributed=args.distributed,
        trust_remote_code=args.trust_remote_code,
    )

    # Convert to YAML
    yaml_content = to_yaml(config)

    # Determine output path
    if args.output:
        output_path = os.path.expanduser(args.output)
    else:
        # Normalize model ID to filename
        name = args.model_id.lower()
        name = re.sub(r'[/_.]', '-', name)
        name = re.sub(r'[^a-z0-9-]', '', name)
        name = re.sub(r'-+', '-', name).strip('-')
        filename = f"{name}.yaml" if name else "default-model.yaml"
        output_path = os.path.expanduser(f"~/.rbg/models/{filename}")

    # Write file
    if not args.stdout:
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, 'w') as f:
            f.write(yaml_content + "\n")
        print(f"Config written to: {output_path}")
    else:
        print(yaml_content)


if __name__ == '__main__':
    main()
