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
