// The black, moving ground of /mcp (after higgsfield.ai/mcp): three slow
// colour fields drifting over black, a masked grid and a vignette. CSS only
// (`.mcp-aurora` in globals.css), transform and opacity, and still under
// reduced motion. Decorative, so hidden from assistive tech.
export function Aurora() {
  return (
    <div aria-hidden className="mcp-aurora pointer-events-none absolute inset-0 -z-10 overflow-hidden bg-black">
      <span className="mcp-orb mcp-orb-a" />
      <span className="mcp-orb mcp-orb-b" />
      <span className="mcp-orb mcp-orb-c" />
      <span className="mcp-grid" />
      <span className="absolute inset-0 bg-[radial-gradient(ellipse_at_center,transparent_30%,rgba(0,0,0,0.85)_100%)]" />
    </div>
  );
}
