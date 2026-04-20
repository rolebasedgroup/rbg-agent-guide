---
name: rbg-model-deploy
description: Deploy LLM models to Kubernetes using RBG (Role-Based Group) CRD and CLI. Use when the user wants to deploy AI models, mentions RBG, kubectl rbg, or model deployment on K8s.
---

# RBG Model Deployment

Help users quickly deploy models using RBG CRD + RBG CLI.

## Trigger Conditions

- User explicitly wants to deploy an LLM model to Kubernetes
- User mentions RBG, `kubectl rbg`, or model deployment related commands
- User asks how to run a model service

## Capabilities

**Supported**: Deploy LLM models to K8s using RBG, manage RBG services (list, delete, restart), generate/repair model configs, install RBG environment.

**Not Supported**: Model training/fine-tuning, non-RBG deployments, model conversion/quantization, K8s cluster creation.

**Prerequisites**: K8s cluster access; model source determined by RBG config (HuggingFace, ModelScope, etc.)

## Scripts

Scripts are located in the `scripts/` directory relative to this skill. Find the script directory:

```bash
cd /path/to/rbg-model-deploy/scripts
```

**Available scripts**:
- `generate_service_name.py` - Generate service name from model ID
- `generate_model_config.py` - Generate model configuration YAML

## Pre-flight Checks

```bash
# Check K8s connection
kubectl cluster-info

# Check RBG CRD
kubectl get crd rolebasedgroups.workloads.x-k8s.io

# Check RBG CLI
kubectl rbg version

# Check RBG config
kubectl rbg llm config view
```

If any check fails, see installation.md for setup instructions.

## Model Deployment Flow

### Step 1: Get Model ID

Ask the user:
> Please enter the model ID to deploy (e.g., Qwen/Qwen3.5-0.5B):

### Step 2: Download Model

Check existing models first, only download if not present:

```bash
# List downloaded models
kubectl rbg llm models

# Download model only if not found
kubectl rbg llm pull <model_id>
```

**Wait Discipline**: Model download can take hours. Use blocking wait and wait passively:
```bash
kubectl wait --for=condition=complete job/<job-name> -n <namespace> --timeout=0
```
Do NOT check logs repeatedly during wait.

### Step 3: Execute Deployment

After model download completes, deploy the model using `kubectl rbg llm run`:

**Step 3.1: Generate service name**
```bash
SERVICE_NAME=$(python scripts/generate_service_name.py <model_id>)
# Example: python scripts/generate_service_name.py Qwen/Qwen3.5-0.8B → qwen-qwen3-5-0-8b
```

**Step 3.2: Deploy**
```bash
kubectl rbg llm run $SERVICE_NAME <model_id>
```

Example:
```bash
python scripts/generate_service_name.py Qwen/Qwen3.5-0.8B
# Output: qwen-qwen3-5-0-8b
kubectl rbg llm run qwen-qwen3-5-0-8b Qwen/Qwen3.5-0.8B
```

Common parameters: `--replicas` (default 1), `--mode` (from config), `--engine` (vllm, sglang), `--namespace` (default default).

**If error `no configuration found for model`**: See Troubleshooting section.

### Step 4: Verify Deployment

```bash
kubectl rbg llm list
kubectl rbg llm list -n <namespace>
kubectl rbg llm list -A
```

### Step 5: Usage Tips

After successful deployment, get the port and inform user:

```bash
kubectl get rbg <service_name> -o jsonpath='{.metadata.annotations.rbg\.workloads\.x-k8s\.io/cli-metadata}' | jq -r '.port'
```

> Model deployed successfully! You can interact with the model via:
> 1. `kubectl rbg llm chat -i <service_name>`
> 2. `kubectl rbg llm chat <service_name> --prompt "your question"`
> 3. `kubectl port-forward svc/<service_name> <port>:<port> -n <namespace>`

## Troubleshooting

### Configuration Not Found

If `kubectl rbg llm run` fails with `no configuration found for model`:

**CRITICAL: Read config-generation.md BEFORE generating any configuration.**

Follow the 5 steps in config-generation.md:
1. Step 1: Gather model info (params, dtype, trust_remote_code)
2. Step 2: Get GPU info (user-specified → cluster check → ask user)
3. Step 3: Search engine compatibility and image
4. Step 4: Run `generate_model_config.py` (auto-calculates VRAM and GPUs)
5. Step 5: Re-run `kubectl rbg llm run $SERVICE_NAME <model_id>`
