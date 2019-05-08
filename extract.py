"""Automatisation of the Kaamelott file handling.

usage:
    python extract.py <kdenlive file>

To improve character name recognition and filename inference,
install unidecode python package.

"""

import os
import re
import sys
import json
import itertools
import subprocess
import audacity_scripting
import xml.etree.ElementTree as ET
from pprint import pprint
from shutil import copyfile
from functools import lru_cache


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
    text = text.lower().replace(' ', '_').replace('-', '_')
    try:
        from unidecode import unidecode
        text = unidecode(text)
    except ImportError:
        pass
    fname = ''.join(c for c in text if REGEX_BASENAME.fullmatch(c)).strip('_')
    data = data_from_sounds_json()
    if data:
        already_used = {cit['file'] for cit in data}
        if fname in already_used:
            print(f'WARNING filename "{fname}" is already used in existing data. A suffix will be added.')
            fname += '_2'
    return fname



def make_json_data(text:str, character:str, livre:int, episode:int, fname:str) -> dict:
    data = {
        'character': character_name(character),
        'episode': f'Livre {ROMAN[livre]}, {episode:02} - {episode_name(livre, episode)}',
        'file': os.path.split(fname)[1],  # sounds.json and .mp3 are in the same directory
        'title': text
    }
    return ''.join(' '*4 + line for line in json.dumps(data, indent=' '*4, ensure_ascii=False).splitlines(True)) + ',\n'


def data_from_sounds_json() -> list or None:
    "Return list of dict found in sound.json, or None if no file available"
    if os.path.exists('data/sounds.json'):
        with open('data/sounds.json') as fd:
            return json.load(fd)


@lru_cache()
def episode_name(livre:int, episode:int) -> str:
    question = f"Titre de l'épisode S{livre}E{episode} ? "
    return input(question).title() or '???'


def normalized_name(name:str) -> str:
    try:
        from unidecode import unidecode
    except ImportError:
        return name.lower()
    return unidecode(name.lower())

@lru_cache()
def character_name(character:str) -> str:
    data = data_from_sounds_json()
    if data:
        # print('OK data available:', len(data))
        characters = {
            normalized_name(char): char
            for char in set(itertools.chain.from_iterable(cit['character'].split(' - ') for cit in data))
        }
        # print('\t', character, '->', normalized_name(character))
        # print('\t', characters)
        realname = characters.get(normalized_name(character))
        if realname is None:
            print(f'Character "{character}" unknown. Will be used as-is.')
        else:
            character = realname
    return character


if len(sys.argv) != 2:
    print(__doc__)
    exit(1)

root = ET.parse(sys.argv[1]).getroot()

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
