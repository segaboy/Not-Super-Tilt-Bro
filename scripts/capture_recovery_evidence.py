#!/usr/bin/env python3
"""Render existing verified recovery captures; no new gameplay or timing claim."""
import argparse
import hashlib
import io
import json
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--results',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();report=json.loads((a.results/'report.json').read_text())
    if report['status']!='pass' or len(report['cases'])!=34:raise ValueError('requires complete recovery qualification')
    out=a.output.resolve();out.mkdir(parents=True,exist_ok=False);runs=[];sources={}
    for who in ('p1','p2'):
        name=who+'_recovery_early_hold';log=a.results/(name+'.log');series=a.results/(name+'.pbmseq')
        data=json.loads(log.read_text().split('--- stderr ---')[0]);s=data['frame_series'];blob=series.read_bytes()
        if s['rom_sha256']!=report['rom_sha256'] or s['processed']!=32 or s['dropped'] or s['missing_images'] or len(blob)!=s['bytes']:
            raise ValueError('incomplete or different capture')
        frames=[]
        for sample in s['samples']:
            raw=blob[sample['offset']:sample['offset']+sample['length']]
            im=Image.open(io.BytesIO(raw)).convert('RGB')
            if im.size!=(512,342):raise ValueError('unexpected frame dimensions')
            frames.append(im)
        runs.append(frames);sources[name]={'log_sha256':sha(log),'series_sha256':sha(series),
                                          'first_vbl':s['samples'][0]['requested'],'last_vbl':s['samples'][-1]['requested']}
    frames=[];font=ImageFont.load_default(size=16)
    for i in range(32):
        im=Image.new('RGB',(1064,410),'#e9e8e2');draw=ImageDraw.Draw(im)
        draw.text((12,10),'Player 1: early jump held through recovery',fill='black',font=font)
        draw.text((540,10),'Player 2: early jump held through recovery',fill='black',font=font)
        im.paste(runs[0][i],(12,40));im.paste(runs[1][i],(540,40))
        draw.text((12,389),f'Mac ROM prototype | captured VBL {50+i} | 6x slow playback | original placeholder art',fill='black',font=font)
        frames.append(im)
    frames[0].save(out/'recovery-jump.gif',save_all=True,append_images=frames[1:],duration=100,loop=0,disposal=2)
    frames[20].save(out/'recovery-jump.png')
    result={'status':'pass','rom_sha256':report['rom_sha256'],'qualification_report_sha256':sha(a.results/'report.json'),
            'source_sha256':sha(Path(__file__)),'captures':sources,
            'presentation':'32 VBL-indexed live-framebuffer samples per player. 100 ms per sample, approximately 6x slower than modeled time. Independent test runs shown side by side.',
            'scope':'Original-art prototype; recovery jump only, not a completed port or full match; no physical-hardware claim.',
            'files':{f.name:sha(f) for f in out.iterdir() if f.is_file()}}
    (out/'capture.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
if __name__=='__main__':main()
