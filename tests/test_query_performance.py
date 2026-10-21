"""PostgreSQL benchmark compatibility entry point; not a mutating test import."""
if __name__ == '__main__':
    import runpy
    from pathlib import Path
    runpy.run_path(str(Path(__file__).resolve().parents[1] / 'scripts' / 'run_benchmarks.py'), run_name='__main__')
