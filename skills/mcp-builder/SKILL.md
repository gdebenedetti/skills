---
name: mcp-builder
description: Build or update Model Context Protocol (MCP) servers that expose tools, resources, or prompts over local or remote transports. Use for MCP integrations; use the upstream specification and SDK docs for the selected versions.
license: Complete terms in LICENSE.txt
---

# Build an MCP server

Use this skill when implementing or reviewing an MCP server. Treat MCP, OpenAPI, Open Context Protocol (OCP), and Context7 as separate things; see [source and contract guidance](./references/api_contracts.md).

## Workflow

1. **Establish the contract.** Read the current [MCP specification](https://modelcontextprotocol.io/specification/latest) and identify its published revision. Inspect the service's official OpenAPI document or SDK types. If OCP is relevant, verify its maturity and scope before using it. Use Context7 only to retrieve documentation for the exact framework and version in use.
2. **Design the server.** Choose `stdio` for a local child process and Streamable HTTP for a remote HTTP service, unless client/deployment requirements dictate otherwise. Define a small, task-oriented tool set; use resources and prompts only when they fit their protocol roles. Define each tool's input and output contract, auth scope, side effects, pagination, and error behavior before writing handlers.
3. **Implement.** Use the current official SDK for the selected language and pin compatible dependency versions. Validate input at the boundary, enforce authorization per operation, keep handlers thin, and return bounded, useful results. Prefer structured output with an `outputSchema` where supported. Mark tool annotations accurately; they are descriptive hints, not access controls.
4. **Secure it.** Apply least privilege, protect credentials, validate token audience and scopes, and never pass an MCP client token through to an upstream API. For Streamable HTTP, follow the current transport security requirements, including `Origin` validation and localhost binding for local servers. Treat tool arguments, upstream responses, and retrieved content as untrusted.
5. **Verify the contract and behavior.** Validate the OpenAPI document when one is supplied; check its operations against the exposed tools and document intentional differences. For MCP `2026-07-28`, test per-request metadata and capability handling, the required `server/discover` response, tool listing, valid and invalid calls, structured outputs, authorization, failures, pagination, and each supported transport. Test the `initialize` handshake only when supporting an earlier protocol revision. Use the [MCP Inspector](https://github.com/modelcontextprotocol/inspector) or an equivalent client. Add realistic read-only evaluations when they help show the server supports user workflows; see [evaluation guidance](./references/evaluation.md).

## References

- [MCP protocol summary](./references/mcp_protocol.md): lifecycle, transports, contracts, and security.
- [MCP design and implementation notes](./references/mcp_best_practices.md): compact design checklist.
- [API contracts, OCP, and Context7](./references/api_contracts.md): source authority and version selection.
- [TypeScript SDK notes](./references/typescript_sdk.md) and [Python SDK notes](./references/python_sdk.md): use with the linked upstream documentation; verify version-specific APIs before copying examples.
- [TypeScript implementation notes](./references/node_mcp_server.md) and [Python implementation notes](./references/python_mcp_server.md): examples and patterns.
