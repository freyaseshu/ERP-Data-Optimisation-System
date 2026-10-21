"""Inspect actual timestamped benchmark JSON; legacy CSVs are never assumed verified."""
import argparse
import json
from pathlib import Path
if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('evidence',nargs='?')
    args=parser.parse_args()
    candidates=sorted((Path(__file__).resolve().parents[1]/'artifacts').glob('benchmarks-*.json'))
    target=Path(args.evidence) if args.evidence else candidates[-1] if candidates else None
    if target is None:parser.error('No evidence yet. Run benchmark.ps1 -ApproveIndexes first.')
    result=json.loads(target.read_text(encoding='utf-8'))
    for row in result['results']:
        print(row['id'],row.get('baseline_time_ms'),row.get('optimised_time_ms'),row.get('improvement_percentage'),'equivalent:',row.get('equivalent'),'new index:',row.get('index_created'))
