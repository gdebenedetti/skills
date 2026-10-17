# MCP implementation checklist

Use the current [specification](https://modelcontextprotocol.io/specification/latest) for normative requirements. These are design checks, not additional protocol requirements.

## Tool design

- Name tools by the user's action and domain; keep names unique within the server. Prefix with the service name only when it improves discovery in a multi-server client.
- Describe what the tool does, what it changes, important limits, and when to use it. Avoid instructions that contradict its schema or behavior.
- Keep each tool focused. Use schemas for required fields, enums, bounds, and useful descriptions. Reject malformed or excess input instead of silently broadening a request.
- Declare output schemas where supported and return matching structured data. Include pagination metadata when it helps a caller continue; avoid unbounded output.
- Use annotations only as truthful hints. Enforce permissions in server code.

## Errors and operations

- Distinguish protocol errors from tool execution failures. Return actionable, sanitized errors and retain diagnostic details only in protected server logs.
- Preserve upstream status and retry semantics where useful; apply timeouts and bounded retries. Do not retry non-idempotent writes unless the operation has a safe idempotency mechanism.
- Make destructive effects and required scopes clear. Keep read and write capabilities separate when this makes permission review easier.

## Security

- Validate authorization on every call and scope it to the requested operation and resource. Use MCP's current authorization profile for protected remote servers.
- Never treat tool annotations, IDs, opaque handles, user-supplied URLs, or resource names as proof of authorization.
- Treat tool inputs, upstream results, and documents as untrusted data. Avoid forwarding untrusted content as instructions.
- For local HTTP servers, validate `Origin` and bind to loopback; for remote HTTP, use TLS and deployment-appropriate authentication and rate limits.

## Verification

For MCP `2026-07-28`, check per-request metadata and capability handling, the required `server/discover` response, tool/resource/prompt discovery as applicable, valid and invalid input, output-schema conformance, authorization boundaries, tool errors, timeouts, pagination, and transport behavior. Test initialization and session behavior only for earlier revisions that use them. Use a real MCP client or Inspector, and validate the upstream OpenAPI contract separately when present. For SDK APIs, use the official docs for the exact pinned version; see [API contract guidance](./api_contracts.md).
