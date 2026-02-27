#!/bin/bash
# Generate a Django session for Plane's legacy /api/ endpoint.
# Required because the /api/ routes use session auth (not API key).
#
# Usage: ./scripts/create-plane-session.sh [container_name] [email]
# Output: session key (128 chars) to use as PLANE_SESSION_ID
#
# Default container: plane-app-api-1
# Default email: first admin user

CONTAINER="${1:-plane-app-api-1}"
EMAIL="${2:-}"

if [ -n "$EMAIL" ]; then
    FILTER="email='$EMAIL'"
else
    FILTER="is_superuser=True"
fi

SESSION_KEY=$(docker exec "$CONTAINER" python3 -c "
import os; os.environ['DJANGO_SETTINGS_MODULE']='plane.settings.production'
import django; django.setup()
from plane.db.models.session import SessionStore
from plane.db.models import User
u = User.objects.filter($FILTER).first()
if not u:
    raise SystemExit('No user found')
s = SessionStore()
s['_auth_user_id'] = str(u.pk)
s['_auth_user_backend'] = 'django.contrib.auth.backends.ModelBackend'
s['_auth_user_hash'] = u.get_session_auth_hash()
s.create()
print(s.session_key)
" 2>/dev/null)

if [ -z "$SESSION_KEY" ]; then
    echo "ERROR: Failed to create session. Is the container running?" >&2
    exit 1
fi

echo "$SESSION_KEY"
