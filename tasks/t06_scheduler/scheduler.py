import sys
import json
import re
import heapq
import datetime
from collections import deque


class TaskScheduler:
    def __init__(self):
        self.tasks = {}  # name -> {"title": str, "deps": set, "status": str, "deadline": str | None}

    def format_task(self, name):
        title = self.tasks[name]["title"]
        return f'{name}: "{title}"' if title else name

    def parse_line(self, line, line_num):
        raw = line.rstrip("\r\n")
        stripped = raw.lstrip("\ufeff").strip()
        if not stripped or stripped.startswith("#"):
            return None

        # Строгий разбор строки формата:
        # Задача <ИМЯ>: "<НАЗВАНИЕ>" - зависит от: <СПИСОК>
        m_head = re.match(r'^\s*задача\s+([^\s,:]+)\s*:\s*(.*)$', raw.lstrip("\ufeff"), re.IGNORECASE)
        if not m_head:
            raise ValueError(f"строка {line_num}: некорректный формат строки: {stripped}")

        name = m_head.group(1)
        rest = m_head.group(2)

        if not name or "," in name or ":" in name or '"' in name:
            raise ValueError(f"строка {line_num}: некорректное имя задачи: {name}")

        if not rest.startswith('"'):
            raise ValueError(f"строка {line_num}: название задачи должно быть в кавычках: {stripped}")

        end_quote = rest.find('"', 1)
        if end_quote == -1:
            raise ValueError(f"строка {line_num}: незакрытая кавычка в названии задачи: {stripped}")

        title = rest[1:end_quote]
        after_title = rest[end_quote + 1:]

        m_tail = re.match(r'^\s*-\s*зависит\s+от\s*:\s*(.*?)\s*$', after_title, re.IGNORECASE)
        if not m_tail:
            raise ValueError(f"строка {line_num}: некорректный формат блока зависимостей: {stripped}")

        deps_raw = m_tail.group(1).strip()

        deps = set()
        if deps_raw == "" or deps_raw == "-":
            pass
        else:
            parts = deps_raw.split(",")
            for p in parts:
                d_clean = p.strip()
                if not d_clean:
                    raise ValueError(f"строка {line_num}: пустая зависимость в списке: {deps_raw}")
                if d_clean == "-":
                    if len(parts) > 1:
                        raise ValueError(f"строка {line_num}: некорректный список зависимостей: {deps_raw}")
                else:
                    if any(ch.isspace() for ch in d_clean) or ":" in d_clean or '"' in d_clean:
                        raise ValueError(f"строка {line_num}: некорректное имя зависимости: {d_clean}")
                    deps.add(d_clean)

        return name, title, deps

    def load_file(self, filepath):
        self.tasks.clear()
        with open(filepath, "r", encoding="utf-8") as f:
            for line_num, line in enumerate(f, 1):
                parsed = self.parse_line(line, line_num)
                if parsed is None:
                    continue
                name, title, deps = parsed
                if name in self.tasks:
                    raise ValueError(f"строка {line_num}: дублирование задачи {name}")
                self.tasks[name] = {
                    "title": title,
                    "deps": set(deps),
                    "status": "pending",
                    "deadline": None,
                }
        for name, info in self.tasks.items():
            for d in info["deps"]:
                if d not in self.tasks:
                    raise ValueError(f"неизвестная зависимость {d} для задачи {name}")

    def find_cycle(self):
        WHITE, GRAY, BLACK = 0, 1, 2
        color = {u: WHITE for u in self.tasks}
        for start in self.tasks.keys():
            if color[start] != WHITE:
                continue
            path = [start]
            color[start] = GRAY
            stack = [(start, iter(sorted(self.tasks[start]["deps"])))]
            while stack:
                u, it = stack[-1]
                try:
                    v = next(it)
                    if v not in self.tasks:
                        continue
                    if color[v] == GRAY:
                        idx = path.index(v)
                        return path[idx:] + [v]
                    if color[v] == WHITE:
                        color[v] = GRAY
                        path.append(v)
                        stack.append((v, iter(sorted(self.tasks[v]["deps"]))))
                except StopIteration:
                    stack.pop()
                    color[u] = BLACK
                    path.pop()
        return None

    def get_ready_all(self):
        return sorted([u for u, info in self.tasks.items() if not info["deps"]])

    def get_topo_order(self):
        in_deg = {u: len(info["deps"]) for u, info in self.tasks.items()}
        dependents = {u: [] for u in self.tasks}
        for u, info in self.tasks.items():
            for d in info["deps"]:
                dependents[d].append(u)

        heap = [u for u, deg in in_deg.items() if deg == 0]
        heapq.heapify(heap)
        order = []
        while heap:
            u = heapq.heappop(heap)
            order.append(u)
            for nxt in dependents[u]:
                in_deg[nxt] -= 1
                if in_deg[nxt] == 0:
                    heapq.heappush(heap, nxt)
        return order

    def get_stages(self):
        order = self.get_topo_order()
        if not order:
            return []
        stage_of = {}
        for u in order:
            deps = self.tasks[u]["deps"]
            if not deps:
                stage_of[u] = 1
            else:
                stage_of[u] = 1 + max(stage_of[d] for d in deps)
        max_stage = max(stage_of.values())
        stages = [[] for _ in range(max_stage)]
        for u in sorted(self.tasks.keys()):
            stages[stage_of[u] - 1].append(u)
        return stages

    def format_plan(self):
        lines = []
        lines.append("Проверка зависимостей: циклов не обнаружено.")
        lines.append("")
        lines.append("Задачи, готовые к выполнению прямо сейчас:")
        ready = self.get_ready_all()
        if not ready:
            lines.append("  нет")
        else:
            for u in ready:
                lines.append(f"  ✓ {self.format_task(u)}")
        lines.append("")
        lines.append("Порядок выполнения всех задач (топологическая сортировка):")
        order = self.get_topo_order()
        if not order:
            lines.append("  нет задач")
        else:
            for idx, u in enumerate(order, 1):
                lines.append(f"  {idx}. {self.format_task(u)}")
        lines.append("")
        lines.append("Параллельные потоки (что можно делать одновременно):")
        stages = self.get_stages()
        if not stages:
            lines.append("  нет задач")
        else:
            for idx, st in enumerate(stages, 1):
                lines.append(f"  Этап {idx}: [{', '.join(st)}]")
        return "\n".join(lines)

    def run_mode1(self, filepath):
        try:
            self.load_file(filepath)
        except Exception as e:
            print(f"Ошибка: {e}", file=sys.stderr)
            return 1

        cycle = self.find_cycle()
        if cycle is not None:
            print("ОШИБКА: обнаружена циклическая зависимость!")
            print(f"Цепочка: {' → '.join(cycle)}")
            print("Невозможно определить порядок выполнения.")
            return 1

        print(self.format_plan())
        return 0

    def is_blocked(self, u):
        visited = set()
        stack = list(self.tasks[u]["deps"])
        while stack:
            curr = stack.pop()
            if curr in visited:
                continue
            visited.add(curr)
            if self.tasks[curr]["status"] == "failed":
                return True
            stack.extend(self.tasks[curr]["deps"])
        return False

    def get_effective_status(self, u):
        st = self.tasks[u]["status"]
        if st == "done":
            return "выполнена"
        if st == "failed":
            return "провалена"
        if self.is_blocked(u):
            return "заблокирована"
        return "ожидает"

    def cmd_add(self, args):
        if not args:
            return "ОШИБКА: не указано имя задачи"
        name = args[0]
        if "," in name or not name:
            return "ОШИБКА: недопустимое имя задачи"
        if name in self.tasks:
            return f"ОШИБКА: задача {name} уже существует"
        deps = args[1:]
        for d in deps:
            if d == name:
                return f"ОШИБКА: циклическая зависимость: {name} → {name}"
            if d not in self.tasks:
                return f"ОШИБКА: задача {d} не найдена"
        self.tasks[name] = {
            "title": "",
            "deps": set(deps),
            "status": "pending",
            "deadline": None,
        }
        return f"Задача {name} добавлена"

    def cmd_dep(self, args):
        if len(args) != 2:
            return "ОШИБКА: неверное число аргументов для dep"
        u, dep_on = args
        if u not in self.tasks:
            return f"ОШИБКА: задача {u} не найдена"
        if dep_on not in self.tasks:
            return f"ОШИБКА: задача {dep_on} не найдена"
        if u == dep_on:
            return f"ОШИБКА: циклическая зависимость: {u} → {u}"
        if dep_on in self.tasks[u]["deps"]:
            return f"{u} зависит от {dep_on}"

        visited = {dep_on}
        parent = {dep_on: None}
        queue = deque([dep_on])
        found = False
        while queue:
            curr = queue.popleft()
            if curr == u:
                found = True
                break
            for nxt in sorted(self.tasks[curr]["deps"]):
                if nxt not in visited:
                    visited.add(nxt)
                    parent[nxt] = curr
                    queue.append(nxt)

        if found:
            path = []
            curr = u
            while curr is not None:
                path.append(curr)
                curr = parent[curr]
            path.reverse()
            cycle_str = " → ".join([u] + path)
            return f"ОШИБКА: циклическая зависимость: {cycle_str}"

        self.tasks[u]["deps"].add(dep_on)
        return f"{u} зависит от {dep_on}"

    def cmd_undep(self, args):
        if len(args) != 2:
            return "ОШИБКА: неверное число аргументов для undep"
        u, dep_on = args
        if u not in self.tasks:
            return f"ОШИБКА: задача {u} не найдена"
        if dep_on not in self.tasks:
            return f"ОШИБКА: задача {dep_on} не найдена"
        if dep_on not in self.tasks[u]["deps"]:
            return f"ОШИБКА: задача {u} не зависит от {dep_on}"
        self.tasks[u]["deps"].remove(dep_on)
        return f"{u} больше не зависит от {dep_on}"

    def cmd_remove(self, args):
        if not args or len(args) > 2:
            return "ОШИБКА: неверные аргументы для remove"
        name = args[0]
        force = False
        if len(args) == 2:
            if args[1] != "--force":
                return "ОШИБКА: неизвестный флаг для remove"
            force = True
        if name not in self.tasks:
            return f"ОШИБКА: задача {name} не найдена"

        rev = {u: [] for u in self.tasks}
        for u, info in self.tasks.items():
            for d in info["deps"]:
                rev[d].append(u)
        dependents = set()
        stack = list(rev[name])
        while stack:
            curr = stack.pop()
            if curr not in dependents:
                dependents.add(curr)
                stack.extend(rev[curr])
        dependents_sorted = sorted(dependents)

        if dependents_sorted and not force:
            return f"ОШИБКА: от задачи {name} зависят: {', '.join(dependents_sorted)}"

        del self.tasks[name]
        for info in self.tasks.values():
            info["deps"].discard(name)
        return f"Задача {name} удалена"

    def cmd_done(self, args):
        if len(args) != 1:
            return "ОШИБКА: неверные аргументы для done"
        name = args[0]
        if name not in self.tasks:
            return f"ОШИБКА: задача {name} не найдена"
        eff = self.get_effective_status(name)
        if eff != "ожидает":
            return f"ОШИБКА: нельзя выполнить задачу {name} в статусе {eff}"
        unmet = sorted([d for d in self.tasks[name]["deps"] if self.tasks[d]["status"] != "done"])
        if unmet:
            return f"ОШИБКА: не выполнены зависимости задачи {name}: {', '.join(unmet)}"
        self.tasks[name]["status"] = "done"
        return f"Задача {name} выполнена"

    def cmd_fail(self, args):
        if len(args) != 1:
            return "ОШИБКА: неверные аргументы для fail"
        name = args[0]
        if name not in self.tasks:
            return f"ОШИБКА: задача {name} не найдена"
        eff = self.get_effective_status(name)
        if eff != "ожидает":
            return f"ОШИБКА: нельзя провалить задачу {name} в статусе {eff}"

        before_blocked = {u for u in self.tasks if u != name and self.get_effective_status(u) == "заблокирована"}
        self.tasks[name]["status"] = "failed"
        after_blocked = {u for u in self.tasks if u != name and self.get_effective_status(u) == "заблокирована"}
        newly_blocked = sorted(after_blocked - before_blocked)

        if newly_blocked:
            return f"Задача {name} провалена; заблокированы: {', '.join(newly_blocked)}"
        return f"Задача {name} провалена"

    def cmd_reset(self, args):
        if len(args) != 1:
            return "ОШИБКА: неверные аргументы для reset"
        name = args[0]
        if name not in self.tasks:
            return f"ОШИБКА: задача {name} не найдена"
        if self.tasks[name]["status"] != "failed":
            return f"ОШИБКА: задача {name} не провалена"

        before_blocked = {u for u in self.tasks if u != name and self.get_effective_status(u) == "заблокирована"}
        self.tasks[name]["status"] = "pending"
        after_blocked = {u for u in self.tasks if u != name and self.get_effective_status(u) == "заблокирована"}
        unblocked = sorted(before_blocked - after_blocked)

        if unblocked:
            return f"Задача {name} снова ожидает; разблокированы: {', '.join(unblocked)}"
        return f"Задача {name} снова ожидает"

    def cmd_status(self, args):
        if len(args) != 1:
            return "ОШИБКА: неверные аргументы для status"
        name = args[0]
        if name not in self.tasks:
            return f"ОШИБКА: задача {name} не найдена"
        return f"{name}: {self.get_effective_status(name)}"

    def cmd_ready(self, args):
        if args:
            return "ОШИБКА: команда ready не принимает аргументов"
        ready = []
        for u, info in self.tasks.items():
            if self.get_effective_status(u) == "ожидает":
                if all(self.tasks[d]["status"] == "done" for d in info["deps"]):
                    ready.append(u)
        ready.sort()
        if not ready:
            return "Готовы к выполнению: нет"
        return f"Готовы к выполнению: {', '.join(ready)}"

    def cmd_order(self, args):
        if args:
            return "ОШИБКА: команда order не принимает аргументов"
        order = self.get_topo_order()
        if not order:
            return "Порядок: нет задач"
        return f"Порядок: {', '.join(order)}"

    def cmd_stages(self, args):
        if args:
            return "ОШИБКА: команда stages не принимает аргументов"
        stages = self.get_stages()
        if not stages:
            return "нет задач"
        return "\n".join(f"Этап {idx}: [{', '.join(st)}]" for idx, st in enumerate(stages, 1))

    def cmd_plan(self, args):
        if args:
            return "ОШИБКА: команда plan не принимает аргументов"
        return self.format_plan()

    def cmd_deadline(self, args):
        if len(args) != 2:
            return "ОШИБКА: неверные аргументы для deadline"
        name, date_str = args
        if name not in self.tasks:
            return f"ОШИБКА: задача {name} не найдена"
        if not re.match(r"^\d{4}-\d{2}-\d{2}$", date_str):
            return "ОШИБКА: неверный формат даты"
        try:
            year, month, day = map(int, date_str.split("-"))
            datetime.date(year, month, day)
        except ValueError:
            return "ОШИБКА: некорректная дата"
        self.tasks[name]["deadline"] = date_str
        return f"Задача {name}: дедлайн {date_str}"

    def cmd_overdue(self, args):
        if len(args) != 1:
            return "ОШИБКА: неверные аргументы для overdue"
        date_str = args[0]
        if not re.match(r"^\d{4}-\d{2}-\d{2}$", date_str):
            return "ОШИБКА: неверный формат даты"
        try:
            year, month, day = map(int, date_str.split("-"))
            datetime.date(year, month, day)
        except ValueError:
            return "ОШИБКА: некорректная дата"

        overdue_tasks = []
        for u, info in self.tasks.items():
            dl = info["deadline"]
            if dl is not None and info["status"] != "done" and dl < date_str:
                overdue_tasks.append(u)
        overdue_tasks.sort()
        if not overdue_tasks:
            return "Просрочены: нет"
        return f"Просрочены: {', '.join(overdue_tasks)}"

    def cmd_save(self, args):
        if len(args) != 1:
            return "ОШИБКА: неверные аргументы для save"
        filepath = args[0]
        data = {}
        for u, info in self.tasks.items():
            data[u] = {
                "title": info["title"],
                "deps": sorted(info["deps"]),
                "status": info["status"],
                "deadline": info["deadline"],
            }
        try:
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            return f"ОШИБКА: не удалось сохранить файл: {e}"
        return f"Сохранено в {filepath}"

    def cmd_load(self, args):
        if len(args) != 1:
            return "ОШИБКА: неверные аргументы для load"
        filepath = args[0]
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
            if not isinstance(data, dict):
                return "ОШИБКА: некорректный формат JSON"
            new_tasks = {}
            for u, info in data.items():
                if not isinstance(info, dict):
                    return "ОШИБКА: некорректный формат задачи в JSON"
                status = info.get("status", "pending")
                if status not in ("pending", "done", "failed"):
                    return "ОШИБКА: некорректный статус задачи в JSON"
                new_tasks[u] = {
                    "title": info.get("title", ""),
                    "deps": set(info.get("deps", [])),
                    "status": status,
                    "deadline": info.get("deadline", None),
                }
            for u, info in new_tasks.items():
                for d in info["deps"]:
                    if d not in new_tasks:
                        return f"ОШИБКА: неизвестная зависимость {d}"
        except Exception as e:
            return f"ОШИБКА: не удалось загрузить файл: {e}"

        old_tasks = self.tasks
        self.tasks = new_tasks
        if self.find_cycle() is not None:
            self.tasks = old_tasks
            return "ОШИБКА: обнаружена циклическая зависимость в файле"
        return f"Загружено задач: {len(self.tasks)}"

    def run_mode2(self):
        handlers = {
            "add": self.cmd_add,
            "dep": self.cmd_dep,
            "undep": self.cmd_undep,
            "remove": self.cmd_remove,
            "done": self.cmd_done,
            "fail": self.cmd_fail,
            "reset": self.cmd_reset,
            "status": self.cmd_status,
            "ready": self.cmd_ready,
            "order": self.cmd_order,
            "stages": self.cmd_stages,
            "plan": self.cmd_plan,
            "deadline": self.cmd_deadline,
            "overdue": self.cmd_overdue,
            "save": self.cmd_save,
            "load": self.cmd_load,
        }
        for line in sys.stdin:
            stripped = line.strip()
            if not stripped:
                continue
            parts = stripped.split()
            cmd = parts[0]
            args = parts[1:]
            if cmd not in handlers:
                print(f"ОШИБКА: неизвестная команда {cmd}")
            else:
                res = handlers[cmd](args)
                if res is not None:
                    print(res)
        return 0


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8")

    scheduler = TaskScheduler()
    if len(sys.argv) == 1:
        sys.exit(scheduler.run_mode2())
    elif len(sys.argv) == 2:
        sys.exit(scheduler.run_mode1(sys.argv[1]))
    else:
        print("Ошибка: неверное число аргументов командной строки", file=sys.stderr)
        sys.exit(2)


if __name__ == "__main__":
    main()

