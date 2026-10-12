import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import App from "./App";
import { ApiError, type Api } from "./api";
import { validateLogin } from "./login";
import { mockApi } from "./mockApi";

const signedOut = () => Promise.reject(new ApiError("Sign in to continue.", 401));

const openSignedOut = async (overrides: Partial<Api> = {}) => {
  const api: Api = { ...mockApi, me: signedOut, ...overrides };
  render(<App api={api} />);
  await screen.findByRole("heading", { name: "Sign in" });
  return { api, user: userEvent.setup() };
};

const fill = async (user: ReturnType<typeof userEvent.setup>, email: string, password: string) => {
  if (email) await user.type(screen.getByLabelText("Email"), email);
  if (password) await user.type(screen.getByLabelText("Password"), password);
};

describe("validateLogin", () => {
  it("TC-0204: accepts a trimmed email and a password", () => {
    expect(validateLogin("  owner@example.com ", "x")).toEqual({});
  });

  it("TC-0204: names what is wrong with each field", () => {
    expect(validateLogin("", "")).toEqual({ email: "Enter your email address.", password: "Enter your password." });
    expect(validateLogin("owner", "x").email).toBe("Enter a valid email address.");
    expect(validateLogin("a@b", "x").email).toBe("Enter a valid email address.");
    expect(validateLogin("a@b.co", "x".repeat(129)).password).toMatch(/at most 128/);
    expect(validateLogin(`${"x".repeat(250)}@a.co`, "x").email).toBe("Enter a valid email address.");
  });
});

describe("the login page", () => {
  it("shows the login page, not the app, when nobody is signed in", async () => {
    await openSignedOut();

    expect(screen.queryByRole("tab")).not.toBeInTheDocument();
    expect(screen.getByLabelText("Email")).toHaveFocus();
  });

  it("TC-0204: an empty form is refused with a message under each field and no request", async () => {
    const login = vi.fn();
    const { user } = await openSignedOut({ login });

    await user.click(screen.getByRole("button", { name: "Sign in" }));

    expect(screen.getByText("Enter your email address.")).toBeInTheDocument();
    expect(screen.getByText("Enter your password.")).toBeInTheDocument();
    expect(screen.getByLabelText("Email")).toHaveAttribute("aria-invalid", "true");
    expect(screen.getByLabelText("Email")).toHaveFocus();
    expect(login).not.toHaveBeenCalled();
  });

  it("TC-0204: a malformed email is flagged when the field is left and cleared once fixed", async () => {
    const { user } = await openSignedOut();

    await user.type(screen.getByLabelText("Email"), "owner@");
    await user.tab();
    expect(screen.getByText("Enter a valid email address.")).toBeInTheDocument();

    await user.type(screen.getByLabelText("Email"), "example.com");
    expect(screen.queryByText("Enter a valid email address.")).not.toBeInTheDocument();
  });

  it("TC-0205: a correct login sends the trimmed email and opens the app", async () => {
    const login = vi.fn().mockResolvedValue({ email: "owner@example.com" });
    const { user } = await openSignedOut({ login });

    await fill(user, "  owner@example.com ", "right-password-1");
    await user.click(screen.getByRole("button", { name: "Sign in" }));

    expect(login).toHaveBeenCalledWith("owner@example.com", "right-password-1");
    expect(await screen.findByRole("tab", { name: "Upload" })).toBeInTheDocument();
    expect(screen.getByText("owner@example.com")).toBeInTheDocument();
  });

  it("TC-0205: a refused login shows the server's one message, clears the password and keeps the page", async () => {
    const message = "Wrong email or password, or the account is locked for a few minutes.";
    const login = vi.fn().mockRejectedValue(new ApiError(message, 401));
    const { user } = await openSignedOut({ login });

    await fill(user, "owner@example.com", "wrong-password");
    await user.click(screen.getByRole("button", { name: "Sign in" }));

    expect(await screen.findByRole("alert")).toHaveTextContent(message);
    expect(screen.getByLabelText("Password")).toHaveValue("");
    expect(screen.getByLabelText("Password")).toHaveFocus();
    expect(screen.queryByRole("tab")).not.toBeInTheDocument();
  });

  it("TC-0205: while the request runs the button is busy, a progress bar shows and a second press sends nothing", async () => {
    let finish!: (user: { email: string }) => void;
    const login = vi.fn(() => new Promise<{ email: string }>((resolve) => (finish = resolve)));
    const { user } = await openSignedOut({ login });

    await fill(user, "owner@example.com", "right-password-1");
    await user.click(screen.getByRole("button", { name: "Sign in" }));
    await user.click(screen.getByRole("button", { name: "Sign in" }));

    expect(screen.getByRole("progressbar", { name: "Signing in" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Sign in" })).toBeDisabled();
    expect(login).toHaveBeenCalledTimes(1);
    finish({ email: "owner@example.com" });
    expect(await screen.findByRole("tab", { name: "Upload" })).toBeInTheDocument();
  });

  it("shows and hides the password on request", async () => {
    const { user } = await openSignedOut();
    const field = screen.getByLabelText("Password");

    expect(field).toHaveAttribute("type", "password");
    await user.click(screen.getByRole("button", { name: "Show password" }));
    expect(field).toHaveAttribute("type", "text");
    await user.click(screen.getByRole("button", { name: "Hide password" }));
    expect(field).toHaveAttribute("type", "password");
  });
});

describe("the session", () => {
  it("TC-0206: a 401 from any call returns to the login page", async () => {
    const contracts = () => Promise.reject(new ApiError("Sign in to continue.", 401));
    render(<App api={{ ...mockApi, contracts }} />);
    const user = userEvent.setup();
    await user.click(await screen.findByRole("tab", { name: "Contracts" }));

    expect(await screen.findByRole("heading", { name: "Sign in" })).toBeInTheDocument();
    expect(screen.queryByRole("tab")).not.toBeInTheDocument();
  });

  it("TC-0206: other errors do not sign the user out", async () => {
    const contracts = () => Promise.reject(new ApiError("The server answered 500.", 500));
    render(<App api={{ ...mockApi, contracts }} />);
    const user = userEvent.setup();
    await user.click(await screen.findByRole("tab", { name: "Contracts" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("The server answered 500.");
    expect(screen.getByRole("tab", { name: "Contracts" })).toBeInTheDocument();
  });

  it("TC-0207: Log out calls the server and returns to the login page", async () => {
    const logout = vi.fn().mockResolvedValue(undefined);
    render(<App api={{ ...mockApi, logout }} />);
    const user = userEvent.setup();

    await user.click(await screen.findByRole("button", { name: "Log out" }));

    expect(logout).toHaveBeenCalledTimes(1);
    expect(await screen.findByRole("heading", { name: "Sign in" })).toBeInTheDocument();
  });

  it("TC-0207: Log out still returns to the login page when the server cannot be reached", async () => {
    const logout = vi.fn().mockRejectedValue(new ApiError("The server is not reachable."));
    render(<App api={{ ...mockApi, logout }} />);
    const user = userEvent.setup();

    await user.click(await screen.findByRole("button", { name: "Log out" }));

    expect(await screen.findByRole("heading", { name: "Sign in" })).toBeInTheDocument();
  });
});
