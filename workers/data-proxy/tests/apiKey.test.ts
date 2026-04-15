// sb-t61h: unit tests for the API key auth helpers.
//
// We avoid the real WebCrypto digest by stubbing `sha256Impl` so each test
// owns a deterministic hash. The Supabase REST surface is replaced by a
// hand-rolled fetch double that asserts on URL + headers without spinning
// up MSW or hitting the network.

import { describe, expect, it, vi } from "vitest";
import {
  type ApiKeyConfig,
  RATE_LIMIT_PER_HOUR,
  authenticateApiKey,
  constantTimeEqual,
  countRecentSubmissions,
  isApiKey,
  lookupApiKey,
  lookupPrefix,
  sha256Hex,
  touchLastUsed,
} from "../src/apiKey";

const SUPABASE_URL = "https://test-project.supabase.co";
const SERVICE_ROLE = "service-role-secret";

const VALID_KEY = `sb_${"a".repeat(32)}`;
const VALID_PREFIX = "sb_aaaaa";

function fakeSha(value: string): string {
  // Deterministic but key-dependent stub — we only need stability + uniqueness
  // across the test cases, not a real cryptographic property.
  return `hash:${value}`;
}

function baseConfig(overrides: Partial<ApiKeyConfig> = {}): ApiKeyConfig {
  return {
    supabaseUrl: SUPABASE_URL,
    serviceRoleKey: SERVICE_ROLE,
    sha256Impl: async (s: string) => fakeSha(s),
    now: () => new Date("2026-04-15T12:00:00Z"),
    ...overrides,
  };
}

describe("isApiKey", () => {
  it("accepts well-formed sb_ keys", () => {
    expect(isApiKey(VALID_KEY)).toBe(true);
  });

  it("rejects JWT-shaped tokens", () => {
    expect(isApiKey("eyJhbGciOiJIUzI1NiJ9.payload.sig")).toBe(false);
  });

  it("rejects sb_ prefix with wrong body length", () => {
    expect(isApiKey("sb_short")).toBe(false);
    expect(isApiKey(`sb_${"a".repeat(31)}`)).toBe(false);
    expect(isApiKey(`sb_${"a".repeat(33)}`)).toBe(false);
  });

  it("rejects empty / unrelated tokens", () => {
    expect(isApiKey("")).toBe(false);
    expect(isApiKey("Bearer foo")).toBe(false);
  });
});

describe("lookupPrefix", () => {
  it("returns the first 8 chars", () => {
    expect(lookupPrefix(VALID_KEY)).toBe(VALID_PREFIX);
  });
});

describe("constantTimeEqual", () => {
  it("returns true for equal strings", () => {
    expect(constantTimeEqual("abc", "abc")).toBe(true);
  });
  it("returns false for differing strings of equal length", () => {
    expect(constantTimeEqual("abc", "abd")).toBe(false);
  });
  it("returns false for different lengths without throwing", () => {
    expect(constantTimeEqual("abc", "ab")).toBe(false);
  });
});

describe("sha256Hex", () => {
  it("produces a 64-char hex digest using WebCrypto", async () => {
    // Real subtle is available in node 20+ via global crypto.
    const out = await sha256Hex("hello");
    expect(out).toMatch(/^[0-9a-f]{64}$/);
    expect(out).toBe(
      // sha256("hello")
      "2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824",
    );
  });
});

describe("authenticateApiKey — happy path", () => {
  it("returns userId + keyId for a matching, in-scope, non-rate-limited key", async () => {
    const fetchMock = vi.fn(async (url: string | URL) => {
      const u = String(url);
      if (u.includes("/rest/v1/api_keys") && u.includes(`key_prefix=eq.${VALID_PREFIX}`)) {
        return new Response(
          JSON.stringify([
            {
              id: 7,
              user_id: "user-uuid",
              scope: "submit",
              expires_at: null,
              revoked_at: null,
              key_hash: fakeSha(VALID_KEY),
            },
          ]),
          { status: 200, headers: { "Content-Type": "application/json" } },
        );
      }
      if (u.includes("/rest/v1/submissions")) {
        // No prior submissions → empty list, count header reports zero.
        return new Response("[]", {
          status: 200,
          headers: { "Content-Range": "*/0", "Content-Type": "application/json" },
        });
      }
      throw new Error(`unexpected fetch ${u}`);
    });

    const auth = await authenticateApiKey(
      VALID_KEY,
      "submit",
      baseConfig({ fetchImpl: fetchMock }),
    );
    expect(auth.ok).toBe(true);
    if (auth.ok) {
      expect(auth.userId).toBe("user-uuid");
      expect(auth.keyId).toBe(7);
      expect(auth.scope).toBe("submit");
    }
  });

  it("accepts read scope when 'both' is granted", async () => {
    const fetchMock = vi.fn(async (url: string | URL) => {
      const u = String(url);
      if (u.includes("/rest/v1/api_keys")) {
        return new Response(
          JSON.stringify([
            {
              id: 1,
              user_id: "user-x",
              scope: "both",
              expires_at: null,
              revoked_at: null,
              key_hash: fakeSha(VALID_KEY),
            },
          ]),
          { status: 200 },
        );
      }
      return new Response("[]", { status: 200, headers: { "Content-Range": "*/0" } });
    });
    const res = await authenticateApiKey(VALID_KEY, "read", baseConfig({ fetchImpl: fetchMock }));
    expect(res.ok).toBe(true);
  });
});

describe("authenticateApiKey — failure modes", () => {
  it("rejects malformed tokens before hitting Supabase", async () => {
    const fetchMock = vi.fn();
    const res = await authenticateApiKey(
      "not-a-key",
      "submit",
      baseConfig({ fetchImpl: fetchMock }),
    );
    expect(res.ok).toBe(false);
    if (!res.ok) {
      expect(res.status).toBe(401);
      expect(res.reason).toMatch(/malformed/);
    }
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("returns 401 when prefix has no row", async () => {
    const fetchMock = vi.fn(async () => new Response("[]", { status: 200 }));
    const res = await authenticateApiKey(VALID_KEY, "submit", baseConfig({ fetchImpl: fetchMock }));
    expect(res.ok).toBe(false);
    if (!res.ok) expect(res.status).toBe(401);
  });

  it("returns 401 when the hash doesn't match the row", async () => {
    const fetchMock = vi.fn(
      async () =>
        new Response(
          JSON.stringify([
            {
              id: 1,
              user_id: "u",
              scope: "submit",
              expires_at: null,
              revoked_at: null,
              key_hash: "hash:WRONG",
            },
          ]),
          { status: 200 },
        ),
    );
    const res = await authenticateApiKey(VALID_KEY, "submit", baseConfig({ fetchImpl: fetchMock }));
    expect(res.ok).toBe(false);
    if (!res.ok) {
      expect(res.status).toBe(401);
      expect(res.reason).toMatch(/unknown/);
    }
  });

  it("returns 401 when the key is expired", async () => {
    const fetchMock = vi.fn(
      async () =>
        new Response(
          JSON.stringify([
            {
              id: 1,
              user_id: "u",
              scope: "submit",
              expires_at: "2025-01-01T00:00:00Z",
              revoked_at: null,
              key_hash: fakeSha(VALID_KEY),
            },
          ]),
          { status: 200 },
        ),
    );
    const res = await authenticateApiKey(VALID_KEY, "submit", baseConfig({ fetchImpl: fetchMock }));
    expect(res.ok).toBe(false);
    if (!res.ok) expect(res.reason).toMatch(/expired/);
  });

  it("returns 403 when scope is insufficient", async () => {
    const fetchMock = vi.fn(
      async () =>
        new Response(
          JSON.stringify([
            {
              id: 1,
              user_id: "u",
              scope: "read",
              expires_at: null,
              revoked_at: null,
              key_hash: fakeSha(VALID_KEY),
            },
          ]),
          { status: 200 },
        ),
    );
    const res = await authenticateApiKey(VALID_KEY, "submit", baseConfig({ fetchImpl: fetchMock }));
    expect(res.ok).toBe(false);
    if (!res.ok) {
      expect(res.status).toBe(403);
      expect(res.reason).toMatch(/scope/);
    }
  });

  it("returns 429 when the rate limit is exceeded", async () => {
    const fetchMock = vi.fn(async (url: string | URL) => {
      const u = String(url);
      if (u.includes("/rest/v1/api_keys")) {
        return new Response(
          JSON.stringify([
            {
              id: 1,
              user_id: "u",
              scope: "submit",
              expires_at: null,
              revoked_at: null,
              key_hash: fakeSha(VALID_KEY),
            },
          ]),
          { status: 200 },
        );
      }
      // 60 prior submissions in the last hour = at the ceiling.
      return new Response(JSON.stringify([]), {
        status: 200,
        headers: { "Content-Range": `*/${RATE_LIMIT_PER_HOUR}` },
      });
    });
    const res = await authenticateApiKey(VALID_KEY, "submit", baseConfig({ fetchImpl: fetchMock }));
    expect(res.ok).toBe(false);
    if (!res.ok) {
      expect(res.status).toBe(429);
      expect(res.reason).toMatch(/rate limit/);
    }
  });

  it("returns 502 when Supabase lookup throws", async () => {
    const fetchMock = vi.fn(async () => new Response("nope", { status: 503 }));
    const res = await authenticateApiKey(VALID_KEY, "submit", baseConfig({ fetchImpl: fetchMock }));
    expect(res.ok).toBe(false);
    if (!res.ok) expect(res.status).toBe(502);
  });
});

describe("lookupApiKey", () => {
  it("queries by prefix and active filter, returns null on empty", async () => {
    let captured: string | URL = "";
    const fetchMock = vi.fn(async (url: string | URL) => {
      captured = url;
      return new Response("[]", { status: 200 });
    });
    const row = await lookupApiKey(VALID_PREFIX, baseConfig({ fetchImpl: fetchMock }));
    expect(row).toBeNull();
    const u = String(captured);
    expect(u).toContain("/rest/v1/api_keys");
    expect(u).toContain(`key_prefix=eq.${VALID_PREFIX}`);
    expect(u).toContain("revoked_at=is.null");
    expect(u).toContain("limit=1");
  });

  it("uses service role headers, never the anon key", async () => {
    const fetchMock = vi.fn(async (_url: string | URL, init?: RequestInit) => {
      const headers = init?.headers as Record<string, string>;
      expect(headers.apikey).toBe(SERVICE_ROLE);
      expect(headers.Authorization).toBe(`Bearer ${SERVICE_ROLE}`);
      return new Response("[]", { status: 200 });
    });
    await lookupApiKey(VALID_PREFIX, baseConfig({ fetchImpl: fetchMock }));
    expect(fetchMock).toHaveBeenCalled();
  });
});

describe("countRecentSubmissions", () => {
  it("returns the Content-Range total when present", async () => {
    const fetchMock = vi.fn(
      async () => new Response("[]", { status: 200, headers: { "Content-Range": "0-9/42" } }),
    );
    const n = await countRecentSubmissions(
      7,
      new Date("2026-04-15T11:00:00Z"),
      baseConfig({ fetchImpl: fetchMock }),
    );
    expect(n).toBe(42);
  });

  it("falls back to body length when no header is set", async () => {
    const fetchMock = vi.fn(
      async () => new Response(JSON.stringify([{}, {}, {}]), { status: 200 }),
    );
    const n = await countRecentSubmissions(7, new Date(), baseConfig({ fetchImpl: fetchMock }));
    expect(n).toBe(3);
  });
});

describe("touchLastUsed", () => {
  it("PATCHes the row with a fresh timestamp", async () => {
    const calls: Array<{ url: string; init: RequestInit | undefined }> = [];
    const fetchMock = vi.fn(async (url: string | URL, init?: RequestInit) => {
      calls.push({ url: String(url), init });
      return new Response(null, { status: 204 });
    });
    await touchLastUsed(7, baseConfig({ fetchImpl: fetchMock }));
    expect(calls).toHaveLength(1);
    const call = calls[0];
    if (!call) throw new Error("expected one PATCH call");
    expect(call.url).toContain("/rest/v1/api_keys?id=eq.7");
    expect(call.init?.method).toBe("PATCH");
    const body = JSON.parse((call.init?.body as string) ?? "{}");
    expect(body.last_used_at).toBe("2026-04-15T12:00:00.000Z");
  });
});
