# Optional extension: Implementation Engine

## Purpose

This repository can support an optional execution layer on top of the current CAIO, knowledge, and Labs workflows.

The core product answers:

- where AI should be implemented,
- what the expected ROI is,
- which risks must be controlled,
- and which runtime mode is appropriate.

The optional implementation engine answers a different question:

- how to package those decisions into repeatable delivery work for an operator, consultant, or AI delivery team.

## Why this should remain optional

The main product is a CAIO-style decision and governance system for SMEs.

An implementation engine introduces additional concerns:

- service delivery templates,
- skill injection,
- execution prompts,
- optional external swarm CLIs,
- human review and packaging of deliverables.

These concerns are useful, but they should not become mandatory for basic product use.

## What the extension does

The optional extension under `extensions/implementation-engine/` provides:

1. a vendor-agnostic skill injection mechanism,
2. a deterministic execution bundle generator,
3. a launcher that can optionally call an external swarm CLI,
4. service blueprints for implementation work derived from VirtuDirector outputs.

## Intended usage

Use the extension when you want to go from:

```text
diagnosis -> roadmap -> controlled implementation package
```

Do not use the extension when you only need:

- chat guidance,
- opportunity prioritization,
- knowledge retrieval,
- lab evaluation,
- governance analysis.

## Positioning

This extension is designed for:

- implementation partners,
- internal AI teams,
- operators running repeated delivery workflows,
- and agencies using VirtuDirector IA as a discovery and governance front-end.

It is not designed as a replacement for the main product runtime.
