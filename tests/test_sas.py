import subprocess

import pytest

from tests.fixtures import BLOCKS_SAS


@pytest.mark.parametrize("sas_file", BLOCKS_SAS)
def test_pddl(sas_file: str):
    command = ["python3", "-m", "pddl2dypdl", sas_file]
    result = subprocess.run(command, capture_output=True, text=True)
    assert result.returncode == 0, f"Command failed with error: {result.stderr}"
    assert "Plan found!" in result.stdout, "Expected success message not found in output."
