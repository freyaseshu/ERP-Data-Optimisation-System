"""Compatibility entry point: use the transactional PostgreSQL dataset loader."""
import runpy
from pathlib import Path
runpy.run_path(str(Path(__file__).resolve().parents[1] / 'scripts' / 'generate_dataset.py'), run_name='__main__')
