"use client";

/* The balance, for a settings section (2026-10-11). The shell already
   keeps one for the header's pill, but it says only "a balance" or
   "nothing" -- a page that IS the balance has to tell "still asking" from
   "could not be read". So this asks for itself, paints the shell's copy
   meanwhile, and re-reads when anything announces that credit moved, as
   the shell does (BALANCE_EVENT; QUEUE_EVENT is when a hold settles). */
import { useCallback, useEffect, useState } from "react";
import { BALANCE_EVENT, QUEUE_EVENT, getBalance, type Balance } from "@/lib/studio-api";
import { useShell } from "@/components/studio/shell";
import { errorText } from "@/components/studio/settings/ui";

export function useBalance(): {
  balance: Balance | null;
  /** asked, and nothing to show yet */
  loading: boolean;
  /** asked, and it could not be read (and there is no older copy to show) */
  error: string | null;
  reload: () => void;
} {
  const { me, balance: fromShell } = useShell();
  const account = me?.account?.id ?? null;
  const [read, setRead] = useState<{ account: number; data: Balance | null; error: string | null } | null>(null);

  const reload = useCallback(() => {
    if (account === null) return;
    getBalance()
      .then((data) => setRead({ account, data, error: null }))
      .catch((err) =>
        // a failed re-read keeps the last good copy on screen
        setRead((was) => ({
          account,
          data: was?.account === account ? was.data : null,
          error: errorText(err, "Could not read your credits"),
        })),
      );
  }, [account]);

  useEffect(() => {
    if (account === null) return;
    reload();
    window.addEventListener(BALANCE_EVENT, reload);
    window.addEventListener(QUEUE_EVENT, reload);
    return () => {
      window.removeEventListener(BALANCE_EVENT, reload);
      window.removeEventListener(QUEUE_EVENT, reload);
    };
  }, [account, reload]);

  const mine = read && read.account === account ? read : null;
  const balance = mine?.data ?? fromShell;
  return {
    balance,
    loading: !balance && !mine,
    error: balance ? null : (mine?.error ?? null),
    reload,
  };
}
