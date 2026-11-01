import type { ParetoResult } from "../data-model.ts";

export function renderParetoFrontierChart(canvas: HTMLCanvasElement, res: ParetoResult): void {
  const ctx = canvas.getContext("2d");
  if (!ctx) return;
  const w = (canvas.width = canvas.clientWidth || 360);
  const h = (canvas.height = canvas.clientHeight || 205);
  ctx.clearRect(0, 0, w, h);

  ctx.strokeStyle = "rgba(148,163,184,0.25)";
  ctx.strokeRect(36, 16, w - 52, h - 38);

  const maxCost = Math.max(res.costGreenUsd, res.costEafUsd, res.costBfUsd, 100);
  const maxCo2 = Math.max(res.co2BfKg, res.co2EafKg, res.co2GreenKg, 50);

  const points = [
    { name: "BF-BOF", cost: res.costBfUsd, co2: res.co2BfKg, color: "#f59e0b" },
    { name: "EAF", cost: res.costEafUsd, co2: res.co2EafKg, color: "#38bdf8" },
    { name: "Low-C", cost: res.costGreenUsd, co2: res.co2GreenKg, color: "#10b981" },
  ];

  ctx.strokeStyle = "#94a3b8";
  ctx.setLineDash([4, 4]);
  ctx.beginPath();
  points.forEach((p, idx) => {
    const x = 36 + (p.cost / maxCost) * (w - 60);
    const y = h - 22 - (p.co2 / maxCo2) * (h - 42);
    if (idx === 0) ctx.moveTo(x, y);
    else ctx.lineTo(x, y);
  });
  ctx.stroke();
  ctx.setLineDash([]);

  points.forEach((p) => {
    const x = 36 + (p.cost / maxCost) * (w - 60);
    const y = h - 22 - (p.co2 / maxCo2) * (h - 42);
    ctx.fillStyle = p.color;
    ctx.beginPath();
    ctx.arc(x, y, 6, 0, 2 * Math.PI);
    ctx.fill();

    ctx.fillStyle = "#e2e8f0";
    ctx.font = "10px Inter, sans-serif";
    ctx.fillText(p.name, x + 8, y + 4);
  });

  ctx.fillStyle = "#e2e8f0";
  ctx.font = "11px Inter, sans-serif";
  ctx.fillText("Frontera de Pareto: Costo ($) vs CO2e (kg)", 42, 30);
}

export function renderRouteComparisonChart(canvas: HTMLCanvasElement, res: ParetoResult): void {
  const ctx = canvas.getContext("2d");
  if (!ctx) return;
  const w = (canvas.width = canvas.clientWidth || 360);
  const h = (canvas.height = canvas.clientHeight || 205);
  ctx.clearRect(0, 0, w, h);

  ctx.strokeStyle = "rgba(148,163,184,0.25)";
  ctx.strokeRect(36, 16, w - 52, h - 38);

  const maxCo2 = Math.max(res.co2BfKg, 1);
  const routes = [
    { label: "BF-BOF", val: res.co2BfKg, color: "#f59e0b" },
    { label: "EAF", val: res.co2EafKg, color: "#38bdf8" },
    { label: "Low-C", val: res.co2GreenKg, color: "#10b981" },
  ];

  routes.forEach((r, idx) => {
    const y = 35 + idx * 48;
    const barW = (r.val / maxCo2) * (w - 110);
    ctx.fillStyle = r.color;
    ctx.fillRect(90, y, barW, 24);

    ctx.fillStyle = "#e2e8f0";
    ctx.font = "10px Inter, sans-serif";
    ctx.fillText(r.label, 42, y + 16);
    ctx.fillText(`${r.val.toFixed(0)} kg`, 96 + barW, y + 16);
  });
}
