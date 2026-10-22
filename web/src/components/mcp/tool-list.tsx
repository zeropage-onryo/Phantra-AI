// The tool list of an MCP documentation page (/mcp, /mcp/claude): the server's
// tools in groups, each group one line on what it does. Plain server HTML on
// purpose: both pages are the documentation URL a directory listing names, and
// a reviewer's fetch reads the list without running anything. The names are
// the server's own (src/mcp_server.py LISTED_TOOLS / CLAUDE_LISTED_TOOLS);
// `spends` marks a group whose tools spend credits, always after a quote and a
// yes.

export type ToolGroup = { tools: string[]; does: string; spends?: boolean };

export function toolCount(groups: ToolGroup[]): number {
  return groups.reduce((n, g) => n + g.tools.length, 0);
}

export function ToolList({ groups }: { groups: ToolGroup[] }) {
  return (
    <div className="mx-auto mt-12 max-w-[960px] divide-y divide-border border-y border-border">
      {groups.map((g) => (
        <div key={g.tools.join(",")} className="grid gap-3 py-5 md:grid-cols-[minmax(0,2fr)_minmax(0,3fr)] md:gap-8">
          <div className="flex flex-wrap items-start gap-1.5">
            {g.tools.map((t) => (
              <code
                key={t}
                className="rounded-md border border-border bg-secondary px-2 py-0.5 font-mono text-[13px] text-foreground"
              >
                {t}
              </code>
            ))}
            {g.spends && (
              <span className="rounded-md bg-[var(--primary)]/15 px-2 py-0.5 text-[12px] font-medium text-foreground">
                spends credits, after a quote and a yes
              </span>
            )}
          </div>
          <p className="text-[15.5px] leading-relaxed text-[var(--ink-2)]">{g.does}</p>
        </div>
      ))}
    </div>
  );
}
