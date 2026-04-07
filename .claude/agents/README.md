# Tanwei Claude Code Agents

This directory stores the project-level Claude Code subagents for Tanwei's `console + edge-agent + central-agent` architecture.

## Design Rules

Every agent markdown must follow the **same complete paradigm** as `example-demo-agent.md`:

1. YAML frontmatter:
   - `name`
   - trigger-rich `description` with `<example>` blocks
   - optional `model`
   - optional `color`
   - optional `memory`
   - optional `tools`
2. Role definition body:
   - `Your Responsibilities`
   - `Output Standards`
   - `Behavioral Guidelines`
   - `Quality Assurance`
3. Role summary line after `---`
4. Full `# Persistent Agent Memory` section (same structure across all agents)

## Writing Standard

- `description` must be concrete enough for routing and should include realistic repository scenarios.
- State explicit ownership boundaries (`owns` / `not owned`) in role language.
- Name required docs and code paths to read before editing.
- Define output structure whenever handoff quality matters.
- Keep architecture naming consistent: `console`, `edge-agent`, `central-agent`.

## Agent Roster

| Agent | Primary Ownership | Not Owned |
| --- | --- | --- |
| `lead-agent` | task decomposition, routing, harness governance | domain implementation details |
| `edge-agent-engineer` | `edge-agent/`, edge detection flow, edge intelligence report contract | `central-agent/` internals, `console/` UX |
| `central-agent-engineer` | `central-agent/`, report ingestion/archive, center-side analysis orchestration | edge-side packet analysis internals, `console/` UX |
| `console-developer` | `console/` admin flows and interaction surface | edge/central inference internals |
| `svm-filter-engineer` | `svm-filter-service/` runtime inference path | offline training decisions |
| `llm-service-engineer` | `llm-service/` runtime and output contract | orchestration/business workflow ownership |
| `detection-ml-engineer` | SVM offline training and artifact recommendation | online runtime serving path |
| `traffic-security-analyst` | threat semantics and engineering implications | direct production code implementation |
| `data-scientist` | measurement, experiment design, statistical comparison | runtime ownership and deployment routing |
| `docker-expert` | compose, Dockerfiles, deployment wiring | service business-logic implementation |
| `evaluator-agent` | independent acceptance and evidence-based verdict | implementation changes while evaluating |
| `doc-gardener` | docs/plans/harness sync and drift repair | undocumented architecture invention |
| `brainstorm-architect` | option generation and leverage scan before implementation | direct implementation execution |
| `example-demo-agent` | demo and reference output format | production ownership |

## Workflow

Default path:

`lead-agent -> specialist -> evaluator-agent -> doc-gardener`

Typical specialist set for this architecture refactor:

- `edge-agent-engineer`
- `central-agent-engineer`
- `console-developer`
- `docker-expert` (when deployment assets change)

Use `brainstorm-architect` before implementation when the problem frame is still unclear.
