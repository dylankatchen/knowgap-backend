"""Rate limits that stop floods, password guessing and runaway paid API use.

Every limit is set far above what a real person does, so normal use never
reaches one. Limits are counted per route and per dyno, in memory, so they
reset when the dyno restarts."""
import hashlib
import logging
from datetime import datetime, timedelta, timezone

import jwt
from quart import jsonify, request
from quart_rate_limiter import RateLimit, RateLimiter, RateLimitExceeded
from quart_rate_limiter.store import MemoryStore

from services.achieveup_auth_service import JWT_ALGORITHM, JWT_SECRET
from utils.security_utils import client_ip

logger = logging.getLogger(__name__)

MINUTE = timedelta(minutes=1)
HOUR = timedelta(hours=1)


async def ip_key():
    # The library's default key reads the first X-Forwarded-For entry, which
    # the client can set to anything; client_ip only trusts Heroku's entry.
    return f'ip:{client_ip()}'


async def user_key():
    """The logged-in user, or the IP for a missing or invalid token (those
    requests are rejected by the route anyway). Keying on the user rather
    than the token means logging in again doesn't start a fresh count."""
    auth_header = request.headers.get('Authorization', '')
    if auth_header.startswith('Bearer '):
        try:
            payload = jwt.decode(auth_header[7:], JWT_SECRET, algorithms=[JWT_ALGORITHM])
            if payload.get('user_id'):
                return f"user:{payload['user_id']}"
        except jwt.InvalidTokenError:
            pass
    return await ip_key()


async def email_ip_key():
    """The email being logged in to, from this address. Counting per email
    alone would let anyone who knows an email keep that account locked out;
    counting per email and address only slows the person guessing."""
    try:
        data = await request.get_json(silent=True)
    except (ValueError, RecursionError):
        # silent only covers malformed JSON. A body that isn't UTF-8, or is
        # nested too deeply, still raises; the route rejects it either way.
        data = None
    email = data.get('email') if isinstance(data, dict) else None
    if isinstance(email, str) and email.strip():
        # Hashed so the key stays short and the address isn't held in memory.
        # surrogatepass: JSON can carry lone surrogates, which plain UTF-8
        # can't encode.
        normalized = email.strip().lower().encode('utf-8', 'surrogatepass')
        digest = hashlib.sha256(normalized).hexdigest()
        return f'email:{digest}:{await ip_key()}'
    return await ip_key()


async def _skip_preflight():
    # A browser sends a CORS preflight before most API calls; it shouldn't
    # use up the call's own limit.
    return request.method == 'OPTIONS'


class ExpiringMemoryStore(MemoryStore):
    """MemoryStore keeps an entry for every key it has ever seen, so a flood
    of different IPs or emails would grow memory without end. An entry whose
    time has passed counts the same as no entry, so those are dropped."""

    PRUNE_EVERY = 1000  # sets between sweeps

    def __init__(self):
        super().__init__()
        self._sets_since_prune = 0

    async def set(self, key, tat):
        await super().set(key, tat)
        self._sets_since_prune += 1
        if self._sets_since_prune >= self.PRUNE_EVERY:
            self._sets_since_prune = 0
            now = datetime.now(timezone.utc)
            self._tats = {k: v for k, v in self._tats.items() if v > now}


limiter = RateLimiter(key_function=ip_key, store=ExpiringMemoryStore(),
                      skip_function=_skip_preflight)

# Login: a lecture hall can share one campus IP, so the IP limit is only a
# flood guard; the per-email-and-address limits are what stop password
# guessing, without letting a stranger lock someone else out.
LOGIN_LIMITS = [
    RateLimit(300, MINUTE, ip_key),
    RateLimit(10, MINUTE, email_ip_key),
    RateLimit(60, HOUR, email_ip_key),
]
SIGNUP_LIMITS = [RateLimit(300, MINUTE, ip_key)]
# Password change, profile update and Canvas token checks: each attempt
# guesses a password or tests a Canvas token.
CREDENTIAL_CHECK_LIMITS = [
    RateLimit(10, MINUTE, user_key),
    RateLimit(60, HOUR, user_key),
]
# Routes that call OpenAI or the YouTube API (billed or quota-limited), or
# start a full Canvas sync.
PAID_API_LIMITS = [
    RateLimit(30, MINUTE, user_key),
    RateLimit(300, HOUR, user_key),
]


async def _rate_limit_response(error):
    logger.warning("Rate limit hit: %s %s from %s", request.method, request.path, client_ip())
    response = jsonify({
        'error': 'Too many requests',
        'message': 'Too many requests. Please wait a moment and try again.',
        'statusCode': 429
    })
    response.status_code = 429
    response.headers['Retry-After'] = str(error.retry_after)
    return response


def init_rate_limits(app):
    limiter.init_app(app)
    app.register_error_handler(RateLimitExceeded, _rate_limit_response)
