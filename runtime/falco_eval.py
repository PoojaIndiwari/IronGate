"""Tiny evaluator for the subset of Falco filter syntax used in falco/custom-rules.yaml.

Why it exists: the replay test used to re-implement each rule in Python, so a rule could
be edited (or be wrong) while the test stayed green. This evaluates the *actual condition
text* from the rules file against recorded events.

Limits (be honest about them): it is not Falco. It supports and/or/not, parentheses,
=, !=, <, <=, >, >=, in (...), startswith, endswith, contains, lists and macros. A field
that is missing from an event makes every comparison false, which mirrors how Falco treats
fields that are not available for an event. It cannot tell you whether a real Falco build
supplies a field (that is what falco/test-rules.md on a live cluster is for).
"""
import re

# Mirrors the macros Falco ships in falco_rules.yaml. Rules here use these four.
DEFAULT_MACROS = {
    "container": "container.id != host",
    "spawned_process": "evt.type in (execve, execveat) and evt.dir = <",
    "open_read": "evt.type in (open, openat, openat2) and evt.is_open_read = true and fd.typechar = f and fd.num >= 0",
    "open_write": "evt.type in (open, openat, openat2) and evt.is_open_write = true and fd.typechar = f and fd.num >= 0",
}

_TOKEN = re.compile(
    r"""\s*(?:
        (?P<str>"(?:[^"\\]|\\.)*")
      | (?P<op>!=|>=|<=|=|<|>|\(|\)|,)
      | (?P<word>[^\s(),=<>!"]+)
    )""",
    re.X,
)
_WORD_OPS = {"startswith", "endswith", "contains", "in", "and", "or", "not"}


def tokenize(text):
    pos, out = 0, []
    text = text.strip()
    while pos < len(text):
        m = _TOKEN.match(text, pos)
        if not m or m.end() == pos:
            raise ValueError(f"cannot tokenize near: {text[pos:pos + 30]!r}")
        pos = m.end()
        if m.group("str") is not None:
            out.append(("str", m.group("str")[1:-1]))
        elif m.group("op") is not None:
            out.append(("op", m.group("op")))
        else:
            word = m.group("word")
            out.append(("kw", word.lower()) if word.lower() in _WORD_OPS else ("word", word))
    return out


class Evaluator:
    def __init__(self, lists, macros=None):
        self.lists = lists
        self.macros = dict(DEFAULT_MACROS)
        if macros:
            self.macros.update(macros)

    def matches(self, condition, event):
        return bool(self._run(condition, event, depth=0))

    def _run(self, condition, event, depth):
        if depth > 10:
            raise ValueError("macro nesting too deep")
        parser = _Parser(tokenize(condition), event, self, depth)
        result = parser.parse_or()
        if parser.i != len(parser.toks):
            raise ValueError(f"unexpected token {parser.toks[parser.i]} in: {condition}")
        return result


class _Parser:
    def __init__(self, toks, event, ev, depth):
        self.toks, self.i, self.event, self.ev, self.depth = toks, 0, event, ev, depth

    def peek(self):
        return self.toks[self.i] if self.i < len(self.toks) else (None, None)

    def take(self):
        tok = self.toks[self.i]
        self.i += 1
        return tok

    def expect(self, kind, value):
        tok = self.take()
        if tok != (kind, value):
            raise ValueError(f"expected {value!r}, got {tok}")

    def parse_or(self):
        left = self.parse_and()
        while self.peek() == ("kw", "or"):
            self.take()
            right = self.parse_and()
            left = left or right
        return left

    def parse_and(self):
        left = self.parse_not()
        while self.peek() == ("kw", "and"):
            self.take()
            right = self.parse_not()
            left = left and right
        return left

    def parse_not(self):
        if self.peek() == ("kw", "not"):
            self.take()
            return not self.parse_not()
        return self.parse_atom()

    def parse_atom(self):
        if self.peek() == ("op", "("):
            self.take()
            value = self.parse_or()
            self.expect("op", ")")
            return value
        kind, name = self.take()
        if kind != "word":
            raise ValueError(f"unexpected token {(kind, name)}")
        nxt = self.peek()
        is_compare = nxt[0] == "op" and nxt[1] in ("=", "!=", "<", "<=", ">", ">=") or nxt[0] == "kw" and nxt[1] in ("in", "startswith", "endswith", "contains")
        if not is_compare:
            if name not in self.ev.macros:
                raise ValueError(f"unknown macro or bare word: {name}")
            return self.ev._run(self.ev.macros[name], self.event, self.depth + 1)
        op = self.take()[1]
        if op == "in":
            self.expect("op", "(")
            values = []
            while self.peek() != ("op", ")"):
                if self.peek() == ("op", ","):
                    self.take()
                    continue
                values.extend(self.value_or_list(self.take()))
            self.expect("op", ")")
        else:
            values = self.value_or_list(self.take())
        return self.compare(name, op, values)

    def value_or_list(self, tok):
        kind, text = tok
        if kind == "word" and text in self.ev.lists:
            return list(self.ev.lists[text])
        return [text]

    def compare(self, field, op, values):
        if field not in self.event or self.event[field] is None:
            return False
        actual = self.event[field]
        if isinstance(actual, bool):
            actual = "true" if actual else "false"
        actual_s = str(actual)
        if op in ("=", "in"):
            return any(actual_s == str(v) for v in values)
        if op == "!=":
            return all(actual_s != str(v) for v in values)
        v = str(values[0])
        if op == "startswith":
            return actual_s.startswith(v)
        if op == "endswith":
            return actual_s.endswith(v)
        if op == "contains":
            return v in actual_s
        try:
            a, b = float(actual_s), float(v)
        except ValueError:
            return False
        return {"<": a < b, "<=": a <= b, ">": a > b, ">=": a >= b}[op]
