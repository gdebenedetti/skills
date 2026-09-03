#!/bin/zsh

set -euo pipefail

SCRIPT_DIR="${0:A:h}"
TARGET_SCRIPT="${SCRIPT_DIR}/ensure-gh-auth.sh"

assert_contains() {
  local haystack="$1"
  local needle="$2"

  if [[ "$haystack" != *"$needle"* ]]; then
    printf 'expected output to contain: %s\n' "$needle" >&2
    printf 'actual output:\n%s\n' "$haystack" >&2
    return 1
  fi
}

run_case() {
  local name="$1"
  local mode="$2"
  local expected_status="$3"
  local expected_text="$4"
  local session_token="${5:-}"
  local env_file_mode="${6:-absent}"
  local auth_profile="${7:-}"

  local tmpdir fakebin fakegh output exit_code
  tmpdir="$(mktemp -d)"
  fakebin="${tmpdir}/bin"
  fakegh="${fakebin}/gh"

  mkdir -p "${fakebin}" "${tmpdir}/home/.config/gh"

  cat > "${fakegh}" <<'EOF'
#!/bin/sh
case "${MOCK_GH_MODE}" in
  valid)
    printf '%s\n' "${MOCK_GH_LOGIN:-mock-user}"
    exit 0
    ;;
  invalid)
    printf 'gh: Bad credentials\n' >&2
    exit 1
    ;;
  network)
    printf 'error connecting to api.github.com\n' >&2
    exit 1
    ;;
  unexpected)
    printf 'gh should not have been called\n' >&2
    exit 99
    ;;
  *)
    printf 'unexpected mock mode: %s\n' "${MOCK_GH_MODE}" >&2
    exit 98
    ;;
esac
EOF
  chmod 755 "${fakegh}"

  case "${env_file_mode}" in
    present)
      cat > "${tmpdir}/home/.config/gh/codex-token.env" <<'EOF'
export GH_TOKEN_FINEGRAINED='dummy-finegrained-token'
export GH_TOKEN_CLASSIC='dummy-classic-token'
export GH_TOKEN='dummy-token'
export GITHUB_TOKEN="$GH_TOKEN"
EOF
      ;;
    absent)
      ;;
    *)
      printf 'unknown env_file_mode: %s\n' "${env_file_mode}" >&2
      return 1
      ;;
  esac

  set +e
  output="$(
    HOME="${tmpdir}/home" \
    PATH="${fakebin}:${PATH}" \
    MOCK_GH_MODE="${mode}" \
    MOCK_GH_LOGIN="mock-user" \
    GH_TOKEN="${session_token}" \
    GITHUB_TOKEN="" \
    GH_TOKEN_CLASSIC="" \
    GH_TOKEN_FINEGRAINED="" \
    GH_AUTH_PROFILE="${auth_profile}" \
    "${TARGET_SCRIPT}" 2>&1
  )"
  exit_code=$?
  set -e

  if [[ ${exit_code} -ne ${expected_status} ]]; then
    printf 'case %s failed: expected exit %s, got %s\n' "${name}" "${expected_status}" "${exit_code}" >&2
    printf 'output:\n%s\n' "${output}" >&2
    rm -rf "${tmpdir}"
    return 1
  fi

  assert_contains "${output}" "${expected_text}"
  rm -rf "${tmpdir}"
  printf 'ok - %s\n' "${name}"
}

run_case "valid session token" "valid" 0 "ok: mock-user" "session-token" "absent"
run_case "missing token" "unexpected" 11 "missing_token:" "" "absent"
run_case "invalid rehydrated token" "invalid" 10 "token_invalid:" "" "present"
run_case "network unavailable" "network" 20 "network_unavailable:" "session-token" "absent"
run_case "network unavailable after rehydrate" "network" 20 "rehydrated GH_TOKEN" "" "present"
run_case "rehydrated auth" "valid" 0 "rehydrated from" "" "present"
run_case "classic profile from env file" "valid" 0 "rehydrated from" "" "present" "classic"
run_case "finegrained profile from env file" "valid" 0 "rehydrated from" "" "present" "finegrained"
run_case "missing requested profile token" "unexpected" 12 "missing_profile_token:" "" "absent" "classic"
run_case "unknown requested profile" "unexpected" 12 "unknown_profile:" "" "absent" "unknown"
