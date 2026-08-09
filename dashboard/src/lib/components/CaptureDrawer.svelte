<script lang="ts">
  // One drawer for every capture. Whatever the user opens it for, the whole
  // batch leaves as ONE pair commit — the point of the build is that a
  // submission is atomic, so the UI must never split one into several.
  import type { CaptureSpec, FieldWrite } from "$lib/capture";

  let {
    spec,
    now,
    busy = false,
    onsubmit,
    onclose,
  }: {
    spec: CaptureSpec;
    now: string;
    busy?: boolean;
    onsubmit: (writes: FieldWrite[]) => void;
    onclose: () => void;
  } = $props();

  let values = $state<Record<string, string>>({});
  let time = $state(now);

  function submit(e: Event) {
    e.preventDefault();
    const writes: FieldWrite[] = [];

    if (spec.grouped && spec.groupField) {
      const entry: Record<string, any> = {};
      for (const f of spec.fields) {
        const raw = values[f.field]?.trim();
        if (!raw) continue;
        entry[f.field] = f.kind === "number" || f.kind === "score" ? Number(raw) : raw;
      }
      if (Object.keys(entry).length) writes.push({ field: spec.groupField, value: entry, time });
    } else {
      for (const f of spec.fields) {
        const raw = values[f.field]?.trim();
        if (!raw) continue;
        writes.push({
          field: f.field,
          value: f.kind === "score" || f.kind === "number" ? Number(raw) : raw,
          time,
        });
      }
    }
    if (writes.length) onsubmit(writes);
  }

  function onkeydown(e: KeyboardEvent) {
    if (e.key === "Escape") onclose();
  }
</script>

<svelte:window on:keydown={onkeydown} />

<div class="scrim" role="presentation" onclick={onclose}></div>

<div class="drawer" role="dialog" aria-modal="true" aria-label={spec.title}>
  <div class="row-between" style="margin-bottom:var(--s-2);">
    <h2>{spec.title}</h2>
    <button class="ghost small-btn" onclick={onclose}>Close</button>
  </div>

  {#if spec.hint}
    <p class="small muted" style="margin-bottom:var(--s-2);">{spec.hint}</p>
  {/if}

  <form class="stack" onsubmit={submit}>
    <div>
      <label for="capture-time">Time</label>
      <input id="capture-time" type="time" bind:value={time} />
    </div>

    {#each spec.fields as f (f.field)}
      <div>
        <label for="cap-{f.field}">{f.label}</label>
        {#if f.kind === "score"}
          <input id="cap-{f.field}" type="number" min="1" max={f.max ?? 5}
                 inputmode="numeric" placeholder={f.placeholder}
                 bind:value={values[f.field]} />
        {:else if f.kind === "number"}
          <input id="cap-{f.field}" type="number" min="0" inputmode="numeric"
                 placeholder={f.placeholder} bind:value={values[f.field]} />
        {:else if f.kind === "time"}
          <input id="cap-{f.field}" type="time" bind:value={values[f.field]} />
        {:else}
          <input id="cap-{f.field}" type="text" placeholder={f.placeholder}
                 bind:value={values[f.field]} />
        {/if}
      </div>
    {/each}

    <div class="row" style="margin-top:var(--s-1);">
      <button class="primary grow" type="submit" disabled={busy}>
        {busy ? "Writing…" : "Save"}
      </button>
    </div>
    <p class="tiny muted">
      Saves both records in one commit. Nothing is reported as logged until both are confirmed.
    </p>
  </form>
</div>
