import sys
import json
import logging
import traceback
import requests
from utils import produce_wav_file, clean_weather_text

log = logging.getLogger("BMH")



def getMarineForecast():
    try:
        config = json.load(open('config.json', encoding='utf-8'))
        marineZones = config.get('Marine', {}).get('marineZones', ["ANZ338", "ANZ330"])
        marinePre = config.get('Marine', {}).get('marinePre', "Here is the marine forecast for New York Harbor and Long Island Sound.")
        marinePost = config.get('Marine', {}).get('marinePost', "")
        
        phonemeDict = json.load(open('phonemeDB.json', encoding='utf-8'))
        replaceDict = phonemeDict['replace']
        phonemeDict = phonemeDict['phonemes']
        speed = config['ttsSpeed']
        globalTimeout = int(config.get('globalHTTPTimeout', 15))
        pause = config['endPause']
        
        full_forecast_text = ""
        
        for zone in marineZones:
            try:
                # Try the official marine zone forecast endpoint
                apiCall = requests.get(f'https://api.weather.gov/zones/marine/{zone}/forecast', timeout=globalTimeout)
                apiCall.raise_for_status()
                data = apiCall.json()
                
                forecast_parts = []
                for period in data['properties']['periods']:
                    name = period['name'].capitalize()
                    detailedForecast = period['detailedForecast']
                    forecast_parts.append(f"{name}, {detailedForecast}")
                
                full_forecast_text += " ".join(forecast_parts) + " "
            except Exception as e:
                log.warning(f"[MARINE] Zone {zone} failed, falling back to OKX Office Coastal Forecast...")
                try:
                    # FALLBACK: Fetch the latest Coastal Waters Forecast (CWF) for NEW YORK CITY (OKX)
                    product_list = requests.get('https://api.weather.gov/products/types/CWF/locations/OKX', timeout=globalTimeout).json()
                    product_id = product_list['@graph'][0]['id']
                    
                    # Fix: If product_id is not a full URL, construct it
                    if not product_id.startswith('http'):
                        product_url = f"https://api.weather.gov/products/{product_id}"
                    else:
                        product_url = product_id

                    product_data = requests.get(product_url, timeout=globalTimeout).json()
                    text = product_data['productText']
                    
                    # Look for the section for New York Harbor or the specific zone
                    # Usually looks like "ANZ330-..." or "NEW YORK HARBOR-"
                    if zone in text or "NEW YORK HARBOR" in text.upper():
                        # We'll grab the first few hundred chars of the text as a placeholder 
                        # or parse the specific zone if possible.
                        lines = text.split('\n')
                        capture = False
                        captured_lines = []
                        for line in lines:
                            if zone in line: capture = True
                            elif capture and line.startswith('$$'): break
                            elif capture: captured_lines.append(line.strip())
                        
                        if captured_lines:
                            full_forecast_text += " ".join(captured_lines) + " "
                        else:
                            # If parsing fails, just use the first visible forecast
                            full_forecast_text += "The coastal waters forecast for New York City is currently available on the weather gov website. "
                except Exception as e2:
                    log.error(f"[MARINE] Absolute fallback failed: {e2}")

        finalForecast = clean_weather_text(full_forecast_text)
        
        # Phoneme and word replacement
        for phoneme in phonemeDict:
            finalForecast = str(finalForecast).replace(phoneme, f'<vtml_phoneme alphabet="x-cmu" ph="{phonemeDict[phoneme]}"></vtml_phoneme>')
        for word in replaceDict:
            finalForecast = str(finalForecast).replace(word, replaceDict[word])

        finalForecast = f'{marinePre}\n{finalForecast}\n{marinePost}'
        finalForecast = f'<vtml_volume value="200"> <vtml_speed value="{speed}"> ' + finalForecast + f'<vtml_pause time="{pause}"/> </vtml_volume> </vtml_speed>'
        finalForecast = finalForecast.replace('\n', ' ').replace('\r', ' ')

        log.debug('[MARINE] Final Text: %s', finalForecast)
        produce_wav_file(finalForecast, 'MarineForecast.wav')
        
    except Exception:
        log.error('[MARINE] %s', traceback.format_exc())
        # Not exiting here so other products can still run

if __name__ == '__main__':
    print('[MARINE] This is one of the BMH modules, not a standalone program.')
