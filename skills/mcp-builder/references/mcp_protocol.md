# MCP protocol notes

Use the [published specification](https://modelcontextprotocol.io/specification/latest) as the authority. Record the revision used for implementation and check it again when upgrading an SDK. This summary reflects the specification published as `2026-07-28`; clients and servers may support other revisions.

## Protocol model

MCP is a JSON-RPC protocol between a host's client and a server. In revision `2026-07-28`, there is no `initialize`/`initialized` handshake: every request carries its protocol version and client capabilities in `_meta`. Servers must implement `server/discover` so clients can request advertised server capabilities up front, but clients can proceed without calling it. Earlier revisions, including `2025-11-25`, use the initialization handshake; support it only when required for compatibility. Servers can expose tools, resources, and prompts; these are different interfaces, not interchangeable labels for an API endpoint.

## Transport

- **stdio**: local client launches a server process. Keep stdout for protocol messages; send logs to stderr.
- **Streamable HTTP**: client and independently running server communicate over HTTP. For `2026-07-28`, requests are stateless at the protocol layer and carry version metadata per request; earlier revisions may use connection-scoped sessions. Follow the selected revision's request, response, and version-header rules rather than copying old HTTP+SSE examples.
- **HTTP+SSE**: legacy transport from the `2024-11-05` specification. Do not select it for a new implementation unless a target client requires it.

Transport choice is a deployment decision. It does not select the server's authorization model or make a server stateless by itself.

## Tool contracts

A tool has a stable name, a specific description, an `inputSchema`, and optionally an `outputSchema`. The current specification uses JSON Schema 2020-12 by default. Return structured data matching the declared output schema in `structuredContent` when supported, and concise text content when useful to the caller. Bound large results and expose filters or pagination for collection tools.

Use annotations such as `readOnlyHint`, `destructiveHint`, `idempotentHint`, and `openWorldHint` only when they truthfully describe behavior. They are hints and must never replace authorization, validation, or confirmation controls.

Protocol-level failures and tool execution failures are different. Return a tool result with `isError` for an execution failure; use JSON-RPC errors for protocol errors. Give callers a useful recovery step without leaking secrets, stack traces, or sensitive upstream details.

## Authorization and security

Authorization is optional at the protocol level; add it when the service or deployment requires protected access. For protected remote servers, follow the MCP authorization specification and its OAuth 2.1 profile, including Protected Resource Metadata, authorization-server discovery, audience-bound token validation, HTTPS, and PKCE where applicable. Do not invent a generic bearer-token flow in place of that profile.

The server must authorize every operation against the authenticated principal and requested resource. Never forward the MCP client's access token to an upstream API; obtain and use a separate upstream credential. Keep secrets out of source, tool descriptions, and returned errors.

For Streamable HTTP, validate `Origin` on incoming requests to prevent DNS rebinding. If serving a local process, bind to loopback unless a deliberate network deployment requires otherwise. Validate inputs, constrain resource access, and avoid unsafe URL fetching, path traversal, shell interpolation, and unbounded requests.

## Compatibility check

Before implementation or upgrade, check the specification revision, client support, and the selected SDK's supported protocol versions. For `2026-07-28`, test per-request metadata and the server's `server/discover` response; for earlier revisions, test the `initialize` handshake and session behavior they require. Use the SDK examples for that release line. Do not assume a new schema field or transport behavior is supported by every client.
