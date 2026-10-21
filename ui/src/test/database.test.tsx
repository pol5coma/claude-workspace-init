import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import type { Messages, Organization } from "../api";
import { Directory } from "../lib/people";
import { Database } from "../views/Database";
import actors from "./fixtures/actors.json";
import db from "./fixtures/db.json";
import events from "./fixtures/events.json";
import messages from "./fixtures/messages.json";
import organization from "./fixtures/organization.json";

const responses: Record<string, unknown> = { "/db": db, "/db/events": events, "/db/actors": actors };

afterEach(() => vi.unstubAllGlobals());

describe("Database view", () => {
  it("switches tables without rendering one table's rows with another's columns", async () => {
    // Slow responses: the previous table's rows must not be reused while the next one loads.
    vi.stubGlobal(
      "fetch",
      vi.fn(async (url: string) => {
        await new Promise((resolve) => setTimeout(resolve, 30));
        const path = url.replace(/^\/api\/runs\/[^/]+/, "");
        return new Response(JSON.stringify(responses[path] ?? []), { status: 200 });
      }),
    );
    const directory = new Directory(
      (organization as unknown as Organization).definitions,
      (messages as unknown as Messages).actors,
    );
    render(
      <QueryClientProvider client={new QueryClient()}>
        <Database runId="run" pulse="1" directory={directory} />
      </QueryClientProvider>,
    );
    expect(await screen.findByText("run_created")).toBeTruthy();
    fireEvent.click(screen.getByText("spado_actors"));
    expect(screen.getByText("Loading…")).toBeTruthy();
    expect(await screen.findByText("orchestrator")).toBeTruthy();
    fireEvent.click(screen.getByText("spado_events"));
    expect(await screen.findByText("run_created")).toBeTruthy();
  });
});
