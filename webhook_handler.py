import logging
from flask import Flask, request, abort
import hmac
import hashlib
import os
import subprocess
import docker
from docker.errors import DockerException

app = Flask(__name__)

WEBHOOK_SECRET = os.environ.get('GH_WEBHOOK_SECRET')

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Docker client
try:
    docker_client = docker.DockerClient(base_url='unix://var/run/docker.sock')
except DockerException as e:
    logger.error(f'Failed to connect to Docker daemon: {e}')
    docker_client = None


def is_valid_signature(payload_body, signature):
    expected_signature = hmac.new(
        key=WEBHOOK_SECRET.encode(),
        msg=payload_body,
        digestmod=hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(f'sha256={expected_signature}', signature)


def pull_latest_code():
    """Pull the latest code from the main branch."""
    logger.info('Pulling latest code from GitHub')
    try:
        subprocess.check_call(['git', 'pull', 'origin', 'main'], cwd='/stocklerts')
    except subprocess.CalledProcessError as e:
        logger.error(f'Git pull failed: {e}')
        raise


def rebuild_and_restart_containers():
    """Rebuild and restart Docker containers using Docker SDK."""
    if docker_client is None:
        logger.error('Docker client is not initialized.')
        raise DockerException('Docker client not available.')

    try:
        # Rebuild the stocklerts-app container
        logger.info('Rebuilding stocklerts-app container')
        image, build_logs = docker_client.images.build(
            path='/stocklerts',
            dockerfile='Dockerfile',
            tag='stocklerts-app:latest',
            rm=True
        )
        for chunk in build_logs:
            if 'stream' in chunk:
                for line in chunk['stream'].splitlines():
                    logger.debug(line)

        # Restart the stocklerts-app container
        container = docker_client.containers.get('stocklerts-app')
        logger.info('Restarting stocklerts-app container')
        container.stop()
        container.remove()
        docker_client.containers.run(
            'stocklerts-app:latest',
            detach=True,
            name='stocklerts-app',
            volumes=['/stocklerts:/stocklerts'],  # Update with your actual path
            environment={
                'FINNHUB_API_KEY': os.getenv('FINNHUB_API_KEY'),
                'ENCRYPT_KEY': os.getenv('ENCRYPT_KEY')
            },
            restart_policy={"Name": "unless-stopped"}
        )
    except DockerException as e:
        logger.error(f'Docker operation failed: {e}')
        raise


@app.route('/webhook', methods=['POST'])
def webhook():
    logging.info(f'Request: {request.json}')

    signature = request.headers.get('X-Hub-Signature-256')
    if not signature:
        abort(400, 'X-Hub-Signature-256 header is missing')

    if not is_valid_signature(request.data, signature):
        abort(401, 'Invalid signature')

    if request.json.get('ref') == 'refs/heads/main':
        try:
            pull_latest_code()
            rebuild_and_restart_containers()
        except Exception as e:
            logger.error(f'Deployment failed: {e}')
            abort(500, 'Deployment failed')

        return 'OK', 200

    return 'Not main branch', 200


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)