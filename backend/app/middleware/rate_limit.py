from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
MARKET_DATA_LIMIT = "30/minute"
CRUD_LIMIT = "60/minute"
