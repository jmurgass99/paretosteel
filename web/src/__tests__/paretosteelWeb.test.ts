import assert from "node:assert/strict";
import { solveParetoSteelWasm } from "../solver/wasmSolver.ts";

const spans = [
  { id: "SPAN-1", lengthM: 7.5, udlKnM: 28 },
  { id: "SPAN-2", lengthM: 6.0, udlKnM: 22 },
];

const res4 = await solveParetoSteelWasm(spans, 4);
const res12 = await solveParetoSteelWasm(spans, 12);

assert.equal(res4.stations.length, 8);
assert.equal(res12.stations.length, 24);
assert.equal(res12.mapping.spanToStations.get("SPAN-1")?.length, 12);
assert.ok(res12.totalMassKg > 100);
assert.ok(res12.co2GreenKg < res12.co2BfKg);
assert.ok(res12.costGreenUsd > res12.costBfUsd);
console.log(
  `ParetoSteel WASM test OK: Mass=${res12.totalMassKg.toFixed(0)} kg, Cost(Green)=${res12.costGreenUsd.toFixed(0)} $, CO2(Green)=${res12.co2GreenKg.toFixed(0)} kg`
);
