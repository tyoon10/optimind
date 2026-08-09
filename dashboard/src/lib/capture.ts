import type { FieldWrite } from "./writeDaily";

/** Declarative description of one capture form. */
export interface CaptureField {
  field: string;
  label: string;
  kind: "time" | "score" | "number" | "text";
  placeholder?: string;
  max?: number;
}

export interface CaptureSpec {
  title: string;
  hint?: string;
  fields: CaptureField[];
  /** Fields submitted together as ONE event entry (a meal, a coffee). */
  grouped?: boolean;
  groupField?: string;
}

export type { FieldWrite };
