"""
PDDL2DyPDL: A translator from PDDL to DyPDL
Author: Dillon Z. Chen
Year: 2025
"""

from dataclasses import dataclass

import didppy as dp


@dataclass
class Operator:
    name: str
    preconditions: dict[int, int]
    effects: dict[int, int]
    cost: float


@dataclass
class Rule:
    preconditions: dict[int, int]
    var: int
    val: int


@dataclass
class Variable:
    name: str
    values: list[str]
    axiom_layer: int


class Sas2DypdlTransformer:
    def __init__(self, sas_content: str):
        self._detected_axioms = False
        self._detected_conditional_effects = False

        self._model = dp.Model()
        self._parse(sas_content)

    @property
    def detected_axioms(self) -> bool:
        return self._detected_axioms

    @property
    def detected_conditional_effects(self) -> bool:
        return self._detected_conditional_effects

    def _parse(self, sas_content) -> None:
        self._init: dict[int, int] = {}
        self._goal: dict[int, int] = {}
        self._variables: dict[int, Variable] = {}
        self._rules: list[Rule] = []
        self._operators: list[Operator] = []
        self._axiom_heads = {}
        self._axiom_edges = {}  # body nodes <- head node, note backward direction

        line_iterator = iter(sas_content.splitlines())

        def get_line():
            try:
                return next(line_iterator).replace("\n", "")
            except StopIteration:
                return None

        while True:
            line = get_line()
            if line is None:
                break
            if line == "begin_variable":
                var_name = get_line()
                axiom_layer = int(get_line())
                n_values = int(get_line())
                var_values = [get_line() for _ in range(n_values)]
                assert get_line() == "end_variable"
                i = len(self._variables)
                assert f"var{i}" == var_name
                self._variables[i] = Variable(
                    name=var_name,
                    values=var_values,
                    axiom_layer=axiom_layer,
                )
            elif line == "begin_rule":
                self._detected_axioms = True
                # raise NotImplementedError("Axioms are not yet supported.")

                n_preconditions = int(get_line())
                preconditions = {}
                for _ in range(n_preconditions):
                    var_index, value = get_line().split()
                    value = int(value)
                    assert var_index not in preconditions
                    preconditions[int(var_index)] = value
                toks = get_line().split()
                assert len(toks) == 3
                # the last row is (var, 1 - val, val)
                # makes sense, as derived facts can only be true or false
                var = int(toks[0])
                val = int(toks[2])
                assert len(self._variables[var].values) == 2
                assert self._variables[var].values[0].startswith("Atom")
                assert self._variables[var].values[1].startswith("NegatedAtom")
                assert val == 0  # represents atom switching on, should never switch off
                rule = Rule(preconditions=preconditions, var=var, val=val)
                self._rules.append(rule)
                assert get_line() == "end_rule"
                if var not in self._axiom_heads:
                    self._axiom_heads[var] = []
                self._axiom_heads[var].append(rule)

                if var not in self._axiom_edges:
                    self._axiom_edges[var] = set()
                self._axiom_edges[var].update(preconditions.keys())
            elif line == "begin_operator":
                op_name = get_line()
                n_preconditions = int(get_line())
                preconditions = {}
                for _ in range(n_preconditions):
                    var, val = get_line().split()
                    var = int(var)
                    val = int(val)
                    assert var not in preconditions
                    preconditions[var] = val
                n_effects = int(get_line())
                effects = {}
                for _ in range(n_effects):
                    toks = get_line().split()
                    cond = int(toks[0])
                    var = int(toks[1])
                    pre = int(toks[2])
                    post = int(toks[3])
                    if cond != 0:
                        self._detected_conditional_effects = True
                        # raise NotImplementedError("Conditional effects are not yet supported.")
                        continue
                    assert var not in preconditions
                    assert var not in effects
                    preconditions[var] = pre
                    effects[var] = post
                cost = float(get_line())
                assert int(round(cost)) == float(cost), "action costs must be int"
                cost = int(round(cost))
                self._operators.append(Operator(name=op_name, preconditions=preconditions, effects=effects, cost=cost))
                assert get_line() == "end_operator"
            elif line == "begin_goal":
                n_goals = int(get_line())
                for _ in range(n_goals):
                    var, val = get_line().split()
                    var = int(var)
                    val = int(val)
                    assert var not in self._goal
                    self._goal[var] = val
                assert get_line() == "end_goal"
            elif line == "begin_state":
                for var in range(len(self._variables)):
                    val = int(get_line())
                    self._init[var] = val
                assert get_line() == "end_state"

    def _handle_variables(self) -> None:
        self._didp_variables = {}

        """state vars"""
        for i, variable in self._variables.items():
            if i in self._axiom_heads:
                continue
            var = self._model.add_int_var(name=variable.name, target=self._init[i])
            self._didp_variables[i] = var

    def _handle_axioms(self) -> None:
        var = next(iter(self._didp_variables.values()))
        TRUE = var == var
        FALSE = var != var
        # value iteration to stratify, does not terminate if cycles exist
        # TODO throw an error if there is a cycle in the axiom graph
        # call --layer-strategy max in the downward translator or manually detect cycles
        cur_V = {i: None for i in self._axiom_edges}
        new_V = {i: 0 for i in self._axiom_edges}

        def is_diff():
            for i in cur_V:
                if new_V[i] != cur_V[i]:
                    return True
            return False

        while is_diff():
            cur_V = new_V.copy()
            for head, body in self._axiom_edges.items():
                update = 1
                for i in body:
                    if i in cur_V:
                        update = max(update, cur_V[i] + 1)
                new_V[head] = update

        assert new_V.keys() == self._axiom_edges.keys()

        min_val = float("inf")
        max_val = float("-inf")
        val_to_head = {}
        for head, val in new_V.items():
            if val not in val_to_head:
                val_to_head[val] = []
            val_to_head[val].append(head)
            min_val = min(min_val, val)
            max_val = max(max_val, val)

        if min_val != float("inf") and max_val != float("-inf"):
            for i in range(min_val, max_val + 1):
                for head in val_to_head[i]:
                    bodies = []
                    trivial = False

                    for rule in self._axiom_heads[head]:
                        assert rule.var == head
                        if len(rule.preconditions) == 0:
                            trivial = True
                            break
                        body = None
                        for var, val in rule.preconditions.items():

                            def get_atom():
                                if var not in self._axiom_heads:
                                    ret = self._didp_variables[var] == val
                                elif val == 0:
                                    # if 0 in sas, it means turned on
                                    ret = self._didp_variables[var]
                                else:
                                    assert val == 1
                                    # if 1 in sas, it means not turned on
                                    ret = ~self._didp_variables[var]
                                # print(type(ret))
                                # assert isinstance(ret, dp.builtins.Condition)
                                return ret

                            if body is None:
                                body = get_atom()
                            else:
                                body = body & get_atom()
                        bodies.append(body)

                    if trivial:
                        trigger = TRUE
                    else:
                        trigger = bodies[0]
                        for i in range(1, len(bodies)):
                            trigger = trigger | bodies[i]
                    self._didp_variables[head] = self._model.add_bool_state_fun(trigger)

    def _handle_operators(self) -> None:
        didp_actions = {}
        for op in self._operators:
            preconditions = []
            for var, val in op.preconditions.items():
                if val == -1:
                    continue
                if var not in self._axiom_heads:
                    preconditions.append(self._didp_variables[var] == val)
                else:
                    preconditions.append(self._didp_variables[var])
            effects = []
            for var, val in op.effects.items():
                assert var not in self._axiom_heads
                effects.append((self._didp_variables[var], val))
            didp_action = dp.Transition(
                name=op.name,
                cost=op.cost + dp.IntExpr.state_cost(),
                preconditions=preconditions,
                effects=effects,
            )
            didp_actions[op.name] = didp_action
            self._model.add_transition(didp_action)

    def _handle_goal(self) -> None:
        base_case = []
        for var, val in self._goal.items():
            if var in self._axiom_heads:
                if val == 1:
                    base_case.append(self._didp_variables[var])
                else:
                    assert val == 0
                    base_case.append(~self._didp_variables[var])
            else:
                base_case.append(self._didp_variables[var] == val)
        self._model.add_base_case(base_case)

    def transform(self) -> dp.Model:
        if self.detected_axioms or self.detected_conditional_effects:
            raise NotImplementedError("Axioms and conditional effects are not yet supported.")

        self._handle_variables()
        self._handle_operators()
        self._handle_goal()
        return self._model
