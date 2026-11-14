# Environment and transport verification

Use this checklist when an MCP server depends on local services, containers, or a database. It complements protocol and SDK tests; it does not replace them.

## Preflight a repository and Compose environment

1. Read repository instructions, the README, Compose files, environment templates, and service-specific configuration before creating or starting resources.
2. Inspect existing Compose projects and containers (for example, `docker compose ls --all`, `docker ps`, then `docker inspect` the relevant containers). Record project names, Compose labels, networks, published ports, mounts, named volumes, health, and service dependencies. Compose project names scope resource names, so the same Compose file can create a second, isolated database or service stack.
3. Identify which project and services the task owns. Use explicit project/service scope for Compose operations. Avoid broad `up`, `down`, or volume removal when another local stack or application may use those resources.
4. Before bringing up a test stack, check whether it would create a duplicate Postgres, Airflow, or other stateful service beside an active local instance. Use `--no-deps` only when dependencies are already available and verified.
5. After starting or changing services, check health and logs for the scoped services. Prefer a targeted smoke check (for example, `curl` plus `jq` against the known endpoint) with a clear health preflight and actionable failure output.

## Confirm the actual data path

1. Inspect the running application's effective host, port, database name, schema/search path, and connection configuration from inside its runtime environment. Do not infer the target from a Compose file or a familiar hostname alone.
2. Inspect the database container's actual mounts and volumes. The hostname `postgres` only resolves within a network and does not prove two services use the same database or persistent volume.
3. Compare the connected database identity, schemas, and representative row counts with the expected source. Preserve divergent copies until the source of truth is explicit.
4. When stopping a duplicate or obsolete stack, preserve its volumes until ownership and data disposition are confirmed. Do not remove state as part of routine cleanup.

## Separate test layers

- **Unit/in-process tests** exercise handlers and business logic without requiring a listening HTTP service.
- **HTTP integration tests** are opt-in and target a running server through an HTTP client. Keep their fixtures/configuration scoped (for example, a local `conftest.py` and an explicit pytest marker), require an explicit base URL, and perform a health preflight before sending protocol traffic.
- **Protocol tests** verify JSON-RPC envelopes, HTTP status and headers, content types, session/version behavior, and error mapping. They do not establish that domain data is correct or that application-specific coverage is adequate; test those separately against the intended data source.
- **Smoke checks** should exercise a small representative request over the actual transport, with bounded output and a clear failure message.

For Streamable HTTP, maintain separate cases for the exact protocol revisions and SDK versions the server supports. A legacy session-based test suite and a modern stateless suite may have different handshakes, headers, and lifecycle behavior. In MCP `2025-11-25` and `2026-07-28`, an accepted client notification POST returns `202 Accepted` with no body; tests and clients must not parse that response as JSON. Keep normative specification expectations distinct from SDK-specific behavior and explicitly marked local exceptions or expected failures. Recheck the selected revision's transport page when upgrading the SDK or protocol version.
