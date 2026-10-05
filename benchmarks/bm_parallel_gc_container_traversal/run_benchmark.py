import gc
import time

import pyperf


DEFAULT_LEVELS = {
    "list": 1000,
    "tuple": 1000,
    "dict-unicode": 700,
    "dict-general": 500,
    "dict-split": 20000,
}
DEFAULT_SPLIT_WIDTH = 16
BENCHMARK_NAMES = {
    kind: f"parallel_gc_{kind.replace('-', '_')}_traversal"
    for kind in DEFAULT_LEVELS
}


class Graph:
    __slots__ = (
        "kind",
        "root",
        "container_nodes",
        "auxiliary_nodes",
        "edges",
        "levels",
        "width",
    )

    def __init__(
        self,
        kind,
        root,
        container_nodes,
        auxiliary_nodes,
        edges,
        levels,
        width=0,
    ):
        self.kind = kind
        self.root = root
        self.container_nodes = container_nodes
        self.auxiliary_nodes = auxiliary_nodes
        self.edges = edges
        self.levels = levels
        self.width = width


class TrackedKey:
    __slots__ = ("index",)

    def __init__(self, index):
        self.index = index


def require_levels(levels):
    if levels <= 0:
        raise ValueError("levels must be positive")


def build_list_graph(levels):
    require_levels(levels)
    current = []
    for width in range(levels):
        current = [current] * width
    return Graph(
        "list",
        current,
        levels,
        0,
        sum(range(levels)),
        levels,
    )


def build_tuple_graph(levels):
    require_levels(levels)
    anchor = []
    current = None
    for width in range(levels):
        references = () if current is None else (current,) * width
        current = (anchor,) + references
    return Graph(
        "tuple",
        current,
        levels,
        1,
        sum(width + 1 for width in range(levels)),
        levels,
    )


def build_unicode_dict_graph(levels):
    require_levels(levels)
    anchor = []
    current = None
    for width in range(levels):
        new = {"anchor": anchor}
        if current is not None:
            new.update((f"value-{index}", current) for index in range(width))
        current = new
    return Graph(
        "dict-unicode",
        current,
        levels,
        1,
        sum(width + 1 for width in range(levels)),
        levels,
    )


def build_general_dict_graph(levels):
    require_levels(levels)
    anchor = []
    current = None
    key_count = 0
    for width in range(levels):
        new = {-1: anchor}
        if current is not None:
            for index in range(width):
                new[TrackedKey(index)] = current
                key_count += 1
        current = new
    return Graph(
        "dict-general",
        current,
        levels,
        key_count + 1,
        sum(2 * (width + 1) for width in range(levels)),
        levels,
    )


def build_split_dict_graph(levels, width=DEFAULT_SPLIT_WIDTH):
    require_levels(levels)
    if width <= 0:
        raise ValueError("split dictionary width must be positive")

    class SplitNode:
        pass

    names = tuple(f"value_{index}" for index in range(width))
    template = SplitNode()
    for name in names:
        setattr(template, name, None)

    current = []
    for _ in range(levels):
        node = SplitNode()
        for name in names:
            setattr(node, name, current)
        current = node.__dict__
    return Graph(
        "dict-split",
        current,
        levels,
        1,
        levels * width,
        levels,
        width,
    )


BUILDERS = {
    "list": build_list_graph,
    "tuple": build_tuple_graph,
    "dict-unicode": build_unicode_dict_graph,
    "dict-general": build_general_dict_graph,
    "dict-split": build_split_dict_graph,
}


def build_graph(kind, levels=None):
    try:
        builder = BUILDERS[kind]
    except KeyError:
        raise ValueError(f"unknown container: {kind!r}") from None
    if levels is None:
        levels = DEFAULT_LEVELS[kind]
    return builder(levels)


def split_table_probe():
    try:
        import _testinternalcapi
    except ImportError:
        return None
    return getattr(_testinternalcapi, "has_split_table", None)


def validate_graph(graph, *, require_split_probe=False):
    current = graph.root
    split_probe = split_table_probe()
    if require_split_probe and graph.kind == "dict-split" and split_probe is None:
        raise RuntimeError("split-dictionary benchmark requires has_split_table")

    for width in reversed(range(graph.levels)):
        if not gc.is_tracked(current):
            raise RuntimeError(f"untracked {graph.kind} node at level {width}")
        if graph.kind == "list":
            if type(current) is not list or len(current) != width:
                raise RuntimeError("list graph shape changed")
            if width:
                child = current[0]
                if any(item is not child for item in current):
                    raise RuntimeError("list graph lost repeated references")
                current = child
        elif graph.kind == "tuple":
            if type(current) is not tuple or len(current) != width + 1:
                raise RuntimeError("tuple graph shape changed")
            if type(current[0]) is not list:
                raise RuntimeError("tuple graph lost its tracked anchor")
            if width:
                child = current[1]
                if any(item is not child for item in current[1:]):
                    raise RuntimeError("tuple graph lost repeated references")
                current = child
        elif graph.kind == "dict-unicode":
            if type(current) is not dict or len(current) != width + 1:
                raise RuntimeError("Unicode dictionary graph shape changed")
            if any(type(key) is not str for key in current):
                raise RuntimeError("Unicode dictionary graph has a general key")
            if width:
                child = current["value-0"]
                values = (
                    value
                    for key, value in current.items()
                    if key != "anchor"
                )
                if any(value is not child for value in values):
                    raise RuntimeError("Unicode dictionary references changed")
                current = child
        elif graph.kind == "dict-general":
            if type(current) is not dict or len(current) != width + 1:
                raise RuntimeError("general dictionary graph shape changed")
            keys = [key for key in current if type(key) is TrackedKey]
            if len(keys) != width or any(not gc.is_tracked(key) for key in keys):
                raise RuntimeError("general dictionary keys changed")
            if width:
                child = current[keys[0]]
                if any(current[key] is not child for key in keys):
                    raise RuntimeError("general dictionary references changed")
                current = child
        elif graph.kind == "dict-split":
            if type(current) is not dict or len(current) != graph.width:
                raise RuntimeError("split dictionary graph shape changed")
            if split_probe is not None and not split_probe(current):
                raise RuntimeError("dictionary is not split")
            child = current["value_0"]
            if any(value is not child for value in current.values()):
                raise RuntimeError("split dictionary references changed")
            current = child
        else:
            raise RuntimeError(f"unvalidated graph kind: {graph.kind!r}")


def benchmark_collection(loops, graph):
    total = 0.0
    for _ in range(loops):
        gc.collect()
        start = time.perf_counter()
        collected = gc.collect()
        total += time.perf_counter() - start
        if collected not in (None, 0):
            raise RuntimeError(f"collection unexpectedly found {collected} objects")
    return total


def add_cmdline_args(command, args):
    command.extend(("--container", args.container))
    if args.levels is not None:
        command.extend(("--levels", str(args.levels)))


def main():
    runner = pyperf.Runner(add_cmdline_args=add_cmdline_args)
    runner.argparser.add_argument(
        "--container", choices=tuple(DEFAULT_LEVELS), required=True
    )
    runner.argparser.add_argument("--levels", type=int)
    args = runner.parse_args()

    gc.disable()
    graph = build_graph(args.container, args.levels)
    gc.collect()
    validate_graph(graph, require_split_probe=True)

    runner.metadata.update({
        "description": "Parallel-GC exact-container traversal",
        "parallel_gc_graph_kind": graph.kind,
        "parallel_gc_graph_container_nodes": graph.container_nodes,
        "parallel_gc_graph_auxiliary_nodes": graph.auxiliary_nodes,
        "parallel_gc_graph_edges": graph.edges,
        "parallel_gc_graph_levels": graph.levels,
        "parallel_gc_graph_split_width": graph.width,
        "parallel_gc_collections_per_loop": 2,
        "parallel_gc_measured_collections_per_loop": 1,
    })
    runner.bench_time_func(
        BENCHMARK_NAMES[graph.kind], benchmark_collection, graph
    )


if __name__ == "__main__":
    main()
