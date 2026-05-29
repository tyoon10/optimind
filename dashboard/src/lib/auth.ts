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
