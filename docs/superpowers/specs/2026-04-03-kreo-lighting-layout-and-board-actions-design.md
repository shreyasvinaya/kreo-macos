# Kreo Lighting Layout And Board Actions Design

## Goal

Refine the new per-key Lighting screen so it matches the physical Kreo Swarm keyboard more closely and adds fast whole-board staging controls without sacrificing the existing single-key editor model.

## Scope

Included:
- mirror the physical keyboard layout more faithfully
- render the separate right-side navigation cluster
- render the arrow cluster in its physical position
- render the top-right knob area as a visible non-editable module
- keep unmapped physical keys dimmed but visible
- add whole-board staged actions:
  - solid fill
  - two-color split
  - three-color split
  - checker
  - simple rainbow preset
- auto-refresh the per-key state when the screen is clean

Excluded:
- knob interaction
- drag/brush painting
- effect-programming UI
- profile-specific lighting workflows

## Existing Context

The Lighting screen now supports:
- real per-key color loading
- single-key selection
- staged color edits
- explicit apply/reset
- physical keyboard writes

The current problem is presentation and speed of use:
- the board layout still feels generic rather than matching the real device
- there are no quick whole-board operations
- the screen does not keep itself live when idle

## Architecture

This should remain one Lighting-screen slice. No new subsystem is required.

Backend changes:
- no major protocol redesign
- add helper methods for generating staged whole-board preset diffs from the currently loaded per-key model
- keep the backend diff-apply contract unchanged

Frontend changes:
- replace the generic keyboard matrix with a physical-board composition
- add a board-actions section in the inspector
- add clean-state auto-refresh behavior

The staged edit model remains the same:
- presets only mutate staged state
- single-key edits only mutate staged state
- apply writes the merged staged diff

## Layout Direction

The keyboard visual should mirror the physical board from the photo:
- correct row lengths and proportions
- separate right navigation column
- dedicated arrow cluster in the lower-right area
- visible top-right knob block
- more realistic negative space between the alpha block and side cluster

The knob should be visually present but never selectable.

Unmapped physical keys should:
- remain visible in the board
- render dimmed
- be non-clickable

Mapped keys should:
- render full brightness
- show their live/staged color
- remain selectable

## Board Actions

The right inspector should add a persistent `Board actions` section below the selected-key editor.

Actions:
- `Solid fill`
  - one color picker
  - applies the color to all mapped keys in staged state
- `Two-color split`
  - two color pickers
  - split should follow the board’s physical left/right distribution
- `Three-color split`
  - three color pickers
  - split should match the broad left/center/right visual structure already confirmed on hardware
- `Checker`
  - two color pickers
  - alternating mapped-key pattern
- `Rainbow`
  - one-click preset
  - deterministic left-to-right hue progression across mapped keys

All actions should recolor the board immediately in staged state.
None of them should write to the keyboard until `Apply staged edits`.

## Refresh Model

The screen should refresh from hardware automatically when it is clean.

Rules:
- if `stagedEdits` is empty, auto-refresh per-key state on an interval
- if `stagedEdits` is non-empty, suspend auto-refresh
- after `Apply`, perform an immediate refresh and resume clean-state refresh
- after `Reset`, perform an immediate refresh and resume clean-state refresh
- preserve selected key if it still exists after refresh

This keeps the board live while idle without overwriting local work.

## Data Flow

1. `Lighting` opens
2. per-key state loads immediately
3. clean-state refresh loop starts
4. user selects a key or triggers a board action
5. staged state becomes dirty
6. refresh loop pauses
7. board renders staged colors immediately
8. user applies or resets
9. staged state clears
10. immediate refresh runs
11. clean-state refresh loop resumes

## Preset Semantics

Whole-board actions should operate only on mapped keys currently known to the UI.

Recommended semantics:
- `Solid fill`: every mapped key gets the same color
- `Two-color split`: sort mapped keys by horizontal board grouping and split into two contiguous groups
- `Three-color split`: split mapped keys into left, center, right contiguous groups
- `Checker`: alternate by visual key order in the rendered board
- `Rainbow`: assign hue by visual key order from left to right, top to bottom

The preset logic should be deterministic so the user can predict the result.

## Acceptance Criteria

This slice is done when:
- the Lighting canvas looks like the physical Kreo Swarm instead of a generic grid
- unmapped keys are dimmed but still visible
- the knob area is visible and non-editable
- whole-board actions stage visible color changes immediately
- single-key editing still works
- auto-refresh happens while clean and pauses while dirty
