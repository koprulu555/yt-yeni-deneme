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
        e
