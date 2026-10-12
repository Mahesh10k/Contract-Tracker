// The only place the browser talks to the server. Shapes mirror app/api/ui/schemas.py.

export type Contract = {
  id: string;
  title: string;
  contract_type: "lease" | "vendor" | "service";
  source_filename: string;
};

export type FieldStatus = "accepted" | "needs_review" | "corrected";

export type Field = {
  field: string;
  value: string | null;
  quote: string | null;
  clause: string | null;
  status: FieldStatus;
  review_reason: string | null;
};

export type Deadline = {
  contract: string;
  kind: "expiry" | "notice_deadline";
  due: string; // ISO date
  days_left: number;
  clause: string | null;
};

export type HeldField = {
  contract: string;
  field: string;
  value: string | null;
  quote: string | null;
  reason: string;
};

export type Citation = { contract: string; clause: string; text: string };
export type Answer = { text: string; citations: Citation[]; refused: boolean };

export type User = { email: string };

export interface Api {
  me(): Promise<User>;
  login(email: string, password: string): Promise<User>;
  logout(): Promise<void>;
  contracts(): Promise<Contract[]>;
  upload(file: File, contractType: Contract["contract_type"]): Promise<string>;
  loadGolden(): Promise<string[]>;
  fields(contractId: string): Promise<Field[]>;
  extract(contractId: string): Promise<string>;
  deadlines(today: string): Promise<Deadline[]>;
  review(): Promise<HeldField[]>;
  ask(question: string): Promise<Answer>;
  sendReminders(today: string): Promise<string>;
}

export class ApiError extends Error {
  /** The HTTP status when the server answered, 0 when it could not be reached. */
  readonly status: number;

  constructor(message: string, status = 0) {
    super(message);
    this.status = status;
  }
}

/**
 * Wraps every call so a 401 from the server (the session ended) runs `onExpired` once and still
 * reaches the panel that asked. Login and logout answer their own errors, so they are left alone.
 */
export function guard(api: Api, onExpired: () => void): Api {
  const own = new Set<keyof Api>(["me", "login", "logout"]);
  const wrapped = {} as Record<string, unknown>;
  for (const name of Object.keys(api) as (keyof Api)[]) {
    const original = api[name] as (...args: unknown[]) => Promise<unknown>;
    wrapped[name] = own.has(name)
      ? original
      : async (...args: unknown[]) => {
          try {
            return await original(...args);
          } catch (error) {
            if (error instanceof ApiError && error.status === 401) onExpired();
            throw error;
          }
        };
  }
  return wrapped as unknown as Api;
}

async function call<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`/api${path}`, init);
  } catch {
    throw new ApiError("The server is not reachable. Start it with make ui, then reload.");
  }
  if (!response.ok) {
    const body = (await response.json().catch(() => null)) as { error?: { message?: string } } | null;
    throw new ApiError(body?.error?.message ?? `The server answered ${response.status}.`, response.status);
  }
  return (await response.json()) as T;
}

const json = (body: unknown): RequestInit => ({
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify(body),
});

export const httpApi: Api = {
  me: () => call("/auth/me"),
  login: (email, password) => call("/auth/login", json({ email, password })),
  logout: async () => {
    await call("/auth/logout", { method: "POST" });
  },
  contracts: () => call("/contracts"),
  upload: async (file, contractType) => {
    const form = new FormData();
    form.append("file", file);
    form.append("contract_type", contractType);
    return (await call<{ message: string }>("/contracts", { method: "POST", body: form })).message;
  },
  loadGolden: async () => (await call<{ loaded: string[] }>("/contracts/golden", { method: "POST" })).loaded,
  fields: (id) => call(`/contracts/${id}/fields`),
  extract: async (id) => (await call<{ message: string }>(`/contracts/${id}/extract`, { method: "POST" })).message,
  deadlines: (today) => call(`/deadlines?today=${today}`),
  review: () => call("/review"),
  ask: (question) => call("/ask", json({ question })),
  sendReminders: async (today) => (await call<{ message: string }>("/reminders/send", json({ today }))).message,
};
