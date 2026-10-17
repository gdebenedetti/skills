# Python MCP server patterns

Use the [official MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk) documentation and examples for compilable code. Pin a release and follow its documented FastMCP, validation, return-value, and transport APIs; do not rely on snippets from an unpinned older revision.

## Define the wire contract first

Use a clear MCP-level contract regardless of Python framework. The [TypeScript implementation notes](./node_mcp_server.md#define-the-wire-contract-first) show a version-agnostic `tools/list` descriptor with bounded input, an output schema, and annotations. In Python, model these constraints using the official SDK's supported type/schema mechanism and return data matching the output contract.

## Implementation checks

- Keep service clients separate from tool handlers. Validate arguments before I/O and authorize each operation against the current principal.
- Handle timeouts, rate limits, upstream errors, and bounded pagination explicitly. Do not return large or sensitive upstream payloads by default.
- Send stdio logs to stderr. For Streamable HTTP, follow the current MCP transport and authorization specifications.
- Test discovery and invocation through an MCP client or [Inspector](https://github.com/modelcontextprotocol/inspector), including invalid input, output shape, auth failures, and upstream errors.
- Confirm version-specific APIs in [Python SDK notes](./python_sdk.md) and wire requirements in [MCP protocol notes](./mcp_protocol.md).
