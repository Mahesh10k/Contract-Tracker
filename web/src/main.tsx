import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import App from "./App";
import { httpApi } from "./api";
import "./design/variants/1-ledger.css";
import "./index.css";
import { mockApi, slow } from "./mockApi";

// 1-ledger is the chosen direction (docs/design/variants/react-ui/approved.json). In development
// only, ?variant=2-panel|3-grid renders the other directions and ?mock=1 uses sample data.
const params = new URLSearchParams(window.location.search);
const alternatives = import.meta.env.DEV
  ? import.meta.glob("./design/variants/*.css")
  : ({} as Record<string, () => Promise<unknown>>);
const requested = params.get("variant");
const load = requested ? alternatives[`./design/variants/${requested}.css`] : undefined;
document.documentElement.dataset.variant = requested && load ? requested : "1-ledger";
const useMock = import.meta.env.DEV && params.has("mock");
const delay = Number(params.get("delay") ?? 0);

void (load ? load() : Promise.resolve()).then(() => {
  createRoot(document.getElementById("root")!).render(
    <StrictMode>
      <App api={useMock ? (delay > 0 ? slow(mockApi, delay) : mockApi) : httpApi} />
    </StrictMode>,
  );
});
