#!/bin/sh

echo "Generating env.yaml..."

# Init pods env
env | grep -E '^(PODS_|DB_)' | sed -E 's/^([^=]+)=(.*)/- name: \1\n  value: \2/' | yq -p yaml ".[].value |= to_string" > env.yaml

echo "env.yaml generated"
