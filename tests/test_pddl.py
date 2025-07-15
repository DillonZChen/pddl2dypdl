import subprocess

import pytest

from tests.fixtures import BLOCKS_PDDL


@pytest.mark.parametrize("domain_pddl, problem_pddl", BLOCKS_PDDL)
def test_pddl(domain_pddl: str, problem_pddl: str):
    command = ["python3", "-m", "pddl2dypdl", domain_pddl, problem_pddl]
    result = subprocess.run(command, capture_output=True, text=True)
    assert result.returncode == 0, f"Command failed with error: {result.stderr}"
    assert "Plan found!" in result.stdout, "Expected success message not found in output."
