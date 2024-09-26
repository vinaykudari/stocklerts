import logging
from flask import Flask, request, abort
import hmac
import hashlib
import os
import subprocess

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
    logging.info(f'Request: {request.json}')

    # signature = request.headers.get('X-Hub-Signature-256')
    # if not signature:
    #     abort(400, 'X-Hub-Signature-256 header is missing')
    #
    # if not is_valid_signature(request.data, signature):
    #     abort(401, 'Invalid signature')

    if request.json.get('ref') == 'refs/heads/main':
        try:
            logging.info('Pulling latest code from GitHub')
            # Execute git pull on the host via Docker Compose
            subprocess.check_call(['git', 'pull', 'origin', 'main'])
            subprocess.check_call(['docker-compose', 'up', '-d', '--build'])

        except subprocess.CalledProcessError as e:
            logging.error(f'Error during deployment: {e}')
            abort(500, 'Deployment failed')

        return 'OK', 200

    return 'Not main branch', 200


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
