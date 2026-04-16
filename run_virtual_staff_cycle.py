from __future__ import annotations

import json

from virtual_staff.orchestrator import OrchestratorAgent, default_memory


def main() -> None:
    orchestrator = OrchestratorAgent()
    memory = default_memory()
    action_package = orchestrator.run_cycle(memory=memory, case_name="fh101_virtual_staff")
    print(json.dumps(action_package, indent=2))


if __name__ == "__main__":
    main()
