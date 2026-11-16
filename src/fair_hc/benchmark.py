"""Sequential, resumable experiments. Every planned run has a visible status."""
from pathlib import Path
from importlib.metadata import version
import gzip
import hashlib
import itertools
import json
import platform
import resource
import sys
import time
import traceback

from .adapters import default_parameters, run_method
from .algorithm import validate_parameters
from .data import load_dataset, sample, synthetic, sha256
from .geometry import average_linkage, similarities
from .metrics import evaluate

METHODS = ['average', 'make_fair', 'star', 'splitting_only', 'random_fold']


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def atomic_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + '.tmp')
    temporary.write_text(json.dumps(value, indent=2, allow_nan=False) + '\n')
    temporary.replace(path)


def gzip_json(path, value):
    path = Path(path)
    temporary = path.with_suffix(path.suffix + '.tmp')
    with temporary.open('wb') as f:
        with gzip.GzipFile(fileobj=f, mode='wb', mtime=0, filename='') as z:
            z.write(json.dumps(value, separators=(',', ':'), allow_nan=False).encode())
    temporary.replace(path)


def expand(config):
    for experiment in config['experiments']:
        for n, seed, parameters in itertools.product(
                experiment['sizes'], experiment['seeds'], experiment.get('parameters', [None])):
            yield {**{k: v for k, v in experiment.items() if k not in {'sizes', 'seeds', 'parameters'}},
                   'n': n, 'seed': seed, 'parameters': parameters}


def source_hash():
    directory = Path(__file__).parent
    names = ['tree.py', 'operators.py', 'algorithm.py', 'metrics.py', 'geometry.py',
             'data.py', 'adapters.py', 'benchmark.py']
    return digest({name: sha256(directory / name) for name in names})


def environment():
    return {'python': platform.python_version(), 'platform': platform.platform(),
            'machine': platform.machine(),
            'dependencies': {n: version(n) for n in ['fair-hc', 'numpy', 'scipy', 'matplotlib']},
            'source_hash': source_hash()}


def peak_rss():
    value = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return int(value if sys.platform == 'darwin' else value * 1024)


def run_benchmark(config_path, output, *, data_dir='data/raw', resume=False,
                  memory_gib=8.0, time_limit=None):
    config = json.loads(Path(config_path).read_text())
    if config.get('version') != 1 or memory_gib <= 0:
        raise ValueError('Expected config version 1 and positive memory budget')
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    env = environment()
    methods = config.get('methods', METHODS)
    # Hash custom adapters too; module import is explicitly requested by config.
    import importlib
    for method in methods:
        if ':' in method:
            module = importlib.import_module(method.split(':')[0])
            env.setdefault('adapters', {})[method] = sha256(module.__file__)
    loaded = {}
    for spec in config['experiments']:
        if spec['dataset'] != 'synthetic':
            key = (spec['dataset'], spec.get('bank_mapping', 'married'))
            if key not in loaded:
                loaded[key] = load_dataset(key[0], data_dir, bank_mapping=key[1])
    identity = {'config': config, 'environment': env,
                'inputs': {str(k): d.metadata['sha256'] for k, d in loaded.items()}}
    signature = digest(identity)
    manifest_path = output / 'manifest.json'
    old = json.loads(manifest_path.read_text()) if manifest_path.exists() else None
    if old and (not resume or old['signature'] != signature):
        raise ValueError('Output exists: use --resume with identical code, dependencies, config and inputs, or a new directory')
    manifest = old or {'version': 1, 'signature': signature, **identity, 'runs': {},
                       'profile': config.get('name', Path(config_path).stem)}
    specs = list(expand(config))
    for spec in specs:
        for method in methods:
            run_id = digest({'signature': signature, 'spec': spec, 'method': method})[:20]
            manifest['runs'].setdefault(run_id, {'status': 'pending', 'spec': spec, 'method': method})
    manifest['memory_budget_gib'] = memory_gib
    atomic_json(manifest_path, manifest)
    started = time.perf_counter()
    for spec in specs:
        run_ids = {method: digest({'signature': signature, 'spec': spec, 'method': method})[:20]
                   for method in methods}
        if all(manifest['runs'][rid]['status'] in {'complete', 'excluded'} for rid in run_ids.values()):
            continue
        if time_limit is not None and time.perf_counter() - started >= time_limit:
            manifest['stop_reason'] = 'time_limit; remaining runs are pending'
            break
        # Conservative working-set allowance: square similarities, condensed
        # linkage work/copies, validation blocks, Python trees, and runtime base.
        estimate = 40 * spec['n'] ** 2 + 128 * 1024 ** 2
        if estimate > memory_gib * 1024 ** 3:
            for rid in run_ids.values():
                manifest['runs'][rid].update(status='resource_limited', reason='estimated_memory_budget',
                                              estimated_bytes=estimate)
            atomic_json(manifest_path, manifest)
            continue
        try:
            start = time.perf_counter()
            if spec['dataset'] == 'synthetic':
                data = synthetic(spec['n'], spec['seed'], colors=spec.get('colors', 2),
                                 skewed=spec.get('skewed', False), correlated=spec.get('correlated', False))
            else:
                data = sample(loaded[(spec['dataset'], spec.get('bank_mapping', 'married'))],
                              spec['n'], spec['seed'], standardized=spec.get('standardized', False))
            parameters = spec['parameters'] or default_parameters(data.labels)
            validate_parameters(**parameters, colors=len(set(data.labels)))
            sample_id = digest({'metadata': data.metadata, 'rows': data.row_ids})[:20]
            atomic_json(output / 'samples' / (sample_id + '.json'),
                        {'row_ids': data.row_ids, 'labels': data.labels, 'metadata': data.metadata})
            w = similarities(data.features)
            preprocessing = time.perf_counter() - start
            start = time.perf_counter()
            initial = average_linkage(w, data.labels)
            construction = time.perf_counter() - start
            baseline_cost = None
            for method, rid in run_ids.items():
                entry = manifest['runs'][rid]
                if entry['status'] == 'complete':
                    if method == 'average':
                        baseline_cost = json.loads((output / 'runs' / rid / 'metrics.json').read_text())['metrics']['cost']
                    continue
                run_dir = output / 'runs' / rid
                run_dir.mkdir(parents=True, exist_ok=True)
                entry.update(status='running')
                atomic_json(manifest_path, manifest)
                try:
                    start = time.perf_counter()
                    tree, diagnostics = run_method(method, data, spec['seed'], parameters, initial)
                    transformation = time.perf_counter() - start
                    start = time.perf_counter()
                    metrics = evaluate(tree, w, data.labels)
                    evaluation = time.perf_counter() - start
                    if baseline_cost is None:
                        baseline_cost = metrics['cost'] if method == 'average' else evaluate(initial, w, data.labels)['cost']
                    metrics['cost_ratio_to_average'] = metrics['cost'] / baseline_cost if baseline_cost else None
                    clusters = metrics.pop('clusters')
                    rss = peak_rss()
                    gzip_json(run_dir / 'clusters.json.gz', clusters)
                    gzip_json(run_dir / 'tree.json.gz', tree.to_dict())
                    atomic_json(run_dir / 'metrics.json', {'run_id': rid, 'sample_id': sample_id,
                        'spec': spec, 'method': method, 'parameters': parameters,
                        'metrics': metrics, 'diagnostics': diagnostics, 'environment': env,
                        'times': {'preprocessing': preprocessing, 'construction': construction,
                                  'transformation': transformation, 'evaluation': evaluation},
                        'shared_stage_note': 'preprocessing and construction shared across methods in this sample',
                        'peak_process_rss_bytes': rss, 'estimated_working_set_bytes': estimate})
                    entry.update(status='complete', path=str(Path('runs') / rid / 'metrics.json'),
                                 sample_id=sample_id, parameters=parameters)
                    if rss > memory_gib * 1024 ** 3:
                        manifest['stop_reason'] = 'observed_process_peak_exceeded_budget'
                        atomic_json(manifest_path, manifest)
                        return manifest
                except Exception as exc:
                    entry.update(status='failed', reason=str(exc), traceback=traceback.format_exc())
                atomic_json(manifest_path, manifest)
            print(f"{spec['dataset']} n={spec['n']} seed={spec['seed']} done", flush=True)
            del w, initial
        except ValueError as exc:
            for rid in run_ids.values():
                if manifest['runs'][rid]['status'] != 'complete':
                    manifest['runs'][rid].update(status='excluded', reason=str(exc))
        except Exception as exc:
            for rid in run_ids.values():
                if manifest['runs'][rid]['status'] != 'complete':
                    manifest['runs'][rid].update(status='failed', reason=str(exc), traceback=traceback.format_exc())
        atomic_json(manifest_path, manifest)
    counts = {}
    for entry in manifest['runs'].values():
        counts[entry['status']] = counts.get(entry['status'], 0) + 1
    manifest['status_counts'] = counts
    manifest['complete'] = all(e['status'] in {'complete', 'excluded'} for e in manifest['runs'].values())
    if manifest['complete']:
        manifest.pop('stop_reason', None)
    manifest['elapsed_this_invocation_seconds'] = time.perf_counter() - started
    atomic_json(manifest_path, manifest)
    return manifest
