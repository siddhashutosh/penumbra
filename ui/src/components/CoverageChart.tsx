// Coverage-by-lead + reliability diagram + skill curve (FR-UI-3), Canvas.
import { useEffect, useRef, useState } from "react";
import type { CalibrationReport } from "../types";

const AMBER = "#ffb454";
const TEAL = "#4fd4c4";
const OK = "#6ee787";
const GRID = "rgba(69, 52, 19, 0.5)";
const DIM = "#a08a6c";

type Kind = "coverage" | "reliability" | "skill";

export default function CoverageChart({ data, kind }: { data: CalibrationReport; kind: Kind }) {
  const ref = useRef<HTMLCanvasElement>(null);
  const [w, setW] = useState(500);
  const H = 260;
  const PAD = { l: 42, r: 14, t: 14, b: 30 };

  useEffect(() => {
    const onResize = () => {
      const p = ref.current?.parentElement;
      if (p) setW(p.clientWidth);
    };
    onResize();
    window.addEventListener("resize", onResize);
    return () => window.removeEventListener("resize", onResize);
  }, []);

  useEffect(() => {
    const canvas = ref.current;
    if (!canvas) return;
    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    canvas.width = w * dpr;
    canvas.height = H * dpr;
    canvas.style.width = w + "px";
    canvas.style.height = H + "px";
    const ctx = canvas.getContext("2d")!;
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.clearRect(0, 0, w, H);
    const plotW = w - PAD.l - PAD.r;
    const plotH = H - PAD.t - PAD.b;
    ctx.font = "10px 'IBM Plex Mono', monospace";
    ctx.fillStyle = DIM;

    if (kind === "coverage") {
      const rows = data.coverage_by_lead;
      const X = (i: number) => PAD.l + (i / (rows.length - 1)) * plotW;
      const Y = (v: number) => PAD.t + plotH - v * plotH;
      // y grid 0..1
      for (let k = 0; k <= 5; k++) {
        const v = k / 5, y = Y(v);
        ctx.strokeStyle = GRID; ctx.beginPath();
        ctx.moveTo(PAD.l, y); ctx.lineTo(w - PAD.r, y); ctx.stroke();
        ctx.textAlign = "right"; ctx.fillText(v.toFixed(1), PAD.l - 5, y + 3);
      }
      // target 0.9 line
      ctx.strokeStyle = OK; ctx.setLineDash([4, 4]);
      ctx.beginPath(); ctx.moveTo(PAD.l, Y(0.9)); ctx.lineTo(w - PAD.r, Y(0.9)); ctx.stroke();
      ctx.setLineDash([]);
      ctx.fillStyle = OK; ctx.textAlign = "left"; ctx.fillText("target 0.90", PAD.l + 4, Y(0.9) - 4);
      // empirical 90 line
      const line = (key: "empirical_90" | "empirical_50", color: string) => {
        ctx.strokeStyle = color; ctx.lineWidth = 2; ctx.beginPath();
        rows.forEach((r, i) => {
          const x = X(i), y = Y(r[key]);
          i === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y);
        });
        ctx.stroke();
      };
      line("empirical_90", AMBER);
      line("empirical_50", TEAL);
      ctx.fillStyle = DIM; ctx.textAlign = "center";
      ctx.fillText("lead time (days) →", PAD.l + plotW / 2, H - 8);
    } else if (kind === "reliability") {
      const rows = data.kp_reliability;
      const X = (v: number) => PAD.l + v * plotW;
      const Y = (v: number) => PAD.t + plotH - v * plotH;
      for (let k = 0; k <= 5; k++) {
        const v = k / 5;
        ctx.strokeStyle = GRID;
        ctx.beginPath(); ctx.moveTo(PAD.l, Y(v)); ctx.lineTo(w - PAD.r, Y(v)); ctx.stroke();
        ctx.textAlign = "right"; ctx.fillStyle = DIM; ctx.fillText(v.toFixed(1), PAD.l - 5, Y(v) + 3);
      }
      // perfect-reliability diagonal
      ctx.strokeStyle = OK; ctx.setLineDash([4, 4]);
      ctx.beginPath(); ctx.moveTo(X(0), Y(0)); ctx.lineTo(X(1), Y(1)); ctx.stroke();
      ctx.setLineDash([]);
      // points
      ctx.fillStyle = AMBER;
      rows.forEach((r) => {
        ctx.beginPath();
        ctx.arc(X(r.predicted), Y(r.observed), 3 + Math.min(r.count / 20, 4), 0, Math.PI * 2);
        ctx.fill();
      });
      ctx.fillStyle = DIM; ctx.textAlign = "center";
      ctx.fillText("predicted storm prob →", PAD.l + plotW / 2, H - 8);
    } else {
      const rows = data.skill_vs_noaa;
      const X = (i: number) => PAD.l + (i / (rows.length - 1)) * plotW;
      const vals = rows.map((r) => r.skill ?? 0);
      const lo = Math.min(-0.05, ...vals), hi = Math.max(0.2, ...vals);
      const Y = (v: number) => PAD.t + plotH - ((v - lo) / (hi - lo)) * plotH;
      for (let k = 0; k <= 5; k++) {
        const v = lo + ((hi - lo) * k) / 5;
        ctx.strokeStyle = GRID;
        ctx.beginPath(); ctx.moveTo(PAD.l, Y(v)); ctx.lineTo(w - PAD.r, Y(v)); ctx.stroke();
        ctx.textAlign = "right"; ctx.fillStyle = DIM; ctx.fillText(v.toFixed(2), PAD.l - 5, Y(v) + 3);
      }
      // zero line
      ctx.strokeStyle = DIM; ctx.setLineDash([4, 4]);
      ctx.beginPath(); ctx.moveTo(PAD.l, Y(0)); ctx.lineTo(w - PAD.r, Y(0)); ctx.stroke();
      ctx.setLineDash([]);
      ctx.strokeStyle = AMBER; ctx.lineWidth = 2; ctx.beginPath();
      rows.forEach((r, i) => {
        const x = X(i), y = Y(r.skill ?? 0);
        i === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y);
      });
      ctx.stroke();
      ctx.fillStyle = DIM; ctx.textAlign = "center";
      ctx.fillText("lead time (days) · skill vs persistence →", PAD.l + plotW / 2, H - 8);
    }
  }, [data, w, kind]);

  return <canvas ref={ref} className="chart" />;
}
