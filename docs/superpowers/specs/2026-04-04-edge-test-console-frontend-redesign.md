# Edge Test Console Frontend Redesign

Date: 2026-04-04
Status: Approved in conversation, awaiting final spec review
Owner: Codex

## Overview

Redesign `edge-test-console/frontend` into a desktop-first management console that matches the `console-design` skill language: warm neutral surfaces, muted taupe accent, dense but readable information layout, floating action surfaces, and restrained motion.

The redesign keeps the current product capability unchanged:

- Upload a `.pcap` or `.pcapng` sample
- Create a backend detection task
- Poll task status until completion or failure
- Fetch and render the detection result archive

The work is a frontend-only restructuring. It must preserve the existing API contract and avoid introducing large UI, charting, animation, or state-management dependencies.

## Goals

1. Replace the current showcase-like single page with a true desktop console shell.
2. Reorganize the existing workflow into clearer operational zones:
   - overview
   - upload workspace
   - pipeline tracking
   - result archive
3. Centralize visual tokens so the application follows the `console-design` system consistently.
4. Isolate API integration from presentation so future UI changes do not require touching every render branch.
5. Keep the dependency surface minimal by using the existing `React + TypeScript + Vite + CSS Modules` stack only.

## Non-goals

- No mobile-first or phone-specific redesign work
- No new backend endpoints
- No route-based multi-page app conversion
- No additional charting, component-library, animation-library, or global state packages
- No functional changes to detection semantics, upload rules, or polling cadence unless required for UI correctness

## Current Constraints

The existing frontend already has a small and suitable stack:

- `react`
- `react-dom`
- `vite`
- `typescript`
- CSS Modules

The backend integration is already encapsulated behind:

- `uploadPcap`
- `getTaskStatus`
- `getTaskResult`

These functions remain the only network entry points for the redesign.

## User Experience Direction

The target UI should feel like a polished internal operations console rather than a landing page or marketing panel.

Required visual characteristics:

- Warm layered backgrounds, not cold gray
- Taupe primary accent, not blue
- Soft bordered cards with subtle shadows
- Sticky shell elements for navigation and context
- A bento-style overview area for summary metrics
- A floating action bar for repeated actions
- Purposeful motion only: hover lift, section fade, small transitions

Signature gestures selected for this page:

- `OVERVIEW` watermark in the hero band
- bottom-centered floating action bar

## Information Architecture

The application remains a single-page workflow, but the shell should make it feel like a structured console.

### Left Sidebar

Persistent desktop navigation with:

- product mark / console name
- section anchors for:
  - `任务总览`
  - `流水线追踪`
  - `结果归档`
- environment or capability badge at the bottom

This sidebar is presentational and navigational only. It does not introduce route-level state.

### Top Bar

A sticky top bar provides:

- current page title and subtitle
- overall task state badge
- latest task metadata or idle hint
- optional environment marker

The top bar surfaces system context without taking over core business logic.

### Main Workspace

The content area is split into three major vertical sections.

#### 1. Overview Hero

Purpose:

- establish current operating context
- summarize the current task state
- show key metrics or placeholders depending on task state

Content:

- eyebrow copy
- hero title
- task-state badge
- current stage summary
- three quick metric cards
- watermark background

State behavior:

- idle: show mode and capability summaries
- processing: show live stage and progress-oriented summaries
- completed: show anomaly count, bandwidth saved, processing duration
- failed: show failure state without assuming result data exists

#### 2. Detection Workspace

A two-column operational zone.

Left column:

- upload workspace
- accepted file summary
- validation or failure messaging
- local action controls

Right column:

- pipeline timeline
- progress bar
- stage details
- current backend message

This section is the active work area while a task is being submitted or processed.

#### 3. Result Archive

Purpose:

- render output as an operational archive rather than a plain result dump

Content:

- result summary header
- stat cards
- bandwidth reduction comparison
- archive summary list
- threat cards
- five-tuple metadata
- flow metadata
- token metadata

Empty state behavior must remain explicit when no result exists.

## Component Architecture

The redesign separates shell concerns from task orchestration.

### `App`

Responsibilities:

- own the task state machine
- own the active `taskId`
- own polling lifecycle and teardown
- own reset behavior
- fetch backend data through existing API client functions
- derive page-level view models

`App` remains the orchestration root. It should not accumulate detailed visual markup for every card and panel.

### Shell Components

Suggested shell-level components:

- `ConsoleShell`
- `SidebarNav`
- `Topbar`
- `FloatingActionBar`

Responsibilities:

- layout only
- render navigation and shell chrome
- consume prepared state from `App`
- never call the API directly

### Domain Components

Suggested workflow components:

- `OverviewHero`
- `UploadWorkspace`
- `PipelinePanel`
- `ResultArchive`

Responsibilities:

- render one business region each
- receive normalized props rather than raw API response fragments scattered throughout JSX
- keep business-specific formatting local where sensible

### View-model Layer

Add a lightweight mapping layer such as `src/lib/view-models.ts`.

Responsibilities:

- convert API and app state into presentational data structures
- centralize labels, badges, metric formatting, and fallback values
- prevent repeated ad hoc transformations in component render functions

Examples:

- top bar badge text
- overview metric triplets
- stage presentation metadata
- result summary cards
- empty-state copy selection

## API Adaptation Strategy

The redesign must adapt to the current backend interaction model without changing its contract.

### Stable API Boundary

Keep these functions unchanged as the only HTTP integration points:

- `uploadPcap(file)`
- `getTaskStatus(taskId)`
- `getTaskResult(taskId)`

No component outside the orchestration layer should bypass these functions.

### Lifecycle Rules

#### Upload

- starting a new upload clears prior polling state
- previous result data is reset before the new task begins
- UI enters `uploading`, then `processing` on successful task creation

#### Polling

- polling remains interval-based using the existing client flow
- repeated transient errors are tolerated up to the current retry threshold
- polling stops cleanly when:
  - task completes
  - task fails
  - result fetch fails
  - user resets
  - component unmounts

#### Result Fetch

- result retrieval occurs only after backend status reports `completed`
- if result fetch fails, UI moves into a failed terminal state with recoverable messaging

### State-safe Rendering

The UI must explicitly support these combinations:

1. No task yet, no result
2. Upload in progress
3. Task processing, no result yet
4. Task failed, no result
5. Task completed, result loaded

No view may assume `result` exists unless it is already validated.

## Visual System Integration

### Token Layer

Move the application to a token-first visual system in `src/index.css`.

This file should define:

- background layers
- text hierarchy
- border hierarchy
- taupe primary accent
- spacing scale
- radius scale
- shadow tokens

Modules consume these tokens instead of defining standalone color systems.

### Layout Styling

`App.module.css` should own:

- shell grid
- sidebar width
- sticky top bar behavior
- content column spacing
- section-level desktop layout
- floating action bar placement

Feature module CSS files should own only local internals.

### Motion

Use CSS-only transitions and keyframes:

- 150ms hover transitions for buttons and cards
- 300ms section entrances where helpful
- subtle hover lift on cards
- no overshooting spring behavior

## Dependency Policy

The redesign must not add heavy dependencies for problems that CSS and React already solve.

Explicitly avoid:

- `antd`
- `mui`
- `chakra-ui`
- `mantine`
- `recharts`
- `echarts`
- `framer-motion`
- `zustand`
- `redux`

Allowed approach:

- plain React state
- CSS Modules
- pure utility functions for formatting and mapping
- inline SVG or existing HTML/CSS for icons and simple visualizations

## File Structure Direction

The exact final split may vary, but the architecture should converge toward the following responsibilities:

- `src/App.tsx`
- `src/App.module.css`
- `src/index.css`
- `src/components/ConsoleShell.tsx`
- `src/components/ConsoleShell.module.css`
- `src/components/SidebarNav.tsx`
- `src/components/Topbar.tsx`
- `src/components/OverviewHero.tsx`
- `src/components/UploadWorkspace.tsx`
- `src/components/PipelinePanel.tsx`
- `src/components/ResultArchive.tsx`
- `src/components/FloatingActionBar.tsx`
- `src/lib/view-models.ts`

This is a responsibility guide, not a rigid file-count requirement. Small helper components may remain colocated if that keeps the code easier to follow.

## Error Handling and Empty States

The redesign must improve clarity around non-happy paths.

Required states:

- invalid file type validation
- upload failure
- polling failure after retry exhaustion
- task-reported failure
- completed run with zero threats
- untouched idle state

Each state should have:

- clear title or label
- short explanatory copy
- visual differentiation using the token system
- a recoverable action when relevant

## Testing and Verification

Minimum verification for implementation:

1. `npm run build` passes in `edge-test-console/frontend`
2. idle, processing, failed, and completed render branches remain type-safe
3. existing API interactions still compile against the current backend types
4. no new runtime dependency is introduced unless strictly necessary

Manual behavior checks for implementation:

- upload button disabled behavior during active work
- polling cleanup on reset
- result archive does not render invalid access when `result === null`
- floating action bar actions map correctly to existing workflow actions

## Implementation Notes

Recommended sequencing:

1. establish tokens in `src/index.css`
2. rebuild page shell in `App` and shell components
3. introduce view-model mapping helpers
4. migrate upload workspace
5. migrate pipeline panel
6. migrate result archive
7. add floating action bar and final desktop polish
8. run build verification

## Acceptance Criteria

The redesign is complete when all of the following are true:

- the page visually reads as a desktop management console
- the `console-design` color, spacing, and surface language is consistently applied
- the current upload -> poll -> result workflow still works with the existing backend API
- the frontend dependency list stays effectively unchanged
- empty, loading, processing, failure, and completed states all render coherently
- the code structure is cleaner than the current all-in-one layout
