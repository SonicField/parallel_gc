"""Check generated Makefile header prerequisites without changing headers."""
import pathlib
import subprocess
import sys

root = pathlib.Path('/tmp/parallel-gc-integration-fKKFb7')
phase = sys.argv[1]
assert phase in ('before', 'after')
headers = (
    'pycore_gc_barrier.h',
    'pycore_gc_ft_parallel.h',
    'pycore_gc_parallel.h',
    'pycore_gc_random_walk.h',
    'pycore_ws_deque.h',
)
for mode, target in (
    ('gil-dbg', 'Python/gc_parallel.o'),
    ('ft-dbg', 'Python/gc_free_threading_parallel.o'),
):
    for header in (*headers, 'pycore_gc.h'):
        command = ['make', '-n', '-W', str(root / 'source/Include/internal' / header), target]
        result = subprocess.run(command, cwd=root / mode, text=True,
                                stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        assert result.returncode == 0, result.stdout
        recompiles = ' -c ' in result.stdout
        expected = phase == 'after' or header == 'pycore_gc.h'
        print(f'{mode} {header}: recompiles={recompiles}, expected={expected}', flush=True)
        assert recompiles == expected, result.stdout
print(f'{phase}: all 12 checks passed')
