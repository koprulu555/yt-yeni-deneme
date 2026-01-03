#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import requests
import re
import json
import os
from urllib.parse import unquote
import html
import time
import random

def links_dosyasini_oku():
    """links.txt dosyasını GitHub raw linkinden oku"""
    kanallar = []
    
    try:
        response = requests.get("https://raw.githubusercontent.com/koprulu555/yt-streams/refs/heads/main/links.txt", timeout=10)
        icerik = response.text if response.status_code == 200 else ""
        
        if not icerik:
            with open('links.txt', 'r', encoding='utf-8') as dosya:
                icerik = dosya.read()
    except:
        with open('links.txt', 'r', encoding='utf-8') as dosya:
            icerik = dosya.read()
    
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

# Workers'daki userAgents listesinin aynısı
user_agents = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (iPhone; CPU iPhone OS 17_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Mobile/15E148 Safari/604.1',
    'Mozilla/5.0 (iPad; CPU OS 17_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Mobile/15E148 Safari/604.1',
    'Mozilla/5.0 (Linux; Android 14; SM-S918B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.6099.210 Mobile Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.2210.91',
    'Mozilla/5.0 (X11; CrOS x86_64 14541.0.0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
]

def get_random_user_agent():
    return random.choice(user_agents)

# Workers'daki decodeUnicodeEscapes fonksiyonunun birebir karşılığı
def decode_unicode_escapes(text):
    """Workers'daki decodeUnicodeEscapes'in tam karşılığı"""
    def replace_unicode(match):
        try:
            return chr(int(match.group(1), 16))
        except:
            return match.group(0)
    
    # 1. \uXXXX formatını decode et
    result = re.sub(r'\\u([0-9a-fA-F]{4})', replace_unicode, text)
    
    # 2. HTML entity'leri decode et
    result = html.unescape(result)
    
    # 3. Diğer escape'leri temizle
    result = result.replace('\\/', '/').replace('\\u0026', '&')
    
    # 4. \x22 (") karakterlerini decode et
    result = re.sub(r'\\x22', '"', result)
    
    # 5. \\\ karakterlerini temizle
    result = result.replace('\\\\', '\\')
    
    return result

def get_youtube_page(url):
    """Workers'daki fetch mantığı"""
    headers = {
        'User-Agent': get_random_user_agent(),
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7',
        'Accept-Encoding': 'gzip, deflate',
        'DNT': '1',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'none',
        'Sec-Fetch-User': '?1',
        'Cache-Control': 'max-age=0',
        'Referer': 'https://www.youtube.com.tr/'
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=15)
        if response.status_code == 200:
            return response.text
    except:
        pass
    return None

# Workers'daki extractHlsManifestUrl fonksiyonunun 6 katmanlı araması
def extract_hls_url_workers(html_content):
    """Workers'daki 6 katmanlı aramanın birebir uygulaması"""
    if not html_content:
        return None
    
    # 0. KATMAN: Tüm HTML'i decode et
    decoded_html = decode_unicode_escapes(html_content)
    
    # 1. KATMAN: Doğrudan düz metinde ara
    direct_regex = r'"hlsManifestUrl"\s*:\s*"([^"]+?\.m3u8[^"]*)"'
    match = re.search(direct_regex, decoded_html, re.IGNORECASE | re.DOTALL)
    if match and match[1]:
        url = decode_unicode_escapes(match[1])
        url = url.replace('\\/', '/').replace('\\u0026', '&')
        return unquote(url)
    
    # 2. KATMAN: streamingData objesi içinde ara
    streaming_data_regex = r'"streamingData"\s*:\s*({[^}]+(?:{[^}]+})?[^}]+})'
    match = re.search(streaming_data_regex, decoded_html, re.IGNORECASE | re.DOTALL)
    if match and match[1]:
        try:
            streaming_data_str = match[1]
            hls_match = re.search(r'"hlsManifestUrl"\s*:\s*"([^"]+?\.m3u8[^"]*)"', 
                                 streaming_data_str, re.IGNORECASE)
            if hls_match and hls_match[1]:
                url = decode_unicode_escapes(hls_match[1])
                url = url.replace('\\/', '/').replace('\\u0026', '&')
                return unquote(url)
        except:
            pass
    
    # 3. KATMAN: player_response içinde ara
    player_response_regex = r'"player_response"\s*:\s*"([^"]+)"'
    match = re.search(player_response_regex, decoded_html, re.IGNORECASE | re.DOTALL)
    if match and match[1]:
        try:
            player_response_str = unquote(match[1].replace('\\/', '/').replace('\\u0026', '&'))
            player_response_str = decode_unicode_escapes(player_response_str)
            
            hls_match = re.search(r'"hlsManifestUrl"\s*:\s*"([^"]+?\.m3u8[^"]*)"', 
                                 player_response_str, re.IGNORECASE | re.DOTALL)
            if hls_match and hls_match[1]:
                url = decode_unicode_escapes(hls_match[1])
                url = url.replace('\\/', '/').replace('\\u0026', '&')
                return unquote(url)
        except:
            pass
    
    # 4. KATMAN: adaptive_fmts içinde ara
    adaptive_regex = r'"adaptive_fmts"\s*:\s*"([^"]+)"'
    match = re.search(adaptive_regex, decoded_html, re.IGNORECASE | re.DOTALL)
    if match and match[1]:
        try:
            adaptive_str = unquote(match[1].replace('\\/', '/').replace('\\u0026', '&'))
            adaptive_str_decoded = decode_unicode_escapes(adaptive_str)
            url_match = re.search(r'https?[^,]+\.m3u8[^,&]*', adaptive_str_decoded, re.IGNORECASE)
            if url_match and url_match[0]:
                url = decode_unicode_escapes(url_match[0])
                url = url.replace('\\/', '/').replace('\\u0026', '&')
                return unquote(url)
        except:
            pass
    
    # 5. KATMAN: Genel .m3u8 URL araması
    generic_m3u8_regex = r'(https?://[^"]+?\.m3u8[^"]*)'
    all_matches = re.findall(generic_m3u8_regex, decoded_html, re.IGNORECASE)
    if all_matches:
        for url_match in all_matches:
            if 'manifest.googlevideo.com' in url_match:
                url = decode_unicode_escapes(url_match)
                url = url.replace('\\/', '/').replace('\\u0026', '&')
                return unquote(url)
        
        url = decode_unicode_escapes(all_matches[0])
        url = url.replace('\\/', '/').replace('\\u0026', '&')
        return unquote(url)
    
    # 6. KATMAN: Ham HTML'de Unicode escaped anahtarda ara
    unicode_key_regex = r'\\u0068\\u006c\\u0073\\u004d\\u0061\\u006e\\u0069\\u0066\\u0065\\u0073\\u0074\\u0055\\u0072\\u006c":"([^"]+)"'
    match = re.search(unicode_key_regex, html_content)
    if match and match[1]:
        url = decode_unicode_escapes(match[1])
        url = url.replace('\\/', '/').replace('\\u0026', '&')
        return unquote(url)
    
    return None

def extract_channel_id(html_content):
    """Workers'daki extractChannelIdFromHtml fonksiyonu"""
    decoded_html = decode_unicode_escapes(html_content)
    
    # 1. "channelId":"UC..." formatını ara
    channel_id_regex = r'"channelId"\s*:\s*"([^"]+)"'
    match = re.search(channel_id_regex, decoded_html, re.IGNORECASE)
    if match and match[1]:
        channel_id = match[1]
        if re.match(r'^UC[a-zA-Z0-9_-]{22,}$', channel_id):
            return channel_id
    
    # 2. "videoDetails":{"channelId":"UC..."
    video_details_regex = r'"videoDetails"\s*:\s*{[^}]*"channelId"\s*:\s*"([^"]+)"'
    match = re.search(video_details_regex, decoded_html, re.IGNORECASE | re.DOTALL)
    if match and match[1]:
        channel_id = match[1]
        if re.match(r'^UC[a-zA-Z0-9_-]{22,}$', channel_id):
            return channel_id
    
    # 3. Alternate pattern: \x22channelId\x22:\x22UC...\x22
    alt_regex = r'\\x22channelId\\x22:\\x22([^\\]+)\\x22'
    match = re.search(alt_regex, html_content)
    if match and match[1]:
        channel_id = match[1]
        if re.match(r'^UC[a-zA-Z0-9_-]{22,}$', channel_id):
            return channel_id
    
    return None

def get_hls_url(youtube_url):
    """Workers'daki ana mantığın birebir uygulaması"""
    try:
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
        
        # Önce watch sayfasını dene
        watch_url = f"https://www.youtube.com/watch?v={video_id}"
        print(f"   🔄 Watch sayfası deneniyor: {watch_url}")
        html_content = get_youtube_page(watch_url)
        
        if html_content:
            hls_url = extract_hls_url_workers(html_content)
            if hls_url:
                return hls_url
            
            # Channel ID'yi çıkar ve kanal sayfasını dene
            channel_id = extract_channel_id(html_content)
            if channel_id:
                print(f"   📺 Channel ID bulundu: {channel_id}")
                channel_url = f"https://www.youtube.com/channel/{channel_id}/live"
                print(f"   🔄 Kanal sayfası deneniyor: {channel_url}")
                channel_html = get_youtube_page(channel_url)
                
                if channel_html:
                    channel_hls_url = extract_hls_url_workers(channel_html)
                    if channel_hls_url:
                        return channel_hls_url
        
        # Embed sayfasını dene
        embed_url = f"https://www.youtube.com/embed/{video_id}"
        print(f"   🔄 Embed sayfası deneniyor: {embed_url}")
        html_content = get_youtube_page(embed_url)
        
        if html_content:
            return extract_hls_url_workers(html_content)
        
        return None
        
    except Exception as e:
        print(f"   ❌ Hata: {str(e)[:100]}")
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
    print("🚀 YOUTUBE M3U GENERATOR - WORKERS BİREBİR")
    print("=" * 60)
    
    kanallar = links_dosyasini_oku()
    if not kanallar:
        return
    
    print("\n📡 HLS URL'LERİ ALINIYOR...")
    
    for idx, kanal in enumerate(kanallar, 1):
        print(f"\n🎬 [{idx}/{len(kanallar)}] {kanal['isim']}")
        
        hls_url = get_hls_url(kanal['icerik'])
        
        if hls_url:
            kanal['hls_url'] = hls_url
            print(f"   ✅ {hls_url[:100]}...")
        else:
            kanal['hls_url'] = None
            print(f"   ❌ Bulunamadı")
        
        time.sleep(0.5)
    
    print("\n📝 M3U OLUŞTURULUYOR...")
    basarili = m3u_dosyasi_olustur(kanallar)
    
    print(f"\n✅ Başarılı: {basarili}")
    print(f"❌ Başarısız: {len(kanallar) - basarili}")
    
    if basarili > 0:
        print(f"\n🎉 youtube.m3u oluşturuldu!")
    else:
        print(f"\n⚠️  HLS URL bulunamadı!")

if __name__ == "__main__":
    main()
