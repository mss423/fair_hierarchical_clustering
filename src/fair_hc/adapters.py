"""Adapter protocol: (dataset, seed, parameters, starting_tree=None) -> Tree."""
from .algorithm import transform
from .geometry import similarities, average_linkage
from .tree import star


def default_parameters(labels):
    k = 2
    h = 4 * k ** len(set(labels))
    return {'h': h, 'k': k, 'epsilon': 1 / (4 * h)}


def benchmark_adapter(dataset, seed, parameters, starting_tree=None):
    """Public MakeFair adapter, also usable outside the CLI."""
    start = starting_tree if starting_tree is not None else average_linkage(
        similarities(dataset.features), dataset.labels)
    return transform(start, dataset.labels, seed=seed, **parameters).tree


def run_method(method, dataset, seed, parameters, starting_tree):
    if method == 'average':
        return starting_tree, {}
    if method == 'star':
        return star(dataset.labels), {}
    if method in {'make_fair', 'splitting_only', 'random_fold'}:
        policy = {'make_fair': 'density', 'splitting_only': 'none', 'random_fold': 'random'}[method]
        result = transform(starting_tree, dataset.labels, seed=seed, folding=policy, **parameters)
        return result.tree, result.diagnostics
    if ':' in method:
        import importlib
        module, function = method.split(':', 1)
        result = getattr(importlib.import_module(module), function)(
            dataset, seed, parameters, starting_tree.copy())
        result.validate()
        if result.labels != dataset.labels:
            raise ValueError('Custom adapter changed label-to-row correspondence')
        return result, {'adapter': method}
    raise ValueError('Unknown method: ' + method)
