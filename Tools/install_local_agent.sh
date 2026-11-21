#!/usr/bin/env bash
# Run as the application user on a 64-bit Raspberry Pi, never with sudo.
set -euo pipefail
[[ $(uname -s) == Linux && $(uname -m) == aarch64 ]] || { echo 'Requires Linux ARM64 on Raspberry Pi.'; exit 1; }
[[ $EUID != 0 ]] || { echo 'Run as the HomeHub user, without sudo.'; exit 1; }
for tool in git curl sha256sum c++ python3; do command -v "$tool" >/dev/null || { echo "Missing $tool; see docs/LOCAL_AGENT_PI.md"; exit 1; }; done
agent_root="$HOME/.local/share/homehub/agent"
source_dir="$agent_root/llama-b11960"
model_file="$agent_root/LFM3-1.7B-Q4_K_M.gguf"
mkdir -p "$agent_root"
cmake_bin=$(command -v cmake || true)
if [[ -z "$cmake_bin" ]]; then
    python3 -m venv "$agent_root/build-tools"
    "$agent_root/build-tools/bin/python" -m pip install --disable-pip-version-check 'cmake==3.31.6'
    cmake_bin="$agent_root/build-tools/bin/cmake"
fi
if [[ ! -d "$source_dir" ]]; then
    git clone --depth 1 --branch b11960 https://github.com/ggml-org/llama.cpp.git "$source_dir"
fi
[[ $(git -C "$source_dir" rev-parse HEAD) == 8642541b255bfb5dc39cd351a178be09013a55d6 ]] || { echo 'Unexpected llama.cpp revision'; exit 1; }
[[ -z $(git -C "$source_dir" status --porcelain --untracked-files=no) ]] || { echo 'llama.cpp source has local edits'; exit 1; }
# Remove only generated web assets left by an earlier interrupted build.
# With both UI options OFF, llama.cpp would otherwise still embed this stale directory.
if [[ -d "$source_dir/build/tools/ui/dist" ]]; then
    rm -rf -- "$source_dir/build/tools/ui/dist"
fi
"$cmake_bin" -S "$source_dir" -B "$source_dir/build" -DCMAKE_BUILD_TYPE=Release -DGGML_NATIVE=ON -DGGML_VULKAN=OFF -DLLAMA_CURL=OFF -DLLAMA_BUILD_UI=OFF -DLLAMA_USE_PREBUILT_UI=OFF
"$cmake_bin" --build "$source_dir/build" --target llama-server llama-bench -j 2
expected=3793e1e6e2266919d6e015287221b41100175a98eddaba92e111aed3b05c93c4
if [[ ! -f "$model_file" ]] || [[ $(sha256sum "$model_file" | cut -d ' ' -f 1) != "$expected" ]]; then
    curl --fail --location --retry 3 --output "$model_file.part" 'https://huggingface.co/LiquidAI/LFM3-1.7B-GGUF/resolve/cd0c74c575b5c416f3011b5b4c298077f26ca8c2/LFM3-1.7B-Q4_K_M.gguf'
    [[ $(sha256sum "$model_file.part" | cut -d ' ' -f 1) == "$expected" ]] || { echo 'Model checksum mismatch'; exit 1; }
    mv "$model_file.part" "$model_file"
fi
mkdir -p "$HOME/.config/systemd/user"
script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
cp "$script_dir/../deploy/homehub-agent.service" "$HOME/.config/systemd/user/homehub-agent.service"
systemctl --user daemon-reload
systemctl --user enable homehub-agent.service
systemctl --user restart homehub-agent.service
printf '%s\n' 'Installed. Check: journalctl --user -u homehub-agent -n 40 --no-pager' 'Run benchmark before enabling HOMEHUB_LOCAL_AGENT=1.'
