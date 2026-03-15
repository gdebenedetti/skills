# TypeScript SDK Summary

Curated summary of the official MCP TypeScript SDK guidance for local use inside this skill.

## Version Posture

- Prefer the stable TypeScript SDK for production work
- Treat preview or alpha APIs as opt-in
- If the user explicitly wants the newest upstream SDK surface, verify that separately before coding against it

## Recommended Stack

- TypeScript
- Zod for runtime validation
- `streamable-http` for remote servers
- `stdio` for local servers

## Core Patterns

Use the server abstraction that gives you:
- Tool registration
- Resource registration
- Prompt registration
- Clear transport wiring

Design around:
- Small handlers
- Shared API client utilities
- Shared schema modules
- Structured return values

## Tool Design

For each tool:
- Use explicit names with service context
- Validate every field with Zod
- Keep descriptions short and concrete
- Return structured content when the SDK supports it
- Mark read-only vs mutating behavior clearly

## Project Shape

Recommended layout:

```text
service-mcp-server/
├── package.json
├── tsconfig.json
├── src/
│   ├── index.ts
│   ├── tools/
│   ├── services/
│   ├── schemas/
│   └── types.ts
└── dist/
```

Keep:
- transport setup in `index.ts`
- API clients in `services/`
- Zod schemas near tool inputs and outputs
- one coherent domain per tool file or module

## Transport Guidance

Use `stdio` when:
- the server is local
- the user values simplicity over network deployment

Use `streamable-http` when:
- the server is remote
- the server must scale across requests
- you want standard HTTP deployment and observability

## Reliability Notes

- Compile before testing runtime behavior
- Keep error messages actionable
- Paginate list endpoints
- Prefer deterministic JSON payloads over prose-heavy responses
- Avoid hiding important fields inside freeform text

## Decision Rule

If there is no strong constraint from the user:
- choose TypeScript
- choose `streamable-http` for remote servers
- choose `stdio` for local servers
