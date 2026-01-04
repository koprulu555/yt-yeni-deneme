#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import requests
import re
import json
import os
import sys
from urllib.parse import unquote, quote
import html
import time
import random

# GitHub Actions ortamı kontrolü
IS_GITHUB = os.environ.get('GITHUB_ACTIONS') is not None
print(f"🌍 Ortam: {'GitHub Actions' if IS_GITHUB else 'Yerel Makine'}")

def links_dosyasini_oku():
    """links.txt dosyasını GitHub raw linkinden oku"""
    kanallar = []
    
    try:
        raw_url = "https://raw.githubusercontent.com/koprulu555/yt-yeni-deneme/refs/heads/main/links.txt"
        response = requests.get(raw_url, timeout=15)
        icerik = response.text if response.status_code == 200 else ""
        
        if not icerik:
            with open('links.txt', 'r', encoding='utf-8') as dosya:
                icerik = dosya.read()
    except Exception as e:
        print(f"⚠️ GitHub'dan okuma hatası: {e}")
        try:
            with open('links.txt', 'r', encoding='utf-8') as dosya:
                icerik = dosya.read()
        except:
            print("❌ links.txt dosyası bulunamadı!")
            return kanallar
    
    satirlar = icerik.split('\n')
    mevcut_kanal = {}
    
    for satir in satirlar:
        satir = satir.strip()
        if not satir:
            if mevcut_kanal:
                kanallar.append(mevcut_kanal)
                mevcut_kanal = {}
            continue
        
        if satir.startswith('isim='):
            mevcut_kanal['isim'] = satir[5:]
        elif satir.startswith('içerik='):
            mevcut_kanal['icerik'] = satir[7:]
        elif satir.startswith('logo='):
            mevcut_kanal['logo'] = satir[5:]
    
    if mevcut_kanal:
        kanallar.append(mevcut_kanal)
    
    print(f"📊 {len(kanallar)} kanal bulundu")
    return kanallar

# Genişletilmiş User-Agent listesi
user_agents = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (iPhone; CPU iPhone OS 17_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Mobile/15E148 Safari/604.1',
    'Mozilla/5.0 (Linux; Android 14; SM-S918B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.6099.210 Mobile Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.2210.91',
    'Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)',
    'Mozilla/5.0 (compatible; Bingbot/2.0; +http://www.bing.com/bingbot.htm)'
]

def get_random_user_agent():
    return random.choice(user_agents)

def decode_unicode_escapes(text):
    """Workers'daki decodeUnicodeEscapes'in geliştirilmiş versiyonu"""
    if not text:
        return text
    
    try:
        # Önce tüm unicode escape'leri decode et
        def replace_unicode(match):
            try:
                return chr(int(match.group(1), 16))
            except:
                return match.group(0)
        
        result = text
        
        # Birden fazla katman decode et
        for _ in range(3):  # 3 katman decode
            if '\\u' in result:
                result = re.sub(r'\\u([0-9a-fA-F]{4})', replace_unicode, result)
        
        # HTML entity'leri decode et
        result = html.unescape(result)
        
        # Özel escape karakterlerini temizle
        replacements = [
            ('\\/', '/'),
            ('\\u0026', '&'),
            ('\\x22', '"'),
            ('\\\\', '\\'),
            ('\\"', '"'),
            ("\\'", "'"),
            ('\\n', ''),
            ('\\r', ''),
            ('\\t', ' ')
        ]
        
        for old, new in replacements:
            result = result.replace(old, new)
        
        # URL decode
        try:
            result = unquote(result)
        except:
            pass
            
        return result
        
    except Exception as e:
        print(f"   ⚠️  Unicode decode hatası: {str(e)[:50]}")
        return text

def get_youtube_page_with_retry(url, max_retries=3):
    """Yeniden denemeli ve hibrit (proxy + direct) fetch fonksiyonu"""
    headers = {
        'User-Agent': get_random_user_agent(),
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7',
        'Accept-Encoding': 'gzip, deflate',
        'DNT': '1',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'Referer': 'https://www.youtube.com/',
        'Cache-Control': 'max-age=0'
    }
    
    # GitHub'da daha uzun timeout
    timeout_val = 25 if IS_GITHUB else 15
    
    for attempt in range(max_retries):
        try:
            # GitHub'da veya 2. denemede proxy kullan
            use_proxy = IS_GITHUB or attempt >= 1
            
            if use_proxy:
                # Farklı proxy servisleri
                proxy_servers = [
                    "https://api.codetabs.com/v1/proxy/?quest=",
                    "https://corsproxy.io/?",
                    "https://api.allorigins.win/raw?url="
                ]
                
                proxy_url = random.choice(proxy_servers) + quote(url, safe='')
                target_url = proxy_url
                method = f"Proxy ({proxy_servers.index(proxy_url.split('?')[0])+1})"
            else:
                target_url = url
                method = "Direct"
            
            print(f"   🔄 Deneme {attempt+1}/{max_retries} ({method})...")
            
            response = requests.get(target_url, headers=headers, timeout=timeout_val)
            
            if response.status_code == 200:
                print(f"   ✅ {method} başarılı: {len(response.text)} byte")
                return response.text
            elif response.status_code == 429:  # Too Many Requests
                print(f"   ⚠️  Rate limit! {response.status_code}")
                wait_time = (attempt + 1) * 5  # Artan bekleme süresi
                print(f"   ⏳ {wait_time} saniye bekleniyor...")
                time.sleep(wait_time)
                continue
            else:
                print(f"   ❌ HTTP {response.status_code}")
                
        except requests.exceptions.Timeout:
            print(f"   ⚠️  Zaman aşımı (attempt {attempt+1})")
        except requests.exceptions.ConnectionError:
            print(f"   🔌 Bağlantı hatası (attempt {attempt+1})")
        except Exception as e:
            print(f"   ⚠️  Hata: {str(e)[:50]}")
        
        # Yeniden denemeden önce bekle
        if attempt < max_retries - 1:
            wait = random.uniform(2, 4) if IS_GITHUB else random.uniform(1, 2)
            print(f"   ⏳ {wait:.1f} saniye bekleniyor...")
            time.sleep(wait)
    
    print(f"   ❌ {max_retries} deneme sonunda başarısız")
    return None

def extract_hls_url_advanced(html_content):
    """Geliştirilmiş 8 katmanlı HLS URL arama"""
    if not html_content:
        return None
    
    # HTML'i decode et
    decoded_html = decode_unicode_escapes(html_content)
    
    # Önbellek için ham HTML de sakla
    patterns_to_try = [
        # 1. Doğrudan hlsManifestUrl
        (r'"hlsManifestUrl"\s*:\s*"([^"]+?\.m3u8[^"]*)"', "Doğrudan hlsManifestUrl"),
        
        # 2. streamingData içinde
        (r'"streamingData"\s*:\s*({[^}]+(?:{[^}]+})?[^}]+})', "streamingData objesi"),
        
        # 3. player_response içinde
        (r'"player_response"\s*:\s*"([^"]+)"', "player_response"),
        
        # 4. JSON verisi içinde genel arama
        (r'"hlsManifestUrl"[^}]+"([^"]+?\.m3u8)"', "JSON içi genel"),
        
        # 5. adaptiveFormats içinde
        (r'"adaptiveFormats"\s*:\s*\[(.*?)\]', "adaptiveFormats"),
        
        # 6. videoDetails içinden çıkar
        (r'"videoDetails"[^}]+"liveStreamability"[^}]+"liveStreamabilityRenderer"[^}]+"videoId"\s*:\s*"([^"]+)"', "liveStreamability"),
        
        # 7. ytInitialPlayerResponse içinde
        (r'ytInitialPlayerResponse\s*=\s*({.+?})\s*;', "ytInitialPlayerResponse"),
        
        # 8. Genel m3u8 pattern'i
        (r'(https?://[^"\']+?\.m3u8[^"\']*)', "Genel m3u8 pattern")
    ]
    
    for pattern, pattern_name in patterns_to_try:
        try:
            match = re.search(pattern, decoded_html, re.IGNORECASE | re.DOTALL)
            if match:
                # Pattern 2: streamingData objesi
                if pattern_name == "streamingData objesi":
                    try:
                        streaming_str = match.group(1)
                        hls_match = re.search(r'"hlsManifestUrl"\s*:\s*"([^"]+?\.m3u8[^"]*)"', 
                                            streaming_str, re.IGNORECASE)
                        if hls_match:
                            url = decode_unicode_escapes(hls_match.group(1))
                            url = url.replace('\\/', '/').replace('\\u0026', '&')
                            return unquote(url)
                    except:
                        pass
                
                # Pattern 3: player_response
                elif pattern_name == "player_response":
                    try:
                        player_str = unquote(match.group(1).replace('\\/', '/').replace('\\u0026', '&'))
                        player_str = decode_unicode_escapes(player_str)
                        hls_match = re.search(r'"hlsManifestUrl"\s*:\s*"([^"]+?\.m3u8[^"]*)"', 
                                            player_str, re.IGNORECASE | re.DOTALL)
                        if hls_match:
                            url = decode_unicode_escapes(hls_match.group(1))
                            url = url.replace('\\/', '/').replace('\\u0026', '&')
                            return unquote(url)
                    except:
                        pass
                
                # Pattern 5: adaptiveFormats
                elif pattern_name == "adaptiveFormats":
                    try:
                        adaptive_str = match.group(1)
                        # adaptiveFormats içinde URL ara
                        url_match = re.search(r'"url"\s*:\s*"([^"]+?\.m3u8[^"]*)"', 
                                            adaptive_str, re.IGNORECASE)
                        if url_match:
                            url = decode_unicode_escapes(url_match.group(1))
                            url = url.replace('\\/', '/').replace('\\u0026', '&')
                            return unquote(url)
                    except:
                        pass
                
                # Pattern 7: ytInitialPlayerResponse
                elif pattern_name == "ytInitialPlayerResponse":
                    try:
                        json_str = match.group(1)
                        data = json.loads(json_str)
                        
                        # streamingData içinde ara
                        if 'streamingData' in data and 'hlsManifestUrl' in data['streamingData']:
                            url = data['streamingData']['hlsManifestUrl']
                            url = decode_unicode_escapes(url)
                            return unquote(url)
                    except:
                        pass
                
                # Diğer pattern'ler (1, 4, 6, 8)
                else:
                    url = decode_unicode_escapes(match.group(1))
                    url = url.replace('\\/', '/').replace('\\u0026', '&')
                    # manifest.googlevideo.com içeren URL'leri tercih et
                    if 'manifest.googlevideo.com' in url:
                        print(f"   ✅ {pattern_name} (manifest.googlevideo.com)")
                        return unquote(url)
                    elif '.m3u8' in url:
                        print(f"   ✅ {pattern_name}")
                        return unquote(url)
                        
        except Exception as e:
            continue
    
    # Son çare: Unicode escaped anahtar
    unicode_key_regex = r'\\u0068\\u006c\\u0073\\u004d\\u0061\\u006e\\u0069\\u0066\\u0065\\u0073\\u0074\\u0055\\u0072\\u006c":"([^"]+)"'
    match = re.search(unicode_key_regex, html_content)
    if match and match[1]:
        url = decode_unicode_escapes(match.group(1))
        url = url.replace('\\/', '/').replace('\\u0026', '&')
        return unquote(url)
    
    return None

def extract_channel_id_enhanced(html_content):
    """Geliştirilmiş channel ID extraction"""
    decoded_html = decode_unicode_escapes(html_content)
    
    # Birden fazla pattern dene
    patterns = [
        r'"channelId"\s*:\s*"([^"]+)"',
        r'"ucid"\s*:\s*"([^"]+)"',
        r'channelId["\']?\s*:\s*["\']([^"\']+)["\']',
        r'data-channel-id=["\']([^"\']+)["\']',
        r'"externalChannelId"\s*:\s*"([^"]+)"'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, decoded_html, re.IGNORECASE)
        if match and match[1]:
            channel_id = match.group(1)
            if re.match(r'^UC[a-zA-Z0-9_-]{22,}$', channel_id):
                return channel_id
    
    return None

def get_hls_url_robust(youtube_url):
    """GitHub için optimize edilmiş HLS URL alma"""
    try:
        # Video ID'yi çıkar
        video_id = None
        patterns = [
            r'(?:v=|youtu\.be/|embed/)([a-zA-Z0-9_-]{11})',
            r'youtube\.com/watch\?.*v=([a-zA-Z0-9_-]{11})',
            r'youtube\.com/embed/([a-zA-Z0-9_-]{11})'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, youtube_url)
            if match:
                video_id = match.group(1)
                break
        
        if not video_id:
            return None
        
        print(f"   📹 Video ID: {video_id}")
        
        # 1. Önce watch sayfasını dene
        watch_url = f"https://www.youtube.com/watch?v={video_id}"
        print(f"   🔄 Watch sayfası deneniyor...")
        html_content = get_youtube_page_with_retry(watch_url)
        
        if html_content:
            hls_url = extract_hls_url_advanced(html_content)
            if hls_url:
                return hls_url
            
            # Channel ID'yi çıkar ve kanal sayfasını dene
            channel_id = extract_channel_id_enhanced(html_content)
            if channel_id:
                print(f"   📺 Channel ID bulundu: {channel_id}")
                channel_url = f"https://www.youtube.com/channel/{channel_id}/live"
                print(f"   🔄 Kanal canlı yayın sayfası deneniyor...")
                channel_html = get_youtube_page_with_retry(channel_url)
                
                if channel_html:
                    channel_hls_url = extract_hls_url_advanced(channel_html)
                    if channel_hls_url:
                        return channel_hls_url
        
        # 2. Embed sayfasını dene
        embed_url = f"https://www.youtube.com/embed/{video_id}"
        print(f"   🔄 Embed sayfası deneniyor...")
        html_content = get_youtube_page_with_retry(embed_url)
        
        if html_content:
            hls_url = extract_hls_url_advanced(html_content)
            if hls_url:
                return hls_url
        
        # 3. get_video_info endpoint (son çare)
        if not IS_GITHUB:  # GitHub'da bu endpoint çalışmayabilir
            try:
                info_url = f"https://www.youtube.com/get_video_info?video_id={video_id}&el=detailpage&ps=default&gl=US&hl=en"
                print(f"   🔄 get_video_info deneniyor...")
                response = requests.get(info_url, timeout=10)
                if response.status_code == 200:
                    params = dict(x.split('=') for x in response.text.split('&') if '=' in x)
                    if 'player_response' in params:
                        player_response = unquote(params['player_response'])
                        try:
                            data = json.loads(player_response)
                            if 'streamingData' in data and 'hlsManifestUrl' in data['streamingData']:
                                return data['streamingData']['hlsManifestUrl']
                        except:
                            pass
            except:
                pass
        
        return None
        
    except Exception as e:
        print(f"   ❌ Hata: {str(e)[:80]}")
        return None

def m3u_dosyasi_olustur(kanallar):
    """EPG olmadan M3U oluştur"""
    m3u_icerik = "#EXTM3U\n"
    basarili = 0
    
    for kanal in kanallar:
        if 'hls_url' in kanal and kanal['hls_url']:
            hls_url = kanal['hls_url'].strip()
            m3u_icerik += f'#EXTINF:-1 tvg-id="{kanal["isim"]}" tvg-name="{kanal["isim"]}" tvg-logo="{kanal["logo"]}" group-title="YouTube",{kanal["isim"]}\n'
            m3u_icerik += f'{hls_url}\n'
            basarili += 1
            print(f"   ✅ {kanal['isim']}")
    
    with open('youtube.m3u', 'w', encoding='utf-8') as dosya:
        dosya.write(m3u_icerik)
    
    return basarili

def main():
    print("=" * 60)
    print("🚀 YOUTUBE M3U GENERATOR - GİTHUB OPTİMİZE")
    print("=" * 60)
    
    kanallar = links_dosyasini_oku()
    if not kanallar:
        print("❌ İşlem iptal edildi: Kanallar bulunamadı")
        return
    
    print("\n📡 HLS URL'LERİ ALINIYOR...")
    print(f"⚙️  GitHub Actions: {'Evet' if IS_GITHUB else 'Hayır'}")
    
    basarili = 0
    basarisiz = 0
    
    for idx, kanal in enumerate(kanallar, 1):
        print(f"\n🎬 [{idx}/{len(kanallar)}] {kanal['isim']}")
        
        hls_url = get_hls_url_robust(kanal['icerik'])
        
        if hls_url:
            kanal['hls_url'] = hls_url
            basarili += 1
            print(f"   ✅ {hls_url[:100]}...")
        else:
            kanal['hls_url'] = None
            basarisiz += 1
            print(f"   ❌ Bulunamadı")
        
        # Rate limiting için akıllı bekleme
        if idx < len(kanallar):
            if IS_GITHUB:
                wait_time = random.uniform(3, 6)  # GitHub'da daha uzun bekle
            else:
                wait_time = random.uniform(1, 3)
            
            print(f"   ⏳ {wait_time:.1f} saniye bekleniyor...")
            time.sleep(wait_time)
    
    print("\n📝 M3U OLUŞTURULUYOR...")
    m3u_basarili = m3u_dosyasi_olustur(kanallar)
    
    print(f"\n📊 SONUÇLAR:")
    print(f"✅ Başarılı: {basarili}")
    print(f"❌ Başarısız: {basarisiz}")
    
    # Başarısız kanalları listele
    basarisiz_kanallar = [k['isim'] for k in kanallar if not k.get('hls_url')]
    if basarisiz_kanallar:
        print(f"\n⚠️  BAŞARISIZ KANALLAR:")
        for isim in basarisiz_kanallar:
            print(f"   - {isim}")
    
    if basarili > 0:
        print(f"\n🎉 youtube.m3u oluşturuldu! ({m3u_basarili} kanal)")
        print("📁 'youtube.m3u' dosyasını kontrol edin")
    else:
        print(f"\n⚠️  HİÇBİR KANAL İÇİN HLS URL'Sİ BULUNAMADI!")

if __name__ == "__main__":
    main()
