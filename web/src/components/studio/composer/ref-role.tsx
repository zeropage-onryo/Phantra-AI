"use client";

/* What an attached reference is FOR (lib/ref-roles.ts; src/ref_roles.py):
   one word on the reference's chip, picked from the server's menu. With no
   role the reference reads as it always did, so the control stays quiet
   until it is used -- "for…" -- and shows the role once there is one.

   Draws nothing while the menu has not arrived. */
import { useEffect, useRef, useState } from "react";
import type { RoleOption } from "@/lib/ref-roles";

export function RefRole({
  options,
  value,
  label,
  name,
  onChange,
}: {
  options: RoleOption[];
  value: string;
  /** the role's word, "" when the reference has none */
  label: string;
  /** the reference's own name, for the button's label */
  name: string;
  onChange: (role: string | null) => void;
}) {
  const [open, setOpen] = useState(false);
  const box = useRef<HTMLSpanElement>(null);
  useEffect(() => {
    if (!open) return;
    const off = (e: PointerEvent) => {
      if (!box.current?.contains(e.target as Node)) setOpen(false);
    };
    const esc = (e: KeyboardEvent) => {
      if (e.key === "Escape") setOpen(false);
    };
    document.addEventListener("pointerdown", off);
    document.addEventListener("keydown", esc);
    return () => {
      document.removeEventListener("pointerdown", off);
      document.removeEventListener("keydown", esc);
    };
  }, [open]);
  if (!options.length) return null;
  const pick = (role: string | null) => {
    onChange(role);
    setOpen(false);
  };
  return (
    <span className="pillwrap zc-rolewrap" ref={box}>
      <button
        type="button"
        className={`zc-role${label ? " on" : ""}`}
        aria-haspopup="menu"
        aria-expanded={open}
        aria-label={label ? `${name} is for: ${label}. Change` : `Say what ${name} is for`}
        title="What to take from this reference"
        onClick={() => setOpen((v) => !v)}
      >
        {label || "for…"}
      </button>
      {open ? (
        <span className="pillmenu zc-rolemenu" role="menu">
          <span className="m">Take from this reference</span>
          {options.map((o) => (
            <button type="button" key={o.id} role="menuitem" aria-current={o.id === value ? "true" : undefined} onClick={() => pick(o.id)}>
              {o.label}
              <small>{o.look_only ? "only this, nothing else from it" : "what the picture is of"}</small>
            </button>
          ))}
          {value ? (
            <button type="button" role="menuitem" onClick={() => pick(null)}>
              No role
              <small>read it as before</small>
            </button>
          ) : null}
        </span>
      ) : null}
    </span>
  );
}
