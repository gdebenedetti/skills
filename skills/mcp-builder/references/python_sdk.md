# Python SDK Summary

Curated summary of the official MCP Python SDK guidance for local use inside this skill.

## When to Choose Python

Choose Python when:
- the target service already has strong Python SDK support
- the user wants FastMCP ergonomics
- existing automation or data tooling is already Python-based

## Recommended Stack

- Python 3.10+
- FastMCP-style server patterns
- Pydantic models or type hints for input and output structure
- `stdio` for local servers
- HTTP transport only when the deployment model requires it

## Core Patterns

Design the server around:
- a single server entrypoint
- shared service clients
- typed request/response models
- narrow tool handlers

Keep business logic separate from transport wiring.

## Tool Design

For each tool:
- define explicit parameter models
- validate constraints at the boundary
- keep return shapes predictable
- separate read-only and mutating actions
- expose pagination and filters instead of dumping large payloads

## Project Shape

Recommended layout:

```text
service_mcp_server/
├── pyproject.toml
├── README.md
├── server.py
├── tools/
├── services/
└── models/
```

Keep:
- server construction in the entrypoint
- auth and HTTP clients in `services/`
- models and schemas in `models/`

## Runtime Guidance

- Use typed models for stable interfaces
- Return machine-friendly structures when possible
- Handle auth, rate limits, and missing resources explicitly
- Keep tool descriptions short and concrete

## Decision Rule

If Python is chosen:
- prefer simple FastMCP patterns first
- keep handlers thin
- make data contracts explicit before expanding tool count
