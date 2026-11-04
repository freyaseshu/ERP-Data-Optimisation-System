"""Windows-compatible WSGI entry point with deployment checks and proxy limits."""
import logging
import os
import ipaddress
from app import create_app


def server_options():
    host = os.getenv('ERP_BIND_HOST', '127.0.0.1')
    port = int(os.getenv('ERP_PORT', '8080'))
    threads = int(os.getenv('ERP_THREADS', '4'))
    if not 1 <= port <= 65535 or not 2 <= threads <= 16:
        raise ValueError('ERP_PORT must be 1–65535 and ERP_THREADS must be 2–16.')
    options = dict(host=host, port=port, threads=threads, expose_tracebacks=False,
                   max_request_body_size=65536, max_request_header_size=16384,
                   channel_timeout=60, connection_limit=100, channel_request_lookahead=0)
    proxy = os.getenv('ERP_TRUSTED_PROXY', '')
    if proxy:
        ipaddress.ip_address(proxy)  # Wildcard trust is intentionally unsupported.
        options.update(trusted_proxy=proxy, trusted_proxy_count=1,
                       trusted_proxy_headers={'x-forwarded-for', 'x-forwarded-proto', 'x-forwarded-host', 'x-forwarded-port'},
                       clear_untrusted_proxy_headers=True)
    return options


def main():
    from waitress import serve
    from services.deployment_service import deployment_checks
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(name)s %(message)s')
    application = create_app()
    with application.app_context():
        result = deployment_checks()
        for check in result['checks']:
            logging.info('%s %s: %s', 'PASS' if check['passed'] else 'FAIL', check['name'], check['detail'])
        if not result['success']:
            raise SystemExit('Deployment checks failed. See docs/deployment.md; server was not started.')
    serve(application, **server_options())


if __name__ == '__main__':
    main()
