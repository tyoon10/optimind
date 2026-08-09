// Minimal GitHub Contents API client (raw fetch — same REST endpoints Octokit wraps,
// zero-dep, keeps the bundle light per §7.6). Reads/writes a single file with its sha.

const API = "https://api.github.com";

export interface RepoRef {
  owner: string;
  repo: string;
  branch: string;
  token: string;
}

function b64encode(s: string): string {
  // UTF-8 safe base64 (btoa is latin1-only).
  return btoa(String.fromCharCode(...new TextEncoder().encode(s)));
}
function b64decode(s: string): string {
  const bin = atob(s.replace(/\n/g, ""));
  return new TextDecoder().decode(Uint8Array.from(bin, (c) => c.charCodeAt(0)));
}

function headers(token: string): HeadersInit {
  return {
    Authorization: `Bearer ${token}`,
    Accept: "application/vnd.github+json",
    "X-GitHub-Api-Version": "2022-11-28",
  };
}

export interface FileState {
  text: string | null; // null if the file doesn't exist yet
  sha: string | null;
}

/** GET a file's content + sha. Returns {text:null, sha:null} on 404. */
export async function getFile(ref: RepoRef, path: string): Promise<FileState> {
  const url = `${API}/repos/${ref.owner}/${ref.repo}/contents/${path}?ref=${ref.branch}`;
  const res = await fetch(url, { headers: headers(ref.token) });
  if (res.status === 404) return { text: null, sha: null };
  if (!res.ok) throw new Error(`GitHub GET ${path} failed: ${res.status} ${await res.text()}`);
  const data = await res.json();
  return { text: b64decode(data.content), sha: data.sha };
}

/** PUT (create/update) a file. Pass the current sha for updates (omit/undefined to create). */
export async function putFile(
  ref: RepoRef, path: string, text: string, message: string, sha: string | null,
): Promise<string> {
  const url = `${API}/repos/${ref.owner}/${ref.repo}/contents/${path}`;
  const body: Record<string, unknown> = {
    message,
    content: b64encode(text),
    branch: ref.branch,
  };
  if (sha) body.sha = sha;
  const res = await fetch(url, { method: "PUT", headers: headers(ref.token), body: JSON.stringify(body) });
  if (!res.ok) throw new Error(`GitHub PUT ${path} failed: ${res.status} ${await res.text()}`);
  const data = await res.json();
  return data.content.sha as string;
}

// --- Git Data API: commit several paths in ONE commit -------------------------
//
// The Contents API writes one file per call, so a dual-write took two commits.
// If the second failed, git history kept a state the data model forbids: a
// structured record with no audit-log mirror, or vice versa. The Git Data API
// builds one tree containing both paths and moves the branch once, so the pair
// is atomic at the repository level -- there is no instant at which only half
// of a submission exists.

export interface PairFile {
  path: string;
  text: string;
}

export interface CommitResult {
  sha: string;
  paths: string[];
}

async function gh(ref: RepoRef, path: string, init?: RequestInit): Promise<any> {
  const res = await fetch(`${API}/repos/${ref.owner}/${ref.repo}${path}`, {
    ...init,
    headers: { ...headers(ref.token), ...(init?.body ? { "content-type": "application/json" } : {}) },
  });
  if (!res.ok) {
    throw new Error(`GitHub ${init?.method ?? "GET"} ${path} failed: ${res.status} ${await res.text()}`);
  }
  return res.json();
}

/** Current head commit sha of the target branch. */
export async function getBranchHead(ref: RepoRef): Promise<string> {
  const data = await gh(ref, `/git/ref/heads/${encodeURIComponent(ref.branch)}`);
  return data.object.sha as string;
}

/**
 * Commit every file in one tree, one commit, one ref update.
 * Retries once from a freshly-read head if the branch moved under us — the
 * nightly Reflection and chat sessions push to the same branch.
 */
export async function commitPair(
  ref: RepoRef, files: PairFile[], message: string, retries = 1,
): Promise<CommitResult> {
  if (!files.length) throw new Error("commitPair: no files");

  const head = await getBranchHead(ref);
  const headCommit = await gh(ref, `/git/commits/${head}`);

  const blobs = await Promise.all(
    files.map((f) =>
      gh(ref, "/git/blobs", {
        method: "POST",
        body: JSON.stringify({ content: f.text, encoding: "utf-8" }),
      }).then((b) => ({ path: f.path, sha: b.sha as string })),
    ),
  );

  const tree = await gh(ref, "/git/trees", {
    method: "POST",
    body: JSON.stringify({
      base_tree: headCommit.tree.sha,
      tree: blobs.map((b) => ({ path: b.path, mode: "100644", type: "blob", sha: b.sha })),
    }),
  });

  const commit = await gh(ref, "/git/commits", {
    method: "POST",
    body: JSON.stringify({ message, tree: tree.sha, parents: [head] }),
  });

  try {
    await gh(ref, `/git/refs/heads/${encodeURIComponent(ref.branch)}`, {
      method: "PATCH",
      body: JSON.stringify({ sha: commit.sha, force: false }),
    });
  } catch (e) {
    // Non-fast-forward: someone pushed between our read and our update. Rebuild
    // against the new head rather than force-pushing over their commit.
    if (retries > 0) return commitPair(ref, files, message, retries - 1);
    throw new Error(`branch moved and retries exhausted: ${(e as Error).message}`);
  }

  return { sha: commit.sha as string, paths: files.map((f) => f.path) };
}
