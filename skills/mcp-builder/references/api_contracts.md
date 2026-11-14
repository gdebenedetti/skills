# Source and contract guidance

These sources describe different layers. Do not treat an upstream HTTP API contract as an MCP protocol specification.

## Source order

1. **MCP protocol behavior:** the [published MCP specification](https://modelcontextprotocol.io/specification/latest), including the [tool contract](https://modelcontextprotocol.io/specification/latest/server/tools), [transports](https://modelcontextprotocol.io/specification/latest/basic/transports), and [authorization](https://modelcontextprotocol.io/specification/latest/basic/authorization).
2. **SDK APIs:** the official SDK docs and examples for the exact package version and release line. The [TypeScript SDK v2 documentation](https://ts.sdk.modelcontextprotocol.io/v2/) implements MCP `2026-07-28`; its [repository](https://github.com/modelcontextprotocol/typescript-sdk) distinguishes v2 from the maintained v1.x branch. The [official Python SDK](https://github.com/modelcontextprotocol/python-sdk) publishes its current examples and supported APIs. Do not port code between SDK major versions by guesswork.
3. **Upstream service behavior:** the service's official OpenAPI document, official SDK types, or first-party documentation. Prefer machine-readable contracts over generated summaries.
4. **Library implementation detail:** Context7 can retrieve versioned library documentation, but it is an index and retrieval service, not the protocol authority. Resolve the exact library, select the matching version ID when available, and query a specific task. Check important behavior against the upstream docs.

## Keep the standards distinct

- **MCP** describes the JSON-RPC interaction between an MCP client and server: discovery, tools, resources, prompts, transports, and optional authorization.
- **OpenAPI** describes an HTTP service's API contract. It can inform MCP tool names, inputs, outputs, auth requirements, and error mapping. Translating an OpenAPI operation into a tool is an adapter decision; the MCP tool contract still needs to be designed and validated.
- **Context7** serves documentation for a chosen library/version. It does not define MCP or OpenAPI semantics.

## OpenAPI to MCP mapping

When an OpenAPI contract exists:

1. Record the document's OAS version and validate it with a validator compatible with that version. OpenAPI 3.2.1 is the latest published spec as of 2026-10-16; use the [versioned specification](https://spec.openapis.org/oas/v3.2.1.html), not an unpinned editor draft, unless compatibility requires an earlier version.
2. Map only operations relevant to user workflows. Give MCP tools task-oriented contracts rather than mechanically exposing every path.
3. Translate path/query/header/body inputs into explicit MCP input schemas. Preserve constraints, required fields, auth scopes, pagination, and meaningful response/error semantics.
4. Define output schemas that bound and normalize upstream data. Avoid returning secrets or entire unbounded API responses.
5. Verify each mapped tool against the corresponding operation and record intentional differences. Do not assume an OpenAPI security scheme implements MCP authorization; each boundary must validate its own credentials.

## Context7 versioned lookup

Follow [Context7's current client/tool docs](https://context7.com/docs/resources/all-clients):

1. Call `resolve-library-id` with the official library name and a task-specific query, unless the user already supplied a valid `/owner/project` ID.
2. Inspect candidates and choose the correct library. If a version-specific ID exists, use it for the dependency version being implemented.
3. Call `query-docs` with that ID and a concrete question; constrain the requested language when useful.
4. Treat retrieved snippets as documentation excerpts. Confirm behavioral or security requirements in the owning project's official docs or source.

Do not use an unversioned library match when version drift could change APIs. Record the package version and library ID used when reproducibility matters.
