// The dashboard's dual-write — the GitHub-API mirror of optimind-sdk do_log_field.
//
// Every submission writes BOTH daily/<date>.json (structured) and a
// `### HH:MM | Dashboard` mirror line in journal/<date>.md (audit log), so
// dashboard input reaches the same reflection / long-term-memory pipeline as
// chat input.
//
// Both files land in ONE commit. The previous implementation issued two
// Contents-API PUTs; when the second failed, git history kept a state the data
// model forbids — a structured record with no mirror, or a mirror with no
// record. That is the same class of defect that lost 8/4–8/6, just at the
// repository layer instead of the writer layer.

import {
  type DailyLog, type ProtocolItem,
  applyField, mirrorLine, newDoc, nowHHMM, nowOffsetISO, renderValue, todayNYC, SCHEMA_VERSION, TZ_NAME,
} from "./daily";
import { commitPair, getFile, putFile, type CommitResult, type RepoRef } from "./github";

const dailyPath = (d: string) => `daily/${d}.json`;
const journalPath = (d: string) => `journal/${d}.md`;

/** One field to write. `value` is already structured for event categories. */
export interface FieldWrite {
  field: string;
  value: any;
  time?: string;
}

export interface WriteReport extends CommitResult {
  date: string;
  fields: string[];
  verified: boolean;
}

async function loadDaily(ref: RepoRef, date: string): Promise<{ doc: DailyLog; sha: string | null }> {
  const { text, sha } = await getFile(ref, dailyPath(date));
  return { doc: text ? (JSON.parse(text) as DailyLog) : newDoc(date), sha };
}

/**
 * Write a batch of fields for one date as a single verified pair commit.
 *
 * Backfilling a day means eight or ten fields; one commit per field would make
 * the audit log unreadable and leave partial states between each. The whole
 * batch is applied in memory first, so the JSON and every mirror line come from
 * the same operation.
 */
export async function logFields(
  ref: RepoRef, writes: FieldWrite[], date?: string,
): Promise<WriteReport> {
  const d = date ?? todayNYC();
  if (!writes.length) throw new Error("logFields: nothing to write");

  const { doc } = await loadDaily(ref, d);
  const journal = await getFile(ref, journalPath(d));

  let mirrors = "";
  for (const w of writes) {
    const t = w.time ?? nowHHMM();
    const written = applyField(doc, w.field, w.value, t);
    mirrors += mirrorLine(t, w.field, renderValue(written));
  }

  const dailyText = JSON.stringify(doc, null, 2) + "\n";
  const journalText = (journal.text ?? "") + mirrors;
  const fields = writes.map((w) => w.field);
  const summary = fields.length === 1 ? fields[0] : `${fields.length} fields`;

  const result = await commitPair(
    ref,
    [
      { path: dailyPath(d), text: dailyText },
      { path: journalPath(d), text: journalText },
    ],
    `daily ${d}: ${summary}`,
  );

  // Postcondition: re-fetch both paths and confirm the data is actually there.
  // A commit that succeeded at the API level still has to be readable back.
  const verified = await verifyPair(ref, d, doc, mirrors);
  if (!verified) {
    throw new Error(
      `commit ${result.sha.slice(0, 7)} landed but verification failed for ${d}. ` +
      `Run: python3 scripts/audit_dual_write.py --start ${d} --end ${d}`,
    );
  }

  return { ...result, date: d, fields, verified };
}

/** Read both paths back and confirm the structured field and mirror survived. */
async function verifyPair(
  ref: RepoRef, date: string, expected: DailyLog, mirrors: string,
): Promise<boolean> {
  const [d, j] = await Promise.all([
    getFile(ref, dailyPath(date)),
    getFile(ref, journalPath(date)),
  ]);
  if (!d.text || !j.text) return false;
  try {
    if (JSON.stringify(JSON.parse(d.text).log) !== JSON.stringify(expected.log)) return false;
  } catch {
    return false;
  }
  return mirrors
    .split("\n")
    .filter((l) => l.startsWith("["))
    .every((l) => j.text!.includes(l));
}

/** Log a single structured field with the mandatory dual-write. */
export async function logField(
  ref: RepoRef, field: string, value: any, time?: string, date?: string,
): Promise<WriteReport> {
  return logFields(ref, [{ field, value, time }], date);
}

/** Read a given date's structured log. */
export async function getDaily(ref: RepoRef, date?: string): Promise<DailyLog> {
  return (await loadDaily(ref, date ?? todayNYC())).doc;
}

/** Read a date's raw journal markdown (evidence for backfill and day detail). */
export async function getJournal(ref: RepoRef, date: string): Promise<string | null> {
  return (await getFile(ref, journalPath(date))).text;
}

/** Write the protocol block. Usually the morning Routine does this, not the UI. */
export async function setProtocol(
  ref: RepoRef, items: ProtocolItem[], source = "default", date?: string,
): Promise<void> {
  const d = date ?? todayNYC();
  const { doc, sha } = await loadDaily(ref, d);
  doc.schema_version = SCHEMA_VERSION;
  doc.tz = TZ_NAME;
  doc.protocol = { generated_at: nowOffsetISO(), source, items };
  // Protocol touches only one file, so a single Contents PUT is still correct —
  // there is no pair to keep atomic.
  await putFile(ref, dailyPath(d), JSON.stringify(doc, null, 2) + "\n", `daily ${d}: protocol`, sha);
}
