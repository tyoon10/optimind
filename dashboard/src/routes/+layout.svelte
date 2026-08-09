<script lang="ts">
  import "../app.css";
  import { page } from "$app/stores";

  let { children } = $props();

  const NAV = [
    { href: "/", label: "Today", glyph: "◉" },
    { href: "/history", label: "History", glyph: "▤" },
    { href: "/routines", label: "Routines", glyph: "◇" },
    { href: "/insights", label: "Insights", glyph: "◈" },
  ];

  // `/` would prefix-match everything, so it needs an exact test.
  const isCurrent = (href: string) =>
    href === "/" ? $page.url.pathname === "/" : $page.url.pathname.startsWith(href);
</script>

<div class="shell">
  <nav class="sidebar" aria-label="Main">
    <div style="padding:0 10px var(--s-3);">
      <div style="font-weight:600;">OptiMind</div>
      <div class="tiny muted">Record integrity</div>
    </div>
    <div class="stack-sm">
      {#each NAV as item}
        <a class="navlink" href={item.href} aria-current={isCurrent(item.href) ? "page" : undefined}>
          <span class="mono" aria-hidden="true">{item.glyph}</span>
          <span>{item.label}</span>
        </a>
      {/each}
    </div>
  </nav>

  <main class="main">
    {@render children()}
  </main>
</div>

<nav class="tabbar" aria-label="Main">
  {#each NAV as item}
    <a href={item.href} aria-current={isCurrent(item.href) ? "page" : undefined}>
      <span class="mono" aria-hidden="true">{item.glyph}</span>
      <span>{item.label}</span>
      <span class="tab-dot"></span>
    </a>
  {/each}
</nav>
