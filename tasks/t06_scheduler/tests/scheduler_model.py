from course_program import golden_lookup


order = golden_lookup(__file__, "scheduler_model.order")


stages = golden_lookup(__file__, "scheduler_model.stages")


def reaches(deps, start, goal):
    seen, stack = set(), [start]
    while stack:
        node = stack.pop()
        if node == goal:
            return True
        if node not in seen:
            seen.add(node)
            stack.extend(deps[node])
    return False


plan = golden_lookup(__file__, "scheduler_model.plan")


def task_file(deps, titles=None):
    titles = titles or {}
    return "".join(f'Задача {t}: "{titles.get(t, "")}" - зависит от: {", ".join(d) if d else "-"}\n'
                   for t, d in deps.items())


def is_cycle(deps, chain):
    return (len(chain) >= 2 and chain[0] == chain[-1] and len(set(chain[:-1])) == len(chain) - 1
            and all(b in deps.get(a, ()) for a, b in zip(chain, chain[1:])))
