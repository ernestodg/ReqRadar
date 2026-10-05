import React from "react";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const mockAuth = vi.hoisted(() => {
  const state = {
    session: null as null | { access_token: string; user: { id: string; email?: string } },
    sessionPromise: null as null | Promise<{ data: { session: null }; error: null }>,
    authCallback: null as null | ((_event: string, session: null | { access_token: string; user: { id: string; email?: string } }) => void),
    signInResult: { data: { session: { access_token: "token-1", user: { id: "user-1", email: "user@example.com" } } }, error: null as null | { message: string } },
    signUpResult: { data: { session: null }, error: null as null | { message: string } },
  };
  const supabase = {
    auth: {
      getSession: vi.fn(() => state.sessionPromise ?? Promise.resolve({ data: { session: state.session }, error: null })),
      onAuthStateChange: vi.fn((callback) => {
        state.authCallback = callback;
        return { data: { subscription: { unsubscribe: vi.fn() } } };
      }),
      signInWithPassword: vi.fn(() => Promise.resolve(state.signInResult)),
      signUp: vi.fn(() => Promise.resolve(state.signUpResult)),
      signOut: vi.fn(() => Promise.resolve({ error: null })),
    },
  };
  return { state, supabase };
});

vi.mock("../src/lib/config", () => ({
  apiUrl: "http://api.test",
  frontendConfig: {
    apiUrl: "http://api.test",
    supabaseUrl: "https://example.supabase.co",
    supabaseAnonKey: "anon",
    authEnabled: true,
    authConfigError: null,
    isDevelopment: false,
  },
}));

vi.mock("../src/lib/supabase", () => ({ supabase: mockAuth.supabase }));

import { request } from "../src/lib/api";
import { App } from "../src/main";

function mockProjectsResponse(status = 200) {
  vi.stubGlobal("fetch", vi.fn(() => Promise.resolve({
    ok: status >= 200 && status < 300,
    status,
    statusText: status === 401 ? "Unauthorized" : "OK",
    json: () => Promise.resolve(status === 401 ? { error: { message: "Unauthorized" } } : []),
  })));
}

beforeEach(() => {
  mockAuth.state.session = null;
  mockAuth.state.sessionPromise = null;
  mockAuth.state.authCallback = null;
  mockAuth.state.signInResult = { data: { session: { access_token: "token-1", user: { id: "user-1", email: "user@example.com" } } }, error: null };
  mockAuth.state.signUpResult = { data: { session: null }, error: null };
  vi.clearAllMocks();
  mockProjectsResponse();
});

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

describe("frontend Supabase auth", () => {
  it("shows an auth loading state", () => {
    mockAuth.state.sessionPromise = new Promise(() => undefined);
    render(<App />);
    expect(screen.getByText("Checking your session...")).toBeInTheDocument();
  });

  it("renders auth UI when unauthenticated", async () => {
    render(<App />);
    expect(await screen.findAllByRole("button", { name: "Log in" })).toHaveLength(2);
    expect(screen.getByRole("button", { name: "Create account" })).toBeInTheDocument();
    expect(screen.getByLabelText("Email")).toBeInTheDocument();
    expect(screen.getByLabelText("Password")).toBeInTheDocument();
  });

  it("renders the application when authenticated", async () => {
    mockAuth.state.session = { access_token: "token-1", user: { id: "user-1", email: "user@example.com" } };
    render(<App />);
    expect(await screen.findByTestId("project-name")).toBeInTheDocument();
    expect(screen.getByText("user@example.com")).toBeInTheDocument();
  });

  it("handles sign-in success", async () => {
    render(<App />);
    fireEvent.change(await screen.findByLabelText("Email"), { target: { value: "user@example.com" } });
    fireEvent.change(screen.getByLabelText("Password"), { target: { value: "secret123" } });
    fireEvent.click(screen.getAllByRole("button", { name: "Log in" }).at(-1)!);
    await waitFor(() => expect(mockAuth.supabase.auth.signInWithPassword).toHaveBeenCalledWith({ email: "user@example.com", password: "secret123" }));
  });

  it("shows sign-in failure messages", async () => {
    mockAuth.state.signInResult = { data: { session: null }, error: { message: "Invalid login credentials" } };
    render(<App />);
    fireEvent.change(await screen.findByLabelText("Email"), { target: { value: "user@example.com" } });
    fireEvent.change(screen.getByLabelText("Password"), { target: { value: "wrongpass" } });
    fireEvent.click(screen.getAllByRole("button", { name: "Log in" }).at(-1)!);
    expect(await screen.findByRole("alert")).toHaveTextContent("Invalid login credentials");
  });

  it("shows signup confirmation when email verification is required", async () => {
    render(<App />);
    fireEvent.click(await screen.findByRole("button", { name: "Create account" }));
    fireEvent.change(screen.getByLabelText("Email"), { target: { value: "new@example.com" } });
    fireEvent.change(screen.getByLabelText("Password"), { target: { value: "secret123" } });
    fireEvent.click(screen.getAllByRole("button", { name: "Create account" }).at(-1)!);
    expect(await screen.findByRole("status")).toHaveTextContent("Check your email");
    expect(mockAuth.supabase.auth.signUp).toHaveBeenCalledWith({ email: "new@example.com", password: "secret123" });
  });

  it("logs out authenticated users", async () => {
    mockAuth.state.session = { access_token: "token-1", user: { id: "user-1", email: "user@example.com" } };
    render(<App />);
    fireEvent.click(await screen.findByRole("button", { name: /sign out/i }));
    await waitFor(() => expect(mockAuth.supabase.auth.signOut).toHaveBeenCalled());
  });

  it("attaches a Bearer access token to API requests", async () => {
    mockAuth.state.session = { access_token: "token-1", user: { id: "user-1" } };
    await request("/projects");
    const fetchMock = vi.mocked(fetch);
    const headers = fetchMock.mock.calls[0][1]?.headers as Headers;
    expect(headers.get("authorization")).toBe("Bearer token-1");
  });

  it("signs out on API 401 responses", async () => {
    mockAuth.state.session = { access_token: "token-1", user: { id: "user-1" } };
    mockProjectsResponse(401);
    await expect(request("/projects")).rejects.toThrow("session expired");
    expect(mockAuth.supabase.auth.signOut).toHaveBeenCalled();
  });
});
