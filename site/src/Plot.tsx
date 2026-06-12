import { useEffect, useRef } from "react";

interface PlotProps {
  title: string;
  data: unknown[];
  shapes?: unknown[];
}

export default function Plot({ title, data, shapes = [] }: PlotProps) {
  const ref = useRef<HTMLDivElement | null>(null);
  useEffect(() => {
    let cancelled = false;
    import("plotly.js-dist-min").then((module) => {
      if (!ref.current || cancelled) return;
      const Plotly = module.default;
      Plotly.newPlot(ref.current, data, {
        title,
        paper_bgcolor: "transparent",
        plot_bgcolor: "transparent",
        font: { family: "Inter, Arial, sans-serif", color: "currentColor" },
        margin: { l: 56, r: 24, t: 56, b: 48 },
        shapes,
        xaxis: { showgrid: false },
        yaxis: { gridcolor: "rgba(120,120,120,.18)" }
      }, { displayModeBar: false, responsive: true });
    });
    return () => {
      cancelled = true;
      if (ref.current) {
        import("plotly.js-dist-min").then((module) => module.default.purge(ref.current as HTMLDivElement));
      }
    };
  }, [data, shapes, title]);
  return <div className="plot" ref={ref} role="img" aria-label={title} />;
}
