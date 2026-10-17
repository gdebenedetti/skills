# TypeScript MCP server patterns

Use the [official TypeScript SDK v2 documentation](https://ts.sdk.modelcontextprotocol.io/v2/) and [tool examples](https://github.com/modelcontextprotocol/typescript-sdk/tree/main/examples/tools) for compilable code. Pin a compatible SDK release and follow its exact import paths and transport APIs; v1 and v2 are separate APIs.

## Define the wire contract first

This version-agnostic tool descriptor illustrates the current MCP contract. The SDK should generate or validate an equivalent descriptor and handler:

```json
{
  "name": "catalog_search_items",
  "title": "Search catalog items",
  "description": "Search catalog items by a required query. Returns at most 50 matches.",
  "inputSchema": {
    "type": "object",
    "properties": {
      "query": { "type": "string", "minLength": 1, "maxLength": 200 },
      "limit": { "type": "integer", "minimum": 1, "maximum": 50 }
    },
    "required": ["query"],
    "additionalProperties": false
  },
  "outputSchema": {
    "type": "object",
    "properties": {
      "items": { "type": "array", "items": { "type": "object" } },
      "hasMore": { "type": "boolean" }
    },
    "required": ["items", "hasMore"]
  },
  "annotations": { "readOnlyHint": true }
}
```

Return a `structuredContent` object matching `outputSchema`. Keep text content concise when it helps a client display the result. Set annotations only when they accurately describe actual behavior.

## Build and check

- Use the SDK's schema support for runtime input validation and inferred types.
- Keep API calls in a service/client module and tool handlers focused on authorization, validation, and mapping results.
- Route stdio logs to stderr. Configure Streamable HTTP according to the current transport and authorization specifications.
- Test through an MCP client or [Inspector](https://github.com/modelcontextprotocol/inspector): list the tool, inspect its schema, call valid and invalid cases, and assert structured output.
- Consult [TypeScript SDK notes](./typescript_sdk.md) and [MCP protocol notes](./mcp_protocol.md) for version and wire requirements.
