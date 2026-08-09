<script lang="ts">
  // Native SVG. Gaps are drawn as gaps: the line breaks, and the missing dates
  // get a hollow marker on the baseline. A continuous line over four lost days
  // is how the data layer's failure stayed invisible for a week.
  import type { TrendSeries } from "$lib/types";

  let { series, height = 64 }: { series: TrendSeries; height?: number } = $props();

  const W = 300;
  const PAD = 6;

  const values = $derived(series.points.filter((p) => p.value != null).map((p) => p.value as number));
  const min = $derived(series.scale ? 0 : Math.min(...values, 0));
  const max = $derived(series.scale ?? (values.length ? Math.max(...values) : 1));

  function x(i: number) {
    const n = series.points.length;
    return n <= 1 ? W / 2 : PAD + (i * (W - PAD * 2)) / (n - 1);
  }
  function y(v: number) {
    const span = max - min || 1;
    return height - PAD - ((v - min) / span) * (height - PAD * 2);
  }

  /** Contiguous runs of present values — each becomes its own polyline. */
  const runs = $derived.by(() => {
    const out: Array<Array<{ x: number; y: number }>> = [];
    let cur: Array<{ x: number; y: number }> = [];
    series.points.forEach((p, i) => {
      if (p.value == null) {
        if (cur.length) out.push(cur);
        cur = [];
      } else {
        cur.push({ x: x(i), y: y(p.value) });
      }
    });
    if (cur.length) out.push(cur);
    return out;
  });

  const gaps = $derived(
    series.points.map((p, i) => ({ p, i })).filter(({ p }) => p.value == null),
  );
</script>

{#if !values.length}
  <div class="stack-sm" style="padding:var(--s-2) 0;">
    <p class="small muted">No readings in this window.</p>
    <p class="tiny muted">Nothing was recorded — this is not a value of zero.</p>
  </div>
{:else}
  <svg viewBox="0 0 {W} {height}" width="100%" {height} role="img"
       aria-label="{series.label}: {values.length} of {series.points.length} days recorded">
    {#each runs as run}
      {#if run.length === 1}
        <circle cx={run[0].x} cy={run[0].y} r="3" fill="var(--accent-bright)" />
      {:else}
        <polyline points={run.map((p) => `${p.x},${p.y}`).join(" ")}
                  fill="none" stroke="var(--accent-bright)" stroke-width="2"
                  stroke-linejoin="round" stroke-linecap="round" />
      {/if}
    {/each}

    {#each series.points as p, i}
      {#if p.value != null && p.source === "journal_confirmed"}
        <!-- real, but the structured write lost it -->
        <circle cx={x(i)} cy={y(p.value)} r="3.5" fill="var(--canvas)"
                stroke="var(--info)" stroke-width="2" />
      {:else if p.value != null && p.source === "estimated"}
        <circle cx={x(i)} cy={y(p.value)} r="3" fill="var(--warn)" />
      {/if}
    {/each}

    {#each gaps as g}
      <circle cx={x(g.i)} cy={height - PAD} r="2" fill="none"
              stroke="var(--text-3)" stroke-width="1" stroke-dasharray="1 1" />
    {/each}
  </svg>

  <p class="tiny muted">
    {series.coverage.present}/{series.coverage.closed} closed days recorded
    {#if gaps.length}· {gaps.length} gap{gaps.length > 1 ? "s" : ""} shown, not interpolated{/if}
  </p>
{/if}
