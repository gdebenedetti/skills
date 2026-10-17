# Python SDK notes

Use the [official MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk) repository, documentation, and examples as the API authority. Pin the SDK release and check its supported MCP revisions, Python version, transport options, and schema/output behavior before implementation; this upstream SDK changes frequently.

FastMCP provides a high-level Python server interface. Use the API documented for the pinned release rather than assuming decorator, annotation, or return-value details from an older version. Define explicit parameter constraints and stable output shapes, and check whether the SDK can emit an MCP `outputSchema` and matching structured content for that release.

Choose the language based on the service client and project constraints. Choose transport independently: `stdio` for a local subprocess or Streamable HTTP for a remote server, subject to client support and the current MCP specification.
