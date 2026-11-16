"""Dataset provenance, explicit preprocessing, and paired stratified samples."""
from dataclasses import dataclass
from pathlib import Path
import csv
import hashlib
import numpy as np


@dataclass
class Dataset:
    features: np.ndarray
    labels: list[str]
    row_ids: list
    metadata: dict


def sha256(path):
    digest = hashlib.sha256()
    with open(path, 'rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def load_dataset(name, data_dir='data/raw', *, bank_mapping='married'):
    base = Path(data_dir)
    if name == 'adult':
        path = base / 'adult.data'
        columns = [0, 2, 4, 10, 11, 12]
        names = ['age', 'fnlwgt', 'education-num', 'capital-gain', 'capital-loss', 'hours-per-week']
        with path.open() as f:
            rows = list(csv.reader(f, skipinitialspace=True))
        feature_rows, labels, row_ids = [], [], []
        dropped = []
        for i, row in enumerate(rows):
            if len(row) != 15 or any(v.strip() in {'', '?'} for v in row):
                dropped.append(i)
                continue
            feature_rows.append([float(row[j]) for j in columns])
            labels.append('White' if row[8].strip() == 'White' else 'other')
            row_ids.append(i)
        mapping = 'White versus other race categories'
        missing = 'Drop rows with ? or empty fields in any column (complete cases)'
    elif name == 'bank':
        if bank_mapping not in {'married', 'single'}:
            raise ValueError('bank_mapping must be married or single')
        path = base / 'bank_a.csv'
        names = ['age', 'balance', 'day', 'duration', 'campaign', 'pdays', 'previous']
        feature_rows, labels, row_ids, dropped = [], [], [], []
        with path.open() as f:
            for i, row in enumerate(csv.DictReader(f, delimiter=';')):
                if any(row[c] in {'', '?', 'unknown'} for c in names + ['marital']):
                    dropped.append(i)
                    continue
                feature_rows.append([float(row[c]) for c in names])
                labels.append(bank_mapping if row['marital'] == bank_mapping else 'other')
                row_ids.append(i)
        mapping = bank_mapping + ' versus other marital categories'
        missing = 'Drop missing selected numerical/marital fields; retain unknown unused categorical fields and pdays=-1'
    else:
        raise ValueError('Unknown dataset: ' + name)
    x = np.asarray(feature_rows, dtype=float)
    return Dataset(x, labels, row_ids, {'name': name, 'source': str(path),
        'sha256': sha256(path), 'features': names, 'mapping': mapping,
        'missing_policy': missing, 'dropped_rows': dropped, 'eligible_rows': len(x),
        'group_counts': {c: labels.count(c) for c in sorted(set(labels))},
        'row_id_convention': 'zero-based data row, excluding header where present'})


def sample(dataset, n, seed, *, standardized=False):
    if not isinstance(n, int) or not 0 < n <= len(dataset.labels):
        raise ValueError('Requested sample exceeds eligible rows or is nonpositive')
    rng = np.random.default_rng(seed)
    labels = np.asarray(dataset.labels)
    colors, counts = np.unique(labels, return_counts=True)
    quotas = counts * n / len(labels)
    targets = np.floor(quotas).astype(int)
    # Largest remainders, stable color tie-breaking; no forced 50:50 rebalance.
    for index in np.argsort(-(quotas - targets), kind='stable')[:n - targets.sum()]:
        targets[index] += 1
    indices = np.concatenate([rng.choice(np.flatnonzero(labels == c), int(t), replace=False)
                              for c, t in zip(colors, targets)])
    indices.sort()
    x = dataset.features[indices].copy()
    metadata = {**dataset.metadata, 'seed': seed, 'n': n,
                'sampling': 'largest-remainder proportional allocation, without replacement',
                'standardized': standardized,
                'sample_counts': {str(c): int(t) for c, t in zip(colors, targets)}}
    if standardized:
        mean, scale = x.mean(axis=0), x.std(axis=0)
        scale[scale == 0] = 1
        x = (x - mean) / scale
        metadata['scaler'] = {'mean': mean.tolist(), 'scale': scale.tolist(), 'fit': 'sample', 'ddof': 0}
    else:
        metadata['scaler'] = None
    selected_labels = labels[indices].tolist()
    metadata['sample_hash'] = hashlib.sha256(x.tobytes() + '\0'.join(selected_labels).encode()).hexdigest()
    return Dataset(x, selected_labels, [dataset.row_ids[i] for i in indices], metadata)


def synthetic(n=256, seed=0, *, colors=2, skewed=False, correlated=False):
    if colors < 2 or n < colors:
        raise ValueError('Synthetic data needs at least two nonempty colors')
    rng = np.random.default_rng(seed)
    proportions = np.ones(colors) if not skewed else np.asarray([4] + [1] * (colors - 1))
    q = proportions / proportions.sum() * n
    counts = np.floor(q).astype(int)
    for i in np.argsort(-(q - counts), kind='stable')[:n - counts.sum()]:
        counts[i] += 1
    ids = np.repeat(np.arange(colors), counts)
    rng.shuffle(ids)
    x = rng.normal(size=(n, 2))
    if correlated:
        x[:, 0] += 3 * ids
    labels = [str(i) for i in ids]
    return Dataset(x, labels, list(range(n)), {'name': 'synthetic', 'seed': seed,
        'colors': colors, 'skewed': skewed, 'correlated': correlated,
        'sample_counts': {str(i): int(c) for i, c in enumerate(counts)},
        'sample_hash': hashlib.sha256(x.tobytes() + '\0'.join(labels).encode()).hexdigest()})
