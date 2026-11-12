# 1. Record architecture decisions

Date: 2026-11-12

Status: accepted

## Context

Several agents will change this repository in parallel. Scientific choices stay
in `spec/` and `data/gold/`, which are owner-only. Engineering choices that
change the task format, the package public API, or the directory layout need a
record that the next agent can read.

## Decision

Record those engineering decisions as numbered Markdown files in `docs/adr/`.
A pull request that changes the task format, the public API, or the directory
layout adds a new ADR in the same pull request.

## Consequences

Agents read `docs/adr/` before changing those surfaces. Physics, units,
tolerances, and literature provenance stay in `spec/` and are not decided here.
