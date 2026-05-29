// OAuth code→token exchange. Runs as a Cloudflare Pages Function (adapter-cloudflare),
// NOT in the browser — this is the only place the client_secret lives. GitHub's token
// endpoint sends no CORS headers, so the SPA cannot call it directly; this proxies it.

import { json, error } from "@sveltejs/kit";
import { PUBLIC_GITHUB_CLIENT_ID, PUBLIC_OAUTH_REDIRECT } from "$env/static/public";
import type { RequestHandler } from "./$types";

export const POST: RequestHandler = async ({ request, platform }) => {
  const { code, code_verifier } = await request.json();
  if (!code) throw error(400, "missing code");

  // Secret comes from the Cloudflare env (Pages → Settings → Variables/Secrets).
  // Fallback to process.env for `wrangler dev` / local.
  const clientSecret =
    (platform as any)?.env?.GITHUB_CLIENT_SECRET ??
    (globalThis as any)?.process?.env?.GITHUB_CLIENT_SECRET;
  if (!clientSecret) throw error(500, "server missing GITHUB_CLIENT_SECRET");

  const res = await fetch("https://github.com/login/oauth/access_token", {
    method: "POST",
    headers: { "content-type": "application/json", accept: "application/json" },
    body: JSON.stringify({
      client_id: PUBLIC_GITHUB_CLIENT_ID,
      client_secret: clientSecret,
      code,
      code_verifier,
      redirect_uri: PUBLIC_OAUTH_REDIRECT,
    }),
  });
  if (!res.ok) throw error(502, `github token endpoint ${res.status}`);
  return json(await res.json()); // { access_token, scope, token_type } or { error }
};
