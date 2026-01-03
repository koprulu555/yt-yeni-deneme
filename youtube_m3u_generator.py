#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import requests
import re
import json
import os
from urllib.parse import unquote, quote
import html
import time
import random

def links_dosyasini_oku():
    """links.txt dosyasını GitHub raw linkinden oku ve kanal listesini döndür"""
    kanallar = []
    
    raw_url = "https://raw.githubusercontent.com/koprulu555/yt-streams/refs/heads/main/links.txt"
    
    try:
        response = requests.get(raw_url, timeout=10)
        if response.status_code == 200:
            icerik = response.text
            print("✅ links.txt dosyası GitHub'dan okundu")
        else:
            print(f"❌ links.txt dosyası GitHub'dan indirilemedi! Hata kodu: {response.status_code}")
            # Fallback olarak yerel dosyayı dene
            try:
                with open('links.txt', 'r', encoding='utf-8') as dosya:
                    icerik = dosya.read()
                    print("✅ links.txt dosyası yerelden okundu (fallback)")
            except FileNotFoundError:
                print("❌ links.txt dosyası bulunamadı!")
                return kanallar
    except Exception as e:
        print(f"❌ GitHub bağlantı hatası: {e}")
        # Fallback olarak yerel dosyayı dene
        try:
            with open('links.txt', 'r', encoding='utf-8') as dosya:
                icerik = dosya.read()
                print("✅ links.txt dosyası yerelden okundu (fallback)")
        except FileNotFoundError:
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

# Rastgele User-Agent listesi (Workers'daki gibi)
user_agents = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (iPhone; CPU iPhone OS 17_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Mobile/15E148 Safari/604.1',
    'Mozilla/5.0 (Linux; Android 14; SM-S918B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.6099.210 Mobile Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.2210.91'
]

def get_random_user_agent():
    """Rastgele User-Agent döndür"""
    return random.choice(user_agents)

def decode_unicode_escapes(text):
    """Workers'daki decodeUnicodeEscapes fonksiyonunun Python versiyonu"""
    try:
        # Unicode escape'leri decode et (\u0068 -> h)
        def replace_unicode(match):
            try:
                return chr(int(match.group(1), 16))
            except:
                return match.group(0)
        
        # İlk olarak \uXXXX formatını decode et
        result = re.sub(r'\\u([0-9a-fA-F]{4})', replace_unicode, text)
        
        # HTML entity'leri decode et
        result = html.unescape(result)
        
        # Diğer escape karakterlerini temizle
        result = result.replace('\\/', '/').replace('\\u0026', '&')
        
        return result
    except Exception as e:
        print(f"   ⚠️ Unicode decode hatası: {str(e)[:50]}")
        return text

def get_youtube_page(url):
    """YouTube sayfasını doğrudan çek (Workers mantığı)"""
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
        print(f"   🔄 YouTube sayfasına doğrudan bağlanılıyor...")
        response = requests.get(url, headers=headers, timeout=15)
        
        if response.status_code == 200:
            print(f"   ✅ Sayfa başarıyla alındı: {len(response.text)} byte")
            return response.text
        else:
            print(f"   ❌ HTTP hatası: {response.status_code}")
            return None
            
    except Exception as e:
        print(f"   ❌ Bağlantı hatası: {str(e)[:100]}")
        return None

def extract_hls_url_workers_style(html_content):
    """Workers'daki 6 katmanlı HLS URL çıkarma mantığı"""
    if not html_content:
        return None
    
    # 0. KATMAN: Tüm HTML'i decode et
    decoded_html = decode_unicode_escapes(html_content)
    
    # 1. KATMAN: Doğrudan düz metinde ara
    direct_regex = r'"hlsManifestUrl"\s*:\s*"([^"]+?\.m3u8[^"]*)"'
    match = re.search(direct_regex, decoded_html, re.IGNORECASE)
    if match and match[1]:
        url = decode_unicode_escapes(match[1])
        url = url.replace('\\/', '/').replace('\\u0026', '&')
        try:
            return unquote(url)
        except:
            return url
    
    # 2. KATMAN: streamingData objesi içinde ara
    streaming_data_regex = r'"streamingData"\s*:\s*({[^}]+(?:{[^}]+})?[^}]+})'
    match = re.search(streaming_data_regex, decoded_html, re.IGNORECASE)
    if match and match[1]:
        try:
            streaming_data_str = match[1]
            hls_match = re.search(r'"hlsManifestUrl"\s*:\s*"([^"]+?\.m3u8[^"]*)"', 
                                 streaming_data_str, re.IGNORECASE)
            if hls_match and hls_match[1]:
                url = decode_unicode_escapes(hls_match[1])
                url = url.replace('\\/', '/').replace('\\u0026', '&')
                try:
                    return unquote(url)
                except:
                    return url
        except Exception as e:
            pass
    
    # 3. KATMAN: player_response içinde ara
    player_response_regex = r'"player_response"\s*:\s*"([^"]+)"'
    match = re.search(player_response_regex, decoded_html, re.IGNORECASE)
    if match and match[1]:
        try:
            player_response_str = unquote(match[1].replace('\\/', '/').replace('\\u0026', '&'))
            player_response_str = decode_unicode_escapes(player_response_str)
            
            hls_match = re.search(r'"hlsManifestUrl"\s*:\s*"([^"]+?\.m3u8[^"]*)"', 
                                 player_response_str, re.IGNORECASE)
            if hls_match and hls_match[1]:
                url = decode_unicode_escapes(hls_match[1])
                url = url.replace('\\/', '/').replace('\\u0026', '&')
                try:
                    return unquote(url)
                except:
                    return url
        except Exception as e:
            pass
    
    # 4. KATMAN: adaptive_fmts içinde ara
    adaptive_regex = r'"adaptive_fmts"\s*:\s*"([^"]+)"'
    match = re.search(adaptive_regex, decoded_html, re.IGNORECASE)
    if match and match[1]:
        try:
            adaptive_str = unquote(match[1].replace('\\/', '/').replace('\\u0026', '&'))
            adaptive_str_decoded = decode_unicode_escapes(adaptive_str)
            url_match = re.search(r'https?[^,]+\.m3u8[^,&]*', adaptive_str_decoded, re.IGNORECASE)
            if url_match and url_match[0]:
                url = decode_unicode_escapes(url_match[0])
                url = url.replace('\\/', '/').replace('\\u0026', '&')
                try:
                    return unquote(url)
                except:
                    return url
        except Exception as e:
            pass
    
    # 5. KATMAN: Genel .m3u8 URL araması
    generic_m3u8_regex = r'(https?://[^"]+?\.m3u8[^"]*)'
    all_matches = re.findall(generic_m3u8_regex, decoded_html, re.IGNORECASE)
    if all_matches:
        # manifest.googlevideo.com içerenleri tercih et
        for url_match in all_matches:
            if 'manifest.googlevideo.com' in url_match:
                url = decode_unicode_escapes(url_match)
                url = url.replace('\\/', '/').replace('\\u0026', '&')
                try:
                    return unquote(url)
                except:
                    return url
        
        # Yoksa ilk .m3u8 URL'sini al
        url = decode_unicode_escapes(all_matches[0])
        url = url.replace('\\/', '/').replace('\\u0026', '&')
        try:
            return unquote(url)
        except:
            return url
    
    # 6. KATMAN: Ham HTML'de Unicode escaped anahtarda ara
    unicode_key_regex = r'\\u0068\\u006c\\u0073\\u004d\\u0061\\u006e\\u0069\\u0066\\u0065\\u0073\\u0074\\u0055\\u0072\\u006c":"([^"]+)"'
    match = re.search(unicode_key_regex, html_content)
    if match and match[1]:
        url = decode_unicode_escapes(match[1])
        url = url.replace('\\/', '/').replace('\\u0026', '&')
        try:
            return unquote(url)
        except:
            return url
    
    return None

def fetch_hls_via_get_video_info(video_id):
    """get_video_info endpoint'inden HLS URL'si çekme"""
    url = f"https://www.youtube.com/get_video_info?video_id={video_id}"
    
    headers = {
        'User-Agent': get_random_user_agent(),
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7'
    }
    
    try:
        print(f"   🔄 get_video_info deneniyor...")
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            text = response.text
            
            # URL-encoded parametrelerini parse et
            params = {}
            for param in text.split('&'):
                if '=' in param:
                    key, value = param.split('=', 1)
                    params[key] = unquote(value)
            
            # hlsvp parametresini kontrol et
            if 'hlsvp' in params and params['hlsvp']:
                hls_url = params['hlsvp']
                print(f"   ✅ get_video_info'den hlsvp bulundu")
                return hls_url
            
            # adaptive_fmts içinde HLS URL'si ara
            if 'adaptive_fmts' in params and params['adaptive_fmts']:
                adaptive_fmts = params['adaptive_fmts']
                decoded = unquote(adaptive_fmts)
                m3u8_match = re.search(r'https?[^,]+\.m3u8[^,&]*', decoded, re.IGNORECASE)
                if m3u8_match:
                    print(f"   ✅ get_video_info'den adaptive_fmts bulundu")
                    return m3u8_match[0]
            
            # player_response içinde hlsManifestUrl ara
            if 'player_response' in params and params['player_response']:
                try:
                    player_json = json.loads(params['player_response'])
                    if ('streamingData' in player_json and 
                        'hlsManifestUrl' in player_json['streamingData'] and 
                        player_json['streamingData']['hlsManifestUrl']):
                        hls_url = player_json['streamingData']['hlsManifestUrl']
                        print(f"   ✅ get_video_info'den player_response bulundu")
                        return hls_url
                except Exception as e:
                    pass
            
            return None
        else:
            print(f"   ❌ get_video_info hatası: {response.status_code}")
            return None
            
    except Exception as e:
        print(f"   ⚠️ get_video_info bağlantı hatası: {str(e)[:50]}")
        return None

def extract_channel_id_from_html(html_content):
    """HTML'den Channel ID çıkar"""
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
    match = re.search(video_details_regex, decoded_html, re.IGNORECASE)
    if match and match[1]:
        channel_id = match[1]
        if re.match(r'^UC[a-zA-Z0-9_-]{22,}$', channel_id):
            return channel_id
    
    return None

def get_hls_url_workers_style(youtube_url):
    """Workers mantığıyla HLS URL'sini al"""
    try:
        # Video ID'yi çıkar
        video_id = None
        video_patterns = [
            r'(?:v=|youtu\.be/|embed/)([a-zA-Z0-9_-]{11})',
            r'youtube\.com/watch\?.*v=([a-zA-Z0-9_-]{11})',
            r'youtube\.com/embed/([a-zA-Z0-9_-]{11})'
        ]
        
        for pattern in video_patterns:
            match = re.search(pattern, youtube_url)
            if match:
                video_id = match.group(1)
                break
        
        if not video_id:
            print(f"   ❌ Video ID bulunamadı: {youtube_url}")
            return None
        
        print(f"   📹 Video ID: {video_id}")
        
        # İlk olarak get_video_info dene (Workers'daki gibi)
        hls_url = fetch_hls_via_get_video_info(video_id)
        if hls_url:
            return hls_url
        
        # 1. Embed sayfasını dene
        embed_url = f"https://www.youtube.com/embed/{video_id}"
        print(f"   🔄 Embed sayfası deneniyor: {embed_url}")
        html_content = get_youtube_page(embed_url)
        
        if html_content:
            hls_url = extract_hls_url_workers_style(html_content)
            if hls_url:
                return hls_url
        
        # 2. Watch sayfasını dene
        watch_url = f"https://www.youtube.com/watch?v={video_id}"
        print(f"   🔄 Watch sayfası deneniyor: {watch_url}")
        html_content = get_youtube_page(watch_url)
        
        if html_content:
            hls_url = extract_hls_url_workers_style(html_content)
            if hls_url:
                return hls_url
            
            # Eğer HLS bulunamazsa, channel ID'yi çıkar ve kanal sayfasını dene
            channel_id = extract_channel_id_from_html(html_content)
            if channel_id:
                print(f"   📺 Channel ID bulundu: {channel_id}")
                channel_url = f"https://www.youtube.com/channel/{channel_id}/live"
                print(f"   🔄 Kanal sayfası deneniyor: {channel_url}")
                channel_html = get_youtube_page(channel_url)
                
                if channel_html:
                    channel_hls_url = extract_hls_url_workers_style(channel_html)
                    if channel_hls_url:
                        return channel_hls_url
        
        # Son çare olarak tekrar get_video_info dene
        return fetch_hls_via_get_video_info(video_id)
        
    except Exception as e:
        print(f"   ❌ Workers yöntemi hatası: {str(e)[:100]}")
        return None

def m3u_dosyasi_olustur(kanallar):
    """M3U dosyasını oluştur (EPG satırı olmadan)"""
    m3u_icerik = "#EXTM3U\n"  # EPG satırı kaldırıldı
    basarili_kanallar = 0
    
    for kanal in kanallar:
        if 'hls_url' in kanal and kanal['hls_url']:
            # URL'yi temizle
            hls_url = kanal['hls_url'].strip()
            if '\\' in hls_url:
                hls_url = hls_url.replace('\\', '')
            
            # HLS URL'sine referer ve user-agent ekle (orijinal script'teki gibi)
            if hls_url.startswith('http'):
                m3u_icerik += f'#EXTINF:-1 tvg-id="{kanal["isim"]}" tvg-name="{kanal["isim"]}" tvg-logo="{kanal["logo"]}" group-title="YouTube",{kanal["isim"]}\n'
                m3u_icerik += f'{hls_url}\n'
                basarili_kanallar += 1
                print(f"   ✅ {kanal['isim']} - HLS URL eklendi")
    
    try:
        with open('youtube.m3u', 'w', encoding='utf-8') as dosya:
            dosya.write(m3u_icerik)
        print(f"✅ youtube.m3u dosyası oluşturuldu ({basarili_kanallar} kanal)")
        return basarili_sayisi
    except Exception as e:
        print(f"❌ M3U dosyası yazılamadı: {e}")
        return 0

def main():
    print("=" * 60)
    print("🚀 YOUTUBE M3U GENERATOR - WORKERS MANTIĞI")
    print("=" * 60)
    
    # 1. links.txt dosyasını oku
    kanallar = links_dosyasini_oku()
    if not kanallar:
        print("❌ İşlem iptal edildi: Kanallar bulunamadı")
        return
    
    # 2. Her kanal için HLS URL'sini al (Workers mantığıyla)
    print("\n" + "=" * 60)
    print("📡 HLS URL'LERİ ALINIYOR (WORKERS MANTIĞI)...")
    print("=" * 60)
    
    for idx, kanal in enumerate(kanallar, 1):
        print(f"\n🎬 [{idx}/{len(kanallar)}] KANAL: {kanal['isim']}")
        print(f"   🔗 URL: {kanal['icerik'][:80]}...")
        
        hls_url = get_hls_url_workers_style(kanal['icerik'])
        
        if hls_url:
            kanal['hls_url'] = hls_url
            print(f"   ✅ BAŞARILI - HLS URL: {hls_url[:100]}...")
        else:
            kanal['hls_url'] = None
            print(f"   ❌ BAŞARISIZ - HLS URL bulunamadı")
        
        # Rate limiting önlemi
        if idx < len(kanallar):
            time.sleep(1)
    
    # 3. M3U dosyasını oluştur
    print("\n" + "=" * 60)
    print("📝 M3U DOSYASI OLUŞTURULUYOR...")
    print("=" * 60)
    
    basarili_sayisi = m3u_dosyasi_olustur(kanallar)
    
    # 4. Sonuçları göster
    print("\n" + "=" * 60)
    print("🎉 SONUÇLAR")
    print("=" * 60)
    print(f"📊 Toplam Kanal: {len(kanallar)}")
    print(f"✅ Başarılı: {basarili_sayisi}")
    print(f"❌ Başarısız: {len(kanallar) - basarili_sayisi}")
    
    # Başarısız kanalları listele
    basarisiz_kanallar = [k['isim'] for k in kanallar if not k.get('hls_url')]
    if basarisiz_kanallar:
        print(f"\n⚠️  BAŞARISIZ KANALLAR:")
        for isim in basarisiz_kanallar:
            print(f"   - {isim}")
    
    if basarili_sayisi > 0:
        print("\n🎉 YOUTUBE.M3U DOSYASI BAŞARIYLA OLUŞTURULDU!")
        print("📁 'youtube.m3u' dosyasını kontrol edin")
    else:
        print("\n⚠️  HİÇBİR KANAL İÇİN HLS URL'Sİ BULUNAMADI!")

if __name__ == "__main__":
    main()
