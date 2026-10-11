"use client";

/* The settings area's shared pieces (2026-10-11): every section is built
   out of these, so the six of them read as one page family. They replaced
   the old page's CARD / BTN / PRI / GHOST / FIELD class strings.

   The look is settings.css; nothing here knows a colour. */
import {
  useId,
  type ButtonHTMLAttributes,
  type ComponentType,
  type InputHTMLAttributes,
  type KeyboardEvent,
  type ReactNode,
  type SelectHTMLAttributes,
} from "react";
import { CircleCheck, Info, TriangleAlert } from "lucide-react";
import "@/components/studio/settings/settings.css";

type Icon = ComponentType<{ strokeWidth?: number; "aria-hidden"?: boolean }>;

/** A section's title and its one line, with room for an action on the right. */
export function SectionHeader({
  title,
  description,
  action,
}: {
  title: string;
  description?: string;
  action?: ReactNode;
}) {
  return (
    <header className="zset-head">
      <div className="zset-head-row">
        <div>
          <h2>{title}</h2>
          {description ? <p>{description}</p> : null}
        </div>
        {action}
      </div>
    </header>
  );
}

/** A labelled group: its name above, then one card. `pad` for a card that
 *  holds something other than rows. */
export function SettingsCard({
  title,
  description,
  pad,
  children,
}: {
  title?: string;
  description?: string;
  pad?: boolean;
  children: ReactNode;
}) {
  const id = useId();
  return (
    <section className="zset-group" aria-labelledby={title ? id : undefined}>
      {title ? (
        <div className="zset-group-head">
          <h3 id={id}>{title}</h3>
          {description ? <p>{description}</p> : null}
        </div>
      ) : null}
      <div className={`zset-card${pad ? " zset-card-pad" : ""}`}>{children}</div>
    </section>
  );
}

/** Label and hint on the left, the control on the right (stacked under
 *  640px). `wide` puts the control under the label at any width -- for a
 *  form that needs the whole row. `htmlFor` binds the label to an input. */
export function Row({
  label,
  hint,
  control,
  htmlFor,
  wide,
}: {
  label: ReactNode;
  hint?: ReactNode;
  control?: ReactNode;
  htmlFor?: string;
  wide?: boolean;
}) {
  return (
    <div className="zset-row" data-wide={wide ? "1" : undefined}>
      <div className="zset-row-text">
        {htmlFor ? (
          <label className="zset-row-label" htmlFor={htmlFor}>
            {label}
          </label>
        ) : (
          <span className="zset-row-label">{label}</span>
        )}
        {hint ? <p className="zset-row-hint">{hint}</p> : null}
      </div>
      {control ? <div className="zset-row-control">{control}</div> : null}
    </div>
  );
}

export const Divider = () => <hr className="zset-divider" />;

/** The red-bordered group for what cannot be taken back. Last on its page. */
export function DangerZone({ title = "Danger zone", children }: { title?: string; children: ReactNode }) {
  const id = useId();
  return (
    <section className="zset-group zset-danger" aria-labelledby={id}>
      <div className="zset-group-head">
        <h3 id={id}>{title}</h3>
      </div>
      <div className="zset-card">{children}</div>
    </section>
  );
}

export type Tone = "neutral" | "ok" | "warn" | "signal";

export function Badge({ tone = "neutral", children }: { tone?: Tone; children: ReactNode }) {
  return (
    <span className="zset-badge" data-tone={tone === "neutral" ? undefined : tone}>
      {children}
    </span>
  );
}

/** A figure and what it counts. `hero` is the one big number on a page. */
export function Stat({
  value,
  label,
  size,
  tone,
}: {
  value: ReactNode;
  label: ReactNode;
  size?: "hero";
  tone?: "signal";
}) {
  return (
    <div className="zset-stat" data-size={size} data-tone={tone}>
      <span className="zset-stat-value">{value}</span>
      <span className="zset-stat-label">{label}</span>
    </div>
  );
}

type ButtonProps = ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: "primary" | "ghost" | "danger" | "quiet";
  size?: "sm";
};

/** Primary is white on black; danger is the signal; the rest are outlines. */
export function Button({ variant = "ghost", size, type = "button", className, ...rest }: ButtonProps) {
  return (
    <button
      type={type}
      className={`zset-btn${className ? ` ${className}` : ""}`}
      data-variant={variant}
      data-size={size}
      {...rest}
    />
  );
}

/** the button look on something that is not a button (a link out) */
export const buttonClass = "zset-btn";

export function Field({ className, ...rest }: InputHTMLAttributes<HTMLInputElement>) {
  return <input className={`zset-field${className ? ` ${className}` : ""}`} {...rest} />;
}

export function Select({ className, ...rest }: SelectHTMLAttributes<HTMLSelectElement>) {
  return <select className={`zset-field${className ? ` ${className}` : ""}`} {...rest} />;
}

/** Two or three exclusive choices on one line. A radio group to a screen
 *  reader and to the arrow keys. */
export function Segmented<T extends string>({
  label,
  value,
  options,
  onChange,
}: {
  /** what the choice is about, for a screen reader */
  label: string;
  value: T;
  options: { id: T; label: string }[];
  onChange: (id: T) => void;
}) {
  const move = (e: KeyboardEvent<HTMLDivElement>) => {
    const delta = e.key === "ArrowRight" || e.key === "ArrowDown" ? 1 : e.key === "ArrowLeft" || e.key === "ArrowUp" ? -1 : 0;
    if (!delta) return;
    e.preventDefault();
    const at = options.findIndex((o) => o.id === value);
    const next = options[(at + delta + options.length) % options.length];
    onChange(next.id);
    // focus follows the choice, as it does in a native radio group
    const buttons = e.currentTarget.querySelectorAll<HTMLButtonElement>("button");
    buttons[options.indexOf(next)]?.focus();
  };
  return (
    <div className="zset-seg" role="radiogroup" aria-label={label} onKeyDown={move}>
      {options.map((o) => (
        <button
          key={o.id}
          type="button"
          role="radio"
          aria-checked={o.id === value}
          tabIndex={o.id === value ? 0 : -1}
          onClick={() => onChange(o.id)}
        >
          {o.label}
        </button>
      ))}
    </div>
  );
}

export function Switch({
  checked,
  onChange,
  label,
  disabled,
  id,
}: {
  checked: boolean;
  onChange: (on: boolean) => void;
  /** what it turns on, for a screen reader (the row's label, usually) */
  label: string;
  disabled?: boolean;
  id?: string;
}) {
  return (
    <button
      id={id}
      type="button"
      role="switch"
      className="zset-switch"
      aria-checked={checked}
      aria-label={label}
      disabled={disabled}
      onClick={() => onChange(!checked)}
    />
  );
}

/** One of a row of filters; the chosen one is filled. */
export function Chip({ pressed, onClick, children }: { pressed: boolean; onClick: () => void; children: ReactNode }) {
  return (
    <button type="button" className="zset-chip" aria-pressed={pressed} onClick={onClick}>
      {children}
    </button>
  );
}

/** Something to tell the person: an error, a limit of this server, a done. */
export function Notice({
  tone = "info",
  children,
}: {
  tone?: "info" | "err" | "ok";
  children: ReactNode;
}) {
  const Glyph = tone === "err" ? TriangleAlert : tone === "ok" ? CircleCheck : Info;
  return (
    <div className="zset-notice" data-tone={tone === "info" ? undefined : tone} role={tone === "err" ? "alert" : "status"}>
      <Glyph strokeWidth={1.7} aria-hidden />
      <div>{children}</div>
    </div>
  );
}

/** What a card says when it has nothing to list yet. */
export function EmptyState({
  icon: Glyph,
  title,
  children,
  action,
}: {
  icon?: Icon;
  title: string;
  children?: ReactNode;
  action?: ReactNode;
}) {
  return (
    <div className="zset-empty">
      {Glyph ? <Glyph strokeWidth={1.5} aria-hidden /> : null}
      <b>{title}</b>
      {children ? <p>{children}</p> : null}
      {action}
    </div>
  );
}

/** A bar the width of the text that is on its way. */
export function Skeleton({ width = "60%", height }: { width?: number | string; height?: number }) {
  return <span className="zset-skel" style={{ width, height }} aria-hidden />;
}

/** Rows' worth of skeleton, for a card whose data has not answered yet. */
export function SkeletonRows({ rows = 3 }: { rows?: number }) {
  return (
    <div aria-busy="true" aria-label="Loading">
      {Array.from({ length: rows }, (_, i) => (
        <div className="zset-row" key={i}>
          <div className="zset-row-text" style={{ display: "grid", gap: 8 }}>
            <Skeleton width={i % 2 ? "34%" : "26%"} />
            <Skeleton width={i % 2 ? "52%" : "64%"} height={10} />
          </div>
          <Skeleton width={72} height={28} />
        </div>
      ))}
    </div>
  );
}

export const errorText = (err: unknown, fallback: string) =>
  err instanceof Error && err.message ? err.message : fallback;
