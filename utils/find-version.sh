#!/bin/bash

thisdir="$(dirname "$0")"
awk -F"'" '/__version__ =/ {print $2}' "${thisdir}/../wagl/_version.py"
