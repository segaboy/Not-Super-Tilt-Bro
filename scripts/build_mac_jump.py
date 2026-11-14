#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Dean Howell.
"""Build the opt-in source-derived jump and original movement experiment."""
import argparse
import hashlib
from pathlib import Path
from build_mac_movement import build


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    image, size = build(jumping=True)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open('xb') as stream:
        stream.write(image)
    print(f'ROM sha256={hashlib.sha256(image).hexdigest()} image_bytes={len(image)} code_bytes={size}')


if __name__ == '__main__':
    main()
