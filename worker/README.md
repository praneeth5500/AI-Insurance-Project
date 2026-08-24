# Worker

Async job worker for policy-document processing.

## Phase 0 status: placeholder

This process currently starts, validates configuration, logs, and exits. It
does **not** consume a queue, because the queue technology is an open item
(`docs/13_DECISIONS_AND_OPEN_ITEMS.md`, item 4). Implementing a queue adapter
now would invent a decision that has not been made.

## Why it depends on the backend package

`docs/04_BACKEND_ARCHITECTURE.md` specifies a modular monolith. The worker will
need the same domain code as the API (`documents/`, `policies/`, `ai/`), so it
is a thin entrypoint with an editable path dependency on `../backend` rather
than a second copy of the domain layer. Deployment stays "one image, two
commands".

## What Phase 10 / 11 add

- a `QueueConsumer` adapter (local adapter + SQS adapter);
- the pipeline from `docs/07_POLICY_DECODER_AI.md` section 2;
- retry, dead-letter and failure-state handling, so a failed extraction stays
  visibly failed rather than silently empty.

## Run

```bash
make dev-worker
```
