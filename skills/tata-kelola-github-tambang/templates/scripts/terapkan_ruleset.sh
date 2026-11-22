#!/usr/bin/env bash
# Terapkan ruleset ke repo: ./terapkan_ruleset.sh ORG/REPO
# Butuh: gh CLI login sebagai admin repo. Push ruleset hanya untuk repo privat/internal (plan Team ke atas).
set -euo pipefail
REPO="$1"; D="$(cd "$(dirname "$0")/.." && pwd)/rulesets"
for f in main.json tag-rilis.json push-data-mentah.json; do
  echo "-> $f"
  gh api -X POST "repos/$REPO/rulesets" --input "$D/$f" >/dev/null && echo "   terpasang" || echo "   GAGAL (cek plan/visibilitas/izin)"
done
gh api -X PATCH "repos/$REPO" -f delete_branch_on_merge=true -f allow_merge_commit=false -f allow_rebase_merge=false >/dev/null
echo "Aktifkan juga: Settings > General > Releases > 'Enable release immutability' (atau tingkat organisasi)."
