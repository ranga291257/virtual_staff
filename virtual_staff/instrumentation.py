from __future__ import annotations

from dataclasses import dataclass
from typing import Dict


@dataclass(frozen=True)
class InstrumentTagSpec:
    tag: str
    instrument_id: str
    service: str
    units: str
    signal_role: str  # pv, sp, mv, constraint
    default: float


INSTRUMENT_TAGS: Dict[str, InstrumentTagSpec] = {
    # Process variables (PV)
    "heater.feed_flow_kg_s": InstrumentTagSpec(
        tag="heater.feed_flow_kg_s",
        instrument_id="FI-101",
        service="Process feed flow",
        units="kg/s",
        signal_role="pv",
        default=100.0,
    ),
    "heater.feed_inlet_temp_c": InstrumentTagSpec(
        tag="heater.feed_inlet_temp_c",
        instrument_id="TI-101",
        service="Process inlet temperature",
        units="degC",
        signal_role="pv",
        default=260.0,
    ),
    "heater.stack_temp_c": InstrumentTagSpec(
        tag="heater.stack_temp_c",
        instrument_id="TI-102",
        service="Stack temperature",
        units="degC",
        signal_role="pv",
        default=250.0,
    ),
    "heater.process_pressure_barg": InstrumentTagSpec(
        tag="heater.process_pressure_barg",
        instrument_id="PI-101",
        service="Process pressure",
        units="barg",
        signal_role="pv",
        default=10.0,
    ),
    # Setpoints (SP)
    "heater.target_outlet_temp": InstrumentTagSpec(
        tag="heater.target_outlet_temp",
        instrument_id="TIC-101.SP",
        service="Outlet temperature setpoint",
        units="degC",
        signal_role="sp",
        default=300.0,
    ),
    # Manipulated variables (MV)
    "mv.fuel_valve_open_pct": InstrumentTagSpec(
        tag="mv.fuel_valve_open_pct",
        instrument_id="FV-101",
        service="Fuel gas control valve",
        units="percent",
        signal_role="mv",
        default=52.0,
    ),
    "mv.air_valve_open_pct": InstrumentTagSpec(
        tag="mv.air_valve_open_pct",
        instrument_id="FV-102",
        service="Combustion air control valve",
        units="percent",
        signal_role="mv",
        default=48.0,
    ),
    "mv.damper_open_pct": InstrumentTagSpec(
        tag="mv.damper_open_pct",
        instrument_id="DV-101",
        service="Stack damper",
        units="percent",
        signal_role="mv",
        default=45.0,
    ),
    # Other process constants
    "heater.cp_kj_kg_k": InstrumentTagSpec(
        tag="heater.cp_kj_kg_k",
        instrument_id="MODEL.CP",
        service="Process heat capacity",
        units="kJ/kg-K",
        signal_role="constraint",
        default=2.5,
    ),
    "heater.density_kg_m3": InstrumentTagSpec(
        tag="heater.density_kg_m3",
        instrument_id="MODEL.DENSITY",
        service="Process density",
        units="kg/m3",
        signal_role="constraint",
        default=800.0,
    ),
    "heater.tube_dp_bar": InstrumentTagSpec(
        tag="heater.tube_dp_bar",
        instrument_id="PDI-101",
        service="Tube pressure drop",
        units="bar",
        signal_role="pv",
        default=1.5,
    ),
    "constraints.max_excess_air_fraction": InstrumentTagSpec(
        tag="constraints.max_excess_air_fraction",
        instrument_id="POLICY.EXCESS_AIR_MAX",
        service="Policy max excess air",
        units="fraction",
        signal_role="constraint",
        default=0.30,
    ),
    "constraints.alarm_stack_temp_cap_c": InstrumentTagSpec(
        tag="constraints.alarm_stack_temp_cap_c",
        instrument_id="POLICY.STACK_TEMP_CAP",
        service="Alarm response stack temperature cap",
        units="degC",
        signal_role="constraint",
        default=245.0,
    ),
}


DEFAULT_TAG_VALUES: Dict[str, float] = {tag: spec.default for tag, spec in INSTRUMENT_TAGS.items()}
