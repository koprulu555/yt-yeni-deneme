#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import requests
import re
import json
import os
from urllib.parse import unquote, quote
import html

def links_dosyasini_oku():
    """links.txt dosyasını GitHub raw linkinden oku ve kanal listesini döndür"""
    kanallar = []
    
    raw_url = "https://raw.githubusercontent.com/koprulu555/yt-yeni-deneme/refs/heads/main/links.txt"
    
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

def decode_unicode_escape(text):
    """Unicode escape sekanslarını decode et"""
    try:
        # JSON formatındaki unicode escape'leri decode et
        return bytes(text, 'utf-8').decode('unicode_escape')
    except:
        try:
            # HTML entity'leri decode et
            return html.unescape(text)
        except:
            return text

def get_youtube_page(url):
    """YouTube sayfasını doğrudan çek"""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7',
        'Accept-Encoding': 'gzip, deflate, br',
        'DNT': '1',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'none',
        'Sec-Fetch-User': '?1',
        'Cache-Control': 'max-age=0',
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

def extract_hls_url(html_content):
    """HTML'den HLS URL'sini çoklu yöntemlerle çıkar"""
    if not html_content:
        return None
    
    # 1. Önce orijinal HTML'de ara
    patterns = [
        # Yeni YouTube formatı
        r'"hlsManifestUrl"\s*:\s*"([^"]+)"',
        r'"playbackUrl"\s*:\s*"([^"]+m3u8[^"]*)"',
        r'"url"\s*:\s*"([^"]+m3u8[^"]*)"',
        # Eski formatlar
        r'hlsManifestUrl["\']?\s*:\s*["\']([^"\']+m3u8[^"\']*)["\']',
        r'"hls_url"\s*:\s*"([^"]+)"',
        # Genel m3u8 araması
        r'(https?://[^"\']+\.m3u8[^"\']*)'
    ]
    
    for pattern in patterns:
        matches = re.findall(pattern, html_content)
        for match in matches:
            if 'm3u8' in match:
                # İlk decode denemesi
                decoded = decode_unicode_escape(match)
                decoded = decoded.replace('\\u0026', '&').replace('\\/', '/')
                
                # Ek decode işlemleri
                for _ in range(3):  # Çoklu decode katmanları için
                    if '\\u' in decoded:
                        try:
                            decoded = decoded.encode('utf-8').decode('unicode_escape')
                        except:
                            pass
                
                if decoded.startswith('http'):
                    print(f"   ✅ Pattern bulundu: {pattern[:50]}...")
                    return decoded
    
    # 2. JSON verisi içinde ara
    json_patterns = [
        r'ytInitialPlayerResponse\s*=\s*({.+?})\s*;',
        r'var ytInitialPlayerResponse\s*=\s*({.+?})\s*;',
        r'window\["ytInitialPlayerResponse"\]\s*=\s*({.+?})\s*;'
    ]
    
    for pattern in json_patterns:
        match = re.search(pattern, html_content, re.DOTALL)
        if match:
            try:
                json_str = match.group(1)
                # JSON'daki escape karakterlerini temizle
                json_str = decode_unicode_escape(json_str)
                data = json.loads(json_str)
                
                # StreamingData içinde ara
                if 'streamingData' in data:
                    streaming_data = data['streamingData']
                    
                    # HLS manifest URL'si
                    if 'hlsManifestUrl' in streaming_data:
                        url = streaming_data['hlsManifestUrl']
                        url = decode_unicode_escape(url)
                        url = url.replace('\\u0026', '&').replace('\\/', '/')
                        if url.startswith('http'):
                            print("   ✅ JSON'dan hlsManifestUrl bulundu")
                            return url
                    
                    # Adaptive formats içinde ara
                    if 'adaptiveFormats' in streaming_data:
                        for fmt in streaming_data['adaptiveFormats']:
                            if 'url' in fmt and 'm3u8' in fmt['url']:
                                url = fmt['url']
                                url = decode_unicode_escape(url)
                                url = url.replace('\\u0026', '&').replace('\\/', '/')
                                if url.startswith('http'):
                                    print("   ✅ JSON'dan adaptive format URL bulundu")
                                    return url
            except Exception as e:
                print(f"   ⚠️ JSON parse hatası: {str(e)[:50]}")
                continue
    
    # 3. Tüm HTML'i decode edip tekrar ara
    try:
        decoded_html = decode_unicode_escape(html_content)
        # Tekrar pattern'leri dene
        for pattern in patterns:
            matches = re.findall(pattern, decoded_html)
            for match in matches:
                if 'm3u8' in match:
                    url = decode_unicode_escape(match)
                    url = url.replace('\\u0026', '&').replace('\\/', '/')
                    if url.startswith('http'):
                        print(f"   ✅ Decode edilmiş HTML'den URL bulundu")
                        return url
    except Exception as e:
        print(f"   ⚠️ HTML decode hatası: {str(e)[:50]}")
    
    return None

def get_hls_url_direct(youtube_url):
    """Direkt YouTube'dan HLS URL'sini al"""
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
            print(f"   ❌ Video ID bulunamadı: {youtube_url}")
            return None
        
        print(f"   📹 Video ID: {video_id}")
        
        # 1. Önce embed sayfasını dene
        embed_url = f"https://www.youtube.com/embed/{video_id}?autoplay=1"
        print(f"   🔄 Embed sayfası deneniyor: {embed_url}")
        html_content = get_youtube_page(embed_url)
        
        if html_content:
            hls_url = extract_hls_url(html_content)
            if hls_url:
                return hls_url
        
        # 2. Ana watch sayfasını dene
        watch_url = f"https://www.youtube.com/watch?v={video_id}"
        print(f"   🔄 Watch sayfası deneniyor: {watch_url}")
        html_content = get_youtube_page(watch_url)
        
        if html_content:
            hls_url = extract_hls_url(html_content)
            if hls_url:
                return hls_url
        
        # 3. get_video_info endpoint'ini dene (eski yöntem)
        info_url = f"https://www.youtube.com/get_video_info?video_id={video_id}&html5=1&c=TVHTML5&cver=7.20240101.00.00"
        print(f"   🔄 get_video_info deneniyor")
        try:
            response = requests.get(info_url, timeout=10)
            if response.status_code == 200:
                params = dict(x.split('=') for x in response.text.split('&') if '=' in x)
                if 'player_response' in params:
                    player_response = unquote(params['player_response'])
                    try:
                        data = json.loads(player_response)
                        if 'streamingData' in data and 'hlsManifestUrl' in data['streamingData']:
                            hls_url = data['streamingData']['hlsManifestUrl']
                            print("   ✅ get_video_info'den URL bulundu")
                            return hls_url
                    except:
                        pass
        except Exception as e:
            print(f"   ⚠️ get_video_info hatası: {str(e)[:50]}")
        
        return None
        
    except Exception as e:
        print(f"   ❌ Direkt yöntem hatası: {e}")
        return None

def m3u_dosyasi_olustur(kanallar):
    """M3U dosyasını oluştur"""
    m3u_icerik = "#EXTM3U x-tvg-url=\"https://github.com/botallen/epg/releases/download/latest/epg.xml\"\n"
    basarili_kanallar = 0
    
    for kanal in kanallar:
        if 'hls_url' in kanal and kanal['hls_url']:
            # URL'yi temizle
            hls_url = kanal['hls_url'].strip()
            if '\\' in hls_url:
                hls_url = hls_url.replace('\\', '')
            
            m3u_icerik += f'#EXTINF:-1 tvg-id="{kanal["isim"].replace(" ", "")}" tvg-name="{kanal["isim"]}" tvg-logo="{kanal["logo"]}" group-title="YouTube",{kanal["isim"]}\n'
            m3u_icerik += f'{hls_url}\n'
            basarili_kanallar += 1
            print(f"   ✅ {kanal['isim']} - HLS URL eklendi")
    
    try:
        with open('youtube.m3u', 'w', encoding='utf-8') as dosya:
            dosya.write(m3u_icerik)
        print(f"✅ youtube.m3u dosyası oluşturuldu ({basarili_kanallar} kanal)")
        return basarili_kanallar
    except Exception as e:
        print(f"❌ M3U dosyası yazılamadı: {e}")
        return 0

def main():
    print("=" * 60)
    print("🚀 YENİ YOUTUBE M3U GENERATOR - PROXY'SİZ SÜRÜM")
    print("=" * 60)
    
    # 1. links.txt dosyasını oku
    kanallar = links_dosyasini_oku()
    if not kanallar:
        print("❌ İşlem iptal edildi: Kanallar bulunamadı")
        return
    
    # 2. Her kanal için HLS URL'sini al
    print("\n" + "=" * 60)
    print("📡 HLS URL'LERİ ALINIYOR...")
    print("=" * 60)
    
    for idx, kanal in enumerate(kanallar, 1):
        print(f"\n🎬 [{idx}/{len(kanallar)}] KANAL: {kanal['isim']}")
        print(f"   🔗 URL: {kanal['icerik'][:80]}...")
        
        hls_url = get_hls_url_direct(kanal['icerik'])
        
        if hls_url:
            kanal['hls_url'] = hls_url
            print(f"   ✅ BAŞARILI - HLS URL: {hls_url[:100]}...")
        else:
            kanal['hls_url'] = None
            print(f"   ❌ BAŞARISIZ - HLS URL bulunamadı")
    
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
        print("🔍 YouTube'un API yapısı değişmiş olabilir")

if __name__ == "__main__":
    main()
