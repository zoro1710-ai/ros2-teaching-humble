#!/usr/bin/env bash
# Delete the generated build/ install/ log/ directories.
#
# Reach for this when a build starts failing for no visible reason, usually
# after renaming a package or an entry point. It never touches src/.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${REPO_ROOT}"

echo "Removing build/ install/ log/ from ${REPO_ROOT}"
rm -rf build install log
echo "Done. Rebuild with: ./scripts/build.sh"
