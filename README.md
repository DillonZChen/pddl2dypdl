PDDL2DyPDL
==========

PDDL2DyPDL is a translator that converts PDDL planning problems into
[DIDP](https://github.com/domain-independent-dp/didp-rs) problems modelled in
DyPDL to be solved with DIDP solvers. PDDL2DyPDL currently supports the STRIPS
fragment of PDDL and SAS+ problems. To install PDDL2DyPDL, run in the root
directory

    pip install .

To get instructions on how to use PDDL2DyPDL from the command line, run

    python3 -m pddl2dypdl -h

## Reference
If you find this tool useful in your research or would like to know more about it, please reference
```
@inproceedings{
  title        = {STRIPS2DyPDL: A Translator from Automated Planning Problems into Domain-Independent Dynamic Programming Problems},
  author       = {Dillon Z. Chen},
  year         = {2025},
  booktitle    = {Proceedings of the 24th Workshop on Constraint Modelling and Reformulation (ModRef)},
}
```
