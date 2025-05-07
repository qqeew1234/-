#!/usr/bin/env python3
# weather_counter.py

from flask import Flask, jsonify, request, send_from_directory
import requests, random, time

# Flask 앱 생성: 현재 폴더를 static 파일 루트로 설정
app = Flask(
    __name__,
    static_folder='.',
    static_url_path=''
)

# 서버 카운터 및 캐시 상태
counter = 0
last_weather_ts = 0
current_weather = 'clouds'
image_cache = []

WEATHER_URL = (
    "https://api.open-meteo.com/v1/forecast"
    "?latitude={lat}&longitude={lon}&current_weather=true"
)
WIKI_IMAGE_API = (
    "https://en.wikipedia.org/w/api.php?action=query&format=json"
    "&prop=pageimages&piprop=original"
    "&generator=geosearch&ggscoord={lat}%7C{lon}&ggsradius=10000&ggslimit=4"
)

def get_inc_range(weather):
    if weather == 'rain':
        return [0, 1]   # 비일 때 0~1
    elif weather == 'clouds':
        return [2, 3]   # 흐릴 때 2~3
    else:  # 'clear'
        return [4, 5]   # 맑을 때 4~5

@app.route('/counter')
def get_counter():
    global counter, last_weather_ts, current_weather, image_cache

    lat  = request.args.get('lat',  '37.5665')
    lon  = request.args.get('lon',  '126.9780')
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
            if code == 0:
                current_weather = 'clear'
            elif code in (1,2,3):
                current_weather = 'clouds'
            else:
                current_weather = 'rain'
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

    # 동기화 요청(sync=true)이면 서버 카운트 증가
    if sync:
        inc_min, inc_max = get_inc_range(current_weather)
        counter += random.randint(inc_min, inc_max)

    # 클라이언트용 증분 범위
    inc_range = get_inc_range(current_weather)

    return jsonify(
        counter=counter,
        weather=current_weather,
        incRange=inc_range,
        image_urls=image_cache
    )

# 정적 파일(index.html) 서빙
@app.route('/')
def index():
    return send_from_directory('.', 'index.html')

# 중간 캐시까지 차단
@app.after_request
def set_no_cache(res):
    res.headers['Cache-Control'] = 'no-store'
    return res

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
