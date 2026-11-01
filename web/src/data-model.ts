export interface SemanticSpan {
  id: string;
  lengthM: number;
  udlKnM: number;
}

export interface SpanStationMapping {
  spanToStations: Map<string, number[]>;
  stationToSpan: Map<number, string>;
  routeToPareto: Map<string, number[]>;
}

export interface DiscretizedStationNode {
  index: number;
  spanId: string;
  xM: number;
  dxM: number;
  momentKnm: number;
  shearKn: number;
  minWplCm3: number;
}

export interface ParetoResult {
  stations: DiscretizedStationNode[];
  mapping: SpanStationMapping;
  totalMassKg: number;
  maxMomentKnm: number;
  costBfUsd: number;
  co2BfKg: number;
  costEafUsd: number;
  co2EafKg: number;
  costGreenUsd: number;
  co2GreenKg: number;
}
