import os
from dotenv import load_dotenv


load_dotenv()

BASE_DIR = os.path.dirname(__file__)


def get_project_path(value: str | None, default: str) -> str:
    """Resolve relative paths from the project root."""
    if not value:
        return default

    if os.path.isabs(value):
        return value

    return os.path.join(BASE_DIR, value)


def get_int(value: str | None, default: int) -> int:
    """Parse integer config values with a safe fallback."""
    if not value:
        return default

    try:
        return int(value)
    except ValueError:
        return default


def get_extensions(value: str | None) -> set[str]:
    """Parse allowed extensions from comma-separated env value."""
    if not value:
        return {'xlsx', 'xls'}

    extensions = {
        extension.strip().lower().lstrip('.')
        for extension in value.split(',')
        if extension.strip()
    }
    return extensions or {'xlsx', 'xls'}


class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
    UPLOAD_FOLDER = get_project_path(
        os.environ.get('UPLOAD_FOLDER'),
        os.path.join(BASE_DIR, 'uploads')
    )
    ALLOWED_EXTENSIONS = get_extensions(os.environ.get('ALLOWED_EXTENSIONS'))
    MAX_CONTENT_LENGTH = get_int(
        os.environ.get('MAX_CONTENT_LENGTH'),
        16 * 1024 * 1024
    )

    # These defaults can still be overridden from the web UI.
    DEFAULT_WAREHOUSE = os.environ.get('DEFAULT_WAREHOUSE', 'Main Warehouse')
    DEFAULT_TEAM = os.environ.get('DEFAULT_TEAM', '')
    DEFAULT_COUNTRY = os.environ.get('DEFAULT_COUNTRY', 'Indonesia')
    DEFAULT_TAX = os.environ.get('DEFAULT_TAX', '0')
    DEFAULT_PAYMENT_TERM = os.environ.get('DEFAULT_PAYMENT_TERM', 'Immediate Payment')
