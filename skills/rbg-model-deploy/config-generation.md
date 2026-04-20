# Configuration Generation Rules

**When to Read**: When `kubectl rbg llm run` fails with `no configuration found for model`.

---

## ⚠️ CRITICAL: DO NOT USE `kubectl rbg llm generate`

| Command | Use? |
|---------|------|
| `kubectl rbg llm generate` | ❌ **NO** - generates incompatible configs |
| `python scripts/generate_model_config.py` | ✅ **YES** - generates compliant configs |

**MUST use script to generate config file.**

---

## Pre-Generation Steps

### Step 1: Get Model Info

**⚠️ CRITICAL: NEVER guess model information!**

| Info | Source |
|------|--------|
| Architecture, params, precision | HuggingFace/ModelScope model card / `config.json` |
| Engine compatibility | Web search: "<model> vLLM/SGLang support" |

- Read `~/.rbg/config` for model source (HuggingFace, ModelScope)
- Search web for model requirements
- Read `config.json` for `params`, `torch_dtype`, and `trust_remote_code`
- Note: `params` (e.g., 7B, 70B), `torch_dtype` (e.g., bfloat16), and `trust_remote_code` are required for config generation

### Step 2: Get GPU Info

**Priority order**:

1. **User specified** → Use user's value
   - GPU model (e.g., RTX 4090, A100 40G)
   - GPUs per node (e.g., 8)

2. **User not specified** → Check cluster
   ```bash
   kubectl get nodes -o wide
   kubectl describe nodes | grep -A5 "Capacity:" | grep -i gpu
   ```

3. **Cluster check failed** → Ask user
   > Warning: GPU not found in cluster. Please specify GPU model and count, or check cluster configuration.

**Output**: 
- `gpu-model`: GPU model name
- `gpu-vram`: VRAM per GPU (GB)
- `gpus-per-node`: GPU count per node

### Step 3: Search Compatible Engine Image

Search web for:
- "<GPU model> vLLM/SGLang version limit" (e.g., "V100 vLLM <0.5.4")
- "<model_id> vLLM/SGLang minimum version", "<model_id> nightly"

**If version conflict** (GPU needs <X but model needs >=Y):
> Warning: Version conflict - GPU needs <engine> <X, but model needs >=Y.
> Options: Use different GPUs, change model version, or try quantization.

**Engine selection**: Prefer vLLM unless user specifies otherwise.

**Output**: engine + image tag (e.g., `vllm/vllm-openai:nightly`)

### Step 4: Calculate GPU Requirements and Generate Config

## ⚠️ CRITICAL: 配置生成前必须完成的检查清单

Before running `generate_model_config.py`, confirm the following information is collected:

- [ ] Step 1: Model parameters (params, dtype, trust_remote_code)
- [ ] Step 2: GPU info (model, VRAM, count per node)
- [ ] **Step 3: Image search (GPU version limits + model compatibility)** ← emphasize with checkbox

**DO NOT proceed if any item is incomplete!**

**Generate config** (automatically calculates VRAM and GPUs needed):
```bash
python scripts/generate_model_config.py <model_id> \
    --params <params> \              # From Step 1
    --dtype <dtype> \                # From Step 1 config.json
    --engine <vllm|sglang> \         # From Step 3
    --image <image> \                # From Step 3
    --gpu-vram <GB> \                # From Step 2
    --gpus-per-node <N> \            # From Step 2
    --gpu-type <type> \              # Optional, default: nvidia.com/gpu
    --trust-remote-code \            # From Step 1 (if config.json has trust_remote_code: true)
```

**Script automatically**:
- Calculates VRAM: model weights + KV cache + 15% buffer
- Calculates GPUs needed: `ceil(total_vram / gpu_vram)`
- Determines single-node vs multi-node (based on `gpus > gpus-per-node`)
- Calculates memory, CPU, shmSize
- Generates correct YAML format
- Writes to `~/.rbg/models/`

### Step 5: Re-run Deployment

**Generate service name** (if not already generated):
```bash
SERVICE_NAME=$(python scripts/generate_service_name.py <model_id>)
```

**Deploy**:
```bash
kubectl rbg llm run $SERVICE_NAME <model_id>
```
