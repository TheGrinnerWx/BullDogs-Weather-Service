import sys
import json
import logging
import traceback
import requests
from utils import produce_wav_file, clean_weather_text

log = logging.getLogger("BMH")

def toFahrenheit(celsius):
    if celsius is None:
        return "N/A"
    return str(round((celsius * 1.8) + 32, 0)).replace('.0', '')

def getRegionalSummary():
    try:
        config = json.load(open('config.json', encoding='utf-8'))
        regionalConfig = config.get('Regional', {})
        stations = regionalConfig.get('stations', ["KJFK", "KLGA", "KEWR", "KTEB", "KHPN", "KISP", "KFRG", "KCDW", "KMMU", "KBDL", "KHVN"])
        regions = regionalConfig.get('regions', {
            "KJFK": "New York City",
            "KLGA": "New York City",
            "KEWR": "Northern New Jersey",
            "KTEB": "Northern New Jersey",
            "KHPN": "Westchester and Connecticut",
            "KISP": "Long Island",
            "KFRG": "Long Island",
            "KCDW": "Suburban New Jersey",
            "KMMU": "Suburban New Jersey",
            "KBDL": "Westchester and Connecticut",
            "KHVN": "Westchester and Connecticut"
        })
        regionalPre = regionalConfig.get('regionalPre', "Elsewhere across the region at TIME.")
        regionalPost = regionalConfig.get('regionalPost', "")
        
        from datetime import datetime
        currentTime = datetime.now().strftime('%I %p').lstrip('0')
        regionalPre = regionalPre.replace('TIME', currentTime)

        phonemeDict = json.load(open('phonemeDB.json', encoding='utf-8'))
        replaceDict = phonemeDict.get('replace', {})
        phonemeDict = phonemeDict.get('phonemes', {})
        speed = config.get('ttsSpeed', "110")
        globalTimeout = int(config.get('globalHTTPTimeout', 15))
        pause = config.get('endPause', "1300")
        
        summary_parts = []
        current_region = None
        
        for station in stations:
            try:
                apiCall = requests.get(f'https://api.weather.gov/stations/{station}/observations/latest', timeout=globalTimeout)
                apiCall.raise_for_status()
                data = apiCall.json()
                
                region = regions.get(station, "Other Locations")
                if region != current_region:
                    summary_parts.append(f"\n{region}. ")
                    current_region = region
                
                city = config.get('Observations', {}).get('cityNameDef', {}).get(station, station)
                sky = data['properties'].get('textDescription', 'fair')
                temp = toFahrenheit(data['properties']['temperature'].get('value'))
                
                summary_parts.append(f"At {city}, {sky} and {temp}. ")
                
            except Exception as e:
                log.error(f"[REGIONAL] Error fetching data for {station}: {e}")

        finalSummary = clean_weather_text("".join(summary_parts))
        
        # Phoneme and word replacement
        for phoneme, replacement in phonemeDict.items():
            finalSummary = finalSummary.replace(phoneme, f'<vtml_phoneme alphabet="x-cmu" ph="{replacement}"></vtml_phoneme>')
        for word, replacement in replaceDict.items():
            finalSummary = finalSummary.replace(word, replacement)

        finalSummary = f'{regionalPre}\n{finalSummary}\n{regionalPost}'
        finalSummary = f'<vtml_volume value="200"> <vtml_speed value="{speed}"> ' + finalSummary + f'<vtml_pause time="{pause}"/> </vtml_volume> </vtml_speed>'
        finalSummary = finalSummary.replace('\n', ' ').replace('\r', ' ')

        log.debug('[REGIONAL] Final Text: %s', finalSummary)
        produce_wav_file(finalSummary, 'RegionalSummary.wav')
        
    except Exception:
        log.error('[REGIONAL] %s', traceback.format_exc())

if __name__ == '__main__':
    print('[REGIONAL] This is one of the BMH modules, not a standalone program.')
