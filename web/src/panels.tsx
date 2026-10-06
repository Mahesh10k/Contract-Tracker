import { useEffect, useRef, useState } from "react";
import type { Answer, Api, Contract, Deadline, Field, HeldField } from "./api";
import { Empty, formatDay, label, Notice, PanelHead, StatusBadge, type Message } from "./ui";

const fail = (error: unknown): Message => ({
  tone: "bad",
  text: error instanceof Error ? error.message : "Something went wrong.",
});

/** One request at a time per panel: a double click must not run the server work twice. */
function useBusy() {
  const [busy, setBusy] = useState(false);
  const running = useRef(false);
  const guard = async (work: () => Promise<void>) => {
    if (running.current) return;
    running.current = true;
    setBusy(true);
    try {
      await work();
    } finally {
      running.current = false;
      setBusy(false);
    }
  };
  return [busy, guard] as const;
}

export function UploadPanel({ api, onChanged }: { api: Api; onChanged: () => void }) {
  const [type, setType] = useState<Contract["contract_type"]>("lease");
  const [file, setFile] = useState<File | null>(null);
  const [message, setMessage] = useState<Message>(null);
  const [busy, guard] = useBusy();

  const run = (work: () => Promise<string>) =>
    guard(async () => {
      try {
        setMessage({ tone: "ok", text: await work() });
        onChanged();
      } catch (error) {
        setMessage(fail(error));
      }
    });

  return (
    <section data-slot="panel" role="tabpanel" aria-labelledby="t-upload">
      <PanelHead
        title="Upload a contract"
        lede="Text PDFs only. The type is yours to pick; scanned PDFs are refused with a reason."
      />
      <div data-slot="controls">
        <div data-slot="field-group">
          <label data-slot="label" htmlFor="upload-type">Contract type</label>
          <select
            id="upload-type"
            data-slot="select"
            value={type}
            onChange={(e) => setType(e.target.value as Contract["contract_type"])}
          >
            <option value="lease">Lease</option>
            <option value="vendor">Vendor agreement</option>
            <option value="service">Service agreement</option>
          </select>
        </div>
        <div data-slot="field-group">
          <label data-slot="label" htmlFor="upload-file">Contract PDF</label>
          <input
            id="upload-file"
            data-slot="input"
            type="file"
            accept="application/pdf"
            onChange={(e) => setFile(e.target.files?.[0] ?? null)}
          />
        </div>
        <button
          data-slot="button"
          data-primary
          disabled={!file || busy}
          aria-busy={busy}
          onClick={() => file && run(async () => `Loaded ${await api.upload(file, type)}`)}
        >
          Load contract
        </button>
      </div>
      <div data-slot="controls">
        <button
          data-slot="button"
          disabled={busy}
          aria-busy={busy}
          onClick={() => run(async () => `Loaded: ${(await api.loadGolden()).join(", ")}`)}
        >
          Load the 6 golden contracts
        </button>
        <span data-slot="panel-lede">The set the evals use, with their real titles.</span>
      </div>
      <Notice message={message} />
    </section>
  );
}

export function ContractsPanel({ api, version, onChanged }: { api: Api; version: number; onChanged: () => void }) {
  const [contracts, setContracts] = useState<Contract[]>([]);
  const [pickedId, setPickedId] = useState("");
  const [fields, setFields] = useState<Field[]>([]);
  const [message, setMessage] = useState<Message>(null);
  const picked = contracts.find((c) => c.id === pickedId) ?? contracts[0];
  const [busy, guard] = useBusy();

  useEffect(() => {
    api.contracts().then(setContracts).catch((e) => setMessage(fail(e)));
  }, [api, version]);

  const pickedKey = picked?.id;
  useEffect(() => {
    if (!pickedKey) return;
    api.fields(pickedKey).then(setFields).catch((e) => setMessage(fail(e)));
  }, [api, pickedKey, version]);

  const extract = () =>
    guard(async () => {
      if (!picked) return;
      try {
        setMessage({ tone: "ok", text: await api.extract(picked.id) });
        onChanged();
      } catch (error) {
        setMessage(fail(error));
      }
    });

  if (contracts.length === 0) {
    return (
      <section data-slot="panel" role="tabpanel" aria-labelledby="t-contracts">
        <PanelHead title="Contracts" lede="Every field comes with the sentence it was taken from." />
        <Notice message={message} />
        <Empty title="No contracts loaded yet">Use the Upload tab to load your first contract.</Empty>
      </section>
    );
  }

  return (
    <section data-slot="panel" role="tabpanel" aria-labelledby="t-contracts">
      <PanelHead title="Contracts" lede="Every field comes with the sentence it was taken from." />
      <div data-slot="controls">
        <div data-slot="field-group">
          <label data-slot="label" htmlFor="contract-pick">Contract</label>
          <select id="contract-pick" data-slot="select" value={picked?.id} onChange={(e) => setPickedId(e.target.value)}>
            {contracts.map((c) => (
              <option key={c.id} value={c.id}>{c.title}</option>
            ))}
          </select>
        </div>
        <button data-slot="button" data-primary disabled={busy} aria-busy={busy} onClick={extract}>
          Extract fields
        </button>
        <span data-slot="panel-lede">{picked?.contract_type}, loaded from {picked?.source_filename}</span>
      </div>
      <Notice message={message} />
      {fields.length === 0 ? (
        <Empty title="Not extracted yet">Press Extract fields to read this contract.</Empty>
      ) : (
        <div data-slot="table-wrap">
          <table data-slot="table">
            <thead>
              <tr><th>Field</th><th>Value</th><th>Quote</th><th>Clause</th><th>Status</th></tr>
            </thead>
            <tbody>
              {fields.map((f) => (
                <tr key={f.field}>
                  <th scope="row">{label(f.field)}</th>
                  <td>{f.value ?? "Not stated"}</td>
                  <td>{f.quote ? <blockquote data-slot="quote">{f.quote}</blockquote> : "No quote"}</td>
                  <td><span data-slot="clause">{f.clause ?? "none"}</span></td>
                  <td><StatusBadge status={f.status} reason={f.review_reason} /></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}

export function DeadlinesPanel({ api, today, version }: { api: Api; today: string; version: number }) {
  const [rows, setRows] = useState<Deadline[]>([]);
  const [message, setMessage] = useState<Message>(null);
  const [busy, guard] = useBusy();

  useEffect(() => {
    api.deadlines(today).then(setRows).catch((e) => setMessage(fail(e)));
  }, [api, today, version]);

  const send = () =>
    guard(async () => {
      try {
        setMessage({ tone: "ok", text: await api.sendReminders(today) });
      } catch (error) {
        setMessage(fail(error));
      }
    });

  return (
    <section data-slot="panel" role="tabpanel" aria-labelledby="t-deadlines">
      <PanelHead
        title="Deadlines"
        lede="Computed in code from accepted fields, soonest first. Held fields never produce a date."
      />
      <div data-slot="controls">
        <button data-slot="button" data-primary disabled={busy} aria-busy={busy} onClick={send}>
          Send due reminders
        </button>
        <span data-slot="panel-lede">Treating {formatDay(today)} as today.</span>
      </div>
      <Notice message={message} />
      {rows.length === 0 ? (
        <Empty title="No deadlines yet">Extract a contract that states an effective date and a term.</Empty>
      ) : (
        <div data-slot="table-wrap">
          <table data-slot="table">
            <thead>
              <tr><th>Contract</th><th>Deadline</th><th>Due</th><th className="num">Days left</th><th>Clause</th></tr>
            </thead>
            <tbody>
              {rows.map((r) => (
                <tr key={`${r.contract}-${r.kind}`}>
                  <th scope="row">{r.contract}</th>
                  <td>{r.kind === "expiry" ? "Contract expires" : "Notice deadline"}</td>
                  <td>{formatDay(r.due)}</td>
                  <td className="num">{r.days_left}</td>
                  <td><span data-slot="clause">{r.clause ?? "none"}</span></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}

export function AskPanel({ api }: { api: Api }) {
  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState<Answer | null>(null);
  const [message, setMessage] = useState<Message>(null);
  const [busy, guard] = useBusy();

  const ask = () =>
    guard(async () => {
      setMessage(null);
      try {
        setAnswer(await api.ask(question));
      } catch (error) {
        setAnswer(null);
        setMessage(fail(error));
      }
    });

  return (
    <section data-slot="panel" role="tabpanel" aria-labelledby="t-ask">
      <PanelHead
        title="Ask the contracts"
        lede="Answers come only from the clauses found for your question, each cited. If they do not answer it, you get “Not found in these contracts”."
      />
      <div data-slot="controls">
        <div data-slot="field-group">
          <label data-slot="label" htmlFor="ask-question">Question about the loaded contracts</label>
          <input
            id="ask-question"
            data-slot="input"
            style={{ minWidth: "min(32rem, 80vw)" }}
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
          />
        </div>
        <button
          data-slot="button"
          data-primary
          disabled={!question.trim() || busy}
          aria-busy={busy}
          onClick={ask}
        >
          Ask
        </button>
      </div>
      <Notice message={message} />
      {answer && (
        <div data-slot="answer">
          <p role={answer.refused ? "alert" : undefined}>{answer.text}</p>
          {answer.citations.map((c) => (
            <div data-slot="citation" key={`${c.contract}-${c.clause}`}>
              <cite>{c.contract}, clause {c.clause}</cite>
              <blockquote data-slot="quote">{c.text}</blockquote>
            </div>
          ))}
        </div>
      )}
    </section>
  );
}

export function ReviewPanel({ api, version }: { api: Api; version: number }) {
  const [rows, setRows] = useState<HeldField[] | null>(null);
  const [message, setMessage] = useState<Message>(null);

  useEffect(() => {
    api.review().then(setRows).catch((e) => setMessage(fail(e)));
  }, [api, version]);

  return (
    <section data-slot="panel" role="tabpanel" aria-labelledby="t-review">
      <PanelHead
        title="Needs review"
        lede="Fields the system would not trust: no quote found in the cited clause, or a value no parser could read."
      />
      <Notice message={message} />
      {rows && rows.length === 0 && <Empty title="Nothing is waiting for review.">Every extracted field has a checked quote.</Empty>}
      {rows && rows.length > 0 && (
        <div data-slot="table-wrap">
          <table data-slot="table">
            <thead>
              <tr><th>Contract</th><th>Field</th><th>Value</th><th>Quote</th><th>Reason</th></tr>
            </thead>
            <tbody>
              {rows.map((r) => (
                <tr key={`${r.contract}-${r.field}`}>
                  <th scope="row">{r.contract}</th>
                  <td>{label(r.field)}</td>
                  <td>{r.value ?? "Not stated"}</td>
                  <td>{r.quote ? <blockquote data-slot="quote">{r.quote}</blockquote> : "No quote"}</td>
                  <td><span data-slot="badge" data-tone="warn">{label(r.reason)}</span></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}
