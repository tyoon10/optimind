// GitHub OAuth (Authorization Code + PKCE) — client side. Isolated here so the auth
// mechanism can change without touching the rest of the app (§7.6 decision). The
// client_secret is NEVER in the browser; the code→token exchange happens in the
// Cloudflare Pages Function at /api/oauth/token (GitHub's token endpoint has no CORS).

import {
  PUBLIC_GITHUB_CLIENT_ID, PUBLIC_OAUTH_REDIRECT,
  PUBLIC_REPO_OWNER, PUBLIC_REPO, PUBLIC_BRANCH,
} from "$env/static/public";
import type { RepoRef } from "./github";

const TOKEN_KEY = "optimind_gh_token";
const VERIFIER_KEY = "optimind_pkce_verifier";
const STATE_KEY = "optimind_oauth_state";
const SCOPE = "repo"; // contents read/write on the private journal repo

function b64url(bytes: ArrayBuffer): string {
  return btoa(String.fromCharCode(...new Uint8Array(bytes)))
    .replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
}
function randomString(n = 64): string {
  return b64url(crypto.getRandomValues(new Uint8Array(n)).buffer);
}
async function sha256(s: string): Promise<ArrayBuffer> {
  return crypto.subtle.digest("SHA-256", new TextEncoder().encode(s));
}

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}
export function clearToken(): void {
  localStorage.removeItem(TOKEN_KEY);
}

/**
 * Store a GitHub token directly.
 *
 * The OAuth flow needs a registered OAuth App and a server-side secret for the
 * code exchange, which is the right shape for a deployed phone-facing app and
 * overkill for a local one. A fine-grained PAT scoped to the single journal
 * repo gets you running immediately with a narrower grant than OAuth's `repo`
 * scope, which covers every repository you can read.
 *
 * The token lives in this browser's localStorage and is sent only to
 * api.github.com. Revoke it at github.com/settings/tokens.
 */
export function setToken(token: string): void {
  const t = token.trim();
  if (!t) throw new Error("Empty token");
  localStorage.setItem(TOKEN_KEY, t);
}

/** Confirm the token actually reaches the configured repo before we rely on it. */
export async function verifyToken(token: string): Promise<{ ok: boolean; detail: string }> {
  const res = await fetch(
    `https://api.github.com/repos/${PUBLIC_REPO_OWNER}/${PUBLIC_REPO}`,
    { headers: { Authorization: `Bearer ${token.trim()}`, Accept: "application/vnd.github+json" } },
  );
  if (res.ok) {
    const repo = await res.json();
    // Only reject when GitHub explicitly reports no write access. Some token
    // types omit `permissions` entirely, and blocking a working token at the
    // door is worse than letting the first write fail with a clear message.
    if (repo.permissions && repo.permissions.push === false) {
      return { ok: false, detail: "Token can read the repo but not write it. Grant Contents: Read and write." };
    }
    return { ok: true, detail: `Connected to ${repo.full_name}` };
  }
  if (res.status === 401) return { ok: false, detail: "Token rejected (401). Check it was copied whole." };
  if (res.status === 404) {
    return {
      ok: false,
      detail: `Cannot see ${PUBLIC_REPO_OWNER}/${PUBLIC_REPO}. For a fine-grained token, confirm this repo is selected.`,
    };
  }
  return { ok: false, detail: `GitHub returned ${res.status}` };
}
export function isAuthed(): boolean {
  return !!getToken();
}

/** Build a RepoRef from the stored token + build-time repo config. Throws if unauthed. */
export function repoRef(): RepoRef {
  const token = getToken();
  if (!token) throw new Error("Not authenticated");
  return { owner: PUBLIC_REPO_OWNER, repo: PUBLIC_REPO, branch: PUBLIC_BRANCH, token };
}

/** Kick off the OAuth flow: stash a PKCE verifier + state, redirect to GitHub. */
export async function login(): Promise<void> {
  const verifier = randomString();
  const state = randomString(16);
  const challenge = b64url(await sha256(verifier));
  sessionStorage.setItem(VERIFIER_KEY, verifier);
  sessionStorage.setItem(STATE_KEY, state);
  const p = new URLSearchParams({
    client_id: PUBLIC_GITHUB_CLIENT_ID,
    redirect_uri: PUBLIC_OAUTH_REDIRECT,
    scope: SCOPE,
    state,
    code_challenge: challenge,
    code_challenge_method: "S256",
  });
  window.location.href = `https://github.com/login/oauth/authorize?${p}`;
}

/** Handle the /auth/callback?code&state redirect: verify state, exchange via the Function, store token. */
export async function handleCallback(code: string, state: string): Promise<void> {
  if (state !== sessionStorage.getItem(STATE_KEY)) throw new Error("OAuth state mismatch");
  const verifier = sessionStorage.getItem(VERIFIER_KEY);
  if (!verifier) throw new Error("Missing PKCE verifier");
  const res = await fetch("/api/oauth/token", {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ code, code_verifier: verifier }),
  });
  if (!res.ok) throw new Error(`Token exchange failed: ${res.status} ${await res.text()}`);
  const { access_token, error } = await res.json();
  if (error || !access_token) throw new Error(`OAuth error: ${error ?? "no token"}`);
  localStorage.setItem(TOKEN_KEY, access_token);
  sessionStorage.removeItem(VERIFIER_KEY);
  sessionStorage.removeItem(STATE_KEY);
}
