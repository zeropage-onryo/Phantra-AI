import { Suspense } from "react";
import { notFound } from "next/navigation";
import { ProjectHome } from "@/components/studio/project-home";
import { ProjectWorkspace } from "@/components/studio/project-workspace";

/* A project (2026-11-02, Mike's pick "B2"): its HOME -- the cover, the two
   doors, the brand kit, its sessions and workflows (components/studio/
   project-home.tsx) -- unless the address names the canvas. ?scene= (and
   &shot=), ?view=canvas and ?new=1 open the workspace: its scenes, the
   Director canvas and the brief (components/studio/project-workspace.tsx),
   which is where every scene link written before 2026-11-02 points. */
export default async function ProjectPage({
  params,
  searchParams,
}: {
  params: Promise<{ id: string }>;
  searchParams: Promise<{ scene?: string; view?: string; new?: string }>;
}) {
  const { id } = await params;
  if (!/^\d+$/.test(id)) notFound();
  const q = await searchParams;
  const canvas = !!q.scene || q.view === "canvas" || q.new === "1";
  return (
    <Suspense fallback={null}>
      {canvas ? <ProjectWorkspace key={id} id={Number(id)} /> : <ProjectHome key={id} id={Number(id)} />}
    </Suspense>
  );
}
