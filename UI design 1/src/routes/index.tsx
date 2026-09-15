import { createFileRoute } from "@tanstack/react-router";
import { ICStudioApp } from "@/ic/App";

export const Route = createFileRoute("/")({
  head: () => ({
    meta: [
      { title: "Axiom IC Studio — Analog IC Design Workstation" },
      {
        name: "description",
        content:
          "Interactive mock workstation for custom analog and mixed-signal IC design: schematic, layout, simulation, waveforms, DRC/LVS and extraction.",
      },
      { property: "og:title", content: "Axiom IC Studio — Analog IC Design Workstation" },
      {
        property: "og:description",
        content:
          "Schematic capture, layout, simulation explorer, waveform analysis, and physical verification in one dense engineering UI.",
      },
      { property: "og:type", content: "website" },
      { name: "twitter:card", content: "summary_large_image" },
    ],
  }),
  component: ICStudioApp,
});
