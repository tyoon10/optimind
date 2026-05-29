<script lang="ts">
  import { onMount } from "svelte";
  import { isAuthed, login, repoRef, clearToken } from "$lib/auth";
  import { getDaily, logField } from "$lib/writeDaily";
  import { todayNYC, nowHHMM, type DailyLog } from "$lib/daily";

  let authed = $state(false);
  let daily = $state<DailyLog | null>(null);
  let busy = $state(false);
  let toast = $state<string | null>(null);
  let err = $state<string | null>(null);

  const date = todayNYC();

  // form models
  let sleep = $state({ bedtime: "", wake_time: "", quality: "" });
  let caffeine = $state({ time: nowHHMM(), amount_mg: "", source: "" });
  let meal = $state({ time: nowHHMM(), items: "" });
  let workout = $state({ time: nowHHMM(), duration_min: "", type: "" });

  onMount(async () => {
    authed = isAuthed();
    if (authed) await load();
  });

  async function load() {
    try {
      daily = await getDaily(repoRef(), date);
    } catch (e) {
      err = (e as Error).message;
    }
  }

  function flash(msg: string) {
    toast = msg;
    setTimeout(() => (toast = null), 1500);
  }

  async function submit(field: string, value: any, time?: string) {
    busy = true;
    err = null;
    try {
      await logField(repoRef(), field, value, time);
      flash(`logged ${field}`);
      await load();
    } catch (e) {
      err = (e as Error).message;
    } finally {
      busy = false;
    }
  }

  async function logSleep(e: Event) {
    e.preventDefault();
    if (sleep.bedtime) await submit("sleep.bedtime", sleep.bedtime);
    if (sleep.wake_time) await submit("sleep.wake_time", sleep.wake_time);
    if (sleep.quality) await submit("sleep.quality", Number(sleep.quality));
  }
  async function logCaffeine(e: Event) {
    e.preventDefault();
    await submit("caffeine", { amount_mg: Number(caffeine.amount_mg), source: caffeine.source }, caffeine.time);
    caffeine = { time: nowHHMM(), amount_mg: "", source: "" };
  }
  async function logMeal(e: Event) {
    e.preventDefault();
    await submit("meal", { items: meal.items }, meal.time);
    meal = { time: nowHHMM(), items: "" };
  }
  async function logWorkout(e: Event) {
    e.preventDefault();
    await submit("workout", { duration_min: Number(workout.duration_min), type: workout.type }, workout.time);
    workout = { time: nowHHMM(), duration_min: "", type: "" };
  }
  async function toggleRoutine(id: string, done: boolean) {
    await submit(`routine.${id}`, { done, time: nowHHMM() });
  }
</script>

<h1>OptiMind — {date}</h1>

{#if !authed}
  <div class="card">
    <p>Connect your GitHub account to log to <code>optimind-journal</code>.</p>
    <button onclick={() => login()}>Connect GitHub</button>
  </div>
{:else}
  {#if err}<div class="card" style="border:1px solid #ef4444">{err}</div>{/if}

  <h2>Today's protocol</h2>
  <div class="card">
    {#if daily?.protocol?.items?.length}
      {#each daily.protocol.items as item}
        <label class="check">
          <input
            type="checkbox"
            checked={daily?.log?.routine?.[item.id]?.done ?? false}
            disabled={busy}
            onchange={(e) => toggleRoutine(item.id, (e.target as HTMLInputElement).checked)}
          />
          <span>{item.id}{item.expected_window ? ` · ${item.expected_window}` : ""}</span>
        </label>
      {/each}
    {:else}
      <p class="muted">No protocol yet today — the morning brief sets it, or log freely below.</p>
    {/if}
  </div>

  <h2>Sleep</h2>
  <form class="card" onsubmit={logSleep}>
    <div class="row">
      <div><label>bedtime</label><input type="time" bind:value={sleep.bedtime} /></div>
      <div><label>wake</label><input type="time" bind:value={sleep.wake_time} /></div>
      <div><label>quality 1–10</label><input type="number" min="1" max="10" bind:value={sleep.quality} /></div>
    </div>
    <button disabled={busy}>Log sleep</button>
  </form>

  <h2>Caffeine</h2>
  <form class="card" onsubmit={logCaffeine}>
    <div class="row">
      <div><label>time</label><input type="time" bind:value={caffeine.time} /></div>
      <div><label>mg</label><input type="number" min="0" bind:value={caffeine.amount_mg} /></div>
    </div>
    <label>source</label><input bind:value={caffeine.source} placeholder="espresso" />
    <button disabled={busy}>Log caffeine</button>
  </form>

  <h2>Meal</h2>
  <form class="card" onsubmit={logMeal}>
    <div class="row">
      <div><label>time</label><input type="time" bind:value={meal.time} /></div>
      <div style="flex:2"><label>items</label><input bind:value={meal.items} placeholder="eggs, oats" /></div>
    </div>
    <button disabled={busy}>Log meal</button>
  </form>

  <h2>Workout</h2>
  <form class="card" onsubmit={logWorkout}>
    <div class="row">
      <div><label>time</label><input type="time" bind:value={workout.time} /></div>
      <div><label>min</label><input type="number" min="0" bind:value={workout.duration_min} /></div>
      <div><label>type</label><input bind:value={workout.type} placeholder="strength" /></div>
    </div>
    <button disabled={busy}>Log workout</button>
  </form>

  <button class="secondary" onclick={() => { clearToken(); authed = false; }}>Sign out</button>
{/if}

{#if toast}<div class="toast">{toast}</div>{/if}
