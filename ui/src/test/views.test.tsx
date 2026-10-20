import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen } from "@testing-library/react";
import type { ReactNode } from "react";
import { describe, expect, it } from "vitest";
import type { Messages, Organization, Overview, RevisionMeta } from "../api";
import { Directory } from "../lib/people";
import { setTheme } from "../lib/theme";
import { COrganization } from "../views/COrganization";
import { Communication } from "../views/Communication";
import { Workflow } from "../views/Workflow";
import documents from "./fixtures/documents.json";
import messages from "./fixtures/messages.json";
import organization from "./fixtures/organization.json";
import overview from "./fixtures/overview.json";

const org = organization as unknown as Organization;
const msgs = messages as unknown as Messages;
const ov = overview as unknown as Overview;
const directory = new Directory(org.definitions, msgs.actors);

function wrap(children: ReactNode) {
  const client = new QueryClient();
  return render(
    <QueryClientProvider client={client}>
      <div style={{ width: 1200, height: 800 }}>{children}</div>
    </QueryClientProvider>,
  );
}

describe("views render the demo run", () => {
  it("C-Organization", () => {
    wrap(
      <COrganization
        overview={ov}
        org={org}
        messages={msgs}
        documents={documents as unknown as RevisionMeta[]}
        directory={directory}
        onOpenDocument={() => {}}
      />,
    );
    expect(screen.getByText("Whole organization", { exact: false })).toBeTruthy();
    expect(screen.getByText("reports to")).toBeTruthy();
  });

  it("C-Organization legend can be hidden", () => {
    wrap(
      <COrganization
        overview={ov}
        org={org}
        messages={msgs}
        documents={documents as unknown as RevisionMeta[]}
        directory={directory}
        onOpenDocument={() => {}}
      />,
    );
    fireEvent.click(screen.getByLabelText("Legend"));
    expect(screen.queryByText("reports to")).toBeNull();
    fireEvent.click(screen.getByLabelText("Legend"));
    expect(screen.getByText("reports to")).toBeTruthy();
  });

  it("Workflow", () => {
    wrap(<Workflow overview={ov} directory={directory} onOpenDocument={() => {}} />);
    expect(screen.getByText("Idea & Strategy")).toBeTruthy();
    expect(screen.getAllByText("Accepted").length).toBeGreaterThan(0);
  });

  it("Communication", () => {
    wrap(<Communication messages={msgs} directory={directory} />);
    expect(screen.getByRole("img", { name: "Sequence diagram" })).toBeTruthy();
    expect(screen.getByText(`${msgs.messages.length} messages`)).toBeTruthy();
  });
});

describe("theme", () => {
  it("applies the chosen theme to the document", () => {
    setTheme("dark");
    expect(document.documentElement.dataset.theme).toBe("dark");
    setTheme("light");
    expect(document.documentElement.dataset.theme).toBe("light");
  });
});
