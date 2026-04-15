// End-to-end unit test for the Worker fetch handler. We supply a fake R2
// bucket + a test-only key resolver so the handler runs through the real
// auth/path/CORS/audit wiring without touching the network.

import { SignJWT, createLocalJWKSet, exportJWK, generateKeyPair } from "jose";
import { beforeAll, describe, expect, it, vi } from "vitest";
import {
  __clearKeySetCacheForTesting,
  __setKeySetForTesting,
  expectedIssuerFor,
  jwksUrlFor,
} from "../src/auth";
import worker from "../src/index";

const SUPABASE_URL = "https://test-project.supabase.co";
const WORKER_ORIGIN = "https://api.synthbench.org";
const SITE_ORIGIN = "https://synthbench.org";

type KeyPair = Awaited<ReturnType<typeof generateKeyPair>>;
let validKeys: KeyPair;
let jwks: Awaited<ReturnType<typeof createLocalJWKSet>>;

beforeAll(async () => {
  validKeys = await generateKeyPair("ES256");
  const jwk = await exportJWK(validKeys.publicKey);
  jwk.alg = "ES256";
  jwk.kid = "test-key-e2e";
  jwks = createLocalJWKSet({ keys: [jwk] });
  __clearKeySetCacheForTesting();
  __setKeySetForTesting(jwksUrlFor(SUPABASE_URL), jwks);
});

async function signToken(overrides: Partial<{ sub: string; aud: string; exp: number }> = {}) {
  return new SignJWT({})
    .setProtectedHeader({ alg: "ES256" })
    .setSubject(overrides.sub ?? "user-abc")
    .setIssuer(expectedIssuerFor(SUPABASE_URL))
    .setAudience(overrides.aud ?? "authenticated")
    .setIssuedAt()
    .setExpirationTime(`${overrides.exp ?? 3600}s`)
    .sign(validKeys.privateKey);
}

// Minimal R2Bucket double with the shape the Worker actually uses. Only
// `get()` is exercised; other methods throw so accidental usage fails loudly.
function makeBucket(store: Map<string, string>): R2Bucket {
  return {
    async get(key: string) {
      const value = store.get(key);
      if (value === undefined) return null;
      return {
        body: new Response(value).body,
      } as unknown as R2ObjectBody;
    },
  } as unknown as R2Bucket;
}

interface PutRecord {
  key: string;
  value: string;
  httpMetadata: { contentType?: string } | undefined;
  customMetadata: Record<string, string> | undefined;
}

function makeWritableBucket(puts: PutRecord[]): R2Bucket {
  return {
    async put(
      key: string,
      value: string,
      opts?: {
        httpMetadata?: { contentType?: string };
        customMetadata?: Record<string, string>;
      },
    ) {
      puts.push({
        key,
        value,
        httpMetadata: opts?.httpMetadata,
        customMetadata: opts?.customMetadata,
      });
      return { key } as unknown as R2Object;
    },
  } as unknown as R2Bucket;
}

interface Harness {
  env: Parameters<typeof worker.fetch>[1];
  ctx: ExecutionContext;
  waitUntilPromises: Promise<unknown>[];
  fetchMock: ReturnType<typeof vi.fn>;
  submissionPuts: PutRecord[];
}

function makeHarness(
  store: Map<string, string> = new Map([["run/abc.json", '{"ok":true}']]),
): Harness {
  const waitUntilPromises: Promise<unknown>[] = [];
  const ctx = {
    waitUntil(p: Promise<unknown>) {
      waitUntilPromises.push(p);
    },
    passThroughOnException() {},
  } as unknown as ExecutionContext;

  // The Worker's audit writer calls global fetch; route through a vitest
  // spy so we can assert on audit emissions without a live network.
  const fetchMock = vi.fn(async () => new Response(null, { status: 201 }));
  vi.stubGlobal("fetch", fetchMock);

  const submissionPuts: PutRecord[] = [];

  const env = {
    DATA_BUCKET: makeBucket(store),
    SUBMISSIONS_BUCKET: makeWritableBucket(submissionPuts),
    SUPABASE_URL,
    SUPABASE_JWT_AUD: "authenticated",
    SUPABASE_SERVICE_ROLE_KEY: "service-role-secret",
    ALLOWED_ORIGINS: `${SITE_ORIGIN},https://www.synthbench.org`,
    GITHUB_DISPATCH_TOKEN: "ghp-test",
    GITHUB_DISPATCH_REPO: "DataViking-Tech/synthbench",
    GITHUB_DISPATCH_WORKFLOW: "process-submission.yml",
    GITHUB_DISPATCH_REF: "main",
  } as Parameters<typeof worker.fetch>[1];

  return { env, ctx, waitUntilPromises, fetchMock, submissionPuts };
}

function validSubmissionJson(): string {
  return JSON.stringify({
    benchmark: "synthbench",
    config: {
      model: "gpt-5",
      provider: "openai",
      dataset: "globalopinionqa",
      framework: "native",
    },
    aggregate: {
      n_questions: 1,
      composite_parity: 0.7,
      mean_jsd: 0.2,
      mean_tau: 0.55,
    },
    per_question: [
      {
        human_distribution: [0.25, 0.25, 0.5],
        model_distribution: [0.3, 0.3, 0.4],
      },
    ],
    scores: { p_dist: 0.8, p_rank: 0.6 },
  });
}

describe("Worker fetch handler", () => {
  it("handles CORS preflight for allowed origins", async () => {
    const { env, ctx } = makeHarness();
    const res = await worker.fetch(
      new Request(`${WORKER_ORIGIN}/data/run/abc.json`, {
        method: "OPTIONS",
        headers: { Origin: SITE_ORIGIN },
      }),
      env,
      ctx,
    );
    expect(res.status).toBe(204);
    expect(res.headers.get("Access-Control-Allow-Origin")).toBe(SITE_ORIGIN);
    expect(res.headers.get("Access-Control-Allow-Credentials")).toBe("true");
  });

  it("returns 401 when Authorization is missing", async () => {
    const { env, ctx } = makeHarness();
    const res = await worker.fetch(
      new Request(`${WORKER_ORIGIN}/data/run/abc.json`, { headers: { Origin: SITE_ORIGIN } }),
      env,
      ctx,
    );
    expect(res.status).toBe(401);
    expect(await res.json()).toEqual({ error: "sign in to view" });
    expect(res.headers.get("Access-Control-Allow-Origin")).toBe(SITE_ORIGIN);
  });

  it("returns 401 for invalid JWTs", async () => {
    const { env, ctx } = makeHarness();
    const res = await worker.fetch(
      new Request(`${WORKER_ORIGIN}/data/run/abc.json`, {
        headers: { Authorization: "Bearer nope.not.jwt" },
      }),
      env,
      ctx,
    );
    expect(res.status).toBe(401);
    expect(await res.json()).toEqual({ error: "invalid token" });
  });

  it("returns 400 for bad paths (unknown top-level dir)", async () => {
    const { env, ctx } = makeHarness();
    const token = await signToken();
    // Note: URL-level traversal like `/data/../x` gets normalized by the URL
    // parser before it reaches the Worker, so we exercise the allowlist path
    // instead — a syntactically valid /data/ request with a forbidden prefix.
    const res = await worker.fetch(
      new Request(`${WORKER_ORIGIN}/data/secret/thing.json`, {
        headers: { Authorization: `Bearer ${token}` },
      }),
      env,
      ctx,
    );
    expect(res.status).toBe(400);
  });

  it("returns 404 for unknown R2 keys", async () => {
    const { env, ctx } = makeHarness(new Map());
    const token = await signToken();
    const res = await worker.fetch(
      new Request(`${WORKER_ORIGIN}/data/run/missing.json`, {
        headers: { Authorization: `Bearer ${token}` },
      }),
      env,
      ctx,
    );
    expect(res.status).toBe(404);
  });

  it("returns 200 + JSON body + audit log for authenticated hits", async () => {
    const { env, ctx, waitUntilPromises, fetchMock } = makeHarness(
      new Map([["question/opinions_qa/q1.json", '{"key":"q1"}']]),
    );
    const token = await signToken({ sub: "user-xyz" });
    const res = await worker.fetch(
      new Request(`${WORKER_ORIGIN}/data/question/opinions_qa/q1.json`, {
        headers: {
          Authorization: `Bearer ${token}`,
          Origin: SITE_ORIGIN,
          "CF-Connecting-IP": "203.0.113.7",
          "User-Agent": "vitest-harness",
        },
      }),
      env,
      ctx,
    );
    expect(res.status).toBe(200);
    expect(res.headers.get("Content-Type")).toContain("application/json");
    expect(res.headers.get("Cache-Control")).toBe("private, max-age=60");
    expect(res.headers.get("Access-Control-Allow-Origin")).toBe(SITE_ORIGIN);
    expect(await res.json()).toEqual({ key: "q1" });

    // Flush the fire-and-forget audit write and assert on its payload.
    await Promise.all(waitUntilPromises);
    expect(fetchMock).toHaveBeenCalledTimes(1);
    const auditCall = fetchMock.mock.calls[0];
    if (!auditCall) throw new Error("expected audit fetch to be called");
    const [url, init] = auditCall;
    expect(url).toBe(`${SUPABASE_URL}/rest/v1/data_access_log`);
    const body = JSON.parse((init as RequestInit).body as string);
    expect(body).toEqual({
      user_id: "user-xyz",
      dataset: "opinions_qa",
      artifact_path: "question/opinions_qa/q1.json",
      request_ip: "203.0.113.7",
      user_agent: "vitest-harness",
    });
  });

  it("returns HEAD with no body on authenticated hits", async () => {
    const { env, ctx, waitUntilPromises, fetchMock } = makeHarness();
    const token = await signToken();
    const res = await worker.fetch(
      new Request(`${WORKER_ORIGIN}/data/run/abc.json`, {
        method: "HEAD",
        headers: { Authorization: `Bearer ${token}` },
      }),
      env,
      ctx,
    );
    expect(res.status).toBe(200);
    expect(await res.text()).toBe("");
    // HEAD intentionally does not audit (no body read) — keeps the audit log
    // focused on actual data retrievals.
    await Promise.all(waitUntilPromises);
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("returns 500 when required env is missing", async () => {
    const { env, ctx } = makeHarness();
    const brokenEnv = { ...env, SUPABASE_URL: "" };
    const res = await worker.fetch(
      new Request(`${WORKER_ORIGIN}/data/run/abc.json`),
      brokenEnv,
      ctx,
    );
    expect(res.status).toBe(500);
  });

  it("does not leak CORS headers to disallowed origins on success", async () => {
    const { env, ctx } = makeHarness();
    const token = await signToken();
    const res = await worker.fetch(
      new Request(`${WORKER_ORIGIN}/data/run/abc.json`, {
        headers: { Authorization: `Bearer ${token}`, Origin: "https://evil.example" },
      }),
      env,
      ctx,
    );
    expect(res.status).toBe(200);
    expect(res.headers.get("Access-Control-Allow-Origin")).toBeNull();
    expect(res.headers.get("Vary")).toBe("Origin");
  });
});

describe("/submit route (sb-me0f)", () => {
  it("rejects GET with 405", async () => {
    const { env, ctx } = makeHarness();
    const token = await signToken();
    const res = await worker.fetch(
      new Request(`${WORKER_ORIGIN}/submit`, {
        method: "GET",
        headers: { Authorization: `Bearer ${token}` },
      }),
      env,
      ctx,
    );
    expect(res.status).toBe(405);
  });

  it("returns 401 when Authorization is missing", async () => {
    const { env, ctx } = makeHarness();
    const res = await worker.fetch(
      new Request(`${WORKER_ORIGIN}/submit`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: validSubmissionJson(),
      }),
      env,
      ctx,
    );
    expect(res.status).toBe(401);
  });

  it("returns 400 for invalid JSON bodies", async () => {
    const { env, ctx } = makeHarness();
    const token = await signToken();
    const res = await worker.fetch(
      new Request(`${WORKER_ORIGIN}/submit`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
        },
        body: "not valid json{",
      }),
      env,
      ctx,
    );
    expect(res.status).toBe(400);
    const body = (await res.json()) as { error: string };
    expect(body.error).toMatch(/invalid JSON/);
  });

  it("returns 400 when Tier-1 schema fails", async () => {
    const { env, ctx } = makeHarness();
    const token = await signToken();
    const res = await worker.fetch(
      new Request(`${WORKER_ORIGIN}/submit`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ benchmark: "other" }),
      }),
      env,
      ctx,
    );
    expect(res.status).toBe(400);
  });

  it("returns 413 when Content-Length exceeds the cap", async () => {
    const { env, ctx } = makeHarness();
    const token = await signToken();
    const res = await worker.fetch(
      new Request(`${WORKER_ORIGIN}/submit`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
          "Content-Length": String(10 * 1024 * 1024),
        },
        body: "{}",
      }),
      env,
      ctx,
    );
    expect(res.status).toBe(413);
  });

  it("returns 503 when GH dispatch env is not configured", async () => {
    const { env, ctx } = makeHarness();
    const token = await signToken();
    const brokenEnv = { ...env, GITHUB_DISPATCH_TOKEN: "" };
    const res = await worker.fetch(
      new Request(`${WORKER_ORIGIN}/submit`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
        },
        body: validSubmissionJson(),
      }),
      brokenEnv,
      ctx,
    );
    expect(res.status).toBe(503);
  });

  it("stages to R2, inserts the row, dispatches the workflow, returns 202", async () => {
    const { env, ctx, fetchMock, submissionPuts } = makeHarness();
    // First fetch call = Supabase insert (returns the row); second = GH dispatch.
    fetchMock.mockImplementation(async (url: string | URL, _init?: RequestInit) => {
      const u = String(url);
      if (u.includes("/rest/v1/submissions")) {
        return new Response(
          JSON.stringify([{ id: 42, submitted_at: "2026-04-15T09:00:00Z", status: "validating" }]),
          { status: 201, headers: { "Content-Type": "application/json" } },
        );
      }
      if (u.includes("api.github.com") && u.includes("/dispatches")) {
        return new Response(null, { status: 204 });
      }
      return new Response(null, { status: 500 });
    });

    const token = await signToken({ sub: "user-xyz" });
    const res = await worker.fetch(
      new Request(`${WORKER_ORIGIN}/submit`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
          Origin: SITE_ORIGIN,
          "User-Agent": "vitest-harness",
        },
        body: validSubmissionJson(),
      }),
      env,
      ctx,
    );
    expect(res.status).toBe(202);
    const body = (await res.json()) as { submission_id: number; status: string; file_path: string };
    expect(body.submission_id).toBe(42);
    expect(body.status).toBe("validating");
    expect(body.file_path).toMatch(/^submissions\/\d{4}\/\d{2}\/\d{2}\/user-xyz\//);
    expect(res.headers.get("Access-Control-Allow-Origin")).toBe(SITE_ORIGIN);

    // R2 staging happened with the right object body + metadata.
    expect(submissionPuts).toHaveLength(1);
    const put = submissionPuts[0];
    if (!put) throw new Error("expected R2 put");
    expect(put.customMetadata?.user_id).toBe("user-xyz");
    expect(put.customMetadata?.model_name).toBe("gpt-5");
    expect(put.customMetadata?.dataset).toBe("globalopinionqa");

    // Both Supabase + GH dispatch were called.
    const calls = fetchMock.mock.calls.map((c) => String(c[0]));
    expect(calls.some((u) => u.includes("/rest/v1/submissions"))).toBe(true);
    expect(
      calls.some(
        (u) =>
          u.includes("api.github.com") &&
          u.includes("DataViking-Tech/synthbench") &&
          u.includes("process-submission.yml"),
      ),
    ).toBe(true);
  });

  it("still returns 202 with a warning when dispatch fails after insert", async () => {
    const { env, ctx, fetchMock } = makeHarness();
    fetchMock.mockImplementation(async (url: string | URL) => {
      const u = String(url);
      if (u.includes("/rest/v1/submissions")) {
        return new Response(
          JSON.stringify([{ id: 99, submitted_at: "2026-04-15T09:00:00Z", status: "validating" }]),
          { status: 201 },
        );
      }
      if (u.includes("api.github.com")) {
        return new Response("boom", { status: 500 });
      }
      return new Response(null, { status: 500 });
    });

    const token = await signToken();
    const res = await worker.fetch(
      new Request(`${WORKER_ORIGIN}/submit`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
        },
        body: validSubmissionJson(),
      }),
      env,
      ctx,
    );
    expect(res.status).toBe(202);
    const body = (await res.json()) as { submission_id: number; warning?: string };
    expect(body.submission_id).toBe(99);
    expect(body.warning).toMatch(/dispatch failed/);
  });

  it("returns 502 when Supabase insert fails", async () => {
    const { env, ctx, fetchMock } = makeHarness();
    fetchMock.mockImplementation(async () => new Response("down", { status: 503 }));
    const token = await signToken();
    const res = await worker.fetch(
      new Request(`${WORKER_ORIGIN}/submit`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
        },
        body: validSubmissionJson(),
      }),
      env,
      ctx,
    );
    expect(res.status).toBe(502);
  });

  // sb-t61h: API-key auth path. We exercise the full handler so a regression
  // in the JWT-vs-key router (in handleSubmit) gets caught here, not just in
  // the apiKey unit suite.
  describe("API key auth (sb-t61h)", () => {
    const VALID_KEY = `sb_${"a".repeat(32)}`;
    const VALID_PREFIX = "sb_aaaaa";

    it("accepts a valid sb_ key, stamps api_key_id on the row, and stages with auth_method=api_key", async () => {
      const { env, ctx, fetchMock, submissionPuts } = makeHarness();

      // Compute the real sha256 of the test key so the Worker's WebCrypto
      // path matches the value we hand back from the Supabase double.
      const keyHash = await import("../src/apiKey").then((m) => m.sha256Hex(VALID_KEY));

      const insertCalls: RequestInit[] = [];
      fetchMock.mockImplementation(async (url: string | URL, init?: RequestInit) => {
        const u = String(url);
        if (u.includes("/rest/v1/api_keys") && u.includes(`key_prefix=eq.${VALID_PREFIX}`)) {
          return new Response(
            JSON.stringify([
              {
                id: 11,
                user_id: "user-cli",
                scope: "submit",
                expires_at: null,
                revoked_at: null,
                key_hash: keyHash,
              },
            ]),
            { status: 200 },
          );
        }
        if (u.includes("/rest/v1/submissions") && (init?.method ?? "GET") === "GET") {
          return new Response("[]", {
            status: 200,
            headers: { "Content-Range": "*/0" },
          });
        }
        if (u.includes("/rest/v1/submissions") && init?.method === "POST") {
          insertCalls.push(init);
          return new Response(
            JSON.stringify([
              { id: 501, submitted_at: "2026-04-15T12:00:00Z", status: "validating" },
            ]),
            { status: 201 },
          );
        }
        if (u.includes("/rest/v1/api_keys") && init?.method === "PATCH") {
          return new Response(null, { status: 204 });
        }
        if (u.includes("api.github.com")) {
          return new Response(null, { status: 204 });
        }
        return new Response("unexpected", { status: 500 });
      });

      const res = await worker.fetch(
        new Request(`${WORKER_ORIGIN}/submit`, {
          method: "POST",
          headers: {
            Authorization: `Bearer ${VALID_KEY}`,
            "Content-Type": "application/json",
            "User-Agent": "synthbench-cli/0.1",
          },
          body: validSubmissionJson(),
        }),
        env,
        ctx,
      );
      expect(res.status).toBe(202);
      const body = (await res.json()) as { submission_id: number };
      expect(body.submission_id).toBe(501);

      // R2 staging marked as api_key auth.
      expect(submissionPuts).toHaveLength(1);
      const put = submissionPuts[0];
      if (!put) throw new Error("expected R2 put");
      expect(put.customMetadata?.user_id).toBe("user-cli");
      expect(put.customMetadata?.auth_method).toBe("api_key");

      // Insert payload tagged with api_key_id.
      expect(insertCalls).toHaveLength(1);
      const insertCall = insertCalls[0];
      if (!insertCall) throw new Error("expected insert call");
      const insertBody = JSON.parse(insertCall.body as string);
      expect(insertBody.api_key_id).toBe(11);
      expect(insertBody.user_id).toBe("user-cli");
    });

    it("returns 401 when the api key is unknown", async () => {
      const { env, ctx, fetchMock } = makeHarness();
      fetchMock.mockImplementation(async (url: string | URL) => {
        const u = String(url);
        if (u.includes("/rest/v1/api_keys")) return new Response("[]", { status: 200 });
        return new Response(null, { status: 500 });
      });
      const res = await worker.fetch(
        new Request(`${WORKER_ORIGIN}/submit`, {
          method: "POST",
          headers: {
            Authorization: `Bearer ${VALID_KEY}`,
            "Content-Type": "application/json",
          },
          body: validSubmissionJson(),
        }),
        env,
        ctx,
      );
      expect(res.status).toBe(401);
      expect(await res.json()).toEqual({ error: "unknown api key" });
    });

    it("returns 429 when the per-key rate limit is exceeded", async () => {
      const { env, ctx, fetchMock } = makeHarness();
      const keyHash = await import("../src/apiKey").then((m) => m.sha256Hex(VALID_KEY));
      fetchMock.mockImplementation(async (url: string | URL) => {
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
                key_hash: keyHash,
              },
            ]),
            { status: 200 },
          );
        }
        // 60 prior submissions in the last hour → at the ceiling.
        return new Response("[]", {
          status: 200,
          headers: { "Content-Range": "*/60" },
        });
      });
      const res = await worker.fetch(
        new Request(`${WORKER_ORIGIN}/submit`, {
          method: "POST",
          headers: {
            Authorization: `Bearer ${VALID_KEY}`,
            "Content-Type": "application/json",
          },
          body: validSubmissionJson(),
        }),
        env,
        ctx,
      );
      expect(res.status).toBe(429);
    });

    // sb-ymux: poll route exercised through the real router. We want to catch
    // regressions in both the path parser (`/submit/<id>`) and the api-key-only
    // gate, so this suite hits `worker.fetch` directly rather than calling the
    // helper in isolation.
    describe("GET /submit/<id> status poll (sb-ymux)", () => {
      async function mockKeyLookup(fetchMock: ReturnType<typeof vi.fn>, keyHash: string) {
        fetchMock.mockImplementation(async (url: string | URL, init?: RequestInit) => {
          const u = String(url);
          const method = (init?.method ?? "GET").toUpperCase();
          if (u.includes("/rest/v1/api_keys") && method === "GET") {
            return new Response(
              JSON.stringify([
                {
                  id: 7,
                  user_id: "user-cli",
                  scope: "submit",
                  expires_at: null,
                  revoked_at: null,
                  key_hash: keyHash,
                },
              ]),
              { status: 200 },
            );
          }
          if (u.includes("/rest/v1/api_keys") && method === "PATCH") {
            return new Response(null, { status: 204 });
          }
          // rate-limit count
          if (
            u.includes("/rest/v1/submissions") &&
            method === "GET" &&
            u.includes("submitted_at=gte.")
          ) {
            return new Response("[]", { status: 200, headers: { "Content-Range": "*/0" } });
          }
          // status lookup for the submission itself
          if (
            u.includes("/rest/v1/submissions") &&
            method === "GET" &&
            u.includes("id=eq.42") &&
            u.includes("user_id=eq.user-cli")
          ) {
            return new Response(
              JSON.stringify([
                {
                  id: 42,
                  status: "published",
                  submitted_at: "2026-04-15T09:00:00Z",
                  rejection_reason: null,
                  leaderboard_entry_id: "claude-haiku-4-5__globalopinionqa",
                  model_name: "claude-haiku-4-5",
                  dataset: "globalopinionqa",
                },
              ]),
              { status: 200 },
            );
          }
          // Cross-user peek — id matches but user_id filter drops it.
          if (u.includes("/rest/v1/submissions") && method === "GET" && u.includes("id=eq.99")) {
            return new Response("[]", { status: 200 });
          }
          return new Response("unexpected", { status: 500 });
        });
      }

      it("returns 200 + status for the key owner's own submission", async () => {
        const { env, ctx, fetchMock } = makeHarness();
        const keyHash = await import("../src/apiKey").then((m) => m.sha256Hex(VALID_KEY));
        await mockKeyLookup(fetchMock, keyHash);

        const res = await worker.fetch(
          new Request(`${WORKER_ORIGIN}/submit/42`, {
            method: "GET",
            headers: { Authorization: `Bearer ${VALID_KEY}` },
          }),
          env,
          ctx,
        );
        expect(res.status).toBe(200);
        const body = (await res.json()) as {
          submission_id: number;
          status: string;
          leaderboard_entry_id: string | null;
          rejection_reason: string | null;
        };
        expect(body.submission_id).toBe(42);
        expect(body.status).toBe("published");
        expect(body.leaderboard_entry_id).toBe("claude-haiku-4-5__globalopinionqa");
        expect(body.rejection_reason).toBeNull();
      });

      it("returns 404 when the submission id belongs to another user", async () => {
        const { env, ctx, fetchMock } = makeHarness();
        const keyHash = await import("../src/apiKey").then((m) => m.sha256Hex(VALID_KEY));
        await mockKeyLookup(fetchMock, keyHash);

        const res = await worker.fetch(
          new Request(`${WORKER_ORIGIN}/submit/99`, {
            method: "GET",
            headers: { Authorization: `Bearer ${VALID_KEY}` },
          }),
          env,
          ctx,
        );
        expect(res.status).toBe(404);
        // Same shape as truly-missing ids — no enumeration side channel.
        expect(await res.json()).toEqual({ error: "not found" });
      });

      it("rejects JWT auth with 401 (status endpoint is api-key only)", async () => {
        const { env, ctx } = makeHarness();
        const token = await signToken();
        const res = await worker.fetch(
          new Request(`${WORKER_ORIGIN}/submit/42`, {
            method: "GET",
            headers: { Authorization: `Bearer ${token}` },
          }),
          env,
          ctx,
        );
        expect(res.status).toBe(401);
      });

      it("returns 401 when Authorization is missing", async () => {
        const { env, ctx } = makeHarness();
        const res = await worker.fetch(
          new Request(`${WORKER_ORIGIN}/submit/42`, { method: "GET" }),
          env,
          ctx,
        );
        expect(res.status).toBe(401);
      });

      it("returns 405 for POST /submit/<id>", async () => {
        const { env, ctx } = makeHarness();
        const res = await worker.fetch(
          new Request(`${WORKER_ORIGIN}/submit/42`, {
            method: "POST",
            headers: { Authorization: `Bearer ${VALID_KEY}` },
          }),
          env,
          ctx,
        );
        expect(res.status).toBe(405);
      });

      it("falls through to the POST handler (405) for non-numeric /submit/<x>", async () => {
        // `/submit/abc` is not a status lookup; the router delegates it to
        // handleSubmit which 405s non-POST.
        const { env, ctx } = makeHarness();
        const res = await worker.fetch(
          new Request(`${WORKER_ORIGIN}/submit/abc`, {
            method: "GET",
            headers: { Authorization: `Bearer ${VALID_KEY}` },
          }),
          env,
          ctx,
        );
        expect(res.status).toBe(405);
      });
    });

    it("returns 403 when the api key lacks submit scope", async () => {
      const { env, ctx, fetchMock } = makeHarness();
      const keyHash = await import("../src/apiKey").then((m) => m.sha256Hex(VALID_KEY));
      fetchMock.mockImplementation(async (url: string | URL) => {
        const u = String(url);
        if (u.includes("/rest/v1/api_keys")) {
          return new Response(
            JSON.stringify([
              {
                id: 1,
                user_id: "u",
                scope: "read",
                expires_at: null,
                revoked_at: null,
                key_hash: keyHash,
              },
            ]),
            { status: 200 },
          );
        }
        return new Response("[]", { status: 200, headers: { "Content-Range": "*/0" } });
      });
      const res = await worker.fetch(
        new Request(`${WORKER_ORIGIN}/submit`, {
          method: "POST",
          headers: {
            Authorization: `Bearer ${VALID_KEY}`,
            "Content-Type": "application/json",
          },
          body: validSubmissionJson(),
        }),
        env,
        ctx,
      );
      expect(res.status).toBe(403);
    });
  });
});
