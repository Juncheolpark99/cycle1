#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Engineering Unit Converter — standalone Tkinter GUI, Python 3.9+, offline."""
import math
import tkinter as tk
from tkinter import ttk, messagebox

# Each conversion factor maps the unit to SI; absolute temperature has an offset.
# Format: category | unit:factor, ... . Temperature is handled separately.
DATA = """
압력 · Pressure (absolute)|Pa:1,kPa:1000,MPa:1000000,bar:100000,mbar:100,psi (psia):6894.757293168,atm:101325,kgf/cm²:98066.5,inHg (0°C):3386.38815789,mmHg (conventional):133.322387415
압력차 · Pressure difference|Pa:1,kPa:1000,MPa:1000000,bar:100000,psi (Δpsi):6894.757293168,inH₂O (4°C):249.08891,mmH₂O (4°C):9.80665
온도차 · Temperature difference|ΔK:1,Δ°C:1,Δ°F:0.5555555555555556,Δ°R:0.5555555555555556
질량유량 · Mass flow|kg/s:1,kg/min:0.016666666666666666,kg/h:0.0002777777777777778,g/s:0.001,lbm/s:0.45359237,lbm/min:0.007559872833333333,lbm/h:0.00012599788055555555
체적유량 · Volumetric flow|m³/s:1,m³/min:0.016666666666666666,m³/h:0.0002777777777777778,L/s:0.001,L/min:0.000016666666666666667,ft³/s:0.028316846592,ft³/min (CFM):0.0004719474432,US gal/min (GPM):0.0000630901964
힘/추력 · Force/Thrust|N:1,kN:1000,lbf:4.4482216152605,kgf:9.80665,tf (metric):9806.65
토크 · Torque|N·m:1,kN·m:1000,lbf·ft:1.3558179483314004,lbf·in:0.1129848290276167,kgf·m:9.80665
동력 · Power|W:1,kW:1000,MW:1000000,hp (mechanical):745.6998715822702,PS (metric hp):735.49875,BTU/h (IT):0.2930710701722222
에너지 · Energy|J:1,kJ:1000,MJ:1000000,kWh:3600000,BTU (IT):1055.05585262,kcal (thermochemical):4184,ft·lbf:1.3558179483314004
비에너지 · Specific energy|J/kg:1,kJ/kg:1000,MJ/kg:1000000,BTU/lbm (IT):2326.000325775,kcal/kg:4184
비열 · Specific heat|J/(kg·K):1,kJ/(kg·K):1000,BTU/(lbm·°R):4186.800586395,cal/(g·K):4184
밀도 · Density|kg/m³:1,g/cm³:1000,lbm/ft³:16.01846337396014
질량 · Mass|kg:1,g:0.001,tonne:1000,lbm:0.45359237,oz (avoirdupois):0.028349523125
길이 · Length|m:1,mm:0.001,cm:0.01,km:1000,in:0.0254,ft:0.3048,mile:1609.344,nmi:1852
면적 · Area|m²:1,cm²:0.0001,mm²:0.000001,ft²:0.09290304,in²:0.00064516
체적 · Volume|m³:1,L:0.001,mL:0.000001,ft³:0.028316846592,in³:0.000016387064,US gal:0.003785411784
속도 · Speed|m/s:1,km/h:0.2777777777777778,ft/s:0.3048,ft/min:0.00508,mph:0.44704,knot:0.5144444444444445
가속도 · Acceleration|m/s²:1,ft/s²:0.3048,g₀:9.80665
회전속도 · Rotational speed|rpm:0.10471975511965977,rev/s:6.283185307179586,rad/s:1,deg/s:0.017453292519943295
관성모멘트 · Mass moment of inertia|kg·m²:1,lbm·ft²:0.0421401100938048,slug·ft²:1.3558179483314004
점성계수 · Dynamic viscosity|Pa·s:1,mPa·s:0.001,cP:0.001,P (poise):0.1
동점성계수 · Kinematic viscosity|m²/s:1,mm²/s:0.000001,cSt:0.000001,St:0.0001
TSFC · Thrust-specific fuel consumption|kg/(N·s):1,kg/(kN·s):0.001,kg/(N·h):0.0002777777777777778,kg/(kN·h):0.0000002777777777777778,lbm/(lbf·h):0.000028327533693831
PSFC · Power-specific fuel consumption|kg/(W·s):1,kg/kWh:0.0000002777777777777778,g/kWh:0.0000000002777777777777778,lbm/(hp·h):0.000000168974
"""
UNIT_SETS = {}
for line in DATA.strip().splitlines():
    category, raw = line.split("|", 1)
    UNIT_SETS[category] = dict((name, float(factor))
                               for name, factor in (entry.rsplit(":", 1) for entry in raw.split(",")))
UNIT_SETS["온도 · Temperature"] = {"K": 1.0, "°C": 1.0, "°F": 5 / 9, "°R": 5 / 9}

DEFAULTS = {
    "압력 · Pressure (absolute)": ("psi (psia)", "kPa", "29"),
    "온도 · Temperature": ("°F", "°C", "1000"),
    "질량유량 · Mass flow": ("lbm/s", "kg/s", "100"),
    "힘/추력 · Force/Thrust": ("lbf", "kN", "10000"),
    "토크 · Torque": ("lbf·ft", "N·m", "1000"),
    "TSFC · Thrust-specific fuel consumption": ("lbm/(lbf·h)", "kg/(kN·h)", "0.8"),
}
OFFSETS = {"K": 0, "°C": 273.15, "°F": 459.67, "°R": 0}


def convert(value, category, from_unit, to_unit):
    """Convert among units of one physical dimension, with temperature offsets."""
    if not math.isfinite(value):
        raise ValueError("유한한 숫자를 입력하세요.")
    units = UNIT_SETS[category]
    if category == "온도 · Temperature":
        si = (value + OFFSETS[from_unit]) * units[from_unit]
        if si < -1e-9:
            raise ValueError("절대온도가 0 K 미만입니다.")
        result = si / units[to_unit] - OFFSETS[to_unit]
    else:
        result = value * units[from_unit] / units[to_unit]
    if not math.isfinite(result):
        raise ValueError("변환값이 표현 범위를 벗어났습니다.")
    return result


class ConverterApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("공학용 단위변환기 | Engineering Unit Converter")
        self.geometry("750x530")
        self.minsize(600, 440)
        self.configure(padx=20, pady=18)
        self.category = tk.StringVar(value="압력 · Pressure (absolute)")
        self.from_unit, self.to_unit = tk.StringVar(), tk.StringVar()
        self.source_value, self.result = tk.StringVar(), tk.StringVar()
        self.precision = tk.StringVar(value="8")
        self.notes = tk.StringVar()
        self.build_ui()
        self.update_category()
        self.source_value.trace_add("write", lambda *_: self.calculate())

    def build_ui(self):
        ttk.Label(self, text="공학용 단위변환기", font=("Arial", 18, "bold")).pack(anchor="w", pady=(0, 8))
        ttk.Label(self, text="항공·가스터빈 공학 | Python 표준 라이브러리 | 오프라인 실행").pack(anchor="w", pady=(0, 15))
        ttk.Label(self, text="변환 분야").pack(anchor="w")
        category = ttk.Combobox(self, textvariable=self.category, values=list(UNIT_SETS), state="readonly")
        category.pack(fill="x", pady=(5, 15))
        category.bind("<<ComboboxSelected>>", lambda _: self.update_category())
        frame = ttk.Frame(self)
        frame.pack(fill="x")
        frame.columnconfigure(0, weight=1)
        frame.columnconfigure(2, weight=1)
        ttk.Label(frame, text="입력 단위").grid(row=0, column=0, sticky="w")
        ttk.Label(frame, text="출력 단위").grid(row=0, column=2, sticky="w")
        self.from_combo = ttk.Combobox(frame, textvariable=self.from_unit, state="readonly")
        self.to_combo = ttk.Combobox(frame, textvariable=self.to_unit, state="readonly")
        self.from_combo.grid(row=1, column=0, sticky="ew", pady=6)
        self.to_combo.grid(row=1, column=2, sticky="ew", pady=6)
        self.from_combo.bind("<<ComboboxSelected>>", lambda _: self.calculate())
        self.to_combo.bind("<<ComboboxSelected>>", lambda _: self.calculate())
        ttk.Button(frame, text="⇄ 교환", command=self.swap).grid(row=1, column=1, padx=12)
        ttk.Label(frame, text="변환할 값").grid(row=2, column=0, sticky="w", pady=(15, 0))
        entry = ttk.Entry(frame, textvariable=self.source_value, font=("Arial", 15))
        entry.grid(row=3, column=0, columnspan=3, sticky="ew", pady=5)
        output = ttk.LabelFrame(self, text="변환 결과", padding=14)
        output.pack(fill="x", pady=(20, 10))
        ttk.Label(output, textvariable=self.result, font=("Arial", 18, "bold"), wraplength=650).pack(anchor="w")
        bar = ttk.Frame(output)
        bar.pack(fill="x", pady=(12, 0))
        ttk.Button(bar, text="결과 복사", command=self.copy_result).pack(side="left")
        ttk.Label(bar, text="유효숫자").pack(side="right")
        digits = ttk.Combobox(bar, textvariable=self.precision, values=["4", "6", "8", "10", "12", "15"],
                              state="readonly", width=5)
        digits.pack(side="right", padx=8)
        digits.bind("<<ComboboxSelected>>", lambda _: self.calculate())
        ttk.Label(self, textvariable=self.notes, wraplength=685).pack(fill="x", pady=(10, 0))
        ttk.Label(self, text="주의: psia는 절대압입니다. psig 변환에는 별도의 기준 대기압이 필요합니다.",
                  wraplength=685).pack(fill="x", pady=(10, 0))
        entry.focus_set()

    def update_category(self):
        category = self.category.get()
        units = list(UNIT_SETS[category])
        self.from_combo["values"] = units
        self.to_combo["values"] = units
        a, b, x = DEFAULTS.get(category, (units[0], units[1], "1"))
        self.from_unit.set(a)
        self.to_unit.set(b)
        self.source_value.set(x)
        self.notes.set("온도는 절대온도, 온도차는 별도 분야입니다." if category == "온도 · Temperature"
                       else "동일한 물리 차원의 단위 간 변환입니다.")
        self.calculate()

    def calculate(self):
        try:
            value = float(self.source_value.get().strip().replace(",", ""))
            result = convert(value, self.category.get(), self.from_unit.get(), self.to_unit.get())
            self.result.set(f"{result:.{int(self.precision.get())}g}  {self.to_unit.get()}")
        except (ValueError, KeyError, OverflowError, ZeroDivisionError) as exc:
            self.result.set(f"입력 확인: {exc}")

    def swap(self):
        try:
            value = float(self.source_value.get().strip().replace(",", ""))
            result = convert(value, self.category.get(), self.from_unit.get(), self.to_unit.get())
            a, b = self.from_unit.get(), self.to_unit.get()
            self.from_unit.set(b)
            self.to_unit.set(a)
            self.source_value.set(f"{result:.15g}")
        except (ValueError, KeyError, OverflowError):
            a, b = self.from_unit.get(), self.to_unit.get()
            self.from_unit.set(b)
            self.to_unit.set(a)
            self.calculate()

    def copy_result(self):
        value = self.result.get()
        if not value or value.startswith("입력 확인"):
            messagebox.showwarning("복사 실패", "유효한 결과가 없습니다.")
            return
        self.clipboard_clear()
        self.clipboard_append(value)
        self.update()


if __name__ == "__main__":
    ConverterApp().mainloop()
