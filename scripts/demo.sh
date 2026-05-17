#!/usr/bin/env bash
# Full demo: spins up the stack, exercises every endpoint, tears down.
set -euo pipefail

BASE_URL="http://localhost:8080"
PUBLIC="/public/v1/heroes"
ADMIN="/admin/v1/heroes"

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
ENV_FILE="${REPO_ROOT}/.env"
ENV_CREATED=false

# ── Colours ───────────────────────────────────────────────────────────────────

BOLD="\033[1m"
DIM="\033[2m"
GREEN="\033[32m"
YELLOW="\033[33m"
CYAN="\033[36m"
RED="\033[31m"
RESET="\033[0m"

step()  { echo -e "\n${BOLD}${CYAN}▶ $*${RESET}"; }
ok()    { echo -e "${GREEN}✓ $*${RESET}"; }
info()  { echo -e "${DIM}  $*${RESET}"; }
fail()  { echo -e "${RED}✗ $*${RESET}"; exit 1; }

# ── .env ──────────────────────────────────────────────────────────────────────

# Create a minimal .env for Docker if one doesn't exist
if [[ ! -f "$ENV_FILE" ]]; then
    cat > "$ENV_FILE" <<'EOF'
APP_TITLE="Hero App"
APP_HOST="0.0.0.0"
APP_PORT=8080
APP_RELOAD=false
APP_DEBUG=false
PREFIX_PUBLIC="/public"
PREFIX_ADMIN="/admin"
POSTGRESQL_DSN="postgresql+asyncpg://hero:heroPass123@db:5432/heroes_db"
SECURITY_API_KEY="demo_secret_key"
EOF
    ENV_CREATED=true
    info "Created temporary .env for demo"
fi

# Read API key from .env
API_KEY=$(grep -E '^SECURITY_API_KEY=' "$ENV_FILE" | cut -d'=' -f2 | tr -d '"' | tr -d "'")

# ── Helpers ───────────────────────────────────────────────────────────────────

curl_json() {
    # Usage: curl_json METHOD PATH [BODY]
    local method="$1" path="$2" body="${3:-}"
    local args=(-s -S -X "$method" "${BASE_URL}${path}" \
        -H "Content-Type: application/json" \
        -H "access_token: ${API_KEY}")
    [[ -n "$body" ]] && args+=(-d "$body")
    curl "${args[@]}"
}

pretty() { python3 -m json.tool 2>/dev/null || cat; }

assert_field() {
    # assert_field RESPONSE FIELD  — exits if field is null/absent
    local val
    val=$(echo "$1" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('$2',''))" 2>/dev/null)
    [[ -n "$val" ]] || fail "Expected field '$2' in response"
    echo "$val"
}

wait_healthy() {
    step "Waiting for service to become healthy…"
    local max=120 i=0
    until curl -sf "${BASE_URL}/health_check" >/dev/null 2>&1; do
        i=$((i+1))
        [[ $i -ge $max ]] && fail "Service did not start within ${max}s"
        printf "."
        sleep 1
    done
    echo ""
    ok "Service is up"
}

# ── Lifecycle ─────────────────────────────────────────────────────────────────

cleanup() {
    step "Tearing down stack"
    docker compose down -v 2>/dev/null || true
    [[ "$ENV_CREATED" == true ]] && rm -f "$ENV_FILE" && info "Removed temporary .env"
    ok "Done"
}
trap cleanup EXIT

step "Starting stack with docker compose (clean slate)"
docker compose down -v 2>/dev/null || true
docker compose up -d --build --force-recreate
wait_healthy

# ── Demo ──────────────────────────────────────────────────────────────────────

echo -e "\n${BOLD}${YELLOW}════════════════════════════════════════${RESET}"
echo -e "${BOLD}${YELLOW}  Heroes API — full demo${RESET}"
echo -e "${BOLD}${YELLOW}════════════════════════════════════════${RESET}"

# 1. Create hero
step "[PUBLIC] POST ${PUBLIC}  — create hero"
RESP=$(curl_json POST "$PUBLIC" '{"nickname":"IronFist","role":"warrior"}')
echo "$RESP" | pretty
HERO_UUID=$(assert_field "$RESP" "uuid")
ok "Created hero: $HERO_UUID"

# 2. Get hero (public)
step "[PUBLIC] GET ${PUBLIC}/${HERO_UUID}  — retrieve hero"
RESP=$(curl_json GET "$PUBLIC/$HERO_UUID")
echo "$RESP" | pretty
assert_field "$RESP" "uuid" >/dev/null
ok "Hero retrieved"

# 3. Full update (PUT)
step "[PUBLIC] PUT ${PUBLIC}/${HERO_UUID}  — full update"
RESP=$(curl_json PUT "$PUBLIC/$HERO_UUID" '{"nickname":"SteelFist","role":"tank"}')
echo "$RESP" | pretty
assert_field "$RESP" "uuid" >/dev/null
ok "Hero updated (PUT)"

# 4. Partial update (PATCH)
step "[PUBLIC] PATCH ${PUBLIC}/${HERO_UUID}  — patch nickname only"
RESP=$(curl_json PATCH "$PUBLIC/$HERO_UUID" '{"nickname":"GoldenFist"}')
echo "$RESP" | pretty
assert_field "$RESP" "uuid" >/dev/null
ok "Hero patched (PATCH)"

# 5. Public search
step "[PUBLIC] POST ${PUBLIC}/search  — search by role"
RESP=$(curl_json POST "$PUBLIC/search" '{"role":"tank","limit":5}')
echo "$RESP" | pretty
assert_field "$RESP" "count" >/dev/null
ok "Search returned $(echo "$RESP" | python3 -c 'import sys,json; print(json.load(sys.stdin)["count"])') hero(s)"

# 6. Create a second hero to soft-delete via public route
step "[PUBLIC] POST ${PUBLIC}  — create a second hero (for public delete demo)"
RESP2=$(curl_json POST "$PUBLIC" '{"nickname":"ShadowBlade","role":"assassin"}')
HERO2_UUID=$(assert_field "$RESP2" "uuid")
ok "Created second hero: $HERO2_UUID"

# 7. Public soft-delete
step "[PUBLIC] DELETE ${PUBLIC}/${HERO2_UUID}  — soft delete"
RESP=$(curl_json DELETE "$PUBLIC/$HERO2_UUID")
echo "$RESP" | pretty
ok "Hero soft-deleted"

# 8. Admin — get hero (including soft-deleted fields)
step "[ADMIN]  GET ${ADMIN}/${HERO_UUID}  — retrieve as staff"
RESP=$(curl_json GET "$ADMIN/$HERO_UUID")
echo "$RESP" | pretty
assert_field "$RESP" "uuid" >/dev/null
ok "Admin retrieve OK"

# 9. Admin — search (sees soft-deleted records too)
step "[ADMIN]  POST ${ADMIN}/search  — search as staff (all roles)"
RESP=$(curl_json POST "$ADMIN/search" '{"limit":10,"order_by":[{"field":"created_at","desc":true}]}')
echo "$RESP" | pretty
ok "Admin search returned $(echo "$RESP" | python3 -c 'import sys,json; print(json.load(sys.stdin)["count"])') hero(s)"

# 10. Admin — permanent delete
step "[ADMIN]  DELETE ${ADMIN}/${HERO_UUID}?permanent=true  — hard delete"
RESP=$(curl_json DELETE "$ADMIN/$HERO_UUID?permanent=true")
echo "$RESP" | pretty
ok "Hero permanently deleted"

# 11. Confirm 404 after hard delete
step "[PUBLIC] GET ${PUBLIC}/${HERO_UUID}  — expect 404 after hard delete"
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" -X GET "${BASE_URL}${PUBLIC}/${HERO_UUID}" \
    -H "Content-Type: application/json" \
    -H "access_token: ${API_KEY}")
info "HTTP status: $HTTP_CODE"
[[ "$HTTP_CODE" == "404" ]] && ok "Got expected 404" || fail "Expected 404, got $HTTP_CODE"

# 12. Unauthorized admin call
step "[ADMIN]  GET ${ADMIN}/${HERO2_UUID}  — expect 403 with wrong key"
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" -X GET "${BASE_URL}${ADMIN}/${HERO2_UUID}" \
    -H "Content-Type: application/json" \
    -H "access_token: wrong_key")
info "HTTP status: $HTTP_CODE"
[[ "$HTTP_CODE" == "403" ]] && ok "Got expected 403" || fail "Expected 403, got $HTTP_CODE"

# ── Done ──────────────────────────────────────────────────────────────────────

echo -e "\n${BOLD}${GREEN}════════════════════════════════════════${RESET}"
echo -e "${BOLD}${GREEN}  All checks passed!${RESET}"
echo -e "${BOLD}${GREEN}════════════════════════════════════════${RESET}\n"

echo -e "\n${BOLD}${GREEN}  (cleanup handled by trap on EXIT)${RESET}"
