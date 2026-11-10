"""Cycle orchestration and conservation checks, independent of component physics."""
from dataclasses import dataclass
from math import sqrt
from .physics import Gas, Station, NozzleResult, compressor, combustor, turbine_for_work, nozzle

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
