# VirtuDirector IA Implementation Engine

This optional extension packages VirtuDirector outputs into implementation-ready execution bundles.

It is intentionally vendor-agnostic.

The extension can:

- load skill files,
- compose a swarm-style execution brief,
- write a full output package to disk,
- and optionally call an external CLI if one is configured.

## What it is for

Use this extension after VirtuDirector has already identified:

- the target use case,
- the expected business outcome,
- the preferred runtime mode,
- and the main risks and controls.

Typical sequence:

1. run diagnosis in `/app`,
2. confirm the priority use case,
3. prepare the implementation engine input,
4. generate the execution package,
5. review it,
6. hand it to a human team or an external agent runtime.

## What it is not for

This extension does not replace:

- the CAIO chat,
- the knowledge layer,
- the Labs review pipeline,
- or the main governance workflows.

## Files

- `skill_injector.py`: loads and concatenates skill markdown.
- `swarm_launcher.py`: builds an execution package and optionally calls an external command.
- `services/`: service-specific implementation blueprints.
- `skills/`: reusable skill files.
- `config/`: default execution settings and sample client config.

## Quick start

### 1. Prepare a client config

Edit:

- `config/example-client.json`

### 2. Generate an execution bundle

```bash
python extensions/implementation-engine/swarm_launcher.py \
  --client-config extensions/implementation-engine/config/example-client.json \
  --service-file extensions/implementation-engine/services/customer-support-automation.md \
  --skill-dir extensions/implementation-engine/skills/base \
  --skill-dir extensions/implementation-engine/skills/verticals \
  --skill shopify-ecommerce \
  --output-dir /tmp/virtudirector-implementation-demo \
  --review
```

### 3. Inspect the generated files

The output directory will contain:

- `swarm_input.md`
- `execution_request.json`
- `review_checklist.md`
- `command.txt`
- optionally `stdout.txt` and `stderr.txt` if an external command runs

## External CLI execution

If you want the launcher to call a real external agent/swarm CLI, set:

```bash
export IMPLEMENTATION_SWARM_COMMAND="your-command-here"
```

The launcher will append the generated `swarm_input.md` path to that command.

Example:

```bash
export IMPLEMENTATION_SWARM_COMMAND="kimi run --input"
```

This extension does not assume that a specific CLI is installed. It only provides a clean handoff point.

## Review mode

Use `--review` to write an explicit human review checklist into the output package.

This keeps the extension aligned with the repository’s core principle:

```text
generate -> review -> approve -> execute
```
