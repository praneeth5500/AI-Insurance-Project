import { afterEach, describe, expect, it, vi } from "vitest";

import { track } from "@/lib/analytics/track";

afterEach(() => vi.unstubAllGlobals());

describe("track", () => {
  it("posts the event to the analytics endpoint", () => {
    const fetchMock = vi.fn().mockResolvedValue({ ok: true });
    vi.stubGlobal("fetch", fetchMock);

    track("match_opened", { position: 3 });

    expect(fetchMock).toHaveBeenCalledOnce();
    const [url, init] = fetchMock.mock.calls[0]!;
    expect(url).toContain("/api/v1/analytics/events");
    expect(JSON.parse(init.body as string)).toEqual({
      name: "match_opened",
      properties: { position: 3 },
    });
  });

  it("survives a navigation so an event on a link click is not lost", () => {
    const fetchMock = vi.fn().mockResolvedValue({ ok: true });
    vi.stubGlobal("fetch", fetchMock);

    track("match_opened", { position: 1 });

    expect(fetchMock.mock.calls[0]![1].keepalive).toBe(true);
  });

  it("never lets a failed measurement reach the caller", async () => {
    // A measurement that can fail a reader's action is worse than none.
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new Error("offline")));

    expect(() => track("home_viewed", {})).not.toThrow();
    await Promise.resolve();
  });
});
