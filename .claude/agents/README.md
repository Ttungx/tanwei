# Tanwei Claude Code Agents

This directory stores the project-level Claude Code subagents for the Tanwei repository.

## Design Rules

Each subagent file should follow the Tanwei project format:

1. YAML frontmatter with:
   - `name`
   - trigger-rich `description`
   - optional `model`
   - optional `color`
   - optional `memory`
   - optional `tools`
2. A repository-specific system prompt body
3. A narrow, explicit scope
4. Clear handoff expectations
5. Role-specific quality gates and output contract

## Writing Standard

- `description` should be concrete enough for routing and should usually include 1-2 `<example>` blocks.
- Prefer repo language over generic internet templates.
- State what the agent owns and what it does not own.
- Name required docs and files to read before acting.
- Define output structure when the role benefits from predictable handoffs.
- If the role may use persistent memory, treat repo files as the source of truth and memory as fallback context only.

## Roster

- `lead-agent`
- `evaluator-agent`
- `brainstorm-architect`
- `agent-loop-engineer`
- `detection-ml-engineer`
- `svm-filter-engineer`
- `llm-service-engineer`
- `traffic-security-analyst`
- `data-scientist`
- `frontend-developer`
- `docker-expert`
- `doc-gardener`
- `example-demo-agent`

## Workflow

Default path:

`lead-agent -> specialist agent -> evaluator-agent -> doc-gardener`

Use `brainstorm-architect` before implementation when the problem or solution space is still unclear.
