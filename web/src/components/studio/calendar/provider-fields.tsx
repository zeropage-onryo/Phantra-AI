"use client";

/* A platform's own per-post form (2026-10-22, docs/tasks/task-social-providers.md):
   the fields the provider's SETTINGS declares (a subreddit, a flair, a
   story-or-reel switch), drawn the same way in the calendar's drawer and
   the Library's Post… panel. `missing()` says which required fields are
   empty, so a press is disabled rather than refused by the server. */
import type { ProviderField } from "@/lib/studio-api";

export type Values = Record<string, unknown>;

export function missing(fields: ProviderField[], values: Values): string[] {
  return fields.filter((f) => f.required && !String(values[f.key] ?? "").trim()).map((f) => f.label);
}

export function ProviderFields({
  fields,
  values,
  onChange,
  disabled,
  compact,
}: {
  fields: ProviderField[];
  values: Values;
  onChange: (next: Values) => void;
  disabled?: boolean;
  compact?: boolean;
}) {
  if (!fields.length) return null;
  const set = (key: string, value: unknown) => onChange({ ...values, [key]: value });
  return (
    <div className={`cal-pf${compact ? " compact" : ""}`}>
      {fields.map((f) => {
        const id = `pf-${f.key}`;
        if (f.type === "boolean") {
          return (
            <label key={f.key} className="cal-pf-check">
              <input type="checkbox" checked={!!values[f.key]} onChange={(e) => set(f.key, e.target.checked)} disabled={disabled} />
              {f.label}
            </label>
          );
        }
        if (f.type === "select") {
          return (
            <label key={f.key} className="cal-pf-row">
              <span>{f.label}</span>
              <select className="cal-in" value={String(values[f.key] ?? f.options?.[0]?.id ?? "")} onChange={(e) => set(f.key, e.target.value)} disabled={disabled} id={id}>
                {(f.options ?? []).map((o) => (
                  <option key={o.id} value={o.id}>
                    {o.label}
                  </option>
                ))}
              </select>
            </label>
          );
        }
        return (
          <label key={f.key} className="cal-pf-row">
            <span>
              {f.label}
              {f.required ? " *" : ""}
            </span>
            <input className="cal-in" type="text" value={String(values[f.key] ?? "")} placeholder={f.placeholder} onChange={(e) => set(f.key, e.target.value)} disabled={disabled} id={id} />
            {f.hint ? <small>{f.hint}</small> : null}
          </label>
        );
      })}
    </div>
  );
}
