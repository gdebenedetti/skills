# TypeScript SDK notes

Use the [official TypeScript SDK repository](https://github.com/modelcontextprotocol/typescript-sdk) and its [v2 docs](https://ts.sdk.modelcontextprotocol.io/v2/) for current APIs. The repository's `main` branch is v2 for the MCP `2026-07-28` revision; the v1.x branch is a separate maintenance line. Select and pin the release line that matches the target client's compatibility needs.

For tool registration, start with the [official tools example](https://github.com/modelcontextprotocol/typescript-sdk/tree/main/examples/tools). It uses `McpServer.registerTool`, schema inference from Standard Schema-compatible inputs, and structured output checked by a client. Verify exact imports and APIs against the installed SDK version before coding; do not copy old `@modelcontextprotocol/sdk` examples into v2 projects.

Choose `stdio` for local subprocess integrations and Streamable HTTP for a remote service when supported by target clients. Select schemas, transports, and authorization from the current spec and deployment requirements, not from this language preference.
