#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Dean Howell.
"""Render qualified air-control gameplay frames with their state observations."""
import argparse
import hashlib
import io
import json
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--results', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    report_path = args.results/'report.json'
    report = json.loads(report_path.read_text(encoding='utf-8'))
    if report['status'] != 'pass' or len(report['cases']) != 14 or len(report['native_calls']) != 6:
        raise ValueError('complete native air-control qualification required')
    record = report['cases']['both_reverse']
    log, sequence = args.results/'both_reverse.log', args.results/'both_reverse.pbmseq'
    if sha(sequence) != record['frames_sha256']:raise ValueError('capture bytes changed')
    series = json.loads(log.read_text(encoding='utf-8').split('--- stderr ---')[0])['frame_series']
    blob = sequence.read_bytes()
    if series['rom_sha256'] != report['rom_sha256'] or series['processed'] != 32 or series['bytes'] != len(blob):
        raise ValueError('capture identity or completion mismatch')
    out = args.output.resolve();out.mkdir(parents=True, exist_ok=False)
    rendered = [];font = ImageFont.load_default(size=16)
    for sample, state in zip(series['samples'], record['observations']):
        if sample['frame'] != state['vbl'] or sample['cycle'] != state['cycle']:
            raise ValueError('state and image alignment mismatch')
        frame = Image.open(io.BytesIO(blob[sample['offset']:sample['offset']+sample['length']])).convert('RGB')
        if frame.size != (512, 342):raise ValueError('unexpected framebuffer dimensions')
        if sample['frame'] == 50:frame.save(out/'air-control.png')
        canvas = Image.new('RGB', (1024, 740), '#e9e8e2')
        canvas.paste(frame.resize((1024, 684), Image.Resampling.NEAREST), (0, 0))
        draw = ImageDraw.Draw(canvas)
        draw.text((12, 692), 'NSTB Mac ROM prototype | both players drift and reverse in midair | original placeholder art', fill='black', font=font)
        velocities = [p['horizontal'] for p in state['players']]
        draw.text((12, 716), f'VBL {state["vbl"]} | horizontal velocity (8.8): P1 {velocities[0]}, P2 {velocities[1]} | 6x slow playback', fill='black', font=font)
        rendered.append(canvas)
    rendered[0].save(out/'air-control.gif', save_all=True, append_images=rendered[1:],
                     duration=100, loop=0, disposal=2)
    receipt = {'status': 'pass', 'rom_sha256': report['rom_sha256'], 'report_sha256': sha(report_path),
               'source_sha256': sha(Path(__file__)), 'input_sha256': {str(p): sha(p) for p in (log, sequence)},
               'presentation': '32 successive VBL 34-65 samples from one simultaneous run. GIF doubles each framebuffer pixel and displays each sample for 100 ms, approximately 6x slower than modeled time. PNG is the unchanged 512x342 VBL 50 framebuffer.',
               'scope': 'Original placeholder-art gameplay prototype; local character collision/rendering, no complete match or physical hardware claim.',
               'files': {p.name: sha(p) for p in out.iterdir() if p.is_file()}}
    (out/'capture.json').write_text(json.dumps(receipt, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(receipt, indent=2))


if __name__ == '__main__':
    main()
