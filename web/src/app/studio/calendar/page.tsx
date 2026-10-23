"use client";

/* /studio/calendar (2026-10-22, docs/tasks/task-calendar.md): what goes
   out, where and when. The page is the Calendar component; everything it
   reads and writes is /api/posts and /api/social, and nothing on it
   spends credits. */
import { Calendar } from "@/components/studio/calendar/calendar";

export default function CalendarPage() {
  return <Calendar />;
}
