"""Run approved workload and export actual results with full evidence."""
import argparse
import csv
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app import create_app
from services.benchmark_service import BenchmarkService

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Creates the displayed workload indexes after explicit approval.')
    parser.add_argument('--approve-indexes', action='store_true', required=True)
    parser.add_argument('--iterations', type=int, default=3)
    args = parser.parse_args()
    with create_app().app_context():
        result = BenchmarkService.run_all_benchmarks(args.iterations)
        folder = Path(__file__).resolve().parents[1] / 'artifacts'
        folder.mkdir(exist_ok=True)
        stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
        target = folder / ('benchmarks-' + stamp)
        target.with_suffix('.json').write_text(json.dumps(result, indent=2, default=str), encoding='utf-8')
        fields = ['id','name','success','baseline_time_ms','optimised_time_ms','improvement_percentage','equivalent','index_created','index_already_present','error']
        with target.with_suffix('.csv').open('w', newline='', encoding='utf-8') as handle:
            writer = csv.DictWriter(handle, fieldnames=fields, extrasaction='ignore')
            writer.writeheader()
            writer.writerows(result['results'])
        for item in result['results']:
            print({key:item.get(key) for key in fields})
        print('Evidence saved to', target.with_suffix('.json'))
        sys.exit(0 if result['success'] else 1)
