// C++ / WebAssembly kernel para huella de carbono embebido y costo de perfiles de acero
extern "C" {
  double embodiedCarbonKg(double mass_kg, double route_factor) {
    return mass_kg * route_factor;
  }

  double beamCostUsd(double mass_kg, double unit_price, double conn_cost) {
    return mass_kg * unit_price + conn_cost;
  }
}
