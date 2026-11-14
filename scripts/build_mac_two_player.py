#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Dean Howell.
"""Build the opt-in independently controlled second-character experiment."""
import argparse
import hashlib
from pathlib import Path
from build_mac_movement import build

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',required=True,type=Path);a=p.parse_args()
    image,size=build(jumping=True,combat=True,two_player=True)
    a.output.parent.mkdir(parents=True,exist_ok=True)
    with a.output.open('xb') as f:f.write(image)
    print(f'ROM sha256={hashlib.sha256(image).hexdigest()} image_bytes={len(image)} code_bytes={size}')

if __name__=='__main__':main()
