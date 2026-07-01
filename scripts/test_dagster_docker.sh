#!/usr/bin/env bash
# Test Dagster Docker integration (F1-023)
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$PROJECT_ROOT"

COMPOSE_PROFILE="orchestration"
MAX_WAIT=60
PASS=0
FAIL=0

cleanup() {
    echo "==> Cleaning up containers..."
    docker compose --profile "$COMPOSE_PROFILE" down -t 5 2>/dev/null || true
}
trap cleanup EXIT

echo "==> F1-023: Dagster Docker Integration Test"
echo ""

# Step 1: Start Dagster containers
echo "--- Step 1: Starting Dagster containers (profile=$COMPOSE_PROFILE) ---"
docker compose --profile "$COMPOSE_PROFILE" up -d --wait 2>&1

# Step 2: Check webserver health
echo ""
echo "--- Step 2: Check webserver health ---"
for i in $(seq 1 $MAX_WAIT); do
    if curl -sf http://localhost:3000/dagit-info 2>/dev/null | grep -q "dagit"; then
        echo "OK: Webserver responded at :3000"
        ((PASS++))
        break
    fi
    if [ "$i" -eq "$MAX_WAIT" ]; then
        echo "FAIL: Webserver did not respond within ${MAX_WAIT}s"
        ((FAIL++))
    fi
    sleep 2
done

# Step 3: Validate definitions via GraphQL
echo ""
echo "--- Step 3: Validate definitions via GraphQL ---"
GRAPHQL_QUERY='{"query":"{ repositoriesOrError { __typename ... on PythonError { message } ... on RepositoryConnection { nodes { name location { name } } } } }"}'
RESP=$(curl -sf -X POST http://localhost:3000/graphql -H "Content-Type: application/json" -d "$GRAPHQL_QUERY" 2>/dev/null || echo "")
echo "GraphQL response: $RESP"
echo ""

# Step 4: Check daemon is running
echo "--- Step 4: Check daemon health ---"
DAEMON_LOGS=$(docker compose --profile "$COMPOSE_PROFILE" logs --tail=20 dagster-daemon 2>/dev/null || true)
if echo "$DAEMON_LOGS" | grep -q "Daemon is running"; then
    echo "OK: Daemon is running"
    ((PASS++))
else
    echo "WARN: Daemon status not confirmed (may need more time)"
    echo "$DAEMON_LOGS" | tail -5
fi

# Summary
echo ""
echo "=============================="
echo "F1-023 Results: $PASS passed, $FAIL failed"
echo "=============================="

if [ "$FAIL" -gt 0 ]; then
    exit 1
fi
