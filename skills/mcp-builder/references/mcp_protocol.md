# MCP Protocol Summary

Curated summary of the official Model Context Protocol specification for local use inside this skill.

## Core Model

- **Host**: The application that connects models, users, and MCP clients
- **Client**: The protocol peer created by the host to talk to one MCP server
- **Server**: The process or service that exposes tools, resources, and prompts

Think in terms of a narrow protocol boundary:
- The server exposes capabilities
- The client negotiates support
- Requests and notifications flow over JSON-RPC

## Lifecycle

1. Initialize the connection and exchange capabilities
2. Advertise supported features
3. Serve requests for tools, resources, and prompts
4. Emit notifications when state changes

Design implication:
- Keep initialization cheap
- Fail fast on unsupported modes
- Be explicit about optional capabilities

## Server Primitives

### Tools

Use tools for side-effectful or parameterized operations.

Good tool design:
- Clear action-oriented names
- Strict input validation
- Focused outputs
- Actionable errors
- Pagination for list/search endpoints

### Resources

Use resources for read-oriented content that can be referenced or loaded by the client.

Good resource design:
- Stable identifiers
- Predictable schemas
- Clear separation from write operations

### Prompts

Use prompts for reusable task scaffolding or guided interaction patterns.

Good prompt design:
- Narrow purpose
- Explicit inputs
- No hidden assumptions about external state

## Transport Choice

### `stdio`

Prefer for:
- Local developer tools
- Single-user local integrations
- Simple process spawning

Benefits:
- Minimal deployment overhead
- Straightforward local debugging

### `streamable-http`

Prefer for:
- Remote services
- Multi-user access
- Horizontal scaling
- Stateless deployments

Benefits:
- Familiar HTTP infrastructure
- Easier hosting and routing
- Better fit for managed platforms

## Capability and Context Boundaries

Design the server so agents can discover only what they need:
- Keep tool descriptions concise
- Avoid giant response payloads
- Return structured data when possible
- Make filtering and pagination first-class

## Safety Expectations

- Validate inputs strictly
- Surface auth and rate-limit failures clearly
- Avoid ambiguous destructive behavior
- Distinguish read-only from mutating tools
- Preserve least surprise in naming and behavior

## Implementation Checklist

- Pick the transport before writing handlers
- Define the server name and version early
- Group tools by service domain
- Add schemas before writing business logic
- Test discovery, invocation, and failure modes
