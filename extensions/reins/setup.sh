#!/usr/bin/env bash
set -euo pipefail

# Reins extension setup — installs all prerequisites and validates the environment.
# Works on macOS (Homebrew) and Linux (apt/curl).
#
# Usage:
#   git clone https://github.com/LuisDee/reins.git ~/.gemini/extensions/reins
#   cd ~/.gemini/extensions/reins
#   bash setup.sh

# ─── Pinned versions ──────────────────────────────────────────────────────────
SERENA_COMMIT="dcbf08520d9b6bccafc9f994284ea2be22458c56"
HASHLINE_VERSION="0.2.0"
SEQTHINK_VERSION="2025.12.18"
CONTEXT7_VERSION="2.1.1"
PLAYWRIGHT_VERSION="0.0.68"
DOCKER_MCP_VERSION="v0.40.0"

# ─── Colors ───────────────────────────────────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
BOLD='\033[1m'
NC='\033[0m'

ok()   { echo -e "  ${GREEN}✓${NC} $1"; }
warn() { echo -e "  ${YELLOW}!${NC} $1"; }
fail() { echo -e "  ${RED}✗${NC} $1"; }
step() { echo -e "\n${BLUE}${BOLD}$1${NC}"; }

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# ─── Detect OS ────────────────────────────────────────────────────────────────
OS="$(uname -s)"
ARCH="$(uname -m)"
case "$OS" in
  Darwin) PLATFORM="macos" ;;
  Linux)  PLATFORM="linux" ;;
  *)      echo "Unsupported OS: $OS"; exit 1 ;;
esac

# Map architecture names
case "$ARCH" in
  x86_64)  GOARCH="amd64" ;;
  aarch64|arm64) GOARCH="arm64" ;;
  *)       echo "Unsupported architecture: $ARCH"; exit 1 ;;
esac

echo -e "${BOLD}Reins — Gemini CLI Extension Installer${NC}"
echo -e "  platform: ${PLATFORM}/${GOARCH}"
echo ""

# ─── Helper: install a package ────────────────────────────────────────────────
install_pkg() {
  local name="$1"
  shift
  if [ "$PLATFORM" = "macos" ]; then
    if ! command -v brew &>/dev/null; then
      fail "homebrew not found — install from https://brew.sh"
      return 1
    fi
    brew install "$@"
  else
    # Linux — caller provides the install command as remaining args
    "$@"
  fi
}

# ─── Link extension if cloned outside ~/.gemini/extensions ───────────────────
step "[1/8] Linking extension"

EXTENSION_DIR="$HOME/.gemini/extensions/reins"
if [ "$SCRIPT_DIR" = "$EXTENSION_DIR" ]; then
  ok "already in ~/.gemini/extensions/reins"
elif [ -L "$EXTENSION_DIR" ] && [ "$(readlink "$EXTENSION_DIR")" = "$SCRIPT_DIR" ]; then
  ok "symlink already exists"
else
  mkdir -p "$HOME/.gemini/extensions"
  if [ -d "$EXTENSION_DIR" ] && [ ! -L "$EXTENSION_DIR" ]; then
    warn "~/.gemini/extensions/reins already exists (not a symlink)"
    warn "backing up to ~/.gemini/extensions/reins.bak"
    mv "$EXTENSION_DIR" "${EXTENSION_DIR}.bak"
  fi
  ln -sfn "$SCRIPT_DIR" "$EXTENSION_DIR"
  ok "linked $SCRIPT_DIR -> ~/.gemini/extensions/reins"
fi

# ─── Check prerequisites ─────────────────────────────────────────────────────
step "[2/8] Checking prerequisites"

errors=0

# Node.js
if command -v node &>/dev/null; then
  ok "node $(node --version)"
else
  if [ "$PLATFORM" = "macos" ]; then
    fail "node not found — install via: brew install node"
  else
    fail "node not found — install via: sudo apt install nodejs npm"
  fi
  ((errors++))
fi

# npx
if command -v npx &>/dev/null; then
  ok "npx $(npx --version)"
else
  fail "npx not found — comes with node"
  ((errors++))
fi

# Bun
if command -v bun &>/dev/null; then
  ok "bun $(bun --version)"
else
  warn "bun not found — installing..."
  if [ "$PLATFORM" = "macos" ]; then
    brew install oven-sh/bun/bun
  else
    curl -fsSL https://bun.sh/install | bash
    export BUN_INSTALL="$HOME/.bun"
    export PATH="$BUN_INSTALL/bin:$PATH"
  fi
  ok "bun $(bun --version)"
fi

# uv
if command -v uv &>/dev/null; then
  ok "uv $(uv --version)"
else
  warn "uv not found — installing..."
  if [ "$PLATFORM" = "macos" ]; then
    brew install uv
  else
    curl -LsSf https://astral.sh/uv/install.sh | sh
    export PATH="$HOME/.local/bin:$PATH"
  fi
  ok "uv $(uv --version)"
fi

# Docker Engine
if command -v docker &>/dev/null; then
  ok "docker $(docker --version | grep -oE '[0-9]+\.[0-9]+\.[0-9]+' | head -1)"
else
  if [ "$PLATFORM" = "macos" ]; then
    fail "docker not found — install Docker Desktop: https://www.docker.com/products/docker-desktop"
  else
    fail "docker not found — install via: sudo apt install docker.io"
  fi
  ((errors++))
fi

# Gemini CLI
if command -v gemini &>/dev/null; then
  ok "gemini CLI $(gemini --version 2>&1)"
else
  fail "gemini CLI not found — install via: npm install -g @google/gemini-cli"
  ((errors++))
fi

if [ "$errors" -gt 0 ]; then
  fail "$errors prerequisite(s) missing. Fix and re-run."
  exit 1
fi

# ─── Install Docker MCP plugin ──────────────────────────────────────────────
step "[3/8] Docker MCP plugin"

if docker mcp --help &>/dev/null 2>&1; then
  ok "docker mcp already installed"
else
  warn "docker mcp not found — installing from GitHub releases..."
  DOCKER_MCP_URL="https://github.com/docker/mcp-gateway/releases/download/${DOCKER_MCP_VERSION}"

  if [ "$PLATFORM" = "macos" ]; then
    DOCKER_MCP_ARCHIVE="docker-mcp-darwin-${GOARCH}.tar.gz"
  else
    DOCKER_MCP_ARCHIVE="docker-mcp-linux-${GOARCH}.tar.gz"
  fi

  TMPDIR_MCP="$(mktemp -d)"
  trap "rm -rf '$TMPDIR_MCP'" EXIT

  curl -fsSL "${DOCKER_MCP_URL}/${DOCKER_MCP_ARCHIVE}" -o "${TMPDIR_MCP}/${DOCKER_MCP_ARCHIVE}"
  tar -xzf "${TMPDIR_MCP}/${DOCKER_MCP_ARCHIVE}" -C "${TMPDIR_MCP}"

  mkdir -p "$HOME/.docker/cli-plugins"
  mv "${TMPDIR_MCP}/docker-mcp" "$HOME/.docker/cli-plugins/docker-mcp"
  chmod +x "$HOME/.docker/cli-plugins/docker-mcp"

  # On Linux without Docker Desktop, bypass the Desktop feature check
  if [ "$PLATFORM" = "linux" ]; then
    ok "setting DOCKER_MCP_IN_CONTAINER=1 for Docker Engine compatibility"
    export DOCKER_MCP_IN_CONTAINER=1
  fi

  if docker mcp --help &>/dev/null 2>&1; then
    ok "docker mcp installed to ~/.docker/cli-plugins/"
  else
    fail "docker mcp install failed — check https://github.com/docker/mcp-gateway"
    exit 1
  fi
fi

# ─── Configure settings.json (merge, don't clobber) ─────────────────────────
step "[4/8] Configuring settings.json"

SETTINGS="$HOME/.gemini/settings.json"
NPX_PATH="$(command -v npx)"
BUNX_PATH="$(command -v bunx)"
UVX_PATH="$(command -v uvx)"
DOCKER_PATH="$(command -v docker)"

# Python script that merges reins config into existing settings.json.
# - Preserves all existing user config (custom MCP servers, other keys)
# - Only adds missing keys — never overwrites existing MCP server entries
# - Creates fresh settings.json if none exists
# - Backs up existing file before writing
MERGE_RESULT=$(python3 - "$SETTINGS" "${SCRIPT_DIR}/settings.template.json" "$NPX_PATH" "$BUNX_PATH" "$UVX_PATH" "$DOCKER_PATH" <<'PYEOF'
import json, sys, os, shutil

settings_path = sys.argv[1]
template_path = sys.argv[2]
npx_path = sys.argv[3]
bunx_path = sys.argv[4]
uvx_path = sys.argv[5]
docker_path = sys.argv[6]

# Load template and resolve placeholders
with open(template_path) as f:
    template = json.load(f)

placeholders = {
    "__NPX__": npx_path,
    "__BUNX__": bunx_path,
    "__UVX__": uvx_path,
    "__DOCKER__": docker_path,
}

for server in template.get("mcpServers", {}).values():
    cmd = server.get("command", "")
    if cmd in placeholders:
        server["command"] = placeholders[cmd]

# Load existing settings or start fresh
if os.path.exists(settings_path):
    try:
        with open(settings_path) as f:
            settings = json.load(f)
    except json.JSONDecodeError:
        print("ERROR: existing settings.json is invalid JSON")
        sys.exit(1)

    # Back up before modifying
    backup = settings_path + ".bak"
    shutil.copy2(settings_path, backup)
    print(f"BACKUP:{backup}")
    created = False
else:
    settings = {}
    created = True

# Merge top-level flags
if not settings.get("subagents"):
    settings["subagents"] = True
    print("ADDED:subagents: true")

exp = settings.setdefault("experimental", {})
if not exp.get("enableAgents"):
    exp["enableAgents"] = True
    print("ADDED:experimental.enableAgents: true")

# Merge MCP servers — only add missing ones, never overwrite
servers = settings.setdefault("mcpServers", {})
for name, config in template.get("mcpServers", {}).items():
    if name in servers:
        print(f"KEPT:{name} (already configured)")
    else:
        servers[name] = config
        print(f"ADDED:{name}")

# Write result
with open(settings_path, "w") as f:
    json.dump(settings, f, indent=2)
    f.write("\n")

if created:
    print("STATUS:created")
else:
    print("STATUS:merged")
PYEOF
)

# Parse the Python output and report results
if [ $? -ne 0 ]; then
  fail "failed to configure settings.json"
  echo "$MERGE_RESULT"
  exit 1
fi

# Report what happened
status=""
while IFS= read -r line; do
  case "$line" in
    STATUS:created)
      ok "created ~/.gemini/settings.json"
      status="created"
      ;;
    STATUS:merged)
      ok "merged into existing ~/.gemini/settings.json"
      status="merged"
      ;;
    BACKUP:*)
      ok "backed up to ${line#BACKUP:}"
      ;;
    ADDED:*)
      ok "added ${line#ADDED:}"
      ;;
    KEPT:*)
      ok "${line#KEPT:}"
      ;;
    ERROR:*)
      fail "${line#ERROR:}"
      exit 1
      ;;
  esac
done <<< "$MERGE_RESULT"

ok "npx    = ${NPX_PATH}"
ok "bunx   = ${BUNX_PATH}"
ok "uvx    = ${UVX_PATH}"
ok "docker = ${DOCKER_PATH}"

# ─── Validate final settings.json ────────────────────────────────────────────
VALID=$(python3 - "$SETTINGS" <<'PYEOF'
import json, sys
path = sys.argv[1]
with open(path) as f:
    d = json.load(f)

errors = []
if not d.get("subagents"):
    errors.append("subagents not set")
if not d.get("experimental", {}).get("enableAgents"):
    errors.append("experimental.enableAgents not set")

required = ["lsp", "hashline", "context7", "sequential-thinking", "playwright", "docker"]
servers = d.get("mcpServers", {})
for s in required:
    if s not in servers:
        errors.append(f"MCP server '{s}' missing")
    else:
        cmd = servers[s].get("command", "")
        if not cmd or cmd.startswith("__"):
            errors.append(f"MCP server '{s}' has unresolved command path: {cmd}")

if errors:
    for e in errors:
        print(f"FAIL:{e}")
    sys.exit(1)
else:
    print("OK")
PYEOF
)

if [ $? -ne 0 ]; then
  while IFS= read -r line; do
    case "$line" in
      FAIL:*) fail "${line#FAIL:}" ;;
    esac
  done <<< "$VALID"
  fail "settings.json validation failed — see errors above"
  exit 1
else
  ok "settings.json validated"
fi

# ─── Pre-cache MCP servers ───────────────────────────────────────────────────
step "[5/8] Pre-caching MCP servers"

echo -n "  serena@${SERENA_COMMIT:0:8}... "
uvx --from "git+https://github.com/oraios/serena@${SERENA_COMMIT}" serena --help &>/dev/null && ok "cached" || warn "download may happen on first gemini launch"

echo -n "  mcp-hashline-edit-server@${HASHLINE_VERSION}... "
bunx mcp-hashline-edit-server@${HASHLINE_VERSION} --version &>/dev/null 2>&1 && ok "cached" || ok "will cache on first use"

echo -n "  @modelcontextprotocol/server-sequential-thinking@${SEQTHINK_VERSION}... "
npx -y @modelcontextprotocol/server-sequential-thinking@${SEQTHINK_VERSION} --help &>/dev/null 2>&1 && ok "cached" || ok "will cache on first use"

echo -n "  @upstash/context7-mcp@${CONTEXT7_VERSION}... "
npx -y @upstash/context7-mcp@${CONTEXT7_VERSION} --help &>/dev/null 2>&1 && ok "cached" || ok "will cache on first use"

echo -n "  @playwright/mcp@${PLAYWRIGHT_VERSION}... "
npx -y @playwright/mcp@${PLAYWRIGHT_VERSION} --help &>/dev/null 2>&1 && ok "cached" || ok "will cache on first use"

# ─── Install Playwright browsers ─────────────────────────────────────────────
step "[6/8] Playwright browsers"

# On headless Linux, Playwright needs system dependencies
if [ "$PLATFORM" = "linux" ]; then
  warn "installing Playwright system dependencies (may need sudo)..."
  npx -y playwright@latest install-deps chromium 2>/dev/null || warn "could not auto-install deps — run: sudo npx playwright install-deps chromium"
fi

if npx -y @playwright/mcp@${PLAYWRIGHT_VERSION} --help 2>&1 | grep -q "version"; then
  ok "chromium available"
else
  warn "installing chromium..."
  npx playwright install chromium
fi

# ─── Copy agents ──────────────────────────────────────────────────────────────
step "[7/8] Installing agents"

mkdir -p "$HOME/.gemini/agents"

for agent in investigator planner reviewer; do
  if [ -f "${SCRIPT_DIR}/agents/${agent}.md" ]; then
    cp "${SCRIPT_DIR}/agents/${agent}.md" "$HOME/.gemini/agents/${agent}.md"
    ok "${agent}"
  else
    fail "${agent}.md not found in extension"
  fi
done

# ─── Final smoke test ────────────────────────────────────────────────────────
step "[8/8] Smoke test"

echo "  launching gemini CLI (this takes ~15s)..."
TOOLS=$(gemini --allowed-mcp-server-names hashline,context7,sequential-thinking,playwright,docker -p "list every tool name, one per line, just the function name" -o text 2>/dev/null) || true

smoke_ok=true
for agent in investigator planner reviewer; do
  if echo "$TOOLS" | grep -qw "$agent"; then
    ok "agent loaded: $agent"
  else
    fail "agent NOT loaded: $agent"
    smoke_ok=false
  fi
done

for tool in hashline__read_file resolve-library-id sequentialthinking browser_navigate mcp-exec; do
  if echo "$TOOLS" | grep -qw "$tool"; then
    ok "MCP tool: $tool"
  else
    fail "MCP tool missing: $tool"
    smoke_ok=false
  fi
done

# ─── Done ─────────────────────────────────────────────────────────────────────
echo ""
if [ "$smoke_ok" = true ]; then
  echo -e "${GREEN}${BOLD}Setup complete!${NC}"
else
  echo -e "${YELLOW}${BOLD}Setup complete with warnings.${NC} Check the errors above."
fi

# Remind Linux users about the Docker MCP env var
if [ "$PLATFORM" = "linux" ]; then
  echo ""
  echo -e "  ${YELLOW}Note:${NC} On Linux without Docker Desktop, add this to your shell profile:"
  echo "    export DOCKER_MCP_IN_CONTAINER=1"
fi

echo ""
echo "  Run 'gemini' in any project and try:"
echo ""
echo "    @investigator trace why /api/login returns 401"
echo "    @planner plan a fix based on the investigation"
echo "    @reviewer review the changes against the plan"
echo ""
