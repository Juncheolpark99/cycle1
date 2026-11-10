"""Simple command-line example with no external dependencies."""
from .solver import CycleInputs, solve_design_point

def main() -> None:
    result = solve_design_point(CycleInputs())
    print("cycle1 v0.1.0 — two-spool separated-flow turbofan design point")
    print(f"Net thrust     : {result.thrust_n:,.1f} N")
    print(f"Fuel flow      : {result.mdot_fuel:.5f} kg/s")
    print(f"Fuel/air ratio : {result.fuel_air_ratio:.6f}")
    print(f"TSFC           : {result.tsfc_kg_per_kn_h:.3f} kg/(kN h)")
    print(f"HP shaft error : {result.hp_shaft_residual_w:.3e} W")
    print(f"LP shaft error : {result.lp_shaft_residual_w:.3e} W")
    print(f"Energy error   : {result.combustor_energy_residual_w:.3e} W")
    print(f"Mass error     : {result.mass_residual_kg_s:.3e} kg/s")
    print("Station  Tt[K]      Pt[kPa]")
    for name, station in result.stations.items():
        print(f"{name:>7}  {station.tt:8.2f}   {station.pt/1000:8.2f}")

if __name__ == "__main__":
    main()
