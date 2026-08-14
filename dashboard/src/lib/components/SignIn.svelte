<script lang="ts">
  // Two ways in. OAuth is the right shape for a deployed, phone-facing app;
  // a fine-grained token is the right shape for running this locally today,
  // and it grants LESS than OAuth does — OAuth's `repo` scope covers every
  // repository you can reach, a fine-grained token covers exactly one.
  import { login, setToken, verifyToken } from "$lib/auth";

  let { onconnected }: { onconnected: () => void } = $props();

  let token = $state("");
  let busy = $state(false);
  let error = $state<string | null>(null);
  let showTokenPath = $state(false);

  const TOKEN_URL =
    "https://github.com/settings/personal-access-tokens/new";

  async function connect(e: Event) {
    e.preventDefault();
    busy = true;
    error = null;
    try {
      const result = await verifyToken(token);
      if (!result.ok) {
        error = result.detail;
        return;
      }
      setToken(token);
      token = "";
      onconnected();
    } catch (err) {
      error = `Could not reach GitHub: ${(err as Error).message}`;
    } finally {
      busy = false;
    }
  }
</script>

<div class="card stack" style="max-width:520px;">
  <div>
    <h1>OptiMind</h1>
    <p class="small muted" style="margin-top:4px;">
      Reads and writes your private journal. Nothing is stored on a server.
    </p>
  </div>

  {#if !showTokenPath}
    <button class="primary" onclick={() => (showTokenPath = true)}>
      Connect with a token
    </button>
    <button class="ghost" onclick={() => login()}>
      Connect with GitHub OAuth
    </button>
    <p class="tiny muted">
      OAuth needs a registered OAuth App and a server-side secret. The token path
      works immediately and grants access to one repository instead of all of them.
    </p>
  {:else}
    <form class="stack" onsubmit={connect}>
      <ol class="small dim" style="padding-left:18px;margin:0;display:flex;flex-direction:column;gap:6px;">
        <li>
          Open <a href={TOKEN_URL} target="_blank" rel="noopener noreferrer"
                  style="color:var(--accent-bright);text-decoration:underline;">
            GitHub → fine-grained tokens</a>
        </li>
        <li>Resource owner <strong>tyoon10</strong>, then <strong>Only select repositories</strong> → <code>optimind-journal</code></li>
        <li>Repository permissions → <strong>Contents: Read and write</strong></li>
        <li>Generate, copy, and paste it below</li>
      </ol>

      <div>
        <label for="pat">Token</label>
        <input id="pat" type="password" bind:value={token} autocomplete="off"
               placeholder="github_pat_..." spellcheck="false" />
      </div>

      {#if error}
        <p class="small" style="color:var(--warn);">{error}</p>
      {/if}

      <button class="primary" type="submit" disabled={busy || !token.trim()}>
        {busy ? "Verifying…" : "Verify and connect"}
      </button>

      <p class="tiny muted">
        Verified against the repo before it is stored, so a wrong or under-scoped
        token fails here rather than at your first log. Kept in this browser's
        localStorage only; revoke any time at github.com/settings/tokens.
      </p>
      <button class="ghost small-btn" type="button" onclick={() => (showTokenPath = false)}>
        Back
      </button>
    </form>
  {/if}
</div>
