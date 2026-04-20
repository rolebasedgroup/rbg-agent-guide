# RBG Installation Commands

## Install RBG CRD and Controller

```bash
mkdir -p ~/.rbg/workspace
cd ~/.rbg/workspace

# Clone repository (if not exists)
if [ ! -d "rbg" ]; then
    git clone https://github.com/sgl-project/rbg.git
fi

cd rbg
helm upgrade --install rbgs deploy/helm/rbgs \
    --create-namespace \
    --namespace rbgs-system \
    --wait
```

## Install RBG CLI

```bash
mkdir -p ~/.rbg/workspace
cd ~/.rbg/workspace

if [ ! -d "rbg" ]; then
    git clone https://github.com/sgl-project/rbg.git
fi

cd rbg
make build-cli

# Ensure binary is in PATH
export PATH="$HOME/.rbg/workspace/rbg/bin:$PATH"
# Or copy to PATH directory
cp bin/kubectl-rbg ~/.local/bin/ 2>/dev/null || sudo cp bin/kubectl-rbg /usr/local/bin/
```

## External References

- RBG Installation Guide: https://github.com/sgl-project/rbg/blob/main/doc/install.md
- RBG CLI README: https://github.com/sgl-project/rbg/cmd/cli/README.md
