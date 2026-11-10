"""Standalone cycle1 v0.1.0 — two-spool separated-exhaust turbofan design point.

Usage:
    python cycle1_standalone.py

Change DEFAULT_INPUTS below and rerun. Pure Python >= 3.10.
Units: Pa, K, kg/s, J/kg, N. Not validated for design/certification.
"""
from __future__ import annotations

"""Pure 0-D component physics. SI units, absolute pressures, total states."""
from dataclasses import dataclass
from math import sqrt

@dataclass(frozen=True)
class Gas:
    cp: float = 1005.0          # J/(kg K)
    gamma: float = 1.4
    r: float = 287.05           # J/(kg K)

    def __post_init__(self):
        if self.cp <= 0 or self.r <= 0 or self.gamma <= 1:
            raise ValueError("Invalid gas properties")

@dataclass(frozen=True)
class Station:
    tt: float  # total temperature K
    pt: float  # total pressure Pa

    def __post_init__(self):
        if self.tt <= 0 or self.pt <= 0:
            raise ValueError("Station temperatures and pressures must be positive")

@dataclass(frozen=True)
class NozzleResult:
    velocity: float
    pressure: float
    temperature: float
    area: float
    choked: bool
    gross_thrust: float

def compressor(inlet: Station, pressure_ratio: float, efficiency: float, gas: Gas) -> tuple[Station, float]:
    if pressure_ratio < 1 or not (0 < efficiency <= 1):
        raise ValueError("Compressor requires PR >= 1 and 0 < efficiency <= 1")
    tau_is = pressure_ratio ** ((gas.gamma - 1) / gas.gamma)
    outlet = Station(inlet.tt * (1 + (tau_is - 1) / efficiency), inlet.pt * pressure_ratio)
    return outlet, gas.cp * (outlet.tt - inlet.tt)  # specific shaft work J/kg

def turbine_for_work(inlet: Station, extracted_work: float, efficiency: float, gas: Gas) -> Station:
    """Extract specified positive shaft work per kg of gas."""
    if extracted_work < 0 or not (0 < efficiency <= 1):
        raise ValueError("Turbine requires nonnegative work and 0 < efficiency <= 1")
    tt_out = inlet.tt - extracted_work / gas.cp
    tt_is_out = inlet.tt - extracted_work / (gas.cp * efficiency)
    if tt_is_out <= 0 or tt_out <= 0:
        raise ValueError("Turbine work demand exceeds feasible temperature drop")
    pr = (tt_is_out / inlet.tt) ** (gas.gamma / (gas.gamma - 1))
    return Station(tt_out, inlet.pt * pr)

def combustor(inlet: Station, tt_exit: float, pressure_ratio: float,
              efficiency: float, lhv: float, gas: Gas) -> tuple[Station, float]:
    """Mass/energy balance: (1+f) cp T4 = cp T3 + f eta LHV."""
    if tt_exit < inlet.tt or not (0 < pressure_ratio <= 1) or not (0 < efficiency <= 1) or lhv <= 0:
        raise ValueError("Invalid combustor inputs")
    denominator = efficiency * lhv - gas.cp * tt_exit
    if denominator <= 0:
        raise ValueError("Combustor heating value insufficient for requested Tt4")
    f = gas.cp * (tt_exit - inlet.tt) / denominator
    return Station(tt_exit, inlet.pt * pressure_ratio), f

def nozzle(inlet: Station, ambient_pressure: float, mdot: float,
           efficiency: float, gas: Gas) -> NozzleResult:
    """Simplified pressure-ratio nozzle; area is inferred, not a fixed throat constraint."""
    if ambient_pressure <= 0 or mdot <= 0 or not (0 < efficiency <= 1):
        raise ValueError("Invalid nozzle inputs")
    if inlet.pt <= ambient_pressure:
        return NozzleResult(0.0, ambient_pressure, inlet.tt, 0.0, False, 0.0)
    critical_ratio = (2 / (gas.gamma + 1)) ** (gas.gamma / (gas.gamma - 1))
    choked = ambient_pressure / inlet.pt <= critical_ratio
    pe = inlet.pt * critical_ratio if choked else ambient_pressure
    te_is = inlet.tt * (pe / inlet.pt) ** ((gas.gamma - 1) / gas.gamma)
    v = sqrt(max(0.0, 2 * efficiency * gas.cp * (inlet.tt - te_is)))
    te = inlet.tt - v * v / (2 * gas.cp)
    rho = pe / (gas.r * te)
    area = mdot / (rho * v)
    return NozzleResult(v, pe, te, area, choked, mdot * v + (pe - ambient_pressure) * area)


"""Cycle orchestration and conservation checks, independent of component physics."""
from dataclasses import dataclass
from math import sqrt


@dataclass(frozen=True)
class CycleInputs:
    ambient_temperature: float = 288.15
    ambient_pressure: float = 101325.0
    mach: float = 0.0
    mdot_air: float = 50.0
    bypass_ratio: float = 2.0
    inlet_pressure_recovery: float = 0.99
    fan_pressure_ratio: float = 1.6
    fan_efficiency: float = 0.88
    hpc_pressure_ratio: float = 8.0
    hpc_efficiency: float = 0.86
    combustor_exit_tt: float = 1450.0
    combustor_pressure_ratio: float = 0.95
    combustor_efficiency: float = 0.99
    fuel_lhv: float = 43e6
    hpt_efficiency: float = 0.9
    lpt_efficiency: float = 0.9
    hp_mechanical_efficiency: float = 0.99
    lp_mechanical_efficiency: float = 0.99
    core_nozzle_efficiency: float = 0.97
    bypass_nozzle_efficiency: float = 0.97

@dataclass(frozen=True)
class CycleResult:
    stations: dict[str, Station]
    core_nozzle: NozzleResult
    bypass_nozzle: NozzleResult
    fuel_air_ratio: float
    mdot_core_air: float
    mdot_bypass_air: float
    mdot_fuel: float
    thrust_n: float
    tsfc_kg_per_ns: float
    hp_shaft_residual_w: float
    lp_shaft_residual_w: float
    combustor_energy_residual_w: float
    mass_residual_kg_s: float

    @property
    def tsfc_kg_per_kn_h(self) -> float:
        return self.tsfc_kg_per_ns * 1000 * 3600

def solve_design_point(x: CycleInputs, gas: Gas | None = None) -> CycleResult:
    gas = gas or Gas()
    if (x.ambient_temperature <= 0 or x.ambient_pressure <= 0 or x.mach < 0
        or x.mdot_air <= 0 or x.bypass_ratio < 0 or not 0 < x.inlet_pressure_recovery <= 1
        or not 0 < x.hp_mechanical_efficiency <= 1
        or not 0 < x.lp_mechanical_efficiency <= 1):
        raise ValueError("Invalid environment, flow or mechanical efficiency")
    mdot_core = x.mdot_air / (1 + x.bypass_ratio)
    mdot_bypass = x.mdot_air - mdot_core
    t0 = x.ambient_temperature
    p0 = x.ambient_pressure
    v0 = x.mach * sqrt(gas.gamma * gas.r * t0)
    tt0 = t0 * (1 + (gas.gamma - 1) * x.mach * x.mach / 2)
    pt0 = p0 * (tt0 / t0) ** (gas.gamma / (gas.gamma - 1))
    s2 = Station(tt0, pt0 * x.inlet_pressure_recovery)
    s13, fan_work = compressor(s2, x.fan_pressure_ratio, x.fan_efficiency, gas)
    s3, hpc_work = compressor(s13, x.hpc_pressure_ratio, x.hpc_efficiency, gas)
    s4, f = combustor(s3, x.combustor_exit_tt, x.combustor_pressure_ratio,
                       x.combustor_efficiency, x.fuel_lhv, gas)
    mdot_fuel = f * mdot_core
    mdot_hot = mdot_core + mdot_fuel
    hp_power = mdot_core * hpc_work
    lp_power = x.mdot_air * fan_work
    hpt_specific = hp_power / (x.hp_mechanical_efficiency * mdot_hot)
    s45 = turbine_for_work(s4, hpt_specific, x.hpt_efficiency, gas)
    lpt_specific = lp_power / (x.lp_mechanical_efficiency * mdot_hot)
    s5 = turbine_for_work(s45, lpt_specific, x.lpt_efficiency, gas)
    core = nozzle(s5, p0, mdot_hot, x.core_nozzle_efficiency, gas)
    bypass = nozzle(s13, p0, mdot_bypass, x.bypass_nozzle_efficiency, gas) if mdot_bypass > 0 else NozzleResult(0., p0, s13.tt, 0., False, 0.)
    thrust = core.gross_thrust + bypass.gross_thrust - x.mdot_air * v0
    if thrust <= 0:
        raise ValueError("Non-positive net thrust; operating point is infeasible")
    e_balance = mdot_core * gas.cp * s3.tt + mdot_fuel * x.combustor_efficiency * x.fuel_lhv - mdot_hot * gas.cp * s4.tt
    return CycleResult(
        stations={"2": s2, "13": s13, "3": s3, "4": s4, "45": s45, "5": s5},
        core_nozzle=core, bypass_nozzle=bypass, fuel_air_ratio=f,
        mdot_core_air=mdot_core, mdot_bypass_air=mdot_bypass, mdot_fuel=mdot_fuel,
        thrust_n=thrust, tsfc_kg_per_ns=mdot_fuel / thrust,
        hp_shaft_residual_w=x.hp_mechanical_efficiency * mdot_hot * gas.cp * (s4.tt - s45.tt) - hp_power,
        lp_shaft_residual_w=x.lp_mechanical_efficiency * mdot_hot * gas.cp * (s45.tt - s5.tt) - lp_power,
        combustor_energy_residual_w=e_balance,
        mass_residual_kg_s=x.mdot_air + mdot_fuel - (mdot_hot + mdot_bypass)
    )


# ===== User-editable input defaults (SI units) =====
DEFAULT_INPUTS = {
    "ambient_temperature": 288.15,        # K (ISA sea-level example)
    "ambient_pressure": 101325.0,          # Pa
    "mach": 0.0,
    "mdot_air": 50.0,                      # kg/s
    "bypass_ratio": 2.0,
    "inlet_pressure_recovery": 0.99,
    "fan_pressure_ratio": 1.6,
    "fan_efficiency": 0.88,
    "hpc_pressure_ratio": 8.0,
    "hpc_efficiency": 0.86,
    "combustor_exit_tt": 1450.0,           # K
    "combustor_pressure_ratio": 0.95,
    "combustor_efficiency": 0.99,
    "fuel_lhv": 43e6,                      # J/kg
    "hpt_efficiency": 0.90,
    "lpt_efficiency": 0.90,
    "hp_mechanical_efficiency": 0.99,
    "lp_mechanical_efficiency": 0.99,
    "core_nozzle_efficiency": 0.97,
    "bypass_nozzle_efficiency": 0.97,
}

def main() -> None:
    r = solve_design_point(CycleInputs(**DEFAULT_INPUTS))
    print("cycle1 standalone v0.1.0 — design point (SI units)")
    print(f"Net thrust    : {r.thrust_n:,.2f} N")
    print(f"Fuel flow     : {r.mdot_fuel:.6f} kg/s")
    print(f"Fuel/air ratio: {r.fuel_air_ratio:.6f}")
    print(f"TSFC          : {r.tsfc_kg_per_kn_h:.3f} kg/(kN h)")
    print(f"HP residual   : {r.hp_shaft_residual_w:.4e} W")
    print(f"LP residual   : {r.lp_shaft_residual_w:.4e} W")
    print(f"Energy resid. : {r.combustor_energy_residual_w:.4e} W")
    print(f"Mass resid.   : {r.mass_residual_kg_s:.4e} kg/s")
    print("Station      Tt [K]        Pt [kPa]")
    for name, s in r.stations.items():
        print(f"{name:>7}  {s.tt:10.2f}     {s.pt / 1000:10.2f}")
    print("Core nozzle  : ", "choked" if r.core_nozzle.choked else "unchoked")
    print("Bypass nozzle: ", "choked" if r.bypass_nozzle.choked else "unchoked")

if __name__ == "__main__":
    main()
