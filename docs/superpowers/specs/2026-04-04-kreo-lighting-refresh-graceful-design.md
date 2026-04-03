# Kreo Lighting Refresh Graceful Design

Date: 2026-04-04

## Goal

Make the Lighting page feel less busy by replacing aggressive polling with slower idle refresh behavior, while also correcting the visible macOS modifier legends on the image-based keyboard surface.

## Scope

This slice includes:

- slower Lighting auto-refresh cadence
- refresh only while the Lighting page is visible, clean, and idle
- a short cooldown after user interaction before polling resumes
- a visible macOS modifier legend overlay for the image-based keyboard

This slice does not include:

- backend lighting changes
- keymap protocol changes
- replacing the vendored keyboard asset set

## Product Direction

The Lighting page should still feel live, but not twitchy.

The correct behavior is:

1. load lighting immediately on page entry
2. pause all polling while there are staged edits
3. when clean, refresh on a slow interval
4. after key selection, color edits, presets, apply, or reset, wait for a short cooldown before the next automatic poll
5. stop polling when the window/tab is hidden

For the keyboard image, the base vendored letters image can remain, but a focused macOS legend overlay should correct the visible modifier labels for:

- Control
- Option
- Command

## Acceptance Criteria

- the Lighting page no longer refreshes every 3 seconds while idle
- the page auto-refreshes only when visible and clean
- user interaction creates a noticeable cooldown before polling resumes
- the image-based board shows macOS-oriented modifier legends, including `Win -> Option`
