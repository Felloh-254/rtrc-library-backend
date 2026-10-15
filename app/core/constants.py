# Event duration units
DURATION_HOURS = "hours"
DURATION_DAYS = "days"

# User roles
ROLE_ADMIN = "admin"
ROLE_PATRON = "patron"

# Default pagination
DEFAULT_PAGE_SIZE = 20

# Blueprint names
BLUEPRINT_ADMIN = "admin"
BLUEPRINT_AUTH = "auth"
BLUEPRINT_SHARED = "shared"
BLUEPRINT_PATRON = "patron"

# Logging formats
ERROR_LOG_FORMAT = "[%(asctime)s] -- [%(levelname)s] -- %(message)s"
ACCESS_LOG_FORMAT = "[%(asctime)s] -- [%(ip_address)s] -- [%(patron_id)s] -- [%(status)s] -- [%(platform)s]"

# Role-based redirects
ROLE_REDIRECTS = {
    "admin": "admin.dashboard",
    "superadmin": "admin.dashboard",
    "patron": "patron.dashboard"
}