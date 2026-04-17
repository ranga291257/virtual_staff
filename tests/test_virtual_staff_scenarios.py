from __future__ import annotations

import tempfile
import time
import unittest

from virtual_staff.contracts import HandoffRequest
from virtual_staff.control_handles import MV_POLICIES
from virtual_staff.event_store import OpsEventStore
from virtual_staff.memory_builder import DEFAULT_TAGS, SharedMemoryBuilder
from virtual_staff.orchestrator import OrchestratorAgent, default_memory
from virtual_staff.tag_store import SQLiteTagStore


class TestVirtualStaffScenarios(unittest.TestCase):
    def _orchestrator(self) -> OrchestratorAgent:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        store = OpsEventStore(base_dir=tmp.name)
        tag_store = SQLiteTagStore(db_path=f"{tmp.name}/tags.db")
        return OrchestratorAgent(event_store=store, tag_store=tag_store)

    def test_normal_cycle(self):
        orch = self._orchestrator()
        result = orch.run_cycle(default_memory(), case_name="test_normal")
        self.assertIn("ranked_options", result)
        self.assertGreaterEqual(len(result["ranked_options"]), 1)
        events = orch.event_store.replay()
        self.assertGreaterEqual(len(events), 1)

    def test_rejection_path(self):
        orch = self._orchestrator()
        memory = default_memory()

        original_run = orch.process_subagent.run

        def reject_candidate(request):
            resp = original_run(request)
            resp.output["candidate_settings"] = [{"excess_air_fraction": 0.5, "stack_temp_c": 500.0}]
            return resp

        orch.process_subagent.run = reject_candidate
        result = orch.run_cycle(memory, case_name="test_reject")
        self.assertEqual(len(result["ranked_options"]), 0)
        self.assertGreaterEqual(len(result["rejected_options"]), 1)

    def test_conflict_path(self):
        orch = self._orchestrator()
        memory = default_memory()

        original_maint = orch.maintenance_subagent.run

        def constrained_maint(request):
            resp = original_maint(request)
            resp.output["maintenance_constraints"]["max_fired_duty_derate_fraction"] = 0.9
            return resp

        orch.maintenance_subagent.run = constrained_maint
        result = orch.run_cycle(memory, case_name="test_conflict")
        self.assertEqual(len(result["ranked_options"]), 0)
        self.assertTrue(
            any("maintenance constraint conflict" in " ".join(opt["reasons"]) for opt in result["rejected_options"])
        )

    def test_fallback_path(self):
        orch = self._orchestrator()
        memory = default_memory()

        def always_fail_case(*args, **kwargs):
            raise RuntimeError("force simulator failure")

        orch.sim_subagent.simulator.execute = always_fail_case
        result = orch.run_cycle(memory, case_name="test_fallback")
        self.assertGreaterEqual(len(result["ranked_options"]), 1)
        runtime_modes = [o["sim_output"].get("runtime_mode") for o in result["ranked_options"]]
        self.assertIn("calc_fallback", runtime_modes)

    def test_retry_timeout(self):
        orch = self._orchestrator()
        req = orch._prepare_process_request(default_memory())
        req.timeout_seconds = 0
        req.retry_limit = 1

        class SlowSubagent:
            def run(self, request):
                time.sleep(0.1)
                raise RuntimeError("should timeout first")

        resp = orch._call_with_retry(SlowSubagent(), req)
        self.assertFalse(resp.success)
        timeout_events = orch.event_store.replay_by_event("handoff_timeout")
        self.assertGreaterEqual(len(timeout_events), 1)

    def test_control_room_operator_alarm_response(self):
        orch = self._orchestrator()
        memory = default_memory()
        memory.active_alarms = [{"code": "HIGH_STACK_TEMP", "severity": "high"}]
        memory.operating_constraints["alarm_stack_temp_cap_c"] = 235.0

        result = orch.run_cycle(memory, case_name="test_operator_alarm")
        self.assertGreaterEqual(len(result["ranked_options"]), 1)
        selected = result["selected_action"]
        self.assertIsNotNone(selected)
        self.assertIn("operator_output", selected)
        self.assertEqual(selected["operator_output"]["operator_mode"], "alarm_response")
        self.assertLessEqual(float(selected["candidate"]["stack_temp_c"]), 235.0)

    def test_sqlite_memory_builder_defaults(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        store = SQLiteTagStore(db_path=f"{tmp.name}/tags.db")
        builder = SharedMemoryBuilder(tag_store=store)

        memory = builder.build(heater_id="FH-201")
        self.assertEqual(memory.heater_state["heater_id"], "FH-201")
        self.assertEqual(float(memory.heater_state["feed_flow_kg_s"]), DEFAULT_TAGS["heater.feed_flow_kg_s"])
        self.assertEqual(
            float(memory.operating_constraints["max_excess_air_fraction"]),
            DEFAULT_TAGS["constraints.max_excess_air_fraction"],
        )

    def test_sqlite_memory_builder_uses_latest_tag_values(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        store = SQLiteTagStore(db_path=f"{tmp.name}/tags.db")
        store.seed_defaults_if_empty(DEFAULT_TAGS)
        store.insert_sample("heater.feed_flow_kg_s", 123.4)
        store.insert_sample("heater.stack_temp_c", 271.0)
        builder = SharedMemoryBuilder(tag_store=store)

        memory = builder.build()
        self.assertEqual(float(memory.heater_state["feed_flow_kg_s"]), 123.4)
        self.assertEqual(float(memory.heater_state["stack_temp_c"]), 271.0)

    def test_mv_commands_written_to_sqlite_and_event_log(self):
        orch = self._orchestrator()
        memory = default_memory()
        orch.run_cycle(memory, case_name="test_mv_write")

        latest = orch.tag_store.latest_values(MV_POLICIES.keys())
        self.assertIn("mv.fuel_valve_open_pct", latest)
        self.assertIn("mv.air_valve_open_pct", latest)
        self.assertIn("mv.damper_open_pct", latest)
        mv_events = orch.event_store.replay_by_event("mv_tag_write")
        self.assertGreaterEqual(len(mv_events), 1)

    def test_mv_ramp_limits_are_enforced(self):
        orch = self._orchestrator()
        memory = default_memory()
        for tag in MV_POLICIES.keys():
            orch.tag_store.insert_sample(tag=tag, value=12.0, source="test")
        orch.run_cycle(memory, case_name="test_mv_ramp")

        mv_events = orch.event_store.replay_by_event("mv_tag_write")
        self.assertGreaterEqual(len(mv_events), 1)
        for record in mv_events:
            payload = record["payload"]
            tag = payload["tag"]
            policy = MV_POLICIES[tag]
            delta = abs(float(payload["applied_value"]) - float(payload["previous_value"]))
            self.assertLessEqual(delta, policy.max_step_delta + 1e-9)


if __name__ == "__main__":
    unittest.main()
