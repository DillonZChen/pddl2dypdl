#!/usr/bin/env python3
"""
PDDL2DyPDL: A translator from PDDL to DyPDL
Author: Dillon Z. Chen
Year: 2025
"""

import argparse
import logging
import os
import subprocess

import didppy as dp
import termcolor as tc

from pddl2dypdl.sas2dypdl import Sas2DypdlTransformer
from pddl2dypdl.util.logging import init_logger
from pddl2dypdl.util.managers import TimerContextManager


_DESCRIPTION = """PDDL2DyPDL: A translator from PDDL to DyPDL."""

_EPILOG = """example usages:

# Plan with PDDL input
python3 -m pddl2dypdl ext/blocks/domain.pddl ext/blocks/problem.pddl

# Plan with SAS+ input
python3 -m pddl2dypdl ext/blocks/problem.sas
"""


PATH_TO_TRANSLATE = f"{os.path.dirname(os.path.abspath(__file__))}/../ext/translate/translate.py"
SOLVERS = ["cabs", "caasdy", "acps", "apps", "lnbs"]


def main():
    init_logger()

    # fmt: off
    parser = argparse.ArgumentParser(
        description=_DESCRIPTION,
        epilog=_EPILOG,
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.add_argument("input1", type=str,
                        help="Path to the domain PDDL file or SAS+ file.")
    parser.add_argument("input2", type=str, nargs="?", default=None,
                        help="Path to the problem PDDL file or None input1 is SAS+.")
    parser.add_argument("--plan-file", type=str, default="sas_plan",
                        help="Path to output plan file.")
    parser.add_argument("-s", "--solver", choices=SOLVERS, default="lnbs",
                        help="DIDP solver.")
    parser.add_argument("-t", "--timeout", type=int, default=1800,
                        help="Time limit for the solver in seconds.")
    parser.add_argument("-v", "--validate", action="store_true",
                        help="Validate the output plan with the VAL tool.")
    args = parser.parse_args()
    # fmt: on

    input1 = args.input1
    input2 = args.input2
    if input1.endswith(".sas"):
        assert os.path.exists(input1), f"SAS+ file {input1} does not exist."
        sas_content = open(input1, "r").read().strip()
        logging.info(f"Read SAS+ file from {tc.colored(input1, 'blue')}")

        if input2 is not None:
            logging.warning("Ignoring second argument as it is not needed for SAS+ input.")
        if args.validate:
            logging.warning("Plan validation is not supported for SAS+ input. Switching off.")
            args.validate = False
    else:
        assert os.path.exists(input1), f"Domain file {input1} does not exist."
        assert os.path.exists(input2), f"Problem file {input2} does not exist."
        with TimerContextManager("translating PDDL to SAS+"):
            output = subprocess.run([PATH_TO_TRANSLATE, input1, input2, "--to-stdout"], capture_output=True, text=True)
            sas_content = output.stdout.strip()
        logging.info(f"Read domain PDDL from {tc.colored(input1, 'blue')}")
        logging.info(f"Read problem PDDL from {tc.colored(input2, 'blue')}")
    logging.info(f"Timeout: {args.timeout}s")

    with TimerContextManager("translating SAS+ to DIDP"):
        transformer = Sas2DypdlTransformer(sas_content)
        model = transformer.transform()

    with TimerContextManager("solving DIDP problem", end=False) as timer:
        plan = None
        # See https://didppy.readthedocs.io/en/stable/solver-selection.html#layer-by-layer-search
        # for why we use keep_all_layers=True for beam search algorithms
        kwargs = {"quiet": False, "time_limit": args.timeout}
        match args.solver:
            case "cabs":
                # Complete Anytime Beam Search
                solver = dp.CABS(model, keep_all_layers=True, **kwargs)
            case "caasdy":
                # Cost-Algebraic A* Solver for DyPDL
                solver = dp.CAASDy(model, **kwargs)
            case "acps":
                # Anytime Column Progressive Search
                solver = dp.ACPS(model, **kwargs)
            case "apps":
                # Anytime Pack Progressive Search
                solver = dp.APPS(model, **kwargs)
            case "lnbs":
                # Large Neighborhood Beam Search
                solver = dp.LNBS(model, keep_all_layers=True, **kwargs)
            case _:
                raise ValueError(args.solver)

        plans_found = 0

        solution, terminated = None, False
        while True:
            solution, terminated = solver.search_next()

            if not solution.time_out and not solution.is_infeasible:
                logging.info("Plan found!")
                logging.info(f"Plan cost: {solution.cost}")
                logging.info(f"Expanded: {solution.expanded}")
                logging.info(f"Generated: {solution.generated}")
                logging.info(f"Planner time: {solution.time}s")

                plan_file = f"{args.plan_file}.{plans_found}"
                logging.info(f"Writing intermediate plan to {tc.colored(plan_file, 'blue')} ...")
                plan = "\n".join([f"({transition.name})" for transition in solution.transitions])
                with open(plan_file, "w") as f:
                    f.write(plan)
                    plans_found += 1

                logging.info("Continuing search...")
            elif solution.time_out:
                logging.warning(tc.colored(f"Search timed out", "yellow"))
                break
            elif solution.is_infeasible:
                logging.warning(tc.colored("Search found no solution", "yellow"))
                break
            if terminated:
                logging.info("Proved optimality.")
                break

        if solution is not None and not solution.time_out:
            logging.info(tc.colored(f"Search completed in {timer.get_time()}s", "green"))

    if plans_found == 0:
        logging.info("No plan found!")
    else:
        plan_file = args.plan_file
        logging.info(f"Writing final plan to {tc.colored(plan_file, 'blue')} ...")
        with open(plan_file, "w") as f:
            f.write(plan)

        if args.validate:
            output = subprocess.run(["which", "validate"], capture_output=True, text=True, check=False).stdout
            if len(output) == 0:
                logging.info("The command `validate` from VAL was not found in path. Skipping plan validation")
            else:
                with TimerContextManager("validating plan"):
                    cmd = ["validate", input1, input2, plan_file]
                    output = subprocess.run(cmd, capture_output=True, text=True, check=False).stdout
                logging.info(f"Validation output:\n{output.strip()}")
                if "Failed plans" in output:
                    logging.critical(tc.colored("INVALID PLAN", "red"))
                    raise RuntimeError("Plan validation failed")

    logging.info("Done.")


if __name__ == "__main__":
    main()
