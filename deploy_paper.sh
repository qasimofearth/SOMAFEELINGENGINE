#!/usr/bin/env bash
# One step: rebuild the paper from FEELING_ENGINE_PAPER.md and publish it to
#   https://feeling-engine-paper.vercel.app
# Usage:  ./deploy_paper.sh
set -euo pipefail
cd "$(dirname "$0")"

ALIAS="feeling-engine-paper.vercel.app"
PROJECT_ID="prj_TJRdoeFTsCUgy85Y2m3akz91CM5W"
ORG_ID="team_K3BqRqG8XCyPvb082qXEBV5X"
DEP="paper_site"

echo "→ Building HTML from FEELING_ENGINE_PAPER.md ..."
python3 build_paper.py >/dev/null

echo "→ Assembling deploy folder ..."
mkdir -p "$DEP/docs/screenshots" "$DEP/.vercel"
cp FEELING_ENGINE_PAPER.html "$DEP/index.html"
cp architecture_diagram.png "$DEP/"
# every image in docs/screenshots/ ships, so new figures just need a line in the markdown
cp docs/screenshots/*.png docs/screenshots/*.jpg docs/screenshots/*.jpeg docs/screenshots/*.gif \
   docs/screenshots/*.webp "$DEP/docs/screenshots/" 2>/dev/null || true
# keep this folder linked to the existing Vercel project (no new project gets made)
printf '{"projectId":"%s","orgId":"%s","projectName":"feeling-engine-paper"}\n' \
   "$PROJECT_ID" "$ORG_ID" > "$DEP/.vercel/project.json"

echo "→ Deploying to production ..."
OUT=$(cd "$DEP" && vercel deploy --prod --yes 2>&1)
URL=$(echo "$OUT" | grep -oE 'https://feeling-engine-paper-[a-z0-9]+-qasim-s-projects-b34c035f\.vercel\.app' | head -1)
if [ -z "$URL" ]; then echo "  !! could not parse deploy URL"; echo "$OUT" | tail -5; exit 1; fi
echo "  deployed: $URL"

echo "→ Pointing $ALIAS at the new deployment ..."
vercel alias set "$URL" "$ALIAS" >/dev/null 2>&1
echo "✓ Live: https://$ALIAS"
