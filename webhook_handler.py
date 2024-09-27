import subprocess

from flask import Flask, request, abort
import hmac
import hashlib
import os

app = Flask(__name__)

WEBHOOK_SECRET = os.environ.get('GH_WEBHOOK_SECRET')


def is_valid_signature(payload_body, signature):
    expected_signature = hmac.new(
        key=WEBHOOK_SECRET.encode(),
        msg=payload_body,
        digestmod=hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(f'sha256={expected_signature}', signature)


@app.route('/webhook', methods=['POST'])
def webhook():
    signature = request.headers.get('X-Hub-Signature-256')
    if not signature:
        abort(400, 'X-Hub-Signature-256 header is missing')

    if not is_valid_signature(request.data, signature):
        abort(401, 'Invalid signature')

    if request.json['ref'] == 'refs/heads/main':
        subprocess.run(['git', 'pull', 'origin', 'main'], check=True)
        subprocess.run(['docker', 'compose', 'down'], check=True)
        subprocess.run(['docker', 'compose', 'up', '--build', '-d'], check=True)
        return 'OK', 200

    return 'Not main branch', 200


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5005)
