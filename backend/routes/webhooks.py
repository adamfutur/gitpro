from flask import Blueprint, request, jsonify
from services.pr_review import build_pr_review
from services.github_service import post_pr_comment, create_commit_status
from services.db_service import get_auto_review
from services.cache import pr_analysis_cache
import hashlib
import hmac
import os
import threading

webhooks_bp = Blueprint('webhooks', __name__)

HANDLED_ACTIONS = {'opened', 'synchronize', 'reopened'}
STATUS_CONTEXT = 'gitcat/review'

def _verify_signature(payload_body, signature_header):
    secret = os.getenv('GITHUB_WEBHOOK_SECRET')
    if not secret or not signature_header or not signature_header.startswith('sha256='):
        return False
    expected = 'sha256=' + hmac.new(secret.encode('utf-8'), payload_body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature_header)

def _run_auto_review(repo_id, pr_number, github_user_id, github_token, owner, repo_name, head_sha):
    """Reviews a PR, posts the result as a GitHub comment, and sets a commit status reflecting
    the verdict — usable as a required check in branch protection. No browser session involved."""
    create_commit_status(
        github_token, owner, repo_name, head_sha,
        state='pending', description='gitcat is reviewing this PR...', context=STATUS_CONTEXT,
    )

    try:
        result, owner, repo_name = build_pr_review(github_token, repo_id, pr_number)
        pr_analysis_cache[(repo_id, pr_number, github_user_id)] = result

        comment = f"## 🐱 gitcat automated review\n\n{result['review']}\n\n" \
                  f"*+{result['additions']}/-{result['deletions']} across {result['files_changed']} files. " \
                  f"Posted automatically by [gitcat](https://github.com/{owner}/{repo_name}) — not a human reviewer.*"
        post_pr_comment(github_token, owner, repo_name, pr_number, comment)

        verdict = result.get('verdict', {'status': 'pass', 'reason': 'No blocking issues identified.'})
        create_commit_status(
            github_token, owner, repo_name, result.get('head_sha', head_sha),
            state='success' if verdict['status'] == 'pass' else 'failure',
            description=verdict['reason'] or 'Review complete.',
            context=STATUS_CONTEXT,
            target_url=result.get('html_url'),
        )
    except Exception as e:
        print(f"Auto-Review Error: {e}")
        import traceback
        traceback.print_exc()
        create_commit_status(
            github_token, owner, repo_name, head_sha,
            state='error', description='gitcat review failed — see server logs.', context=STATUS_CONTEXT,
        )

@webhooks_bp.route('/github', methods=['POST'])
def github_webhook():
    signature = request.headers.get('X-Hub-Signature-256', '')
    if not _verify_signature(request.data, signature):
        return jsonify({'error': 'Invalid signature'}), 401

    event = request.headers.get('X-GitHub-Event')
    payload = request.get_json(silent=True) or {}

    if event == 'ping':
        return jsonify({'message': 'pong'}), 200

    if event != 'pull_request' or payload.get('action') not in HANDLED_ACTIONS:
        return jsonify({'message': 'ignored'}), 200

    repo_id = payload.get('repository', {}).get('id')
    pr = payload.get('pull_request') or {}
    pr_number = pr.get('number')
    head_sha = pr.get('head', {}).get('sha')
    if not repo_id or not pr_number or not head_sha:
        return jsonify({'message': 'ignored'}), 200

    config = get_auto_review(repo_id)
    if not config:
        return jsonify({'message': 'auto-review not enabled for this repo'}), 200

    owner = payload.get('repository', {}).get('owner', {}).get('login')
    repo_name = payload.get('repository', {}).get('name')

    thread = threading.Thread(
        target=_run_auto_review,
        args=(repo_id, pr_number, config['github_user_id'], config['github_token'], owner, repo_name, head_sha),
        daemon=True,
    )
    thread.start()

    return jsonify({'message': 'review queued'}), 202
