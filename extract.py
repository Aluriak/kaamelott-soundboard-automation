"""Automatisation of the Kaamelott file handling.

"""

import os
import re
import json
import audacity_scripting
import subprocess
from pprint import pprint
from shutil import copyfile
import xml.etree.ElementTree as ET


REGEX_EPISODE = re.compile('S([0-9]+)E([0-9]+)')
REGEX_BASENAME = re.compile('[a-zA-Z0-9-_]')
ROMAN = {1: 'I', 2: 'II', 3: 'III', 4: 'IV', 5: 'V', 6: 'VI', 'VII': 7}
ROMAN_NUMBER = {'I': 1, 'II': 2, 'III': 3, 'IV': 4, 'V': 5, 'VI': 6, 'VII': 7}


def get_framerate(fname:str) -> int:
    "Return framerate of given video file"
    # SOURCE: https://askubuntu.com/a/468003
    proc = subprocess.Popen(
        ['ffprobe', '-v', '0', '-of', 'csv=p=0', '-select_streams', 'v:0', '-show_entries', 'stream=r_frame_rate', fname],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    stdout, stderr = proc.communicate()
    stdout = stdout.decode().strip()
    stderr = stderr.decode().strip()
    assert not stderr, '"' + stderr + '"'
    assert stdout.endswith('/1'), stdout
    return int(stdout[:-2])


def find_clips(root):
    for tag in root.findall('producer'):
        uid = tag.get('id')
        for prop in tag.findall('property'):
            if prop.get('name') == 'resource' and prop.text != 'black':
                yield uid, prop.text


def find_cuts(root):
    UNWANTED = 'main bin', 'black_track'
    for tag in root.findall('playlist'):
        if tag.get('id') in UNWANTED:  continue
        # print(tag.get('id'))
        for sub in tag:
            # print(sub.keys(), sub.text)
            if set(sub.keys()) >= {'producer', 'in', 'out'}:
                yield sub.get('producer'), int(sub.get('in')), int(sub.get('out'))


def cut_clip_at(clip:str, fps:int, frame_in:int, frame_out:int, fname:str):
    "extract [in:out] in given clip, saving this in file of given name"
    assert frame_in < frame_out, (frame_in, frame_out)
    # SOURCE: https://superuser.com/a/459488/638365
    start, end = frame_in / fps, frame_out / fps
    proc = subprocess.Popen(
        ['ffmpeg', '-i', clip, '-ss', str(start), '-to', str(end), fname],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    stdout, stderr = proc.communicate()
    # if stderr:  print('STDERR:', stderr.decode())

def play_file(fname:str):
    proc = subprocess.Popen(
        ['mplayer', fname],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    stdout, stderr = proc.communicate()


def infer_episode_from_name(fname:str) -> (int, int):
    "Return (livre, episode), guessed from filename name"
    fname = os.path.split(fname)[1]
    match = REGEX_EPISODE.search(fname)
    if match:
        livre, episode = map(int, match.groups(0))
    else:
        livre, episode = 0, 0
    return livre, episode


def canonical_citation_file(text:str) -> str:
    return ''.join(c for c in text.lower().replace(' ', '_') if REGEX_BASENAME.fullmatch(c)).strip('_')


def make_json_data(text:str, character:str, livre:int, episode:int, fname:str) -> dict:
    data = {
        'character': character.title(),
        'episode': f'Livre {ROMAN[livre]}, {episode:02} - ????',
        'file': os.path.split(fname)[1],  # sounds.json and .mp3 are in the same directory
        'title': text
    }
    return ''.join(' '*4 + line for line in json.dumps(data, indent=' '*4,).splitlines(True)) + ',\n'




root = ET.parse('projet-extraction.kdenlive').getroot()

assert len(tuple(find_clips(root))) == len(dict(find_clips(root))), "there is clips with same id in the file"
clips = dict(find_clips(root))
pprint(clips)

framerates = {uid: get_framerate(clip) for uid, clip in clips.items()}
pprint(framerates)

cuts = tuple(find_cuts(root))
pprint(cuts)


for idx, (clipid, frin, frout) in enumerate(cuts, start=1):
    clip = clips[clipid]
    livre, episode = infer_episode_from_name(clip)
    fname = f'out/extract-{idx}.mp3'
    print(f"Treating cut {idx}, for clip {clipid} (S{livre}E{episode:02})… ")
    print('\textracting…')
    cut_clip_at(clip, framerates[clipid], frin, frout, fname)
    print('\tnormalizing with audacity…')
    audacity_scripting.apply_treatment_on(fname, play=False)
    fname = f'out/macro-output/extract-{idx}.mp3'
    print('\tplaying final file…')
    play_file(fname)
    print('\tprompting info…')
    character = input('Character: ').strip()
    text = input('Text: ').strip()
    livre = input(f'Livre[{livre}]: ').strip() or livre
    episode = input(f'Épisode[{episode}]: ').strip() or episode
    final_fname = f'out/final/{canonical_citation_file(text)}.mp3'
    print('\tsaving everything…')
    copyfile(fname, final_fname)
    with open('out/final/out.json', 'a') as fd:
        fd.write(make_json_data(text, character, livre, episode, final_fname))
    print('\tDone !')
