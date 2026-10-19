#!/usr/bin/env bash
# Deploy Prompt Forge HTTP prototype to Lambda Function URL.
# Uses profile `edgar` and region `ap-southeast-1`.
# Does not write credentials into this repo.

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PROFILE="${AWS_PROFILE:-}"
REGION="${AWS_REGION:-ap-southeast-1}"
FUNCTION_NAME="${PROMPT_FORGE_FUNCTION_NAME:-prompt-forge-http}"
ROLE_NAME="${PROMPT_FORGE_ROLE_NAME:-prompt-forge-http-lambda}"
RUNTIME="${PROMPT_FORGE_RUNTIME:-python3.12}"
HANDLER="prompt_forge.lambda_handler.lambda_handler"

AWS=(aws --region "$REGION")
if [[ -n "$PROFILE" ]]; then
  AWS+=(--profile "$PROFILE")
fi

need_cmd() {
  command -v "$1" >/dev/null 2>&1 || {
    echo "missing required command: $1" >&2
    exit 1
  }
}

need_cmd aws
need_cmd python3

aws_file_uri() {
  local scheme="$1"
  local path="$2"
  if command -v cygpath >/dev/null 2>&1; then
    path="$(cygpath -m "$path")"
  fi
  printf '%s://%s' "$scheme" "$path"
}

echo "Using profile=${PROFILE:-<active-login>} region=${REGION} function=${FUNCTION_NAME}"
"${AWS[@]}" sts get-caller-identity --query 'Account' --output text >/dev/null

ACCOUNT="$("${AWS[@]}" sts get-caller-identity --query 'Account' --output text)"
ROLE_ARN="arn:aws:iam::${ACCOUNT}:role/${ROLE_NAME}"

if ! "${AWS[@]}" iam get-role --role-name "$ROLE_NAME" >/dev/null 2>&1; then
  echo "Creating minimal Lambda execution role ${ROLE_NAME}"
  TRUST="$(mktemp)"
  cat >"$TRUST" <<'JSON'
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": { "Service": "lambda.amazonaws.com" },
      "Action": "sts:AssumeRole"
    }
  ]
}
JSON
  "${AWS[@]}" iam create-role \
    --role-name "$ROLE_NAME" \
    --assume-role-policy-document "$(aws_file_uri file "$TRUST")" \
    --description "Minimal Prompt Forge HTTP Lambda role" >/dev/null
  rm -f "$TRUST"
  "${AWS[@]}" iam attach-role-policy \
    --role-name "$ROLE_NAME" \
    --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole >/dev/null
  # IAM role eventual consistency
  sleep 8
fi

STAGE="$(mktemp -d)"
cleanup() { rm -rf "$STAGE"; }
trap cleanup EXIT

mkdir -p "$STAGE/prompt_forge"
# Zip only the compiler/HTTP package. Do not install mcp.
while IFS= read -r -d '' src_file; do
  rel="${src_file#"$ROOT/src/prompt_forge/"}"
  case "$rel" in
    mcp_server.py|*/__pycache__/*|__pycache__/*) continue ;;
  esac
  dest="$STAGE/prompt_forge/$rel"
  mkdir -p "$(dirname "$dest")"
  cp -a "$src_file" "$dest"
done < <(find "$ROOT/src/prompt_forge" -type f -name '*.py' -print0)
if [[ ! -f "$STAGE/prompt_forge/__init__.py" || ! -f "$STAGE/prompt_forge/lambda_handler.py" ]]; then
  echo "package copy failed" >&2
  exit 1
fi
(
  cd "$STAGE"
  python3 - <<'PYZIP'
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

root = Path("prompt_forge")
with ZipFile("function.zip", "w", compression=ZIP_DEFLATED) as archive:
    for path in sorted(root.rglob("*.py")):
        archive.write(path, path.as_posix())
PYZIP
)

if "${AWS[@]}" lambda get-function --function-name "$FUNCTION_NAME" >/dev/null 2>&1; then
  echo "Updating existing function ${FUNCTION_NAME}"
  "${AWS[@]}" lambda update-function-code \
    --function-name "$FUNCTION_NAME" \
    --zip-file "$(aws_file_uri fileb "${STAGE}/function.zip")" >/dev/null
  "${AWS[@]}" lambda wait function-updated --function-name "$FUNCTION_NAME"
  "${AWS[@]}" lambda update-function-configuration \
    --function-name "$FUNCTION_NAME" \
    --runtime "$RUNTIME" \
    --handler "$HANDLER" \
    --timeout 15 \
    --memory-size 128 >/dev/null
  "${AWS[@]}" lambda wait function-updated --function-name "$FUNCTION_NAME"
else
  echo "Creating function ${FUNCTION_NAME}"
  "${AWS[@]}" lambda create-function \
    --function-name "$FUNCTION_NAME" \
    --runtime "$RUNTIME" \
    --role "$ROLE_ARN" \
    --handler "$HANDLER" \
    --zip-file "$(aws_file_uri fileb "${STAGE}/function.zip")" \
    --timeout 15 \
    --memory-size 128 \
    --architectures x86_64 >/dev/null
  "${AWS[@]}" lambda wait function-active --function-name "$FUNCTION_NAME"
fi

if ! "${AWS[@]}" lambda get-function-url-config --function-name "$FUNCTION_NAME" >/dev/null 2>&1; then
  echo "Creating Function URL (AuthType=NONE) for public /health and /compile"
  "${AWS[@]}" lambda create-function-url-config \
    --function-name "$FUNCTION_NAME" \
    --auth-type NONE \
    --cors '{"AllowOrigins":["*"],"AllowMethods":["GET","POST"]}' >/dev/null
fi

AUTH_TYPE="$("${AWS[@]}" lambda get-function-url-config \
  --function-name "$FUNCTION_NAME" \
  --query 'AuthType' \
  --output text)"
if [[ "$AUTH_TYPE" != "NONE" ]]; then
  echo "existing Function URL AuthType=${AUTH_TYPE}; refusing to grant public permissions" >&2
  exit 1
fi

# Since October 2025, new public Function URLs require both permissions.
# Keep these checks outside URL creation so reruns can repair a partial policy.
POLICY="$("${AWS[@]}" lambda get-policy \
  --function-name "$FUNCTION_NAME" \
  --query 'Policy' \
  --output text 2>/dev/null || true)"

if [[ "$POLICY" != *'FunctionURLAllowPublicAccess'* ]]; then
  "${AWS[@]}" lambda add-permission \
    --function-name "$FUNCTION_NAME" \
    --statement-id FunctionURLAllowPublicAccess \
    --action lambda:InvokeFunctionUrl \
    --principal "*" \
    --function-url-auth-type NONE >/dev/null
fi

if [[ "$POLICY" != *'FunctionURLAllowPublicInvoke'* ]]; then
  "${AWS[@]}" lambda add-permission \
    --function-name "$FUNCTION_NAME" \
    --statement-id FunctionURLAllowPublicInvoke \
    --action lambda:InvokeFunction \
    --principal "*" \
    --invoked-via-function-url >/dev/null
fi

FUNCTION_URL="$("${AWS[@]}" lambda get-function-url-config \
  --function-name "$FUNCTION_NAME" \
  --query 'FunctionUrl' \
  --output text)"
FUNCTION_URL="${FUNCTION_URL%/}"

echo "FUNCTION_URL=${FUNCTION_URL}"
echo "${FUNCTION_URL}"
