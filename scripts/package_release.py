"""Package allowlisted source/assets without credentials, clusters or virtualenvs."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parents[1]
FILES = ('README.md', '.env.example', '.env.production.example', '.gitignore', 'app.py', 'config.py',
         'serve.py', 'requirements.txt', 'requirements-dev.txt', 'constraints.txt', 'run.ps1', 'serve.ps1', 'serve-production.ps1',
         'setup.ps1', 'test.ps1', 'benchmark.ps1', 'pytest.ini')
FOLDERS = ('models', 'routes', 'services', 'utils', 'scripts', 'templates', 'static', 'docs', 'database', 'deploy', 'tests')


def main():
    candidates = [ROOT / name for name in FILES]
    for folder in FOLDERS:
        for path in (ROOT / folder).rglob('*'):
            if not path.is_file() or '__pycache__' in path.parts or path.is_symlink():
                continue
            if folder in ('models', 'routes', 'services', 'utils', 'scripts', 'tests') and path.suffix != '.py':
                continue
            if folder == 'docs' and path.suffix != '.md':
                continue
            if folder == 'database' and path.suffix not in ('.py', '.sql'):
                continue
            if folder == 'deploy' and path.name != 'Caddyfile':
                continue
            if folder == 'templates' and path.suffix != '.html':
                continue
            if folder == 'static' and path.suffix.lower() not in ('.css', '.js', '.woff', '.woff2', '.ttf', '.otf', '.svg', '.png', '.jpg', '.jpeg', '.ico', '.md', '.txt'):
                continue
            candidates.append(path)
    target_dir = ROOT / 'artifacts'
    target_dir.mkdir(exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    target = target_dir / f'erp-windows-release-{stamp}.zip'
    manifest = {}
    with zipfile.ZipFile(target, 'x', compression=zipfile.ZIP_DEFLATED) as package:
        for path in sorted(set(candidates)):
            relative = path.relative_to(ROOT).as_posix()
            if not path.is_file() or path.is_symlink():
                raise ValueError('A required release source file is missing or is a symbolic link: ' + relative)
            payload = path.read_bytes()
            manifest[relative] = hashlib.sha256(payload).hexdigest()
            package.writestr(relative, payload)
        package.writestr('RELEASE-MANIFEST.json', json.dumps({'generated_at': stamp, 'sha256': manifest}, indent=2))
    with zipfile.ZipFile(target) as package:
        assert package.testzip() is None
        assert '.env' not in package.namelist() and not any(name.startswith(('.local/', 'venv/', 'artifacts/')) for name in package.namelist())
    print(json.dumps({'success': True, 'package': str(target), 'source_files': len(manifest), 'bytes': target.stat().st_size}, indent=2))


if __name__ == '__main__':
    main()
