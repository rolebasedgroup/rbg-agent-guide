# RBG CLI Command Reference

## Configuration Commands

```bash
# Initialize configuration
kubectl rbg llm config init

# View current configuration
kubectl rbg llm config view

# Add storage configuration
kubectl rbg llm config add-storage my-pvc --type pvc --config claimName=model-pvc

# List storage configurations
kubectl rbg llm config get-storages

# Add source configuration
kubectl rbg llm config add-source huggingface --type huggingface --config token=hf_xxx

# List source configurations
kubectl rbg llm config get-sources
```

**Important**: Do NOT use `kubectl rbg llm generate` - the configuration it generates is NOT compatible with `kubectl rbg llm run`. Always manually create model configuration files in `~/.rbg/models/`.

## Model Management Commands

```bash
# List downloaded models
kubectl rbg llm models

# List downloaded models from specific source
kubectl rbg llm models --source huggingface

# Download model to storage
kubectl rbg llm pull Qwen/Qwen2.5-7B

# Deploy model (run service)
kubectl rbg llm run <service_name> <model_id>

# List running services
kubectl rbg llm list
kubectl rbg llm list -A  # All namespaces

# Delete service
kubectl rbg llm delete <service_name>

# Chat with model (interactive)
kubectl rbg llm chat -i <service_name>

# Chat with model (single query)
kubectl rbg llm chat <service_name> --prompt "Hello"
```

**Common parameters**: `--replicas` (default 1), `--mode` (from config), `--engine` (vllm/sglang), `--env` (KEY=VALUE), `--arg` (additional args), `--namespace`/`-n` (default default), `--dry-run` (preview).

**service_name Naming Convention** (K8s DNS-1035 label):

Generate compliant name using script:
```bash
python scripts/generate_service_name.py <model_id>
```

## Getting Service Port

The service port is stored in RBG annotation `rbg.workloads.x-k8s.io/cli-metadata`:

```bash
kubectl get rbg <service_name> -o jsonpath='{.metadata.annotations.rbg\.workloads\.x-k8s\.io/cli-metadata}' | jq -r '.port'
```

Common ports by engine:
- vLLM: 8000
- SGLang: 30000
- Triton: 8001
