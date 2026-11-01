import van from "vanjs-core";
import type { SemanticSpan } from "./data-model.ts";
import { solveParetoSteelWasm } from "./solver/wasmSolver.ts";
import { fetchParetosteelHealthApi } from "./solver/apiClient.ts";
import { createParetoViewer3D } from "./viewer/getViewer3D.ts";
import { renderParetoFrontierChart, renderRouteComparisonChart } from "./ui/getParetoCharts.ts";

const { div, h2, h3, label, input, span, strong, canvas, button, select, option } = van.tags;

const spanL1 = van.state(7.5);
const udlQ1 = van.state(28);
const stationsPerSpan = van.state(8);
const activeRoute = van.state("LOW_CARBON");

const massText = van.state("0.0 kg");
const costText = van.state("0 $");
const co2Text = van.state("0 kg");
const momentText = van.state("0.0 kN·m");
const apiStatus = van.state("Modo WASM local");

const viewerWrap = div({ class: "viewer-wrap" });
const paretoCanvas = canvas({ class: "chart" });
const compCanvas = canvas({ class: "chart" });
const viewer = createParetoViewer3D(viewerWrap);

async function recompute() {
  const spans: SemanticSpan[] = [
    { id: "SPAN-1", lengthM: spanL1.val, udlKnM: udlQ1.val },
    { id: "SPAN-2", lengthM: 6.0, udlKnM: 22 },
  ];
  const res = await solveParetoSteelWasm(spans, stationsPerSpan.val);

  massText.val = `${res.totalMassKg.toFixed(0)} kg`;
  momentText.val = `${res.maxMomentKnm.toFixed(1)} kN·m`;

  if (activeRoute.val === "BF_BOF") {
    costText.val = `${res.costBfUsd.toFixed(0)} $`;
    co2Text.val = `${res.co2BfKg.toFixed(0)} kg`;
  } else if (activeRoute.val === "EAF") {
    costText.val = `${res.costEafUsd.toFixed(0)} $`;
    co2Text.val = `${res.co2EafKg.toFixed(0)} kg`;
  } else {
    costText.val = `${res.costGreenUsd.toFixed(0)} $`;
    co2Text.val = `${res.co2GreenKg.toFixed(0)} kg`;
  }

  viewer.update(res, activeRoute.val);
  renderParetoFrontierChart(paretoCanvas, res);
  renderRouteComparisonChart(compCanvas, res);
}

van.derive(() => {
  void recompute();
});

const app = div(
  { class: "layout" },
  div(
    { class: "panel" },
    h2("ParetoSteel 3D"),
    div(
      { class: "control-row" },
      label(() => `Longitud del vano principal L_1 = ${spanL1.val.toFixed(1)} m`),
      input({
        type: "range",
        min: "4.0",
        max: "14.0",
        step: "0.5",
        value: spanL1,
        oninput: (e: Event) => (spanL1.val = Number((e.target as HTMLInputElement).value)),
      })
    ),
    div(
      { class: "control-row" },
      label(() => `Carga uniforme q = ${udlQ1.val} kN/m`),
      input({
        type: "range",
        min: "10",
        max: "60",
        step: "2",
        value: udlQ1,
        oninput: (e: Event) => (udlQ1.val = Number((e.target as HTMLInputElement).value)),
      })
    ),
    div(
      { class: "control-row" },
      label(() => `Estaciones por vano (SpanStationMapping) = ${stationsPerSpan.val}`),
      input({
        type: "range",
        min: "4",
        max: "16",
        step: "2",
        value: stationsPerSpan,
        oninput: (e: Event) => (stationsPerSpan.val = Number((e.target as HTMLInputElement).value)),
      })
    ),
    div(
      { class: "control-row" },
      label("Ruta siderúrgica activa"),
      select(
        {
          value: activeRoute,
          onchange: (e: Event) => (activeRoute.val = (e.target as HTMLSelectElement).value),
        },
        option({ value: "PRIMARY_BF_BOF" }, "Alto Horno BF-BOF (Bajo Costo)"),
        option({ value: "EAF" }, "Horno Eléctrico EAF (Balanceado)"),
        option({ value: "LOW_CARBON" }, "Acero Verde H2 (Bajo Carbono)")
      )
    ),
    div(
      { class: "kpi-grid" },
      div({ class: "kpi" }, span("Masa total"), strong(massText)),
      div({ class: "kpi" }, span("Momento máx"), strong(momentText)),
      div({ class: "kpi" }, span("Costo estimado"), strong(costText)),
      div({ class: "kpi" }, span("CO2 embebido"), strong(co2Text))
    ),
    button(
      {
        onclick: async () => {
          const ok = await fetchParetosteelHealthApi("http://localhost:8000");
          apiStatus.val = ok ? "FastAPI sincronizado OK" : "FastAPI offline (usando WASM local)";
        },
      },
      "Sincronizar con FastAPI"
    ),
    span({ style: "font-size:0.75rem;color:#94a3b8" }, apiStatus)
  ),
  viewerWrap,
  div(
    { class: "panel" },
    h3("Frontera de Pareto Costo vs CO2"),
    paretoCanvas,
    h3("Huella de Carbono por Ruta Siderúrgica"),
    compCanvas
  )
);

document.getElementById("app")?.appendChild(app);
