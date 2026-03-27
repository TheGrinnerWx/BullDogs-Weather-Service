import sys
import json
import logging
import traceback
from utils import produce_wav_file
from datetime import datetime

log = logging.getLogger("BMH")

def getStationID():
    try:
        config = json.load(open('config.json', encoding='utf-8'))
        stationID = config.get('AlertSummary', {}).get('stationID', 'WXB26')
        tagline = config.get('StationID', {}).get('tagline', "This is the Bulldogs Weather Radio, WXB 26, broadcasting on a frequency of 162.55 megahertz.")
        
        # Check for Wednesday RWT
        now = datetime.now()
        is_wednesday_rwt = now.weekday() == 2 and now.hour == 11 and 30 <= now.minute <= 45
        if is_wednesday_rwt:
            tagline += " Please note that the required weekly test for this station is conducted every Wednesday between 11 AM and noon, weather permitting."

        phonemeDict = json.load(open('phonemeDB.json', encoding='utf-8'))
        replaceDict = phonemeDict.get('replace', {})
        phonemeDict = phonemeDict.get('phonemes', {})
        speed = config.get('ttsSpeed', "110")
        pause = config.get('endPause', "1300")
        
        finalID = tagline
        
        # Phoneme and word replacement
        for phoneme, replacement in phonemeDict.items():
            finalID = finalID.replace(phoneme, f'<vtml_phoneme alphabet="x-cmu" ph="{replacement}"></vtml_phoneme>')
        for word, replacement in replaceDict.items():
            finalID = finalID.replace(word, replacement)

        finalID = f'<vtml_volume value="200"> <vtml_speed value="{speed}"> ' + finalID + f'<vtml_pause time="{pause}"/> </vtml_volume> </vtml_speed>'
        finalID = finalID.replace('\n', ' ').replace('\r', ' ')

        log.debug('[STATION ID] Final Text: %s', finalID)
        produce_wav_file(finalID, 'StationID.wav')
        
    except Exception:
        log.error('[STATION ID] %s', traceback.format_exc())

if __name__ == '__main__':
    print('[STATION ID] This is one of the BMH modules, not a standalone program.')
