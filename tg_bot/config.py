import os

# Try loading .env from project root automatically
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


def _get_bool(name, default=False):
    return os.getenv(name, str(default)).lower() in ("true", "1", "yes")


def _get_list(name):
    value = os.getenv(name)
    if not value:
        return []
    return [int(x.strip()) for x in value.split(",") if x.strip()]


class Config(object):
    LOGGER = _get_bool("LOGGER", True)

    # REQUIRED
    API_KEY = os.getenv("API_KEY")
    OWNER_ID = os.getenv("OWNER_ID")
    OWNER_USERNAME = os.getenv("OWNER_USERNAME")

    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL")

    # RECOMMENDED
    MESSAGE_DUMP = None
    LOAD = []
    NO_LOAD = ['translation', 'rss']
    WEBHOOK = False
    URL = None

    # OPTIONAL
    SUDO_USERS = _get_list("SUDO_USERS")
    SUPPORT_USERS = _get_list("SUPPORT_USERS")
    WHITELIST_USERS = []

    DONATION_LINK = os.getenv("DONATION_LINK")
    CERT_PATH = None
    PORT = 5000
    DEL_CMDS = True
    STRICT_GBAN = True
    STRICT_GMUTE = True
    WORKERS = int(os.getenv("WORKERS", 32))
    START_STICKER = True
    START_STICKER_ID = os.getenv("START_STICKER_ID")
    BAN_STICKER = os.getenv("BAN_STICKER")
    ALLOW_EXCL = True
    API_OPENWEATHER = os.getenv("API_OPENWEATHER")

Development = Config

# -----------------------------------------------------------------------------
# OPTIONAL: If someone does NOT want .env or Docker ENV,
# they can comment the class above and uncomment below:

"""
class Config(object):
    LOGGER = True

    API_KEY = "your_token_here"
    OWNER_ID = "427596859"
    OWNER_USERNAME = "corsicanu"

    SQLALCHEMY_DATABASE_URI = "postgresql://user:pass@localhost:5432/tg"

    SUDO_USERS = [123456789]
    SUPPORT_USERS = []
    DONATION_LINK = "paypal.me/example"
    START_STICKER_ID = "sticker_id"
    BAN_STICKER = "sticker_id"
    API_OPENWEATHER = "openweather_key"
"""
