#!/bin/bash

PRISM_ROOT="$(dirname "$(readlink -f "$0")")"

python $PRISM_ROOT/Scripts/PrismTray.py
