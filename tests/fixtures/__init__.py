import os

_CUR_DIR = os.path.dirname(os.path.abspath(__file__))

BLOCKS_PDDL = [(f"{_CUR_DIR}/blocks/domain.pddl", f"{_CUR_DIR}/blocks/p{n:02d}.pddl") for n in range(1, 7)]
BLOCKS_SAS = [f"{_CUR_DIR}/blocks/p{n:02d}.sas" for n in range(1, 7)]
