import type { ReactNode } from "react";
import type { FieldStatus } from "./api";

export type Message = { tone: "ok" | "bad"; text: string } | null;

export function Notice({ message }: { message: Message }) {
  if (!message) return null;
  return (
    <p data-slot="notice" data-tone={message.tone} role={message.tone === "bad" ? "alert" : "status"}>
      {message.text}
    </p>
  );
}

export function Empty({ title, children }: { title: string; children: ReactNode }) {
  return (
    <div data-slot="empty">
      <strong>{title}</strong>
      {children}
    </div>
  );
}

export function PanelHead({ title, lede }: { title: string; lede: string }) {
  return (
    <header>
      <h2 data-slot="panel-title">{title}</h2>
      <p data-slot="panel-lede">{lede}</p>
    </header>
  );
}

export const label = (name: string) =>
  (name.charAt(0).toUpperCase() + name.slice(1)).replaceAll("_", " ");

export function StatusBadge({ status, reason }: { status: FieldStatus; reason: string | null }) {
  if (status === "needs_review") {
    return (
      <span data-slot="badge" data-tone="warn">
        Needs review{reason ? `: ${label(reason).toLowerCase()}` : ""}
      </span>
    );
  }
  return (
    <span data-slot="badge" data-tone="ok">
      {status === "corrected" ? "Corrected" : "Accepted"}
    </span>
  );
}

const day = new Intl.DateTimeFormat("en-GB", { day: "numeric", month: "short", year: "numeric", timeZone: "UTC" });
export const formatDay = (iso: string) => day.format(new Date(`${iso}T00:00:00Z`));

/** Placeholder rows shown while a panel's first request is in flight. The text is for screen readers. */
export function Skeleton({ what, rows = 4 }: { what: string; rows?: number }) {
  return (
    <div data-slot="skeleton" aria-busy="true">
      <span className="sr-only">Loading {what}</span>
      {Array.from({ length: rows }, (_, i) => (
        <div data-slot="skeleton-row" key={i} aria-hidden="true">
          <span />
          <span />
          <span />
        </div>
      ))}
    </div>
  );
}

/** An indeterminate bar for work with no known length (an upload, a model call). */
export function Progress({ label }: { label: string }) {
  return (
    <div data-slot="progress" role="progressbar" aria-label={label}>
      <span />
    </div>
  );
}

/** Shown in place of the answer while the question is being worked on. */
export function Thinking({ children }: { children: ReactNode }) {
  return (
    <div data-slot="thinking" aria-live="polite">
      <span data-slot="dots" aria-hidden="true">
        <i />
        <i />
        <i />
      </span>
      {children}
    </div>
  );
}
