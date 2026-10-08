import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import App from "./App";
import { ApiError, type Api } from "./api";
import { mockApi } from "./mockApi";

const open = (overrides: Partial<Api> = {}) => {
  const api: Api = { ...mockApi, ...overrides };
  render(<App api={api} />);
  return { api, user: userEvent.setup() };
};

describe("the page", () => {
  it("TC-0115: has the five tabs in order", () => {
    open();

    const tabs = screen.getAllByRole("tab").map((t) => t.textContent);

    expect(tabs).toEqual(["Upload", "Contracts", "Deadlines", "Ask", "Needs review"]);
  });

  it("TC-0116: uploading a PDF with its type loads it", async () => {
    const upload = vi.fn().mockResolvedValue("lease-01.pdf");
    const { user } = open({ upload });
    const file = new File(["%PDF-1.4"], "lease-01.pdf", { type: "application/pdf" });

    await user.selectOptions(screen.getByLabelText("Contract type"), "lease");
    await user.upload(screen.getByLabelText("Contract PDF"), file);
    await user.click(screen.getByRole("button", { name: "Load contract" }));

    expect(upload).toHaveBeenCalledWith(file, "lease");
    expect(await screen.findByRole("status")).toHaveTextContent("Loaded lease-01.pdf");
  });

  it("TC-0117: a refused upload shows the reason and no success message", async () => {
    const upload = vi.fn().mockRejectedValue(new ApiError("No text found; scanned PDFs are not supported"));
    const { user } = open({ upload });

    await user.upload(screen.getByLabelText("Contract PDF"), new File(["x"], "scan.pdf", { type: "application/pdf" }));
    await user.click(screen.getByRole("button", { name: "Load contract" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("No text found; scanned PDFs are not supported");
    expect(screen.queryByRole("status")).not.toBeInTheDocument();
  });

  it("keeps Load contract disabled until a file is chosen", () => {
    open();

    expect(screen.getByRole("button", { name: "Load contract" })).toBeDisabled();
  });

  it("TC-0118: a contract shows its fields with value, quote and clause", async () => {
    const { user } = open();

    await user.click(screen.getByRole("tab", { name: "Contracts" }));
    const row = (await screen.findByRole("rowheader", { name: "Notice period" })).closest("tr")!;

    expect(within(row).getByText("not less than thirty days")).toBeInTheDocument();
    expect(within(row).getByText(/giving not less than thirty days written notice/)).toBeInTheDocument();
    expect(within(row).getByText("7")).toBeInTheDocument();
    expect(within(row).getByText("Accepted")).toBeInTheDocument();
  });

  it("TC-0119: a held field is marked with its reason", async () => {
    const { user } = open();

    await user.click(screen.getByRole("tab", { name: "Contracts" }));
    await user.selectOptions(await screen.findByLabelText("Contract"), "Supply Agreement 08");
    const row = (await screen.findAllByRole("rowheader", { name: "Auto renewal" }))[0].closest("tr")!;

    expect(within(row).getByText("Needs review: value missing")).toBeInTheDocument();
    expect(within(row).getByText("Not stated")).toBeInTheDocument();
  });

  it("TC-0120: deadlines are listed soonest first with contract and clause", async () => {
    const { user } = open();

    await user.click(screen.getByRole("tab", { name: "Deadlines" }));
    const rows = await screen.findAllByRole("row");

    expect(within(rows[1]).getByText("Lease Agreement 01")).toBeInTheDocument();
    expect(within(rows[1]).getByText("Notice deadline")).toBeInTheDocument();
    expect(within(rows[1]).getByText("1 Dec 2026")).toBeInTheDocument();
    expect(within(rows[2]).getByText("Contract expires")).toBeInTheDocument();
  });

  it("TC-0122: an answer shows each citation with its clause text", async () => {
    const ask = vi.fn().mockResolvedValue({
      text: "Thirty days written notice.",
      refused: false,
      citations: [{ contract: "Lease Agreement 01", clause: "7", text: "Either party may end this Lease at expiry." }],
    });
    const { user } = open({ ask });

    await user.click(screen.getByRole("tab", { name: "Ask" }));
    await user.type(screen.getByLabelText("Question about the loaded contracts"), "What notice does lease 01 need?");
    await user.click(screen.getByRole("button", { name: "Ask" }));

    expect(await screen.findByText("Thirty days written notice.")).toBeInTheDocument();
    expect(screen.getByText("Lease Agreement 01, clause 7")).toBeInTheDocument();
    expect(screen.getByText("Either party may end this Lease at expiry.")).toBeInTheDocument();
  });

  it("shows the server's message when a question cannot be answered", async () => {
    const ask = vi.fn().mockRejectedValue(new ApiError("Questions cannot be answered right now."));
    const { user } = open({ ask });

    await user.click(screen.getByRole("tab", { name: "Ask" }));
    await user.type(screen.getByLabelText("Question about the loaded contracts"), "Who pays?");
    await user.click(screen.getByRole("button", { name: "Ask" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("Questions cannot be answered right now.");
  });

  it("TC-0123: needs review lists each held field with its reason", async () => {
    const { user } = open();

    await user.click(screen.getByRole("tab", { name: "Needs review" }));
    const row = (await screen.findByRole("rowheader", { name: "Services Agreement 02" })).closest("tr")!;

    expect(within(row).getByText("Notice period")).toBeInTheDocument();
    expect(within(row).getByText("Could not parse")).toBeInTheDocument();
  });

  it("TC-0124: an empty review queue says so", async () => {
    const { user } = open({ review: () => Promise.resolve([]) });

    await user.click(screen.getByRole("tab", { name: "Needs review" }));

    expect(await screen.findByText("Nothing is waiting for review.")).toBeInTheDocument();
  });

  it("shows the empty state before any contract is loaded", async () => {
    const { user } = open({ contracts: () => Promise.resolve([]) });

    await user.click(screen.getByRole("tab", { name: "Contracts" }));

    expect(await screen.findByText("No contracts loaded yet")).toBeInTheDocument();
  });

  it("send due reminders reports the count", async () => {
    const { user } = open({ sendReminders: () => Promise.resolve("2 reminders sent") });

    await user.click(screen.getByRole("tab", { name: "Deadlines" }));
    await user.click(screen.getByRole("button", { name: "Send due reminders" }));

    expect(await screen.findByRole("status")).toHaveTextContent("2 reminders sent");
  });

  it("TC-0181: disables Send due reminders while the request runs and sends it only once", async () => {
    let finish: (message: string) => void = () => {};
    const sendReminders = vi.fn().mockReturnValue(new Promise<string>((resolve) => (finish = resolve)));
    const { user } = open({ sendReminders });

    await user.click(screen.getByRole("tab", { name: "Deadlines" }));
    const button = await screen.findByRole("button", { name: "Send due reminders" });
    await user.click(button);
    await user.click(button);

    expect(button).toBeDisabled();
    expect(button).toHaveAttribute("aria-busy", "true");
    expect(sendReminders).toHaveBeenCalledTimes(1);
    finish("1 reminder sent");
    expect(await screen.findByRole("status")).toHaveTextContent("1 reminder sent");
    expect(button).toBeEnabled();
  });

  it("disables Extract fields while it runs so an uncached contract is not paid for twice", async () => {
    let finish: (message: string) => void = () => {};
    const extract = vi.fn().mockReturnValue(new Promise<string>((resolve) => (finish = resolve)));
    const { user } = open({ extract });

    await user.click(screen.getByRole("tab", { name: "Contracts" }));
    const button = await screen.findByRole("button", { name: "Extract fields" });
    await user.click(button);
    await user.click(button);

    expect(extract).toHaveBeenCalledTimes(1);
    finish("5 accepted, 0 need review");
    expect(await screen.findByRole("status")).toBeInTheDocument();
  });
});

describe("the theme switch", () => {
  it("sets data-theme on the page and remembers the choice", async () => {
    localStorage.removeItem("theme");
    const { user } = open();

    expect(document.documentElement.dataset.theme).toBe("light");
    await user.click(screen.getByRole("button", { name: "Dark theme" }));

    expect(document.documentElement.dataset.theme).toBe("dark");
    expect(localStorage.getItem("theme")).toBe("dark");
    localStorage.removeItem("theme");
  });

  it("starts dark when the stored choice is dark", () => {
    localStorage.setItem("theme", "dark");
    open();

    expect(document.documentElement.dataset.theme).toBe("dark");
    localStorage.removeItem("theme");
  });
});
