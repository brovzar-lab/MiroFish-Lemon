"""
Credit health check utility
Pings OpenRouter /auth/key at startup and warns if balance is low.
Falls back to LiteLLM /health check when using a proxy.
"""
import os
import logging

logger = logging.getLogger('mirofish.credit_check')

LOW_CREDIT_THRESHOLD = 1.00  # USD


def check_openrouter_credits():
    """
    Checks the LLM API key balance / reachability.
    Returns dict: { 'balance': float | None, 'is_low': bool, 'error': str | None }
    """
    api_key = os.environ.get('LLM_API_KEY', '')
    base_url = os.environ.get('LLM_BASE_URL', 'https://openrouter.ai/api/v1')

    try:
        import requests

        # If routing through LiteLLM or another proxy — just ping /health
        if 'openrouter.ai' not in base_url:
            health_url = base_url.rstrip('/v1').rstrip('/') + '/health'
            try:
                resp = requests.get(health_url, timeout=5)
                if resp.status_code == 200:
                    logger.info(f"[CREDIT CHECK] ✅ LLM proxy reachable: {base_url}")
                else:
                    logger.warning(f"[CREDIT CHECK] ⚠️  LLM proxy health check returned HTTP {resp.status_code} at {health_url}")
            except Exception as e:
                logger.warning(f"[CREDIT CHECK] ⚠️  LLM proxy unreachable at {health_url}: {e}")
            return {'balance': None, 'is_low': False, 'error': None}

        # OpenRouter direct — check balance
        resp = requests.get(
            'https://openrouter.ai/api/v1/auth/key',
            headers={'Authorization': f'Bearer {api_key}'},
            timeout=5
        )
        if resp.status_code == 200:
            data = resp.json().get('data', {})
            limit = data.get('limit')
            usage = data.get('usage', 0)
            balance = (limit - usage) if limit is not None else None

            if balance is not None and balance < LOW_CREDIT_THRESHOLD:
                logger.warning(
                    f"[CREDIT CHECK] ⚠️  OpenRouter balance LOW: ${balance:.4f} remaining "
                    f"(threshold: ${LOW_CREDIT_THRESHOLD}). "
                    "Top up at https://openrouter.ai/settings/credits"
                )
                return {'balance': balance, 'is_low': True, 'error': None}
            else:
                bal_str = f"${balance:.4f}" if balance is not None else "unlimited"
                logger.info(f"[CREDIT CHECK] ✅ OpenRouter balance: {bal_str}")
                return {'balance': balance, 'is_low': False, 'error': None}
        else:
            logger.warning(f"[CREDIT CHECK] Could not verify balance (HTTP {resp.status_code})")
            return {'balance': None, 'is_low': False, 'error': f"HTTP {resp.status_code}"}
    except Exception as e:
        logger.warning(f"[CREDIT CHECK] Balance check failed: {e}")
        return {'balance': None, 'is_low': False, 'error': str(e)}
