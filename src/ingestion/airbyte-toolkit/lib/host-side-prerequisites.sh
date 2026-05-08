#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# Airbyte Toolkit — Host-side prerequisites
#
# Two host-side prerequisites that init.sh / register.sh / connect.sh need
# whenever they're invoked from outside the cluster:
#
#   1. CLI tooling: `yq` (Mike Farah's Go binary), `jq`, and Python `yaml`
#      (PyYAML). The toolkit shells out to yq/jq for descriptor parsing
#      and uses inline `python3 - <<PY ... import yaml ...` blocks for
#      state-file IO. Missing tools surface as `command not found` /
#      `ModuleNotFoundError` deep inside register.sh and have no
#      actionable hint.
#
#   2. Port-forward to airbyte-server. When AIRBYTE_API is unset and we're
#      not running in-cluster, env.sh defaults to http://localhost:8001 and
#      will fail workspace resolution unless `kubectl port-forward
#      svc/airbyte-airbyte-server-svc 8001:8001` is already open. Asking
#      the operator to remember this is a footgun; the toolkit can open
#      the forward itself and tear it down on exit.
#
# Both functions are no-ops when running in-cluster (detected via the
# ServiceAccount token file). Both are idempotent — re-sourcing or re-
# calling them when state is already correct is safe (init.sh opens the
# port-forward, sub-scripts re-assert it and find it already up).
#
# ── Tooling install policy by platform ─────────────────────────────────────
#
# The toolkit's `command -v` check ALWAYS runs first — if a tool is on
# PATH (system package manager, manual install, anything), we use it
# unchanged. Auto-install is only the fallback for truly-missing tools.
#
#   • macOS                 — auto: brew where available, else download
#   • WSL (Linux on Windows) — auto: download static binary
#   • Windows native (Git Bash / MSYS) — auto: download static binary
#   • Linux native (no WSL) — fail with platform-agnostic install hint;
#                             user installs via their package manager
#                             (apt, dnf, pacman, ...) and re-runs.
#
# The Linux-native fail is deliberate — Ubuntu's apt `yq` is the wrong
# project (kislyuk's Python wrapper, incompatible syntax), and we don't
# want to download binaries on Linux that bypass distro updates. The
# operator is expected to use snap, dnf-COPR, or a direct binary install
# they manage themselves.
# ---------------------------------------------------------------------------

# Standard install dir for downloaded binaries — out of the way of system
# package managers, doesn't require root, and survives across runs.
INSIGHT_BIN_DIR="${INSIGHT_BIN_DIR:-$HOME/.insight/bin}"

_in_cluster() {
  [[ -f /var/run/secrets/kubernetes.io/serviceaccount/token ]]
}

# ---------------------------------------------------------------------------
# Platform detection. The four predicates are mutually exclusive — at most
# one returns 0 on any given host. _detect_platform returns "<os>/<arch>"
# for the OS/arch labels yq and jq release artifacts use; only consulted
# inside the download branch.
# ---------------------------------------------------------------------------
_is_macos()          { [[ "$(uname -s)" == "Darwin" ]]; }
_is_windows_native() { case "$(uname -s)" in MINGW*|MSYS*|CYGWIN*) return 0 ;; *) return 1 ;; esac; }

_is_wsl() {
  # WSL2 sets WSL_DISTRO_NAME unconditionally. WSL1+2 expose Microsoft in
  # /proc/version (and /proc/sys/kernel/osrelease on most builds). Either
  # signal is enough; we OR them so a stripped-down image still detects.
  [[ -n "${WSL_DISTRO_NAME:-}" ]] && return 0
  [[ -r /proc/version ]] && grep -qiE 'microsoft|wsl' /proc/version && return 0
  return 1
}

_is_linux_native() {
  [[ "$(uname -s)" == "Linux" ]] && ! _is_wsl
}

_detect_platform() {
  local os arch
  case "$(uname -s)" in
    Linux*)   os=linux ;;
    Darwin*)  os=darwin ;;
    MINGW*|MSYS*|CYGWIN*) os=windows ;;
    *) echo "ERROR: unsupported OS: $(uname -s)" >&2; return 1 ;;
  esac
  case "$(uname -m)" in
    x86_64|amd64) arch=amd64 ;;
    aarch64|arm64) arch=arm64 ;;
    *) echo "ERROR: unsupported arch: $(uname -m)" >&2; return 1 ;;
  esac
  echo "$os/$arch"
}

_download() {
  local url="$1" dest="$2"
  if command -v curl >/dev/null 2>&1; then
    curl -sSLf -o "$dest" "$url"
  elif command -v wget >/dev/null 2>&1; then
    wget -qO "$dest" "$url"
  else
    echo "ERROR: neither curl nor wget available — install one and retry" >&2
    return 1
  fi
}

# ---------------------------------------------------------------------------
# Per-tool installers. Each is platform-agnostic about the SOURCE — they
# always download from upstream releases. The platform-specific routing
# (brew on macOS, fail on Linux native) lives in ensure_tooling below.
# ---------------------------------------------------------------------------
_install_yq_download() {
  local platform os arch ext url
  platform=$(_detect_platform) || return 1
  os="${platform%/*}"; arch="${platform#*/}"
  ext=""
  [[ "$os" == "windows" ]] && ext=".exe"
  url="https://github.com/mikefarah/yq/releases/latest/download/yq_${os}_${arch}${ext}"
  echo "  Installing yq from $url" >&2
  mkdir -p "$INSIGHT_BIN_DIR"
  _download "$url" "$INSIGHT_BIN_DIR/yq${ext}" || return 1
  chmod +x "$INSIGHT_BIN_DIR/yq${ext}"
}

_install_jq_download() {
  local platform os arch ext name url
  platform=$(_detect_platform) || return 1
  os="${platform%/*}"; arch="${platform#*/}"
  ext=""
  # jq release naming: linux→linux-amd64, darwin→macos-amd64,
  # windows→windows-amd64.exe. The OS segment differs from yq's.
  case "$os" in
    linux)   name="jq-linux-${arch}" ;;
    darwin)  name="jq-macos-${arch}" ;;
    windows) name="jq-windows-${arch}.exe"; ext=".exe" ;;
  esac
  url="https://github.com/jqlang/jq/releases/latest/download/${name}"
  echo "  Installing jq from $url" >&2
  mkdir -p "$INSIGHT_BIN_DIR"
  _download "$url" "$INSIGHT_BIN_DIR/jq${ext}" || return 1
  chmod +x "$INSIGHT_BIN_DIR/jq${ext}"
}

_brew_install() {
  local pkg="$1"
  command -v brew >/dev/null 2>&1 || return 1
  echo "  Installing $pkg via brew" >&2
  brew install --quiet "$pkg"
}

_install_pyyaml() {
  echo "  Installing PyYAML via pip" >&2
  # Three-step fallback: --user, then plain, then --break-system-packages.
  # The last covers PEP 668 "externally-managed-environment" interpreters
  # (Debian 12+, Ubuntu 23.04+, Homebrew Python 3.12+) where the first
  # two raise an actionable-but-blocking error.
  python3 -m pip install --user --quiet pyyaml \
    || python3 -m pip install --quiet pyyaml \
    || python3 -m pip install --user --quiet --break-system-packages pyyaml
}

# ---------------------------------------------------------------------------
# ensure_tooling — verifies yq, jq, and PyYAML are usable. Auto-installs
# on macOS / WSL / Windows-native; fails with a platform-specific install
# hint on native Linux. Idempotent — call it as many times as you like.
# ---------------------------------------------------------------------------
ensure_tooling() {
  _in_cluster && return 0

  # If we previously installed binaries here, prepend on every call so
  # subsequent commands in this shell can see them (we may not have
  # been the shell that installed them).
  if [[ -d "$INSIGHT_BIN_DIR" ]]; then
    case ":$PATH:" in
      *":$INSIGHT_BIN_DIR:"*) ;;
      *) export PATH="$INSIGHT_BIN_DIR:$PATH" ;;
    esac
  fi

  # Single-pass missing-tools collection — one detection round, one
  # message to the operator instead of three interleaved install logs.
  local missing=()
  command -v yq                          >/dev/null 2>&1 || missing+=(yq)
  command -v jq                          >/dev/null 2>&1 || missing+=(jq)
  python3 -c "import yaml" >/dev/null 2>&1 || missing+=(pyyaml)

  if [[ ${#missing[@]} -eq 0 ]]; then
    return 0
  fi

  # Branch on platform. Auto-install paths share the same per-tool
  # installer functions; the macOS path additionally tries brew first.
  if _is_linux_native; then
    _print_linux_install_hint "${missing[@]}"
    return 1
  fi

  echo "  Missing host tooling: ${missing[*]}" >&2
  local tool
  for tool in "${missing[@]}"; do
    case "$tool" in
      yq)
        if _is_macos && command -v brew >/dev/null 2>&1; then
          _brew_install yq || _install_yq_download || return 1
        else
          _install_yq_download || return 1
        fi
        export PATH="$INSIGHT_BIN_DIR:$PATH"
        ;;
      jq)
        if _is_macos && command -v brew >/dev/null 2>&1; then
          _brew_install jq || _install_jq_download || return 1
        else
          _install_jq_download || return 1
        fi
        export PATH="$INSIGHT_BIN_DIR:$PATH"
        ;;
      pyyaml)
        _install_pyyaml || return 1
        ;;
    esac
  done
}

# ---------------------------------------------------------------------------
# Linux-native fail message. Just lists the missing tools and asks the
# operator to install them. We deliberately do NOT enumerate per-distro
# package commands — the surface of "did we name the right package on
# the right distro" is wider than the value, and the operator already
# knows their package manager.
# ---------------------------------------------------------------------------
_print_linux_install_hint() {
  local missing=("$@")
  cat >&2 <<EOF
ERROR: required CLI tooling missing on host: ${missing[*]}

Detected: native Linux. The toolkit does not auto-install here — install
the missing tools via your distribution's package manager and re-run.

EOF
}

# ---------------------------------------------------------------------------
# ensure_airbyte_pf — opens a background `kubectl port-forward` to
# airbyte-server when running from host and 8001 isn't already serving
# the API. Registers an EXIT trap so the forward dies with the script.
#
# Honors:
#   - AIRBYTE_API: if explicitly set to a non-localhost URL, we trust the
#     operator and skip. (Set to http://localhost:8001 deliberately to
#     opt INTO managed PF for that exact endpoint.)
#   - INSIGHT_NAMESPACE: namespace the airbyte-server svc lives in.
# ---------------------------------------------------------------------------
ensure_airbyte_pf() {
  _in_cluster && return 0

  # If the caller pinned AIRBYTE_API to something other than localhost:8001,
  # they've already taken responsibility for reachability. Skip.
  if [[ -n "${AIRBYTE_API:-}" && "${AIRBYTE_API}" != "http://localhost:8001" ]]; then
    return 0
  fi

  local ns="${INSIGHT_NAMESPACE:-insight}"
  local api="http://localhost:8001"

  # Already responsive? Use whatever's on the other end (PF or local airbyte).
  if curl -sf -o /dev/null --max-time 2 "${api}/api/v1/health" 2>/dev/null; then
    return 0
  fi

  echo "  Opening port-forward to svc/airbyte-airbyte-server-svc 8001:8001" >&2
  kubectl -n "$ns" port-forward svc/airbyte-airbyte-server-svc 8001:8001 \
    >/dev/null 2>&1 &
  local pf_pid=$!
  # Trap EXIT (covers normal exit, set -e abort, signal). Use a defensive
  # kill — process may have already died if PF errored out. Chain to any
  # existing EXIT trap so callers' cleanup isn't clobbered (e.g. the
  # sourcing script may install its own trap before or after this call).
  local prev_trap
  prev_trap=$(trap -p EXIT | sed -E "s/^trap -- '(.*)' EXIT$/\1/")
  # shellcheck disable=SC2064
  trap "kill $pf_pid 2>/dev/null || true; ${prev_trap}" EXIT

  # Wait for the forward to become ready. 30s ceiling avoids hangs when
  # the service is missing or the API server is itself unhealthy.
  for _ in $(seq 1 30); do
    if curl -sf -o /dev/null --max-time 2 "${api}/api/v1/health" 2>/dev/null; then
      return 0
    fi
    # If the PF process died, fail loudly instead of looping.
    if ! kill -0 "$pf_pid" 2>/dev/null; then
      echo "ERROR: port-forward to airbyte-server died unexpectedly" >&2
      return 1
    fi
    sleep 1
  done
  echo "ERROR: airbyte-server did not become reachable on $api within 30s" >&2
  return 1
}
