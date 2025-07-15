import subprocess


def test_blocksworld_pddl():
    # python3 -m pddl2dypdl benchmarks_pddl/blocks/domain.pddl benchmarks_pddl/blocks/probBLOCKS-5-0.pddl
    command = [
        "python3",
        "-m",
        "pddl2dypdl",
        "benchmarks_pddl/blocks/domain.pddl",
        "benchmarks_pddl/blocks/probBLOCKS-5-0.pddl",
    ]
