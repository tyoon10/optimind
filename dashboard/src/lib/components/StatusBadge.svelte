<script lang="ts">
  // Status is never colour alone. Every state carries a glyph AND a word, so it
  // reads correctly in greyscale, with colour-blindness, and at a glance.
  import type { IntegrityStatus, RoutineState, SourceStatus } from "$lib/types";

  let {
    state,
    label,
    size = "md",
  }: {
    state: RoutineState | IntegrityStatus | SourceStatus;
    label?: string;
    size?: "sm" | "md";
  } = $props();

  const MAP: Record<string, { glyph: string; text: string; tone: string; title: string }> = {
    // routine outcomes
    done: { glyph: "✓", text: "Done", tone: "done", title: "Recorded as completed" },
    skipped: { glyph: "–", text: "Skipped", tone: "neutral", title: "You said you didn't do it — a real observation" },
    not_reported: { glyph: "?", text: "Not reported", tone: "neutral", title: "Never asked or never answered — not a miss" },
    missing: { glyph: "○", text: "Missing", tone: "missing", title: "Was due, the day closed, nothing was recorded" },
    not_due: { glyph: "·", text: "Not due", tone: "neutral", title: "Not scheduled for this day" },
    scheduled: { glyph: "◷", text: "Scheduled", tone: "neutral", title: "Due later today" },
    unknown: { glyph: "?", text: "Unknown", tone: "neutral", title: "No evidence either way" },

    // day integrity
    matched: { glyph: "✓", text: "Matched", tone: "done", title: "Both records agree" },
    journal_only: { glyph: "◑", text: "Journal only", tone: "journal", title: "The journal has it, the structured log lost it — a write defect, not a behavior gap" },
    structured_only: { glyph: "◐", text: "Structured only", tone: "journal", title: "The structured log has it, the audit log never recorded it" },
    mixed: { glyph: "◒", text: "Mixed", tone: "journal", title: "Divergence in both directions" },
    needs_input: { glyph: "!", text: "Needs you", tone: "missing", title: "The journal line is incomplete — only you can complete it" },
    blackout: { glyph: "—", text: "No entry", tone: "neutral", title: "No turn occurred and nothing was captured" },
    no_data: { glyph: "—", text: "No facts", tone: "neutral", title: "Turns occurred but produced no structured fact" },
    in_progress: { glyph: "●", text: "Today", tone: "neutral", title: "Still in progress — never counted as a miss" },

    // provenance
    json_confirmed: { glyph: "✓", text: "Recorded", tone: "done", title: "In the structured record" },
    journal_confirmed: { glyph: "◑", text: "Journal only", tone: "journal", title: "Real, but the structured write lost it" },
    estimated: { glyph: "≈", text: "Estimated", tone: "missing", title: "Inferred from a description, not stated" },
    backfilled: { glyph: "↺", text: "Backfilled", tone: "journal", title: "Reconstructed from journal evidence" },
  };

  const info = $derived(MAP[state] ?? MAP.unknown);
</script>

<span class="badge {info.tone}" class:tiny={size === "sm"} title={info.title}>
  <span class="glyph" aria-hidden="true">{info.glyph}</span>
  <span>{label ?? info.text}</span>
</span>
