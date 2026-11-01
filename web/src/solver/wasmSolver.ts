import type { ParetoResult, SemanticSpan } from "../data-model.ts";
import { getSpanStationMesh } from "../mesh/getMesh.ts";

// Binario WebAssembly compilado desde paretoKernel.cpp
const WASM_B64 =
  "AGFzbQEAAAABDgJgAnx8AXxgA3x8fAF8AwMCAAEFAwEAAQciAhBlbWJvZGllZENhcmJvbktnAAALYmVhbUNvc3RVc2QAAQoUAgcAIAAgAaILCgAgACABoiACoAs=";

function decodeBase64(b64: string): Uint8Array {
  if (typeof Buffer !== "undefined") {
    return new Uint8Array(Buffer.from(b64, "base64"));
  }
  const bin = atob(b64);
  const out = new Uint8Array(bin.length);
  for (let i = 0; i < bin.length; i++) out[i] = bin.charCodeAt(i);
  return out;
}

export interface ParetoWasmExports {
  embodiedCarbonKg: (massKg: number, routeFactor: number) => number;
  beamCostUsd: (massKg: number, unitPrice: number, connCost: number) => number;
}

let cachedExports: ParetoWasmExports | null = null;

export async function initParetoWasm(): Promise<ParetoWasmExports> {
  if (cachedExports) return cachedExports;
  const { instance } = await WebAssembly.instantiate(decodeBase64(WASM_B64));
  cachedExports = instance.exports as unknown as ParetoWasmExports;
  return cachedExports;
}

export async function solveParetoSteelWasm(
  spans: SemanticSpan[],
  stationsPerSpan: number
): Promise<ParetoResult> {
  const wasm = await initParetoWasm();
  const { stations, mapping } = getSpanStationMesh(spans, stationsPerSpan);

  const totalLengthM = spans.reduce((acc, s) => acc + s.lengthM, 0);
  const maxMomentKnm = Math.max(...stations.map((s) => s.momentKnm), 1);
  const maxWpl = Math.max(...stations.map((s) => s.minWplCm3), 10);

  // Estimación de masa estructural basada en módulo resistente plástico requerido
  const areaCm2 = 0.35 * Math.pow(maxWpl, 0.68);
  const totalMassKg = areaCm2 * 0.785 * totalLengthM;

  const co2BfKg = wasm.embodiedCarbonKg(totalMassKg, 2.2);
  const costBfUsd = wasm.beamCostUsd(totalMassKg, 1.8, 120);

  const co2EafKg = wasm.embodiedCarbonKg(totalMassKg, 0.75);
  const costEafUsd = wasm.beamCostUsd(totalMassKg, 2.05, 120);

  const co2GreenKg = wasm.embodiedCarbonKg(totalMassKg, 0.28);
  const costGreenUsd = wasm.beamCostUsd(totalMassKg, 2.45, 120);

  return {
    stations,
    mapping,
    totalMassKg,
    maxMomentKnm,
    costBfUsd,
    co2BfKg,
    costEafUsd,
    co2EafKg,
    costGreenUsd,
    co2GreenKg,
  };
}
