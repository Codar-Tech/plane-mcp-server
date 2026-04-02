#!/bin/bash
# Patch plane-sdk WorkItemDetail to accept both str and expanded objects
# for assignees and labels fields. Upstream plane-sdk==0.2.2 only accepts
# expanded objects, but Plane API returns UUIDs when not using expand param.
#
# Run after: uv sync

SCRIPT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
VENV_PYTHON="$SCRIPT_DIR/.venv/bin/python"
SITE_PKG=$("$VENV_PYTHON" -c "import plane; import os; print(os.path.dirname(plane.__file__))" 2>/dev/null)
if [ -z "$SITE_PKG" ]; then
    echo "ERROR: plane package not found"
    exit 1
fi

TARGET="$SITE_PKG/models/work_items.py"
if [ ! -f "$TARGET" ]; then
    echo "ERROR: $TARGET not found"
    exit 1
fi

if grep -q 'UserLite | str' "$TARGET"; then
    echo "Already patched: $TARGET"
    exit 0
fi

sed -i '' 's/assignees: list\[UserLite\]/assignees: list[UserLite | str] = Field(default_factory=list)/' "$TARGET"
sed -i '' 's/labels: list\[Label\]/labels: list[Label | str] = Field(default_factory=list)/' "$TARGET"

if grep -q 'UserLite | str' "$TARGET"; then
    echo "Patched successfully: $TARGET"
else
    echo "ERROR: Patch failed"
    exit 1
fi
