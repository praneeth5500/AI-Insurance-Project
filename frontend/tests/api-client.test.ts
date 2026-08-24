import { afterEach, describe, expect, it, vi } from "vitest";

import { getReadiness, requestJson } from "@/lib/api/client";

function mockFetch(response: Partial<Response> & { json: () => Promise<unknown> }) {
  const fetchMock = vi.fn().mockResolvedValue({ ok: true, status: 200, ...response });
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

afterEach(() => {
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

describe("requestJson", () => {
  it("returns success with the parsed body", async () => {
    mockFetch({ json: async () => ({ status: "ready" }) });

    const result = await requestJson<{ status: string }>("/health/ready");

    expect(result.status).toBe("success");
    if (result.status === "success") {
      expect(result.data.status).toBe("ready");
    }
  });

  it("surfaces the API error envelope unchanged", async () => {
    mockFetch({
      ok: false,
      status: 503,
      json: async () => ({
        error: {
          code: "SERVICE_UNAVAILABLE",
          message: "The service is temporarily unavailable. Please try again shortly.",
          retryable: true,
          requestId: "req_abc123",
        },
      }),
    });

    const result = await requestJson("/health/ready");

    expect(result.status).toBe("error");
    if (result.status === "error") {
      expect(result.error.code).toBe("SERVICE_UNAVAILABLE");
      expect(result.error.retryable).toBe(true);
      expect(result.error.requestId).toBe("req_abc123");
    }
  });

  it("reports a retryable network error when the request cannot be sent", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new Error("ECONNREFUSED 10.0.0.5:8000")));

    const result = await requestJson("/health/ready");

    expect(result.status).toBe("error");
    if (result.status === "error") {
      expect(result.error.code).toBe("NETWORK_UNAVAILABLE");
      expect(result.error.retryable).toBe(true);
      // The underlying reason can name internal hosts and must not be shown.
      expect(result.error.message).not.toContain("10.0.0.5");
    }
  });

  it("does not trust a malformed error body", async () => {
    mockFetch({ ok: false, status: 500, json: async () => ({ oops: true }) });

    const result = await requestJson("/health/ready");

    expect(result.status).toBe("error");
    if (result.status === "error") {
      expect(result.error.code).toBe("UNEXPECTED_RESPONSE");
    }
  });

  it("handles a non-JSON response", async () => {
    mockFetch({
      ok: true,
      status: 200,
      json: async () => {
        throw new Error("Unexpected token < in JSON");
      },
    });

    const result = await requestJson("/health/ready");

    expect(result.status).toBe("error");
    if (result.status === "error") {
      expect(result.error.code).toBe("UNEXPECTED_RESPONSE");
    }
  });
});

describe("getReadiness", () => {
  it("requests the readiness endpoint without caching", async () => {
    const fetchMock = mockFetch({
      json: async () => ({ status: "ready", dependencies: { database: "ok" } }),
    });

    await getReadiness();

    const [url, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(url).toContain("/health/ready");
    expect(init.cache).toBe("no-store");
  });
});
