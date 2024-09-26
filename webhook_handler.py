import logging

from flask import Flask, request, abort
import hmac
import hashlib
import os
import docker

app = Flask(__name__)

WEBHOOK_SECRET = os.environ.get('GH_WEBHOOK_SECRET')


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def is_valid_signature(payload_body, signature):
    expected_signature = hmac.new(
        key=WEBHOOK_SECRET.encode(),
        msg=payload_body,
        digestmod=hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(f'sha256={expected_signature}', signature)


@app.route('/webhook', methods=['POST'])
def webhook():
    logging.info(f'Request: {request.json()}')

    # test
    # signature = request.headers.get('X-Hub-Signature-256')
    # if not signature:
    #     abort(400, 'X-Hub-Signature-256 header is missing')
    #
    # if not is_valid_signature(request.data, signature):
    #     abort(401, 'Invalid signature')

    if request.json['ref'] == 'refs/heads/main':
        client = docker.from_env()

        try:
            app_container = client.containers.get('stocklerts-app')
            logging.info('Updating the codebase')

            # Execute git pull
            exit_code, output = app_container.exec_run('git pull origin main')
            if exit_code != 0:
                logging.info(f'Error pulling latest code: {output.decode()}')
                abort(500, 'Failed to pull the latest code')

            logging.info('Restarting stocklerts')
            app_container.restart()

        except docker.errors.NotFound:
            logging.info('Error: Container not found')
            abort(500, 'Container not found')

        except Exception as e:
            logging.info(f'Error: {e}')
            abort(500, 'Internal server error')

        return 'OK', 200

    return 'Not main branch', 200


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
