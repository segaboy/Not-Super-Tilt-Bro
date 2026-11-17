#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Dean Howell.
"""Render verified two-player aerial-jump frames, without rerunning gameplay."""
import argparse
import hashlib
import io
import json
from pathlib import Path
from PIL import Image, ImageDraw


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--results', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    report_path = args.results/'report.json'
    report = json.loads(report_path.read_text(encoding='utf-8'))
    if report['status'] != 'pass' or len(report['cases']) != 20:
        raise ValueError('complete aerial-jump qualification required')
    record = report['cases']['both_double']
    log, sequence = args.results/'both_double.log', args.results/'both_double.pbmseq'
    if sha(sequence) != record['frames_sha256']:
        raise ValueError('capture bytes changed')
    data = json.loads(log.read_text(encoding='utf-8').split('--- stderr ---')[0])['frame_series']
    blob = sequence.read_bytes()
    if data['rom_sha256'] != report['rom_sha256'] or data['processed'] != 32 or data['bytes'] != len(blob):
        raise ValueError('capture identity or completion mismatch')
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=False)
    rendered = []
    for sample, observation in zip(data['samples'][:31], record['observations'][:31]):
        if sample['frame'] != observation['vbl'] or sample['cycle'] != observation['cycle']:
            raise ValueError('state and frame alignment mismatch')
        frame = Image.open(io.BytesIO(blob[sample['offset']:sample['offset']+sample['length']])).convert('RGB')
        if frame.size != (512, 342):
            raise ValueError('wrong framebuffer size')
        if sample['frame'] == 60:
            frame.save(out/'aerial-jump.png')
        canvas = Image.new('RGB', (512, 380), '#e9e8e2')
        canvas.paste(frame, (0, 0))
        draw = ImageDraw.Draw(canvas)
        draw.text((8, 347), 'NSTB Mac ROM prototype | both players: one aerial jump', fill='black')
        draw.text((8, 362), f'VBL {sample["frame"]} | 6x slow playback | original placeholder art', fill='black')
        rendered.append(canvas)
    rendered[0].save(out/'aerial-jump.gif', save_all=True, append_images=rendered[1:],
                     duration=100, loop=0, disposal=2)
    receipt = {'status': 'pass', 'rom_sha256': report['rom_sha256'],
               'report_sha256': sha(report_path), 'source_sha256': sha(Path(__file__)),
               'input_sha256': {str(p): sha(p) for p in (log, sequence)},
               'presentation': '31 successive framebuffer samples, VBL 38-68, from one simultaneous two-player run. GIF displays each sample for 100 ms, approximately 6x slower than modeled time. PNG is the unchanged 512x342 VBL 60 framebuffer.',
               'scope': 'Original placeholder-art gameplay prototype; no complete match, upstream artwork or physical hardware claim.',
               'files': {p.name: sha(p) for p in out.iterdir() if p.is_file()}}
    (out/'capture.json').write_text(json.dumps(receipt, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(receipt, indent=2))


if __name__ == '__main__':
    main()
