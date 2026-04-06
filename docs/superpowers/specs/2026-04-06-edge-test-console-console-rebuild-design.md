# Edge Test Console Console Rebuild Design

Date: 2026-04-06
Status: Drafted from approved design direction, awaiting spec review
Owner: Codex

## Overview

Rebuild `edge-test-console/frontend` into a desktop-first light-theme management console that follows the `console-design` skill strictly: warm neutral token system, explicit app shell, dense operational surfaces, border-led hierarchy, and lightweight implementation.

This rebuild is not a landing page redesign and not a judge-facing presentation board. The frontend should still read as a real working console, but it must express the project's core value, hybrid method, workflow, and evidence clearly enough that a first-time viewer can understand the system without external narration.

The product capability remains unchanged:

- upload a `.pcap` or `.pcapng` sample
- create a backend detection task
- poll task status until completion or failure
- fetch and display the result archive

The change is therefore an information architecture and interface system rebuild, not a backend or workflow rewrite.

## Goals

1. Reframe the frontend as a true desktop console with a stable shell: sidebar, top bar, content column, floating action bar.
2. Make the homepage `总览优先`, but keep it product-native and operational rather than marketing-oriented.
3. Surface the project's core story inside the console itself:
   - what problem is being handled
   - how the hybrid pipeline works
   - what makes the system distinctive
   - what evidence the current run can prove
4. Keep upload, pipeline tracking, and result archive as first-class workflow modules.
5. Preserve the existing API contract and React + TypeScript + CSS Modules stack.
6. Centralize visual tokens and presentation mapping so future changes do not require reworking every component.

## Non-goals

- No mobile-first redesign
- No route-based multi-page conversion
- No new backend endpoints
- No new charting, UI-library, or animation-library dependencies
- No fabricated benchmark claims or decorative comparison panels unsupported by backend data
- No change to upload validation rules, polling interval, or result semantics unless required for UI correctness

## Product Framing

The rebuilt console should express the project from its own perspective, not from a pitch-deck perspective.

That means the UI should make these ideas legible through the product structure itself:

- this is an edge-side traffic detection workbench
- the system converts raw packet samples into explainable threat archives
- the design uses staged filtering rather than sending all traffic into heavy inference
- the output is not only a label, but also a reduced-bandwidth structured result
- the system is a real four-container closed loop with explicit service boundaries

The UI should help a new viewer understand:

1. what goes in
2. what processing happens
3. what comes out
4. why the architecture matters
5. what quantitative result the current run demonstrates

## Page Archetype

Use the `dashboard recipe` as the primary archetype and mix in `data management recipe` behavior for the archive section.

Why:

- the page must summarize system state and introduce the product quickly
- it also needs dense operational sections immediately below
- the result archive behaves like structured records, not like showcase cards

This yields the following page order:

1. app shell
2. restrained system summary band
3. compact evidence and architecture grid
4. workflow workspace
5. archive management section

## Information Architecture

The app remains a single-page console with local section switching rather than route-level navigation.

### Sidebar

Persistent desktop sidebar with three anchors:

- `系统总览`
- `检测工作台`
- `威胁归档`

Sidebar responsibilities:

- orient the user inside the product
- communicate the console identity
- expose the current active section clearly
- show one compact environment or capability cue in the footer

The sidebar is part of the shell and should remain visible while content scrolls.

### Top Bar

Sticky top bar with:

- current page title
- one-line system subtitle
- current task state
- current stage or idle hint
- mode controls or primary action group

The top bar must feel operational. It should not contain promotional copy.

### Main Column

The main content should be organized into three high-level sections.

#### 1. System Overview

This is the entry section and default view.

It should answer four questions immediately:

- what is this console
- what workflow does it run
- what evidence does it currently have
- what system pieces make the result possible

Recommended content blocks:

- summary band
- evidence grid
- workflow chain panel
- architecture and innovation panel

The overview should remain dense and controlled. It is not a splash hero.

#### 2. Detection Workspace

This section is the actual operator surface and should sit directly below the overview rather than behind a separate route.

Structure:

- left: upload and task controls
- center/right: live pipeline panel
- bottom or adjacent strip: current task summary

The workspace must make the active processing state obvious during runs.

#### 3. Threat Archive

This section renders the result as a structured archive:

- task summary
- compression and runtime metrics
- anomaly inventory
- five-tuple and token metadata

It should feel like a record surface, not like a slideshow summary.

## Overview Content Model

The overview section must explain the project through product-native modules.

### Summary Band

Purpose:

- define the system in one sentence
- show the current console state
- establish the main processing chain visually

Content:

- eyebrow
- title
- one concise description
- current state pill
- one restrained expressive gesture such as a topology watermark or chain signature

The copy should emphasize:

- edge-side detection
- bandwidth reduction
- explainable threat output

### Evidence Grid

This grid should show real or placeholder evidence in compact cards.

Primary cards:

- bandwidth reduction
- anomaly detection count
- processing duration
- runtime mode or deployment shape

Rules:

- use real result data when available
- otherwise use honest placeholders like `等待首个样本`
- do not claim accuracy, recall, F1, or benchmark ranking

### Workflow Chain Panel

This panel should render the core pipeline as a linear operational chain:

`Pcap -> 流重组 -> SVM 初筛 -> TrafficLLM 分词 -> LLM 判定 -> 威胁归档`

Each stage should explain:

- input role
- output role
- why that stage exists

The purpose is not animation spectacle. The purpose is immediate comprehension.

### Architecture and Innovation Panel

This panel should show what is special about the system without breaking console tone.

Content should be grounded in the repository and architecture docs:

- four-container closed loop
- single-direction call chain
- SVM and LLM division of labor
- edge deployment constraints
- structured archive output replacing raw packet transfer

This panel should not read like a prize submission slogan wall. It should read like an engineering summary surface.

## Workspace Design

The workspace section is where the console proves it is a real working product.

### Upload Workspace

Keep the existing file validation and task submission behavior.

UI responsibilities:

- choose sample
- validate file type
- show selected file metadata
- submit task
- surface upload or validation errors clearly

The visual treatment should follow the shared console input and button language.

### Pipeline Panel

The pipeline panel should become more explicit and system-like.

It should show:

- current stage title
- current backend message
- progress percentage
- stage list with active and completed distinction
- progress track

If possible from current state only:

- distinguish `pending`, `active`, `completed`, and `failed` visually

The component should remain deterministic and not invent state that the backend does not provide.

### Current Task Summary

A compact strip or card should summarize the current run:

- task state
- stage label
- latest message
- availability of result data

This allows the console to remain understandable even while the user is scrolled away from the upload panel.

## Threat Archive Design

The archive should read like a result management surface.

### Summary Header

Show:

- task id
- task timestamp if available
- processing duration
- archive status

### Metric Rows

Compact metric cards for:

- bandwidth reduction percent
- anomaly flow count
- original pcap size
- JSON output size
- reduction ratio

### Threat Records

Each threat card should prioritize structured evidence:

- primary and secondary label
- confidence
- five tuple
- protocol
- packet and byte metadata if available
- token count and truncation state

When no threats exist, the empty state should clearly indicate that the run completed and no anomaly candidate was archived.

## State Model

The rebuild must preserve explicit rendering for all supported app states:

1. `idle`
2. `uploading`
3. `processing`
4. `completed`
5. `failed`

The UI must also correctly handle:

- `result === null`
- task failure without result data
- completed task with zero threats
- polling failure after retry exhaustion

No component may assume success-state data exists unless validated by the orchestration layer.

## Component Architecture

The rebuild should reduce the current concentration of layout and shell logic inside `App.tsx`.

Recommended component split:

- `App`
- `ConsoleShell`
- `SidebarNav`
- `Topbar`
- `OverviewBand`
- `EvidenceGrid`
- `WorkflowChain`
- `ArchitecturePanel`
- `UploadWorkspace`
- `PipelinePanel`
- `TaskSummary`
- `ResultArchive`
- `FloatingActionBar`

This is a responsibility map, not a mandatory file count. Smaller related overview components may stay grouped if that keeps the code clearer.

### App Responsibilities

`App` should own:

- current section selection
- task lifecycle state
- task id
- polling setup and teardown
- reset behavior
- backend data retrieval
- top-level view model assembly

### View-model Layer

Extend `src/lib/view-models.ts` into the presentation mapping layer.

Responsibilities:

- overview cards
- workflow chain copy
- architecture summary items
- current state badge copy
- top bar summary text
- result archive stat groups
- empty-state copy

This avoids scattering label logic and fallback formatting across multiple components.

## Visual System

The entire rebuild must follow the `console-design` token rules.

### Token Layer

Use `src/index.css` to define the warm neutral token system:

- background layers
- text colors
- border hierarchy
- primary accent
- success and warning semantics
- spacing scale
- radius scale
- shadow tokens

No component should invent a parallel color system.

### Shell Rules

- desktop-first layout
- explicit sidebar
- explicit top bar
- content padding at `24px`
- section gaps at `24px` or `32px`
- cards at `12px` radius
- controls at `8px` radius
- pills at full radius

### Interaction Rules

Required states:

- hover
- focus
- active
- disabled
- loading where async action exists

Transitions should stay within the `150ms` to `180ms` range for ordinary controls.

### Visual Gesture

Allow one restrained expressive gesture:

- a watermark in the overview band
- or a topology signature line

Everything else should return to strict utility styling.

## Copy Strategy

Copy should sound like a product console operated by engineers, not like an awards poster.

Preferred tone:

- precise
- short
- confident
- explanatory when needed

Avoid:

- inflated slogans
- abstract innovation claims without context
- long marketing paragraphs

The UI should teach by structure and labels, not by persuasive writing.

## API and Data Constraints

Keep the existing API boundary unchanged:

- `uploadPcap(file)`
- `getTaskStatus(taskId)`
- `getTaskResult(taskId)`

The rebuild may derive display values from existing data, but it must not invent unsupported metrics.

Allowed:

- bandwidth reduction formatting
- anomaly ratio formatting
- runtime formatting
- stage mapping
- archive summaries from current fields

Not allowed without new backend support:

- model accuracy
- comparative benchmark scores
- detection recall claims
- historical trends across runs

## Error Handling and Empty States

Required explicit states:

- invalid file type
- upload failure
- polling failure
- backend task failure
- untouched idle overview
- completed run without threats
- archive unavailable before first successful task

Each state should provide:

- short label
- short explanation
- visual distinction
- next action where relevant

## Verification Plan

Implementation verification must include:

1. `npm run build` in `edge-test-console/frontend`
2. type-safe render branches for idle, processing, completed, and failed
3. manual check of upload disable/reset behavior
4. manual check that polling is cleaned up on reset and unmount
5. manual check that result archive never dereferences null data

## Acceptance Criteria

The rebuild is complete when:

- the page reads as a desktop management console before any decorative layer is considered
- the default entry experience is `总览优先`
- the overview clearly explains the product's problem, method, workflow, and evidence using console-native surfaces
- the upload, pipeline, and archive workflow still works against the current backend contract
- no heavyweight dependency is added
- shared tokens and component language are consistent across shell, cards, buttons, pills, inputs, and archive rows
- empty, loading, processing, failure, and completed states all remain coherent
