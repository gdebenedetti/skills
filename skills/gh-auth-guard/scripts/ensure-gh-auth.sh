#!/bin/zsh

set -euo pipefail

HOST="github.com"
ENV_FILE="${HOME}/.config/gh/codex-token.env"
TOKEN_SOURCE="session"
TOKEN_PROFILE="${GH_AUTH_PROFILE:-default}"

normalize_env() {
  if [[ -n "${GH_TOKEN:-}" && -z "${GITHUB_TOKEN:-}" ]]; then
    export GITHUB_TOKEN="$GH_TOKEN"
  elif [[ -n "${GITHUB_TOKEN:-}" && -z "${GH_TOKEN:-}" ]]; then
    export GH_TOKEN="$GITHUB_TOKEN"
  fi
}

select_profile_token() {
  case "$TOKEN_PROFILE" in
    default|current)
      normalize_env
      ;;
    classic)
      if [[ -z "${GH_TOKEN_CLASSIC:-}" ]]; then
        return 1
      fi
      export GH_TOKEN="$GH_TOKEN_CLASSIC"
      export GITHUB_TOKEN="$GH_TOKEN"
      ;;
    finegrained|fg)
      if [[ -z "${GH_TOKEN_FINEGRAINED:-}" ]]; then
        return 1
      fi
      export GH_TOKEN="$GH_TOKEN_FINEGRAINED"
      export GITHUB_TOKEN="$GH_TOKEN"
      ;;
    *)
      printf 'unknown_profile: GH_AUTH_PROFILE must be one of default, current, classic, finegrained, fg\n' >&2
      return 2
      ;;
  esac
}

load_env_file() {
  if [[ ! -r "$ENV_FILE" ]]; then
    return 1
  fi

  # shellcheck disable=SC1090
  . "$ENV_FILE"
  TOKEN_SOURCE="rehydrated"
  select_profile_token
  return 0
}

ensure_token_loaded() {
  if ! select_profile_token; then
    if [[ "$TOKEN_PROFILE" != "default" && "$TOKEN_PROFILE" != "current" ]]; then
      if load_env_file; then
        return 0
      fi
    fi
    return 2
  fi

  if [[ -n "${GH_TOKEN:-}" || -n "${GITHUB_TOKEN:-}" ]]; then
    TOKEN_SOURCE="session"
    return 0
  fi

  if load_env_file; then
    return 0
  fi

  return 1
}

classify_gh_error() {
  local output="$1"

  if [[ "$output" == *"error connecting to api.github.com"* ||
        "$output" == *"Could not resolve host"* ||
        "$output" == *"dial tcp"* ||
        "$output" == *"Temporary failure in name resolution"* ||
        "$output" == *"no such host"* ]]; then
    printf 'network'
    return
  fi

  if [[ "$output" == *"Bad credentials"* ||
        "$output" == *"HTTP 401"* ||
        "$output" == *"invalid token"* ||
        "$output" == *"authentication failed"* ]]; then
    printf 'invalid'
    return
  fi

  printf 'unknown'
}

verify_auth() {
  local output exit_code classification

  set +e
  output="$(gh api --hostname "$HOST" user --jq .login 2>&1)"
  exit_code=$?
  set -e

  if [[ $exit_code -eq 0 ]]; then
    if [[ "$TOKEN_SOURCE" == "rehydrated" ]]; then
      printf 'ok: %s (rehydrated from %s)\n' "$output" "$ENV_FILE"
    else
      printf 'ok: %s\n' "$output"
    fi
    return 0
  fi

  classification="$(classify_gh_error "$output")"

  case "$classification" in
    network)
      if [[ "$TOKEN_SOURCE" == "rehydrated" ]]; then
        printf 'network_unavailable: rehydrated GH_TOKEN from %s, but this session cannot reach GitHub; retry outside the sandbox or with network access\n' "$ENV_FILE" >&2
      else
        printf 'network_unavailable: this session cannot reach GitHub; retry outside the sandbox or with network access\n' >&2
      fi
      return 20
      ;;
    invalid)
      if [[ "$TOKEN_SOURCE" == "rehydrated" ]]; then
        printf 'token_invalid: GitHub rejected the token from %s; run gh auth login and refresh that file\n' "$ENV_FILE" >&2
      else
        printf 'token_invalid: GitHub rejected the current session token; run gh auth login and refresh %s if needed\n' "$ENV_FILE" >&2
      fi
      return 10
      ;;
    *)
      printf 'auth_check_failed: gh api user failed unexpectedly; inspect stderr and retry with network access\n' >&2
      return 30
      ;;
  esac
}

set +e
ensure_token_loaded
ensure_status=$?
set -e

case "$ensure_status" in
  0)
    ;;
  2)
    printf 'missing_profile_token: GH_AUTH_PROFILE=%s could not be resolved from the session or %s\n' "$TOKEN_PROFILE" "$ENV_FILE" >&2
    exit 12
    ;;
  *)
    printf 'missing_token: no GH_TOKEN in this session and %s is absent; run gh auth login and persist the token\n' "$ENV_FILE" >&2
    exit 11
    ;;
esac

verify_auth
