import subprocess
import sys
from pathlib import Path
if __name__ == '__main__':
    sys.exit(subprocess.call([sys.executable, '-m', 'pytest', '-q', '--junitxml=artifacts/test-results.xml'], cwd=Path(__file__).resolve().parents[1]))
