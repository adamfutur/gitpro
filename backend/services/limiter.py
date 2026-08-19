from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

# Per-IP by default. Uses in-memory storage — fine for a single backend instance (e.g. one
# Render web service); would need a shared backend (Redis) behind a load balancer with
# multiple instances, since counts wouldn't be shared across processes otherwise.
limiter = Limiter(key_func=get_remote_address, default_limits=["200 per hour"])
