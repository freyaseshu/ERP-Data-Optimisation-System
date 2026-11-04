"""Check the configured deployment without changing a database or printing secrets."""
import argparse
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app import create_app
from services.deployment_service import deployment_checks


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--production', action='store_true', help='Require APP_ENV=production rather than accepting presentation mode.')
    args = parser.parse_args()
    try:
        app = create_app()
        with app.app_context():
            result = deployment_checks()
            if args.production and result['mode'] != 'production':
                result['success'] = False
                result['checks'].append({'name': 'production_mode', 'passed': False, 'detail': 'Set APP_ENV=production and configure HTTPS and restricted roles.'})
    except ValueError as exc:
        result = {'success': False, 'checks': [{'name': 'configuration', 'passed': False, 'detail': str(exc)}]}
    print(json.dumps(result, indent=2))
    return 0 if result['success'] else 1


if __name__ == '__main__':
    sys.exit(main())
