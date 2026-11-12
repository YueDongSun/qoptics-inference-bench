#!/bin/sh
set -eu
mkdir -p artifacts
printf '%s\n' '{"value": 1}' > artifacts/result.json
