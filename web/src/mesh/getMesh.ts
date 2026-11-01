import type { DiscretizedStationNode, SemanticSpan, SpanStationMapping } from "../data-model.ts";

export function getSpanStationMesh(
  spans: SemanticSpan[],
  stationsPerSpan: number
): { stations: DiscretizedStationNode[]; mapping: SpanStationMapping } {
  const div = Math.max(2, Math.floor(stationsPerSpan));
  const spanToStations = new Map<string, number[]>();
  const stationToSpan = new Map<number, string>();
  const routeToPareto = new Map<string, number[]>();
  const stations: DiscretizedStationNode[] = [];

  let xCursor = 0;
  for (const s of spans) {
    const dx = s.lengthM / div;
    const indices: number[] = [];
    for (let i = 0; i < div; i++) {
      const idx = stations.length;
      const xLoc = (i + 0.5) * dx;
      const moment = 0.5 * s.udlKnM * xLoc * (s.lengthM - xLoc);
      const shear = s.udlKnM * (0.5 * s.lengthM - xLoc);
      const minWpl = (moment * 1000) / 355;
      stations.push({
        index: idx,
        spanId: s.id,
        xM: xCursor + xLoc,
        dxM: dx,
        momentKnm: moment,
        shearKn: shear,
        minWplCm3: Math.max(minWpl, 10),
      });
      indices.push(idx);
      stationToSpan.set(idx, s.id);
    }
    spanToStations.set(s.id, indices);
    xCursor += s.lengthM;
  }

  const allIndices = stations.map((st) => st.index);
  routeToPareto.set("BF_BOF", allIndices);
  routeToPareto.set("EAF", allIndices);
  routeToPareto.set("LOW_CARBON", allIndices);

  return {
    stations,
    mapping: { spanToStations, stationToSpan, routeToPareto },
  };
}
