<script lang="ts">
  import { onMount } from "svelte";
  import { goto } from "$app/navigation";
  import { handleCallback } from "$lib/auth";

  let status = $state("Completing sign-in…");

  onMount(async () => {
    const p = new URLSearchParams(window.location.search);
    const code = p.get("code");
    const state = p.get("state");
    if (!code || !state) {
      status = "Missing code/state in callback.";
      return;
    }
    try {
      await handleCallback(code, state);
      await goto("/");
    } catch (e) {
      status = `Sign-in failed: ${(e as Error).message}`;
    }
  });
</script>

<div class="card">{status}</div>
