// F10.7 fan chart (FR-UI-1): observed history, point forecast, nested p25-p75
// and p05-p95 uncertainty bands, NOAA forecast overlaid. Hand-drawn on Canvas.
import { useEffect, useRef, useState } from "react";
import type { F107Forecast } from "../types";

const AMBER = "#ffb454";
const PLASMA = "#ff7a45";
const TEAL = "#4fd4c4";
const GRID = "rgba(69, 52, 19, 0.5)";
const TEXT_DIM = "#a08a6c";

interface Hover { x: number; idx: number; inForecast: boolean }

export default function FanChart({ data }: { data: F107Forecast }) {
  const ref = useRef<HTMLCanvasElement>(null);
  const [hover, setHover] = useState<Hover | null>(null);
  const [w, setW] = useState(900);
  const H = 340;
  const PAD = { l: 46, r: 16, t: 16, b: 26 };

  useEffect(() => {
    const onResize = () => {
      const parent = ref.current?.parentElement;
      if (parent) setW(parent.clientWidth);
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

    const hist = data.history_values;
    const nHist = hist.length;
    const nFc = data.point.length;
    const total = nHist + nFc;

    // y-range across everything
    let lo = Infinity, hi = -Infinity;
    for (const v of hist) { lo = Math.min(lo, v); hi = Math.max(hi, v); }
    for (const v of data.bands.p05) lo = Math.min(lo, v);
    for (const v of data.bands.p95) hi = Math.max(hi, v);
    lo = Math.floor((lo - 5) / 10) * 10;
    hi = Math.ceil((hi + 5) / 10) * 10;

    const plotW = w - PAD.l - PAD.r;
    const plotH = H - PAD.t - PAD.b;
    const X = (i: number) => PAD.l + (i / (total - 1)) * plotW;
    const Y = (v: number) => PAD.t + plotH - ((v - lo) / (hi - lo)) * plotH;

    // grid + y labels
    ctx.font = "10px 'IBM Plex Mono', monospace";
    ctx.fillStyle = TEXT_DIM;
    ctx.textAlign = "right";
    const ticks = 5;
    for (let k = 0; k <= ticks; k++) {
      const v = lo + ((hi - lo) * k) / ticks;
      const y = Y(v);
      ctx.strokeStyle = GRID;
      ctx.lineWidth = 1;
      ctx.beginPath();
      ctx.moveTo(PAD.l, y);
      ctx.lineTo(w - PAD.r, y);
      ctx.stroke();
      ctx.fillText(String(Math.round(v)), PAD.l - 6, y + 3);
    }

    // vertical divider at "now"
    const nowX = X(nHist - 1);
    ctx.strokeStyle = "rgba(160, 138, 108, 0.4)";
    ctx.setLineDash([4, 4]);
    ctx.beginPath();
    ctx.moveTo(nowX, PAD.t);
    ctx.lineTo(nowX, H - PAD.b);
    ctx.stroke();
    ctx.setLineDash([]);
    ctx.fillStyle = TEXT_DIM;
    ctx.textAlign = "center";
    ctx.fillText("issued", nowX, H - PAD.b + 16);
    ctx.textAlign = "left";
    ctx.fillText("+" + nFc + "d", w - PAD.r - 22, H - PAD.b + 16);

    // fan bands (forecast region): start at the last observed point
    const fx = (i: number) => X(nHist - 1 + i);
    const band = (loArr: number[], hiArr: number[], fill: string) => {
      ctx.beginPath();
      ctx.moveTo(fx(0), Y(hist[nHist - 1]));
      for (let i = 0; i < nFc; i++) ctx.lineTo(fx(i + 1), Y(hiArr[i]));
      for (let i = nFc - 1; i >= 0; i--) ctx.lineTo(fx(i + 1), Y(loArr[i]));
      ctx.closePath();
      ctx.fillStyle = fill;
      ctx.fill();
    };
    band(data.bands.p05, data.bands.p95, "rgba(255, 122, 69, 0.14)"); // 90%
    band(data.bands.p25, data.bands.p75, "rgba(255, 180, 84, 0.24)"); // 50%

    // NOAA overlay (dashed)
    ctx.strokeStyle = TEAL;
    ctx.setLineDash([5, 4]);
    ctx.lineWidth = 1.4;
    ctx.beginPath();
    let started = false;
    for (let i = 0; i < nFc; i++) {
      const v = data.noaa_point[i];
      if (v == null) continue;
      const x = fx(i + 1), y = Y(v);
      if (!started) { ctx.moveTo(x, y); started = true; } else ctx.lineTo(x, y);
    }
    ctx.stroke();
    ctx.setLineDash([]);

    // history line
    ctx.strokeStyle = "rgba(246, 233, 212, 0.75)";
    ctx.lineWidth = 1.4;
    ctx.beginPath();
    for (let i = 0; i < nHist; i++) {
      const x = X(i), y = Y(hist[i]);
      if (i === 0) ctx.moveTo(x, y); else ctx.lineTo(x, y);
    }
    ctx.stroke();

    // point forecast (median band p50)
    ctx.strokeStyle = AMBER;
    ctx.lineWidth = 2;
    ctx.beginPath();
    ctx.moveTo(fx(0), Y(hist[nHist - 1]));
    for (let i = 0; i < nFc; i++) ctx.lineTo(fx(i + 1), Y(data.point[i]));
    ctx.stroke();

    // hover readout
    if (hover && hover.inForecast) {
      const i = hover.idx;
      const x = fx(i + 1);
      ctx.strokeStyle = "rgba(255,180,84,0.5)";
      ctx.beginPath(); ctx.moveTo(x, PAD.t); ctx.lineTo(x, H - PAD.b); ctx.stroke();
      const dot = (v: number, c: string) => {
        ctx.fillStyle = c; ctx.beginPath(); ctx.arc(x, Y(v), 3, 0, Math.PI * 2); ctx.fill();
      };
      dot(data.point[i], AMBER);
      dot(data.bands.p05[i], PLASMA);
      dot(data.bands.p95[i], PLASMA);
    }
  }, [data, w, hover]);

  const onMove = (e: React.MouseEvent) => {
    const rect = ref.current!.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const plotW = w - PAD.l - PAD.r;
    const nHist = data.history_values.length;
    const nFc = data.point.length;
    const total = nHist + nFc;
    const frac = (x - PAD.l) / plotW;
    const globalIdx = Math.round(frac * (total - 1));
    const fcIdx = globalIdx - (nHist - 1) - 1;
    if (fcIdx >= 0 && fcIdx < nFc) setHover({ x, idx: fcIdx, inForecast: true });
    else setHover(null);
  };

  const hv = hover?.inForecast ? hover.idx : null;

  return (
    <div>
      <canvas
        ref={ref}
        className="chart"
        onMouseMove={onMove}
        onMouseLeave={() => setHover(null)}
      />
      <div className="legend-row">
        <div className="item"><span className="ln" style={{ borderColor: "rgba(246,233,212,0.75)" }} />observed F10.7</div>
        <div className="item"><span className="ln" style={{ borderColor: AMBER }} />PENUMBRA point</div>
        <div className="item"><span className="sw" style={{ background: "rgba(255,180,84,0.4)" }} />50% band</div>
        <div className="item"><span className="sw" style={{ background: "rgba(255,122,69,0.28)" }} />90% band</div>
        <div className="item"><span className="ln" style={{ borderColor: TEAL, borderStyle: "dashed" }} />NOAA 45-day</div>
      </div>
      {hv != null && (
        <div className="issued" style={{ marginTop: 8 }}>
          Lead +{hv + 1}d ({data.dates[hv]}): point {data.point[hv].toFixed(0)} sfu ·
          90% band {data.bands.p05[hv].toFixed(0)}–{data.bands.p95[hv].toFixed(0)} sfu
          {data.noaa_point[hv] != null && ` · NOAA ${data.noaa_point[hv]!.toFixed(0)}`}
        </div>
      )}
    </div>
  );
}
