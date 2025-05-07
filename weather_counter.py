#!/usr/bin/env python3
# weather_counter.py

from flask import Flask, jsonify, request, send_from_directory
import requests, random, time

app = Flask(__name__, static_folder='.', static_url_path='')

# Reverse-geocode proxy
@app.route('/reverse')
def reverse_proxy():
    lat = request.args.get('lat')
    lon = request.args.get('lon')
    if not lat or not lon:
        return jsonify({'error': 'lat&lon required'}), 400
    try:
        resp = requests.get(
            'https://nominatim.openstreetmap.org/reverse',
            params={'lat': lat, 'lon': lon, 'format': 'json'},
            headers={'User-Agent': 'LocalWeatherCounter/1.0'},
            timeout=5
        )
        data = resp.json()
        addr = data.get('address', {})
        place = (
            addr.get('city') or
            addr.get('town') or
            addr.get('village') or
            addr.get('county') or
            (data.get('display_name') or '').split(',')[0] or
            'Local'
        )
        return jsonify({'place': place})
    except Exception as e:
        app.logger.error(f"[reverse] fetch failed: {e}")
        return jsonify({'place': 'Local'}), 200

# Weather counter & image API
counter = 0
last_weather_ts = 0
current_weather = 'clouds'
image_cache = []

WEATHER_URL = (
    "https://api.open-meteo.com/v1/forecast"
    "?latitude={lat}&longitude={lon}&current_weather=true"
)
# original 고화질 이미지 요청
WIKI_IMAGE_API = (
    "https://en.wikipedia.org/w/api.php?action=query&format=json"
    "&prop=pageimages&piprop=original"
    "&generator=geosearch&ggscoord={lat}%7C{lon}"
    "&ggsradius=10000&ggslimit=6"
)

def get_inc_range(weather):
    if weather == 'rain':
        return [0, 1]
    elif weather == 'clouds':
        return [2, 3]
    else:
        return [4, 5]

@app.route('/counter')
def get_counter():
    global counter, last_weather_ts, current_weather, image_cache

    lat  = request.args.get('lat', '37.5665')
    lon  = request.args.get('lon', '126.9780')
    sync = request.args.get('sync', 'false').lower() == 'true'
    now  = time.time()

    # 30분마다 날씨+이미지 갱신
    if now - last_weather_ts > 1800 or not image_cache:
        try:
            wj = requests.get(
                WEATHER_URL.format(lat=lat, lon=lon),
                timeout=5
            ).json().get('current_weather', {})
            code = wj.get('weathercode', 1)
            current_weather = (
                'clear' if code == 0 else
                'clouds' if code in (1,2,3) else
                'rain'
            )
        except Exception as e:
            app.logger.error(f"[weather] fetch failed: {e}")

        try:
            wiki = requests.get(
                WIKI_IMAGE_API.format(lat=lat, lon=lon),
                timeout=5
            ).json()
            pages = wiki.get('query', {}).get('pages', {}).values()
            image_cache = [
                p['original']['source']
                for p in pages
                if 'original' in p and 'source' in p['original']
            ]
            random.shuffle(image_cache)
        except Exception as e:
            app.logger.error(f"[wiki] fetch failed: {e}")

        last_weather_ts = now

    # sync=true 이면 카운트 증가
    if sync:
        inc_min, inc_max = get_inc_range(current_weather)
        counter += random.randint(inc_min, inc_max)

    return jsonify(
        counter=counter,
        weather=current_weather,
        incRange=get_inc_range(current_weather),
        image_urls=image_cache
    )

# favicon 서빙
@app.route('/favicon.ico')
def favicon():
    return send_from_directory('.', 'favicon.ico')

# index.html 서빙
@app.route('/')
def index():
    return send_from_directory('.', 'index.html')

# /counter에만 30분 캐시
@app.after_request
def set_cache_control(res):
    if request.path == '/counter':
        res.headers['Cache-Control'] = 'public, max-age=1800'
    return res

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)