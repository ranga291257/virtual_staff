from __future__ import annotations

from typing import Dict, List

from virtual_staff.contracts import SharedMemory
from virtual_staff.instrumentation import DEFAULT_TAG_VALUES, INSTRUMENT_TAGS
from virtual_staff.tag_store import SQLiteTagStore

DEFAULT_TAGS: Dict[str, float] = dict(DEFAULT_TAG_VALUES)


class SharedMemoryBuilder:
    def __init__(self, tag_store: SQLiteTagStore | None = None):
        self.tag_store = tag_store or SQLiteTagStore()

    def build(self, heater_id: str = "FH-101", active_alarms: List[Dict[str, str]] | None = None) -> SharedMemory:
        self.tag_store.seed_defaults_if_empty(DEFAULT_TAGS)
        values = self.tag_store.latest_values(DEFAULT_TAGS.keys())

        def v(tag: str) -> float:
            return float(values.get(tag, DEFAULT_TAGS[tag]))

        return SharedMemory(
            heater_state={
                "heater_id": heater_id,
                "feed_flow_kg_s": v("heater.feed_flow_kg_s"),
                "feed_inlet_temp_c": v("heater.feed_inlet_temp_c"),
                "target_outlet_temp": v("heater.target_outlet_temp"),
                "cp_kj_kg_k": v("heater.cp_kj_kg_k"),
                "density_kg_m3": v("heater.density_kg_m3"),
                "process_pressure_barg": v("heater.process_pressure_barg"),
                "tube_dp_bar": v("heater.tube_dp_bar"),
                "stack_temp_c": v("heater.stack_temp_c"),
                "fuel_valve_open_pct": v("mv.fuel_valve_open_pct"),
                "air_valve_open_pct": v("mv.air_valve_open_pct"),
                "damper_open_pct": v("mv.damper_open_pct"),
                "instrumentation": {
                    tag: {
                        "instrument_id": spec.instrument_id,
                        "service": spec.service,
                        "units": spec.units,
                        "signal_role": spec.signal_role,
                    }
                    for tag, spec in INSTRUMENT_TAGS.items()
                },
            },
            active_alarms=active_alarms or [],
            operating_constraints={
                "max_excess_air_fraction": v("constraints.max_excess_air_fraction"),
                "alarm_stack_temp_cap_c": v("constraints.alarm_stack_temp_cap_c"),
            },
        )
