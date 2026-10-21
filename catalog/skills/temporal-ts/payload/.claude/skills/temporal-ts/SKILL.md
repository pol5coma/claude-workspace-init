---
name: temporal-ts
description: Build durable workflows with Temporal's TypeScript SDK in a Next.js + TypeScript app. Use when writing or reviewing Temporal workflows, activities, workers, signals, queries, updates, retries, timeouts or workflow tests, or when wiring a Next.js route handler / server action to start and inspect workflows. Trigger terms: Temporal, temporal.io, @temporalio, workflow, activity, worker, task queue, signal, query, update, durable execution.
---

# Temporal + TypeScript + Next.js

Temporal runs **workflows** (deterministic orchestration code, replayed from history) that call
**activities** (normal code that does I/O). A **worker** process polls a **task queue** and executes
both. Next.js is only a **client**: it starts, signals, queries and reads workflows. It never runs the
worker.

## Before writing code

1. Restate the business process as steps, decisions, waits and failure modes.
2. Decide what is a workflow (orchestration, waiting, compensation) and what is an activity
   (HTTP, database, email, LLM calls, anything non-deterministic).
3. Choose a stable, meaningful `workflowId` (e.g. `order-${orderId}`) so starts are idempotent.
4. Define timeouts and retry policy per activity before implementing it.

## Project layout

```
src/
  temporal/
    shared.ts        # task queue name, shared types, signal/query/update definitions
    activities.ts    # I/O lives here
    workflows.ts     # deterministic orchestration only
    worker.ts        # separate Node process: `npx tsx src/temporal/worker.ts`
    client.ts        # cached Temporal Client for Next.js server code
  app/api/orders/route.ts            # start / list
  app/api/orders/[id]/route.ts       # status (query) / actions (signal, update)
tests/temporal/                      # workflow and activity tests
```

Packages: `@temporalio/client`, `@temporalio/worker`, `@temporalio/workflow`,
`@temporalio/activity`, and `@temporalio/testing` (dev).
Local server: `temporal server start-dev` (gRPC `localhost:7233`, Web UI `http://localhost:8233`).

## Shared definitions

```ts
// src/temporal/shared.ts
import { defineQuery, defineSignal, defineUpdate } from "@temporalio/workflow";

export const TASK_QUEUE = "orders";

export type OrderInput = { orderId: string; amountCents: number; email: string };
export type OrderStatus = "pending" | "paid" | "shipped" | "cancelled" | "failed";

export const cancelSignal = defineSignal<[reason: string]>("cancel");
export const statusQuery = defineQuery<OrderStatus>("status");
export const approveUpdate = defineUpdate<OrderStatus, [approver: string]>("approve");
```

`defineSignal`/`defineQuery`/`defineUpdate` are safe to import from both client and workflow code.

## Activities: all I/O, idempotent

```ts
// src/temporal/activities.ts
import { ApplicationFailure, Context } from "@temporalio/activity";

export async function chargeCard(orderId: string, amountCents: number): Promise<string> {
  // Pass an idempotency key so retries never double-charge.
  const res = await fetch("https://payments.example/charge", {
    method: "POST",
    headers: { "Idempotency-Key": orderId, "Content-Type": "application/json" },
    body: JSON.stringify({ amountCents }),
  });
  if (res.status === 402) {
    throw ApplicationFailure.nonRetryable("Card declined", "CardDeclined");
  }
  if (!res.ok) throw new Error(`Payment API ${res.status}`); // retryable
  return (await res.json()).chargeId;
}

export async function sendEmail(to: string, subject: string): Promise<void> {
  Context.current().heartbeat(); // long-running activities should heartbeat
  // ...
}
```

Rules:
- Activities may be retried at any point: make them idempotent (idempotency keys, upserts).
- Throw `ApplicationFailure.nonRetryable(message, type)` for business errors that must not retry.
- Long activities call `Context.current().heartbeat(progress)` and set `heartbeatTimeout`.

## Workflows: deterministic orchestration only

```ts
// src/temporal/workflows.ts
import {
  ApplicationFailure, condition, proxyActivities, setHandler, sleep,
} from "@temporalio/workflow";
import type * as activities from "./activities"; // type-only import!
import { approveUpdate, cancelSignal, statusQuery, type OrderInput, type OrderStatus } from "./shared";

const { chargeCard, sendEmail } = proxyActivities<typeof activities>({
  startToCloseTimeout: "30 seconds",
  retry: { initialInterval: "1 second", backoffCoefficient: 2, maximumAttempts: 5,
           nonRetryableErrorTypes: ["CardDeclined"] },
});

export async function orderWorkflow(input: OrderInput): Promise<OrderStatus> {
  let status: OrderStatus = "pending";
  let approved = false;
  let cancelled: string | undefined;

  setHandler(statusQuery, () => status);
  setHandler(cancelSignal, (reason) => { cancelled = reason; });
  setHandler(approveUpdate, (approver) => {
    if (cancelled) throw ApplicationFailure.create({ message: "Order already cancelled" });
    approved = true;
    return status;
  });

  // Durable wait: survives worker restarts and deploys.
  const gotDecision = await condition(() => approved || cancelled !== undefined, "24 hours");
  if (!gotDecision || cancelled) {
    status = "cancelled";
    return status;
  }

  await chargeCard(input.orderId, input.amountCents);
  status = "paid";
  await sleep("1 minute"); // durable timer, not setTimeout semantics you control
  await sendEmail(input.email, `Order ${input.orderId} paid`);
  return status;
}
```

Determinism rules, which are the most common interview mistakes:
- **Never** import activity implementations, Node modules (`fs`, `crypto`, `http`), database clients
  or `fetch` into workflow files. Use `import type` for activities.
- Do all I/O through activities. Workflow code may only compute, call activities, wait and handle messages.
- Use `sleep()` and `condition()` for time and waiting; they are durable.
- The workflow sandbox makes `Date` and `Math.random()` deterministic, but don't build business
  logic on wall-clock time. Pass timestamps in as input or get them from an activity.
- Changing workflow code that has running executions needs `patched("change-id")` /
  `deprecatePatch(...)`, or a new workflow type, otherwise replay fails.
- Very long or looping workflows call `continueAsNew` to keep history bounded.

## Worker: its own process

```ts
// src/temporal/worker.ts
import { NativeConnection, Worker } from "@temporalio/worker";
import * as activities from "./activities";
import { TASK_QUEUE } from "./shared";

async function run() {
  const connection = await NativeConnection.connect({
    address: process.env.TEMPORAL_ADDRESS ?? "localhost:7233",
  });
  const worker = await Worker.create({
    connection,
    namespace: process.env.TEMPORAL_NAMESPACE ?? "default",
    taskQueue: TASK_QUEUE,
    workflowsPath: require.resolve("./workflows"), // ESM: fileURLToPath(new URL("./workflows.ts", import.meta.url))
    activities,
  });
  await worker.run();
}

run().catch((err) => { console.error(err); process.exit(1); });
```

Run it with `npx tsx src/temporal/worker.ts`. The worker bundles `workflowsPath` with webpack into the
sandbox, so workflow files must stay free of non-deterministic imports.

## Next.js: client only

```ts
// src/temporal/client.ts
import { Client, Connection } from "@temporalio/client";

const globalForTemporal = globalThis as unknown as { temporalClient?: Promise<Client> };

export function getTemporalClient(): Promise<Client> {
  // One connection per server process (survives Next.js dev hot reloads).
  globalForTemporal.temporalClient ??= Connection.connect({
    address: process.env.TEMPORAL_ADDRESS ?? "localhost:7233",
  }).then((connection) => new Client({ connection, namespace: process.env.TEMPORAL_NAMESPACE ?? "default" }));
  return globalForTemporal.temporalClient;
}
```

```ts
// src/app/api/orders/route.ts
import { WorkflowExecutionAlreadyStartedError } from "@temporalio/client";
import { NextResponse } from "next/server";
import { getTemporalClient } from "@/temporal/client";
import { TASK_QUEUE, type OrderInput } from "@/temporal/shared";
import { orderWorkflow } from "@/temporal/workflows";

export const runtime = "nodejs"; // the Temporal client needs Node, not the Edge runtime

export async function POST(request: Request) {
  const input = (await request.json()) as OrderInput; // validate (e.g. zod) in real code
  const client = await getTemporalClient();
  try {
    const handle = await client.workflow.start(orderWorkflow, {
      taskQueue: TASK_QUEUE,
      workflowId: `order-${input.orderId}`,
      args: [input],
    });
    return NextResponse.json({ workflowId: handle.workflowId, runId: handle.firstExecutionRunId }, { status: 202 });
  } catch (err) {
    if (err instanceof WorkflowExecutionAlreadyStartedError) {
      return NextResponse.json({ workflowId: `order-${input.orderId}` }, { status: 409 });
    }
    throw err;
  }
}
```

Interacting with a running workflow:

```ts
const handle = client.workflow.getHandle(`order-${id}`);
await handle.signal(cancelSignal, "customer request");
const status = await handle.query(statusQuery);
const result = await handle.executeUpdate(approveUpdate, { args: ["alice"] });
const final = await handle.result(); // waits for completion
```

Next.js notes:
- Importing a workflow function in a route is fine for typing `start`. Alternatively start by name:
  `client.workflow.start("orderWorkflow", ...)`.
- If bundling `@temporalio/client` causes build errors, add it to `serverExternalPackages` in
  `next.config.ts` (`experimental.serverComponentsExternalPackages` on Next.js 14).
- Never create a `Worker` inside Next.js (route handlers, server actions, `instrumentation.ts`).
- Return `202 Accepted` plus the workflow ID for long processes; poll a status route or use the query.

## Testing

```ts
// tests/temporal/order.test.ts
import { TestWorkflowEnvironment } from "@temporalio/testing";
import { Worker } from "@temporalio/worker";
import { orderWorkflow } from "../../src/temporal/workflows";
import { approveUpdate } from "../../src/temporal/shared";

let env: TestWorkflowEnvironment;
beforeAll(async () => { env = await TestWorkflowEnvironment.createTimeSkipping(); });
afterAll(async () => { await env?.teardown(); });

test("charges and emails after approval", async () => {
  const calls: string[] = [];
  const worker = await Worker.create({
    connection: env.nativeConnection,
    taskQueue: "test",
    workflowsPath: require.resolve("../../src/temporal/workflows"),
    activities: {
      chargeCard: async () => { calls.push("charge"); return "ch_1"; },
      sendEmail: async () => { calls.push("email"); },
    },
  });
  const status = await worker.runUntil(async () => {
    const handle = await env.client.workflow.start(orderWorkflow, {
      taskQueue: "test", workflowId: "order-test-1",
      args: [{ orderId: "1", amountCents: 1000, email: "a@b.c" }],
    });
    await handle.executeUpdate(approveUpdate, { args: ["alice"] });
    return handle.result();
  });
  expect(status).toBe("paid");
  expect(calls).toEqual(["charge", "email"]);
});
```

- Time-skipping environment: `sleep("1 minute")` and `condition(..., "24 hours")` complete instantly.
- Test activities alone with `MockActivityEnvironment` from `@temporalio/testing`.
- Cover: happy path, timeout/cancel branch, non-retryable failure, and retry of a transient error.

## Checklist before saying "done"

- [ ] Workflow files import only `@temporalio/workflow`, shared definitions and `import type` activities.
- [ ] Every activity has `startToCloseTimeout` and a deliberate retry policy; business errors are non-retryable.
- [ ] Activities are idempotent (idempotency key, upsert or existence check).
- [ ] `workflowId` is deterministic from business data; duplicate starts are handled.
- [ ] The worker runs as a separate process; Next.js routes use the cached client and `runtime = "nodejs"`.
- [ ] Tests run on `TestWorkflowEnvironment` with mocked activities; `tsc --noEmit` and lint pass.
- [ ] Demonstrate durability: kill the worker mid-workflow, restart it, show it resumes (Web UI at :8233).

## Common errors

| Symptom | Cause | Fix |
|---|---|---|
| `Workflow bundle` / `Module not found` when the worker starts | Workflow imports a Node module or activity implementation | Move the I/O to an activity; use `import type` |
| `Nondeterminism error` after a code change | Running executions replay new code | `patched()` / new workflow type; reset in dev |
| Workflow stuck in "Running", nothing happens | No worker on that task queue, or a different namespace | Start the worker; check `taskQueue` and `namespace` match |
| Activity retries forever | No `maximumAttempts`, or a business error thrown as retryable | Set the retry policy; throw `ApplicationFailure.nonRetryable` |
| `ECONNREFUSED 127.0.0.1:7233` | Temporal dev server not running | `temporal server start-dev` |
| Route works in dev, breaks on Edge | Temporal client on the Edge runtime | `export const runtime = "nodejs"` |
