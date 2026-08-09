// The pair commit must be all-or-nothing. A submission that lands only the JSON
// or only the mirror recreates, at the repository layer, the exact defect that
// lost 8/4-8/6 at the writer layer.

import { describe, expect, it, vi, beforeEach } from "vitest";
import { logField, logFields } from "./writeDaily";
import type { RepoRef } from "./github";

const ref: RepoRef = { owner: "o", repo: "r", branch: "main", token: "t" };

/** A fake GitHub with just enough Git Data API to observe commit shape. */
function fakeGitHub(opts: { refMovesOnce?: boolean; failOn?: string } = {}) {
  const files = new Map<string, string>();
  const commits: Array<{ paths: string[]; message: string }> = [];
  let head = "head0";
  let refMoved = false;
  let pendingTree: Array<{ path: string; sha: string }> = [];
  const blobs = new Map<string, string>();

  const fetchMock = vi.fn(async (url: string, init?: RequestInit) => {
    const u = String(url);
    const body = init?.body ? JSON.parse(String(init.body)) : undefined;
    const json = (data: any) => ({ ok: true, status: 200, json: async () => data, text: async () => "" });
    const fail = (status: number) => ({ ok: false, status, json: async () => ({}), text: async () => "boom" });

    if (opts.failOn && u.includes(opts.failOn)) return fail(500) as any;

    // Contents API read
    if (u.includes("/contents/")) {
      const path = decodeURIComponent(u.split("/contents/")[1].split("?")[0]);
      if (!files.has(path)) return { ok: false, status: 404, json: async () => ({}), text: async () => "" } as any;
      const text = files.get(path)!;
      return json({ content: btoa(unescape(encodeURIComponent(text))), sha: "s" }) as any;
    }
    if (u.endsWith(`/git/ref/heads/main`)) return json({ object: { sha: head } }) as any;
    if (u.includes("/git/commits/")) return json({ tree: { sha: "tree0" } }) as any;
    if (u.endsWith("/git/blobs")) {
      const sha = `blob${blobs.size}`;
      blobs.set(sha, body.content);
      return json({ sha }) as any;
    }
    if (u.endsWith("/git/trees")) {
      pendingTree = body.tree.map((t: any) => ({ path: t.path, sha: t.sha }));
      return json({ sha: "tree1" }) as any;
    }
    if (u.endsWith("/git/commits")) return json({ sha: `commit${commits.length}` }) as any;
    if (u.includes("/git/refs/heads/main")) {
      if (opts.refMovesOnce && !refMoved) {
        refMoved = true;
        head = "head1";
        return fail(422) as any;
      }
      // ref update succeeds: materialise the tree into our file map
      // createBlob posts raw utf-8 (encoding: "utf-8"), so blobs hold plain text.
      for (const t of pendingTree) files.set(t.path, blobs.get(t.sha)!);
      commits.push({ paths: pendingTree.map((t) => t.path), message: body.sha });
      return json({ object: { sha: body.sha } }) as any;
    }
    throw new Error(`unexpected fetch ${u}`);
  });

  return { fetchMock, files, commits, seed: (p: string, t: string) => files.set(p, t) };
}

beforeEach(() => vi.restoreAllMocks());

describe("pair commit", () => {
  it("writes both paths in exactly one commit", async () => {
    const gh = fakeGitHub();
    vi.stubGlobal("fetch", gh.fetchMock);

    const res = await logField(ref, "sleep.quality", 3, "07:00", "2026-08-09");

    expect(gh.commits).toHaveLength(1);
    expect(gh.commits[0].paths.sort()).toEqual(["daily/2026-08-09.json", "journal/2026-08-09.md"]);
    expect(res.verified).toBe(true);
  });

  it("derives the JSON and the mirror from the same in-memory write", async () => {
    const gh = fakeGitHub();
    vi.stubGlobal("fetch", gh.fetchMock);

    await logField(ref, "caffeine", { amount_mg: 65, source: "espresso" }, "08:14", "2026-08-09");

    const doc = JSON.parse(gh.files.get("daily/2026-08-09.json")!);
    expect(doc.log.caffeine[0]).toEqual({ time: "08:14", amount_mg: 65, source: "espresso" });
    expect(gh.files.get("journal/2026-08-09.md")).toContain("[caffeine] 08:14 65 espresso");
  });

  it("batches many fields into ONE commit, not one per field", async () => {
    const gh = fakeGitHub();
    vi.stubGlobal("fetch", gh.fetchMock);

    const res = await logFields(ref, [
      { field: "sleep.bedtime", value: "23:40", time: "07:00" },
      { field: "sleep.wake_time", value: "06:50", time: "07:00" },
      { field: "sleep.quality", value: 3, time: "07:00" },
      { field: "metrics.back_pain", value: { value: 1, scale: 5 }, time: "07:00" },
    ], "2026-08-09");

    expect(gh.commits).toHaveLength(1);
    expect(res.fields).toHaveLength(4);
    const doc = JSON.parse(gh.files.get("daily/2026-08-09.json")!);
    expect(doc.log.sleep).toEqual({ bedtime: "23:40", wake_time: "06:50", quality: 3 });
    expect(doc.log.metrics.back_pain).toEqual({ value: 1, scale: 5 });
  });

  it("appends to an existing journal without disturbing prose", async () => {
    const gh = fakeGitHub();
    gh.seed("journal/2026-08-09.md", "# 2026-08-09\n\n### 09:38 | User\nmorning log\n");
    vi.stubGlobal("fetch", gh.fetchMock);

    await logField(ref, "sleep.quality", 3, "09:40", "2026-08-09");

    const md = gh.files.get("journal/2026-08-09.md")!;
    expect(md).toContain("### 09:38 | User\nmorning log");
    expect(md).toContain("[sleep.quality] 3");
  });

  it("merges into an existing structured record rather than replacing it", async () => {
    const gh = fakeGitHub();
    gh.seed("daily/2026-08-09.json", JSON.stringify({
      schema_version: "1.1", date: "2026-08-09", tz: "America/New_York",
      protocol: { generated_at: "2026-08-09T05:55:00-04:00", source: "rule_derived", items: [{ id: "sunlight" }] },
      log: { sleep: { wake_time: "06:50" } },
    }));
    vi.stubGlobal("fetch", gh.fetchMock);

    await logField(ref, "sleep.quality", 3, "09:40", "2026-08-09");

    const doc = JSON.parse(gh.files.get("daily/2026-08-09.json")!);
    expect(doc.log.sleep).toEqual({ wake_time: "06:50", quality: 3 });
    expect(doc.protocol.items).toHaveLength(1);
  });

  it("retries against the new head when the branch moves under it", async () => {
    const gh = fakeGitHub({ refMovesOnce: true });
    vi.stubGlobal("fetch", gh.fetchMock);

    const res = await logField(ref, "sleep.quality", 3, "07:00", "2026-08-09");

    expect(res.verified).toBe(true);
    expect(gh.commits).toHaveLength(1); // the losing attempt committed nothing
  });

  it("surfaces a failed blob/tree/commit step instead of reporting success", async () => {
    const gh = fakeGitHub({ failOn: "/git/trees" });
    vi.stubGlobal("fetch", gh.fetchMock);

    await expect(logField(ref, "sleep.quality", 3, "07:00", "2026-08-09")).rejects.toThrow(/git\/trees/);
    expect(gh.commits).toHaveLength(0);
  });

  it("rejects an empty batch rather than making an empty commit", async () => {
    const gh = fakeGitHub();
    vi.stubGlobal("fetch", gh.fetchMock);
    await expect(logFields(ref, [], "2026-08-09")).rejects.toThrow(/nothing to write/);
  });
});
