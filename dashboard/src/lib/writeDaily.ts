// The dashboard's dual-write — the GitHub-API mirror of optimind-sdk do_log_field.
// Every logField call writes BOTH daily/<date>.json (structured) AND a `### HH:MM |
// Dashboard` mirror line in journal/<date>.md (audit log), so dashboard inputs reach
// the reflection / long-term-memory pipeline. Isolated here so the write target
// (GitHub API now → a backend later) is a one-file swap.

import {
  type DailyLog, type ProtocolItem,
  applyField, mirrorLine, newDoc, nowHHMM, nowOffsetISO, renderValue, todayNYC, SCHEMA_VERSION, TZ_NAME,
} from "./daily";
import { getFile, putFile, type RepoRef } from "./github";

const dailyPath = (d: string) => `daily/${d}.json`;
const journalPath = (d: string) => `journal/${d}.md`;

async function loadDaily(ref: RepoRef, date: string): Promise<{ doc: DailyLog; sha: string | null }> {
  const { text, sha } = await getFile(ref, dailyPath(date));
  return { doc: text ? (JSON.parse(text) as DailyLog) : newDoc(date), sha };
}

/**
 * Log one structured field with the mandatory dual-write.
 * `value` should already be structured for event categories
 * (e.g. caffeine -> {amount_mg, source}); the dashboard forms provide that.
 */
export async function logField(
  ref: RepoRef, field: string, value: any, time?: string, date?: string,
): Promise<void> {
  const d = date ?? todayNYC();
  const t = time ?? nowHHMM();

  // 1. structured write
  const { doc, sha } = await loadDaily(ref, d);
  const written = applyField(doc, field, value, t);
  const newSha = await putFile(ref, dailyPath(d), JSON.stringify(doc, null, 2) + "\n",
    `daily ${d}: ${field}`, sha);

  // 2. journal mirror (read-append-write; create if absent)
  try {
    const j = await getFile(ref, journalPath(d));
    const body = (j.text ?? "") + mirrorLine(t, field, renderValue(written));
    await putFile(ref, journalPath(d), body, `journal ${d}: [Dashboard] ${field}`, j.sha);
  } catch (e) {
    // Structured write already committed; surface the mirror failure to the caller.
    throw new Error(`daily written (sha ${newSha}) but journal mirror failed: ${(e as Error).message}`);
  }
}

/** Read today's (or a given date's) structured log. */
export async function getDaily(ref: RepoRef, date?: string): Promise<DailyLog> {
  return (await loadDaily(ref, date ?? todayNYC())).doc;
}

/** Write the protocol block (used by the dashboard if it ever sets a plan; usually the morning Routine does). */
export async function setProtocol(
  ref: RepoRef, items: ProtocolItem[], source = "default", date?: string,
): Promise<void> {
  const d = date ?? todayNYC();
  const { doc, sha } = await loadDaily(ref, d);
  doc.schema_version = SCHEMA_VERSION;
  doc.tz = TZ_NAME;
  doc.protocol = { generated_at: nowOffsetISO(), source, items };
  await putFile(ref, dailyPath(d), JSON.stringify(doc, null, 2) + "\n", `daily ${d}: protocol`, sha);
}
