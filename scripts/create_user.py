import argparse
import getpass
import os
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app import create_app
from scripts.generate_dataset import seed_user
if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--username', default='admin')
    parser.add_argument('--role', choices=['Admin', 'Analyst'], default='Admin')
    args = parser.parse_args()
    password = os.getenv('ERP_ADMIN_PASSWORD') or getpass.getpass('New user password (10+ characters): ')
    with create_app().app_context():
        seed_user(args.username, password, args.role)
