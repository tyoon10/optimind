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
