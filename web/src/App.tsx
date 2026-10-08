import { useEffect, useState } from "react";
import type { Api } from "./api";
import { localIso } from "./dates";
import { AskPanel, ContractsPanel, DeadlinesPanel, ReviewPanel, UploadPanel } from "./panels";

const TABS = ["Upload", "Contracts", "Deadlines", "Ask", "Needs review"] as const;
type Tab = (typeof TABS)[number];

const todayIso = () => localIso(new Date());

function useTheme() {
  const [dark, setDark] = useState(() => {
    try {
      const saved = localStorage.getItem("theme");
      if (saved) return saved === "dark";
    } catch {
      /* storage can be blocked; fall through to the system setting */
    }
    return window.matchMedia?.("(prefers-color-scheme: dark)").matches ?? false;
  });
  useEffect(() => {
    document.documentElement.dataset.theme = dark ? "dark" : "light";
    try {
      localStorage.setItem("theme", dark ? "dark" : "light");
    } catch {
      /* a blocked store only loses the remembered choice */
    }
  }, [dark]);
  return [dark, () => setDark((d) => !d)] as const;
}

export default function App({ api }: { api: Api }) {
  const [tab, setTab] = useState<Tab>("Upload");
  const [today, setToday] = useState(todayIso);
  const [version, setVersion] = useState(0);
  const [dark, toggleTheme] = useTheme();
  const changed = () => setVersion((v) => v + 1);

  return (
    <div data-slot="app">
      <div data-slot="shell">
        <header data-slot="masthead">
          <div data-slot="identity">
            <span data-slot="logo" aria-hidden="true">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
                <path d="M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8z" />
                <path d="M14 3v5h5" />
                <path d="M9 13h6" />
                <path d="M9 17h4" />
              </svg>
            </span>
            <div>
              <h1 data-slot="brand">ContractTracker</h1>
              <p data-slot="tagline">Every deadline, with the sentence that sets it.</p>
            </div>
          </div>
          <div data-slot="tools">
            <div data-slot="field-group">
              <label data-slot="label" htmlFor="today">Treat today as</label>
              <input id="today" data-slot="input" type="date" value={today} onChange={(e) => e.target.value && setToday(e.target.value)} />
            </div>
            <button data-slot="button" onClick={toggleTheme} aria-pressed={dark}>
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                <path d="M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8z" />
              </svg>
              {dark ? "Light theme" : "Dark theme"}
            </button>
          </div>
        </header>

        <nav data-slot="tablist" role="tablist" aria-label="Sections">
          {TABS.map((name) => (
            <button
              key={name}
              data-slot="tab"
              role="tab"
              id={`t-${name === "Needs review" ? "review" : name.toLowerCase()}`}
              aria-selected={tab === name}
              onClick={() => setTab(name)}
            >
              {name}
            </button>
          ))}
        </nav>

        <main>
          {tab === "Upload" && <UploadPanel api={api} onChanged={changed} />}
          {tab === "Contracts" && <ContractsPanel api={api} version={version} onChanged={changed} />}
          {tab === "Deadlines" && <DeadlinesPanel api={api} today={today} version={version} />}
          {tab === "Ask" && <AskPanel api={api} />}
          {tab === "Needs review" && <ReviewPanel api={api} version={version} />}
        </main>
      </div>
    </div>
  );
}
