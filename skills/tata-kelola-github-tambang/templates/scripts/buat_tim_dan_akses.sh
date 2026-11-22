#!/usr/bin/env bash
# Buat tim & beri akses repo sesuai matriks RBAC. Pakai: ./buat_tim_dan_akses.sh ORG
set -euo pipefail
ORG="$1"
tim() { gh api -X POST "orgs/$ORG/teams" -f name="$1" -f privacy=closed ${2:+-F parent_team_id=$2} --jq .id 2>/dev/null || gh api "orgs/$ORG/teams/$1" --jq .id; }
akses() { gh api -X PUT "orgs/$ORG/teams/$1/repos/$ORG/$2" -f permission="$3" >/dev/null && echo "  $1 -> $2 : $3"; }
ROOT=$(tim semua-karyawan)
for t in eksplorasi-geologi mine-planning geoteknik-survei gis produksi-maintenance data-devops cpi ktt-pjo manajemen; do tim "$t" "$ROOT" >/dev/null; done
# repo : tim=peran (pull=Read, triage, push=Write, maintain, admin)
declare -A M=(
 [geologi-qaqc]="eksplorasi-geologi=push data-devops=maintain cpi=pull ktt-pjo=pull manajemen=pull"
 [geologi-estimasi]="eksplorasi-geologi=push data-devops=maintain cpi=maintain mine-planning=pull"
 [sdc-pelaporan]="eksplorasi-geologi=push mine-planning=push cpi=maintain data-devops=maintain manajemen=pull"
 [perencanaan-pit]="mine-planning=push geoteknik-survei=push ktt-pjo=maintain data-devops=maintain cpi=pull"
 [perencanaan-jalan]="mine-planning=push geoteknik-survei=push ktt-pjo=maintain data-devops=maintain"
 [geoteknik-lereng]="geoteknik-survei=push ktt-pjo=maintain data-devops=maintain mine-planning=pull"
 [gis-spasial]="gis=push geoteknik-survei=push data-devops=maintain"
 [operasi-fms-etl]="produksi-maintenance=push data-devops=maintain ktt-pjo=pull manajemen=pull"
 [sistem-kritis-alarm]="geoteknik-survei=push produksi-maintenance=push data-devops=push ktt-pjo=maintain"
)
for repo in "${!M[@]}"; do for pair in ${M[$repo]}; do akses "${pair%%=*}" "$repo" "${pair##*=}" || echo "  (repo $repo belum ada)"; done; done
