"""Source-backed, explainable change-impact graph for pull requests.

We only infer direct static imports among files actually inspected.
Dynamic imports, runtime dependencies and unscanned files are not represented.
"""
from __future__ import annotations

import ast
import posixpath
import re

SOURCE_EXTENSIONS = ('.py', '.ts', '.tsx', '.js', '.jsx')
JS_IMPORT_RE = re.compile(
    r"""(?:\b(?:import|export)\s+(?:[\s\S]{0,180}?\s+from\s+)?|\brequire\s*\(|\bimport\s*\()\s*['"]([^'"]+)['"]""",
    re.M,
)


def _normalize(path: str) -> str:
    path = posixpath.normpath(path.replace('\\', '/'))
    return path if path != '.' else ''


def _resolve(source: str, spec: str, known: set[str]) -> str | None:
    """Resolve only to paths that were fetched, not guessed modules."""
    if not spec or spec.startswith(('http:', 'https:')):
        return None
    if spec.startswith('.'):
        base = _normalize(posixpath.join(posixpath.dirname(source), spec))
    else:
        base = _normalize(spec.replace('.', '/') if source.endswith('.py') else spec)
    candidates = [base] + [base + ext for ext in SOURCE_EXTENSIONS] + [
        base + '/index' + ext for ext in SOURCE_EXTENSIONS
    ] + [base + '/__init__.py']
    for candidate in candidates:
        if candidate in known:
            return candidate
    # Python projects frequently import from a package root below backend/src.
    if source.endswith('.py') and not spec.startswith('.'):
        suffixes = tuple('/' + candidate for candidate in candidates)
        matches = [p for p in known if p.endswith(suffixes)]
        if len(matches) == 1:
            return matches[0]
    return None


def _python_imports(path: str, content: str) -> set[str]:
    try:
        tree = ast.parse(content)
    except (SyntaxError, ValueError):
        return set()
    specs = set()
    module_parts = path.split('/')[:-1]
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            specs.update(a.name for a in node.names)
        elif isinstance(node, ast.ImportFrom):
            if node.level:
                parent = module_parts[:max(0, len(module_parts) - node.level + 1)]
                module = '/'.join(parent + (node.module.split('.') if node.module else []))
                specs.add('./' + posixpath.relpath(module, posixpath.dirname(path)))
            elif node.module:
                specs.add(node.module)
    return specs


def _imports(path: str, content: str, known: set[str]) -> set[str]:
    if path.endswith('.py'):
        specs = _python_imports(path, content)
    elif path.endswith(('.ts', '.tsx', '.js', '.jsx')):
        specs = set(JS_IMPORT_RE.findall(content))
    else:
        return set()
    resolved = {_resolve(path, spec, known) for spec in specs}
    return {p for p in resolved if p and p != path}


def build_change_impact_graph(changed_files: list[dict], repo_files: list[dict],
                              max_nodes: int = 28) -> dict:
    """Graph direct imports among source snapshots. Never infer transitive impact."""
    changed = {_normalize(f.get('filename', '')) for f in changed_files}
    available = {
        _normalize(f['path']): f.get('content', '')
        for f in repo_files if f.get('path') and f['path'].endswith(SOURCE_EXTENSIONS)
    }
    known = set(available)
    links = set()
    for path, content in available.items():
        for dep in _imports(path, content, known):
            links.add((path, dep))
    # Prioritize changed files then inbound/outbound immediate neighbors.
    changed_present = sorted(changed & known)
    adjacent = sorted(
        {src for src, dst in links if dst in changed}
        | {dst for src, dst in links if src in changed}
    )
    chosen = (changed_present + [p for p in adjacent if p not in changed_present])[:max_nodes]
    chosen_set = set(chosen)
    edges = [
        {'from': src, 'to': dst, 'type': 'imports'}
        for src, dst in sorted(links) if src in chosen_set and dst in chosen_set
    ]
    inbound = {p: 0 for p in chosen}
    for edge in edges:
        if edge['to'] in changed:
            inbound[edge['to']] += 1
    nodes = [{
        'id': p,
        'label': posixpath.basename(p),
        'changed': p in changed,
        'direct_dependents': inbound.get(p, 0),
    } for p in chosen]
    return {
        'nodes': nodes,
        'edges': edges,
        'changed_files': len(changed),
        'changed_files_in_sample': len(changed & known),
        'sampled_source_files': len(available),
        'source_file_limit': max_nodes,
        'partial': len(changed & known) < len(changed) or len(chosen) >= max_nodes,
        'note': ('Only direct static imports between sampled source files are shown. '
                 'This is not a runtime call graph; dynamic imports, excluded files, '
                 'and dependencies outside the sample may be missing.'),
    }
