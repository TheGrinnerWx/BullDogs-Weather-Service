import urllib.request
import json
import logging
import traceback
from utils import produce_wav_file, clean_weather_text


def getMain():
    log = logging.getLogger("BMH")
    try:
        config = json.load(open('config.json', encoding='utf-8'))
        stations = config.get('Observations', {}).get('regionalObsCodes', ['KEWR', 'KJFK', 'KLGA', 'KNYC', 'KHPN', 'KISP', 'KFRG', 'KMMU', 'KBDL'])
        phonemeDict = json.load(open('phonemeDB.json', encoding='utf-8'))
        replaceDict = phonemeDict.get('replace', {})
        phonemeDict = phonemeDict.get('phonemes', {})
        speed = config.get('ttsSpeed', "110")
        pause = config.get('endPause', "1300")
        
        script = "Regional weather observations. <vtml_pause time=\"500\"/> "

        for station in stations:
            try:
                url = f"https://api.weather.gov/stations/{station}/observations/latest"
                req = urllib.request.Request(url)
                req.add_header('User-Agent', 'BulldogsWeatherRadio/1.0')
                
                with urllib.request.urlopen(req, timeout=10) as response:
                    data = json.loads(response.read().decode())
                    prop = data['properties']

                # SAFE FETCHING: Use .get() and check for None before rounding
                temp_val = prop.get('temperature', {}).get('value')
                humid_val = prop.get('relativeHumidity', {}).get('value')
                wind_val = prop.get('windSpeed', {}).get('value')
                desc = prop.get('textDescription', 'Fair')

                # Convert Celsius to Fahrenheit safely
                if temp_val is not None:
                    temp_f = round((temp_val * 9/5) + 32)
                    temp_str = f"{temp_f} degrees"
                else:
                    temp_str = "Unavailable"

                # Handle Humidity safely
                if humid_val is not None:
                    hum_str = f"Humidity {round(humid_val)} percent"
                else:
                    hum_str = ""

                script += f"At {station}... {desc}... Temperature {temp_str}. {hum_str}. <vtml_pause time=\"800\"/> "
                log.info(f"[OBSERVATIONS] Processed {station}")

            except Exception as e:
                log.error(f"[OBSERVATIONS] Skipping {station} due to data error: {e}")
                continue

        finalScript = clean_weather_text(script)
        
        # Phoneme and word replacement
        for phoneme, replacement in phonemeDict.items():
            finalScript = finalScript.replace(phoneme, f'<vtml_phoneme alphabet="x-cmu" ph="{replacement}"></vtml_phoneme>')
        for word, replacement in replaceDict.items():
            finalScript = finalScript.replace(word, replacement)

        finalScript = f'<vtml_volume value="200"> <vtml_speed value="{speed}"> ' + finalScript + f'<vtml_pause time="{pause}"/> </vtml_volume> </vtml_speed>'
        finalScript = finalScript.replace('\n', ' ').replace('\r', ' ')

        log.debug('[OBSERVATIONS] Final Text: %s', finalScript)
        produce_wav_file(finalScript, 'Observations.wav')
        return finalScript

    except Exception:
        log.error('[OBSERVATIONS] %s', traceback.format_exc())
        return ""

def getObservations():
    """Compatibility wrapper returning the observations script.
    The rest of the system expects a function named getObservations.
    """
    return getMain()
