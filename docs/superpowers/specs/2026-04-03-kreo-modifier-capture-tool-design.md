# Kreo Modifier Capture Tool Design

Date: 2026-04-03

## Goal

Build a small one-shot capture script that records how macOS reports the confusing modifier and remap keys on the Kreo Swarm.

This tool exists to replace guesswork with evidence. It should let the user press each target key once, save a structured results file, and give the configurator enough data to reconcile:

- physical key identity
- macOS keycode and flag behavior
- current backend-decoded assignment for that physical key

## Scope

This slice includes:

- a guided terminal capture script
- modifier/remap key targets only
- one JSON output file written into the repo
- backend keymap snapshot capture alongside macOS event data

This slice does not include:

- full-keyboard capture
- live UI integration
- automatic remap fixes
- permanent background event logging

## Target Keys

The first capture pass should include only the confusing modifier/remap keys:

- left control
- left alt/option
- left gui/command
- right alt/option
- right control
- `fn` only if the chosen macOS event path can observe it reliably

If `fn` is not observable through the capture path, the output must record that explicitly instead of pretending it was captured.

## Product Direction

The script should be guided and finite.

The correct flow is:

1. show the next target key to press
2. wait for a single key-down event
3. record the macOS event details
4. read the current backend keymap snapshot
5. store the event and assignment together
6. repeat until every target has been captured once
7. write one JSON results file and stop

This is intentionally narrower than a raw event logger. The result should be readable, diffable, and easy to analyze.

## Capture Architecture

The capture tool should have three responsibilities:

- guide the user through the target list
- capture macOS keyboard event data
- persist a normalized results file

### Event Source

The script should use a macOS event tap through Python rather than relying on browser tooling or app UI instrumentation.

The event payload should include:

- virtual keycode
- modifier flags
- event type
- characters when available
- characters ignoring modifiers when available
- timestamp

### Backend Snapshot

For each captured target, the script should also fetch the current keymap payload from the existing backend/controller layer and attach the decoded assignment for the matching physical key.

This keeps the evidence file self-contained.

## Output File

The output should be a plain JSON file saved under a predictable path in the repo, for example:

- `captures/modifier-capture-YYYYMMDD-HHMMSS.json`

The file should contain:

- capture metadata
- target order
- one entry per target key
- any skipped or unsupported targets

Each target entry should include:

- requested target label
- observed macOS virtual keycode
- observed flags
- observed characters
- backend `ui_key`
- backend base assignment label and raw value
- backend fn assignment label and raw value when available

## Matching Strategy

The script should not guess based only on the event.

Instead, each capture step should already know which physical target is being requested, and the output should attach:

- the requested physical target label
- the observed event data
- the backend-decoded assignment for that same target key

This avoids fragile “which key was that?” inference during the first evidence pass.

## Error Handling

The tool should fail clearly when:

- input monitoring/accessibility permissions are missing
- the user presses no key within a timeout
- backend keymap state cannot be read

The tool should handle recoverable cases by retrying the current target instead of aborting the whole run.

If `fn` cannot be captured through the event path, the script should mark it as unsupported and continue.

## Testing Strategy

Testing should cover:

### Script Logic

- target sequencing
- JSON payload structure
- unsupported-target handling
- timeout/retry behavior

### Integration Boundary

- backend snapshot adapter behavior with mocked controller data

Manual verification should cover one real run where the user presses each requested key and the resulting JSON file is inspected afterward.

## Acceptance Criteria

This slice is complete when:

- a terminal script guides the user through the modifier targets
- the script stops automatically after all targets are captured
- one JSON results file is written into the repo
- each target record includes both macOS event data and backend-decoded key assignment data
- the script handles unsupported `fn` capture honestly

## Follow-On

After this capture file is produced, the next step is:

- analyze the results
- correct the key identity and macOS label mapping in the configurator
- add regression tests that lock the corrected mapping down
