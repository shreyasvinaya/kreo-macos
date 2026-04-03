# Kreo Lighting Refresh Graceful Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make Lighting auto-refresh slower and less disruptive, and add macOS modifier legend overlays to the image-based keyboard surface.

**Architecture:** Move the refresh timing rules into a small frontend helper with tests, then update the Lighting screen to schedule refreshes from that policy instead of using a fixed 3-second interval. Add a lightweight modifier legend overlay layer on top of the asset-based keyboard using the existing keyboard metadata.

**Tech Stack:** React, TypeScript, Bun test, existing keyboard asset metadata

---
