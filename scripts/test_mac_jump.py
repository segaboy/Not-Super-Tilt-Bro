#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Dean Howell.
"""Test the original ROM's limited jump experiment in headless BootHush."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile

from build_mac_movement import build
from build_mac_run_transition import FIGURE

HEADER = b'P4\n512 342\n'


def sha(data): return hashlib.sha256(data).hexdigest()
def signed(value): return value if value < 32768 else value - 65536


def state(sample):
    raw = bytes.fromhex(sample['memory']['bytes'])
    assert len(raw) == 32 and raw[:8] == b'NST4\0\0\0\1'
    return {'x': int.from_bytes(raw[16:18], 'big'), 'phase': raw[20],
            'jump_state': raw[24], 'clock': raw[25],
            'velocity': signed(int.from_bytes(raw[26:28], 'big')),
            'height': int.from_bytes(raw[28:30], 'big'),
            'button': raw[30], 'jumps': raw[31]}


def pixels(frame, s):
    assert frame.startswith(HEADER) and len(frame) == len(HEADER)+21888
    expected = bytearray(21888)
    x = s['x'] >> 8
    y = 228 - (s['height'] >> 8)
    assert 0 <= y <= 228
    for row, bits in enumerate(FIGURE):
        pattern = ((bits << 8) >> (x % 8)).to_bytes(3, 'big')
        offset = (y+row)*64 + 16 + x//8
        expected[offset:offset+3] = pattern
    for row in range(252,260): expected[row*64+16:row*64+48] = b'\xff'*32
    assert frame[len(HEADER):] == expected, ('bad jump pixels or stale frame',s)


def next_tick(s):
    result = dict(s)
    if s['phase'] == 5:
        return result
    if s['jump_state'] == 1:
        result['clock'] += 1
        if result['clock'] == 4:
            result['jump_state'], result['velocity'] = 2, 0x0480
    elif s['jump_state'] == 2:
        result['clock'] = (result['clock'] + 1) & 255
        velocity = max(s['velocity']-0x60, -0x200)
        if result['clock'] == 8 and not s['button']:
            velocity = 0x0102
        height = s['height'] + velocity
        if height <= 0:
            result['jump_state'], result['velocity'], result['height'] = 0, 0, 0
        else:
            result['velocity'], result['height'] = velocity, height
    return result


def run(exe, rom, root, name, events, points, stop):
    frames = root/(name+'.pbmseq')
    witness = root/(name+'.keyboard')
    command = [str(exe),'--machine','mac128k','--rom',str(rom),'--cycles',str(stop),
               '--timeout-ms','20000','--capture-series',str(frames),
               '--capture-memory','0xb00:32','--keyboard-witness',str(witness)]
    for point in points: command += ['--capture-vbl',str(point)]
    for cycle,key,down in events: command += ['--key',f'{cycle}:{key}:{down}']
    process = subprocess.run(command,capture_output=True,text=True,timeout=25,
                             creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
    if process.returncode: raise RuntimeError(process.stdout+process.stderr)
    result = json.loads(process.stdout)
    series = result['frame_series']
    assert result['status'] == 'cycle_limit'
    assert series['rom_sha256'] == sha(rom.read_bytes()) and series['executable_sha256'] == sha(exe.read_bytes())
    assert (series['requested'],series['processed'],series['pending'],series['missing_images'],series['dropped']) == (len(points),len(points),0,0,0)
    assert result['keyboard_witness']['dropped'] == result['keyboard_witness']['rejected'] == result['keyboard_witness']['pending'] == 0
    rows = [line.split() for line in witness.read_text(encoding='ascii').splitlines()[2:]]
    deliveries = [(int(row[0]),int(row[3])) for row in rows if row[2]=='key_delivered']
    assert [value for _,value in deliveries] == [(key<<1)|1|(0 if down else 128) for _,key,down in events]
    data=frames.read_bytes(); samples=series['samples']; observed=[]
    for sample in samples:
        assert sample['processed'] and sample['image_available']
        current=state(sample); observed.append(current)
        pixels(data[sample['offset']:sample['offset']+sample['length']],current)
    checked=0
    for a,b,old,new in zip(samples,samples[1:],observed,observed[1:]):
        if b['frame'] != a['frame']+1 or any(a['cycle']<=cycle<b['cycle'] for cycle,_ in deliveries):
            continue
        expected=next_tick(old)
        assert (new['jump_state'],new['clock'],new['velocity'],new['height']) == (expected['jump_state'],expected['clock'],expected['velocity'],expected['height']), (name,old,new,expected)
        checked+=1
    (root/(name+'.json')).write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    return {'events':events,'deliveries':deliveries,'oracle_intervals':checked,
            'observations':[{'vbl':sample['frame'],'cycle':sample['cycle'],**s} for sample,s in zip(samples,observed)]}


def test(exe,root):
    image,size=build(jumping=True); rom=root/'jump.rom'
    with rom.open('xb') as stream: stream.write(image)
    points=list(range(5,32))+[34,37,40,43,46]
    scenarios={
        'jump': ([(600000,2,1),(1200000,2,0)],points,6200000),
        'hold': ([(600000,2,1)],points,6200000),
        'airborne_retry': ([(600000,2,1),(900000,2,0),(1500000,2,1),(1800000,2,0)],points,6200000),
        'run_jump': ([(600000,0,1),(900000,2,1),(1400000,2,0),(3400000,0,0)],points,6200000),
        'second_jump': ([(600000,2,1),(900000,2,0),(6000000,2,1),(6300000,2,0)],
                        list(range(5,17))+list(range(18,54,2))+[55,60],8100000),
    }
    cases={name:run(exe,rom,root,name,*args) for name,args in scenarios.items()}
    for name in ('jump','hold','airborne_retry','run_jump'):
        obs=cases[name]['observations']
        assert any(x['jump_state']==1 for x in obs) and any(x['jump_state']==2 for x in obs),name
        assert any(x['height']>0 for x in obs),name
        assert obs[-1]['jump_state']==0 and obs[-1]['height']==0 and obs[-1]['jumps']==1,name
        assert cases[name]['oracle_intervals']>=15,name
    assert cases['hold']['observations'][-1]['button']==1
    assert any(x['clock']==8 and x['velocity']==0x0102 for x in cases['jump']['observations'])
    assert max(x['height'] for x in cases['jump']['observations']) < max(x['height'] for x in cases['hold']['observations'])
    assert cases['airborne_retry']['observations'][-1]['button']==0
    assert max(x['x'] for x in cases['run_jump']['observations']) > 0x8000
    assert any(x['jumps']==2 and x['jump_state'] in (1,2) for x in cases['second_jump']['observations'])
    summary={'result':'pass','rom_sha256':sha(image),'boothush_sha256':sha(exe.read_bytes()),
             'rom_bytes':len(image),'rom_used_through':0x104+size,'cases':cases}
    (root/'summary.json').write_text(json.dumps(summary,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'result':'pass','rom_sha256':summary['rom_sha256'],'boothush_sha256':summary['boothush_sha256'],
                      'rom_used_through':summary['rom_used_through'],'cases':list(cases)},indent=2))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--boothush',required=True,type=Path)
    parser.add_argument('--keep',type=Path)
    args=parser.parse_args()
    if args.keep:
        args.keep.mkdir(parents=True,exist_ok=False); test(args.boothush,args.keep)
    else:
        with tempfile.TemporaryDirectory(prefix='nstb-jump-') as tmp: test(args.boothush,Path(tmp))


if __name__ == '__main__': main()
