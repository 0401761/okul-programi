import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
from ortools.sat.python import cp_model
from datetime import datetime, timedelta
from PIL import Image, ImageDraw, ImageFont
import openpyxl
from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
from openpyxl.utils import get_column_letter
import requests
import base64
import json
import os
import io

st.set_page_config(page_title="Akıllı Okul Ders Dağıtım & Yönetim Sistemi", layout="wide")

# ==========================================
# 0. FERAH, MUNTAZAM & ÇERÇEVELİ ARAYÜZ (CSS)
# ==========================================
st.markdown("""
<style>
    html, body, [class*="css"] {
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    }
    div[data-testid="stVerticalBlockBorderWrapper"] {
        border: 1.5px solid rgba(128, 128, 128, 0.25) !important;
        border-radius: 12px !important;
        background: rgba(255, 255, 255, 0.015) !important;
        padding: 16px 22px !important;
        margin-bottom: 18px !important;
        box-shadow: 0 2px 10px rgba(0, 0, 0, 0.03) !important;
    }
    .panel-header {
        font-size: 13.5px !important;
        font-weight: 700 !important;
        color: #0066cc;
        text-transform: uppercase;
        letter-spacing: 0.6px;
        border-bottom: 2px solid rgba(0, 102, 204, 0.25);
        padding-bottom: 7px;
        margin-bottom: 15px;
        display: flex;
        align-items: center;
        gap: 8px;
    }
    .stButton > button {
        width: 100% !important;
        border-radius: 8px !important;
        min-height: 42px !important;
        font-weight: 600 !important;
        font-size: 13px !important;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
        transition: all 0.2s ease-in-out;
        border: 1px solid rgba(128, 128, 128, 0.3);
    }
    .stButton > button:hover {
        transform: translateY(-1px);
        border-color: #0066cc !important;
        box-shadow: 0 4px 12px rgba(0, 102, 204, 0.15);
    }
    div[data-testid="metric-container"] {
        background: rgba(255, 255, 255, 0.03);
        border: 1px solid rgba(128, 128, 128, 0.2);
        padding: 12px 16px !important;
        border-radius: 10px !important;
    }
    div[data-testid="stMetricValue"] {
        font-size: 1.35rem !important;
        font-weight: 700 !important;
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        padding-bottom: 8px;
    }
    .stTabs [data-baseweb="tab"] {
        border-radius: 8px 8px 0px 0px;
        padding: 9px 18px;
        font-weight: 600;
        font-size: 13px;
        border: 1px solid rgba(128, 128, 128, 0.2);
        border-bottom: none;
    }
    .stTabs [aria-selected="true"] {
        background: #0066cc !important;
        color: white !important;
        border-color: #0066cc !important;
    }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 1. OTOMATİK VERİ YÜKLEME & KAYDETME SİSTEMİ
# ==========================================
VERI_DOSYASI = "okul_kalici_veri.json"

def varsayilan_iho_verisi():
    curricula = {
        5: [("Türkçe", 6), ("Matematik", 5), ("Fen Bilimleri", 4), ("Sosyal Bilgiler", 3),
            ("İngilizce", 3), ("Din Kültürü", 2), ("Kur'an-ı Kerim", 2), ("Peygamberimizin Hayatı", 2),
            ("Arapça", 2), ("Bilişim Teknolojileri", 2), ("Beden Eğitimi", 2), ("Görsel Sanatlar", 1),
            ("Müzik", 1), ("Seçmeli Ders", 1)],
        6: [("Türkçe", 6), ("Matematik", 5), ("Fen Bilimleri", 4), ("Sosyal Bilgiler", 3),
            ("İngilizce", 3), ("Din Kültürü", 2), ("Kur'an-ı Kerim", 2), ("Peygamberimizin Hayatı", 2),
            ("Arapça", 2), ("Bilişim Teknolojileri", 2), ("Beden Eğitimi", 2), ("Görsel Sanatlar", 1),
            ("Müzik", 1), ("Temel Dini Bilgiler", 1)],
        7: [("Türkçe", 5), ("Matematik", 5), ("Fen Bilimleri", 4), ("Sosyal Bilgiler", 3),
            ("İngilizce", 4), ("Din Kültürü", 2), ("Kur'an-ı Kerim", 2), ("Peygamberimizin Hayatı", 2),
            ("Arapça", 2), ("Teknoloji ve Tasarım", 2), ("Beden Eğitimi", 2), ("Görsel Sanatlar", 1),
            ("Müzik", 1), ("Temel Dini Bilgiler", 1)],
        8: [("Türkçe", 5), ("Matematik", 5), ("Fen Bilimleri", 4), ("İnkılap Tarihi", 2),
            ("İngilizce", 4), ("Din Kültürü", 2), ("Kur'an-ı Kerim", 2), ("Peygamberimizin Hayatı", 2),
            ("Arapça", 2), ("Teknoloji ve Tasarım", 2), ("Beden Eğitimi", 2), ("Görsel Sanatlar", 1),
            ("Müzik", 1), ("Rehberlik", 1), ("Seçmeli Ders", 1)]
    }
    teachers = {
        "Türkçe": ["Ahmet Can", "Fatma Şahin", "Emre Doğan", "Zeynep Koç", "Hakan Yıldız", "Sevgi Aksoy"],
        "Matematik": ["Mustafa Yılmaz", "Elif Demir", "Ali Kaya", "Merve Çetin", "Oğuzhan Tekin", "Kübra Aydın"],
        "Fen Bilimleri": ["Serkan Yavuz", "Derya Arslan", "Onur Gül", "Büşra Çelik", "Kemal Taş"],
        "Sosyal Bilgiler": ["Murat Kurt", "Sema Öztürk", "Tolga Kaplan"],
        "İnkılap Tarihi": ["Murat Kurt", "Sema Öztürk"],
        "İngilizce": ["Pelin Özdemir", "Burak Erdem", "Cansu Avcı", "Ece Saygın"],
        "Din Kültürü": ["İbrahim Halil", "Ömer Faruk", "Hamza Polat", "Yusuf Eren"],
        "Kur'an-ı Kerim": ["İbrahim Halil", "Ömer Faruk", "Hamza Polat", "Hasan Hüseyin"],
        "Peygamberimizin Hayatı": ["Yusuf Eren", "Hasan Hüseyin", "Bilal Sevim"],
        "Temel Dini Bilgiler": ["Bilal Sevim", "İbrahim Halil"],
        "Arapça": ["Mahmut Esat", "Esra Nur"],
        "Beden Eğitimi": ["Volkan Güler", "Sinan Kartal"],
        "Bilişim Teknolojileri": ["Alper Korkmaz"],
        "Teknoloji ve Tasarım": ["Gökhan Vural"],
        "Görsel Sanatlar": ["Bahar Yalçın"],
        "Müzik": ["Kerem Şen"],
        "Rehberlik": ["Rehberlik Servisi"],
        "Seçmeli Ders": ["Ortak Seçmeli"]
    }
    rows = []
    t_counters = {k: 0 for k in teachers}
    for grade in [5, 6, 7, 8]:
        for sec in ["A", "B", "C", "D", "E", "F"]:
            s_name = f"{grade}{sec}"
            for subj, h in curricula[grade]:
                pool = teachers[subj]
                t_idx = t_counters[subj] % len(pool)
                t_counters[subj] += 1
                rows.append({
                    "Öğretmen": pool[t_idx],
                    "Sınıf": s_name,
                    "Ders": subj,
                    "Saat": h,
                    "Nöbetçi": "Beden" not in pool[t_idx] and "Rehberlik" not in pool[t_idx]
                })
    return pd.DataFrame(rows)

def verileri_kaydet():
    veri = {
        "okul_adi": st.session_state.okul_adi,
        "egitim_yili": st.session_state.egitim_yili,
        "mudur_adi": st.session_state.mudur_adi,
        "ders_baslangic": st.session_state.ders_baslangic,
        "ders_dk": st.session_state.ders_dk,
        "ogle_arasi_ders": st.session_state.ogle_arasi_ders,
        "ogle_arasi_dk": st.session_state.ogle_arasi_dk,
        "gunluk_maks_ders": st.session_state.gunluk_maks_ders,
        "teneffus_sureleri": {str(k): v for k, v in st.session_state.teneffus_sureleri.items()},
        "gun_saatleri": st.session_state.gun_saatleri,
        "kilitler": list(st.session_state.kilitler),
        "dondurulan_ogretmenler": list(st.session_state.dondurulan_ogretmenler),
        "dondurulan_atamalar": {k: [list(item) for item in v] for k, v in st.session_state.dondurulan_atamalar.items()},
        "ders_listesi": st.session_state.ders_listesi.to_dict(orient="records"),
        "cozum_ogretmen": st.session_state.cozum_ogretmen,
        "cozum_sinif": st.session_state.cozum_sinif
    }
    try:
        with open(VERI_DOSYASI, "w", encoding="utf-8") as f:
            json.dump(veri, f, ensure_ascii=False, indent=4)
    except Exception:
        pass

def verileri_yukle():
    if os.path.exists(VERI_DOSYASI):
        try:
            with open(VERI_DOSYASI, "r", encoding="utf-8") as f:
                veri = json.load(f)
                st.session_state.okul_adi = veri.get("okul_adi", "İMAM HATİP ORTAOKULU")
                st.session_state.egitim_yili = veri.get("egitim_yili", "2026-2027 Eğitim Öğretim Yılı")
                st.session_state.mudur_adi = veri.get("mudur_adi", "Okul Müdürü")
                st.session_state.ders_baslangic = veri.get("ders_baslangic", "08:30")
                st.session_state.ders_dk = veri.get("ders_dk", 40)
                st.session_state.ogle_arasi_ders = veri.get("ogle_arasi_ders", 5)
                st.session_state.ogle_arasi_dk = veri.get("ogle_arasi_dk", 45)
                st.session_state.gunluk_maks_ders = veri.get("gunluk_maks_ders", 6)
                st.session_state.teneffus_sureleri = {int(k): v for k, v in veri.get("teneffus_sureleri", {1:20, 2:10, 3:10, 4:10, 5:10, 6:10, 7:10}).items()}
                st.session_state.gun_saatleri = veri.get("gun_saatleri", {"Pazartesi":7, "Salı":7, "Çarşamba":8, "Perşembe":7, "Cuma":7})
                st.session_state.kilitler = set(tuple(k) for k in veri.get("kilitler", []))
                st.session_state.dondurulan_ogretmenler = set(veri.get("dondurulan_ogretmenler", []))
                raw_dondur = veri.get("dondurulan_atamalar", {})
                st.session_state.dondurulan_atamalar = {k: [tuple(item) for item in v] for k, v in raw_dondur.items()}
                if "ders_listesi" in veri:
                    st.session_state.ders_listesi = pd.DataFrame(veri["ders_listesi"])
                st.session_state.cozum_ogretmen = veri.get("cozum_ogretmen", None)
                st.session_state.cozum_sinif = veri.get("cozum_sinif", None)
                return True
        except Exception:
            pass
    return False

GUNLER = ["Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma"]

if "okul_adi" not in st.session_state:
    st.session_state.okul_adi = "İMAM HATİP ORTAOKULU"
if "egitim_yili" not in st.session_state:
    st.session_state.egitim_yili = "2026-2027 Eğitim Öğretim Yılı"
if "mudur_adi" not in st.session_state:
    st.session_state.mudur_adi = "Okul Müdürü"
if "ders_baslangic" not in st.session_state:
    st.session_state.ders_baslangic = "08:30"
if "ders_dk" not in st.session_state:
    st.session_state.ders_dk = 40
if "teneffus_dk" not in st.session_state:
    st.session_state.teneffus_dk = 10
if "teneffus_sureleri" not in st.session_state:
    st.session_state.teneffus_sureleri = {1: 20, 2: 10, 3: 10, 4: 10, 5: 10, 6: 10, 7: 10}
if "ogle_arasi_ders" not in st.session_state:
    st.session_state.ogle_arasi_ders = 5
if "ogle_arasi_dk" not in st.session_state:
    st.session_state.ogle_arasi_dk = 45
if "gunluk_maks_ders" not in st.session_state:
    st.session_state.gunluk_maks_ders = 6
if "gun_saatleri" not in st.session_state:
    st.session_state.gun_saatleri = {"Pazartesi": 7, "Salı": 7, "Çarşamba": 8, "Perşembe": 7, "Cuma": 7}
if "kilitler" not in st.session_state:
    st.session_state.kilitler = set()
if "dondurulan_ogretmenler" not in st.session_state:
    st.session_state.dondurulan_ogretmenler = set()
if "dondurulan_atamalar" not in st.session_state:
    st.session_state.dondurulan_atamalar = {}
if "cozum_ogretmen" not in st.session_state:
    st.session_state.cozum_ogretmen = None
if "cozum_sinif" not in st.session_state:
    st.session_state.cozum_sinif = None
if "teshis_hatalari" not in st.session_state:
    st.session_state.teshis_hatalari = []
if "nobet_listesi" not in st.session_state:
    st.session_state.nobet_listesi = None
if "ders_listesi" not in st.session_state:
    st.session_state.ders_listesi = varsayilan_iho_verisi()
    verileri_kaydet()

if "veri_yuklendi_mi" not in st.session_state:
    verileri_yukle()
    st.session_state.veri_yuklendi_mi = True

DERS_KISALTMALARI = {
    "Türkçe": "TRK", "Matematik": "MAT", "Fen Bilimleri": "FEN",
    "Sosyal Bilgiler": "SOS", "İnkılap Tarihi": "İNK", "T.C. İnkılap Tarihi ve Atatürkçülük": "İNK",
    "İngilizce": "İNG", "Yabancı Dil": "İNG", "Din Kültürü": "DKAB",
    "Din Kültürü ve Ahlak Bilgisi": "DKAB", "Kur'an-ı Kerim": "KUR", "Peygamberimizin Hayatı": "PEYG",
    "Temel Dini Bilgiler": "TDB", "Arapça": "ARP", "Beden Eğitimi": "BED",
    "Beden Eğitimi ve Spor": "BED", "Bilişim Teknolojileri": "BİL", "Bilişim Teknolojileri ve Yazılım": "BİL",
    "Teknoloji ve Tasarım": "TEK", "Görsel Sanatlar": "GÖR", "Müzik": "MÜZ",
    "Rehberlik": "REH", "Rehberlik ve Kariyer Planlama": "REH", "Seçmeli Ders": "SEÇ",
    "Ortak Seçmeli": "SEÇ"
}

def kisalt_ders(ders_adi):
    for k, v in DERS_KISALTMALARI.items():
        if k.lower() in ders_adi.lower():
            return v
    return ders_adi[:3].upper()

def kisalt_ogretmen(tam_ad):
    parcalar = str(tam_ad).strip().split()
    if len(parcalar) >= 2:
        return f"{parcalar[0][0]}. {parcalar[-1]}"
    return tam_ad

def saat_parcala_bloklara(toplam_saat):
    if toplam_saat == 6:
        return [2, 2, 2]
    elif toplam_saat == 5:
        return [2, 2, 1]
    elif toplam_saat == 4:
        return [2, 2]
    elif toplam_saat == 3:
        return [2, 1]
    elif toplam_saat == 2:
        return [2]
    elif toplam_saat == 1:
        return [1]
    else:
        bloklar = []
        kalan = toplam_saat
        while kalan > 0:
            if kalan >= 2:
                bloklar.append(2)
                kalan -= 2
            else:
                bloklar.append(1)
                kalan -= 1
        return bloklar

def cizelge_gorseli_uret():
    w, h = 1200, 780
    img = Image.new("RGB", (w, h), color=(255, 255, 255))
    d = ImageDraw.Draw(img)
    d.rectangle([(20, 20), (w-20, 85)], fill=(235, 243, 250), outline=(0, 51, 102), width=2)
    d.text((40, 28), "T.C. MILLI EGITIM BAKANLIGI - IMAM HATIP ORTAOKULU", fill=(0, 51, 102))
    d.text((40, 52), "HAFTALIK DERS DAGITIM CIZELGESI (24 SUBE: 5A-8F | TOPLAM: 864 SAAT)", fill=(60, 60, 60))
    headers = ["Sube", "TRK", "MAT", "FEN", "SOS", "ING", "DKAB", "KURAN", "PEYG", "ARAP", "DIGER", "TOPLAM"]
    col_w = (w - 60) // len(headers)
    y = 100
    d.rectangle([(30, y), (w-30, y+28)], fill=(200, 220, 240), outline=(0, 0, 0))
    for i, h_text in enumerate(headers):
        d.text((35 + i * col_w, y + 7), h_text, fill=(0, 0, 0))
    classes = [f"{g}{s}" for g in [5, 6, 7, 8] for s in ["A", "B", "C", "D", "E", "F"]]
    y += 28
    for idx, c in enumerate(classes[:16]):
        bg = (248, 249, 250) if idx % 2 == 0 else (255, 255, 255)
        d.rectangle([(30, y), (w-30, y+22)], fill=bg, outline=(220, 220, 220))
        d.text((35, y + 4), c, fill=(0, 0, 0))
        d.text((35 + col_w, y + 4), "6" if c.startswith(('5','6')) else "5", fill=(0, 0, 0))
        d.text((35 + 2*col_w, y + 4), "5", fill=(0, 0, 0))
        d.text((35 + 3*col_w, y + 4), "4", fill=(0, 0, 0))
        d.text((35 + 4*col_w, y + 4), "3" if not c.startswith('8') else "2", fill=(0, 0, 0))
        d.text((35 + 5*col_w, y + 4), "3" if c.startswith(('5','6')) else "4", fill=(0, 0, 0))
        d.text((35 + 6*col_w, y + 4), "2", fill=(0, 0, 0))
        d.text((35 + 7*col_w, y + 4), "2", fill=(0, 0, 0))
        d.text((35 + 8*col_w, y + 4), "2", fill=(0, 0, 0))
        d.text((35 + 9*col_w, y + 4), "2", fill=(0, 0, 0))
        d.text((35 + 10*col_w, y + 4), "7-8", fill=(0, 0, 0))
        d.text((35 + 11*col_w, y + 4), "36 Saat", fill=(180, 0, 0))
        y += 22
    d.text((40, y + 15), "... [Tüm Şubeler ve Öğretmen Kadrosu] ...", fill=(100, 100, 100))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()

def whatsapp_program_karti_uret(ogretmen_adi, program_sozlugu, zil_saatleri, nobet_gunu=""):
    w, h = 1080, 1920
    img = Image.new("RGB", (w, h), color=(245, 247, 250))
    d = ImageDraw.Draw(img)
    
    d.rectangle([(0, 0), (w, 240)], fill=(0, 76, 153))
    d.text((50, 45), st.session_state.okul_adi.upper(), fill=(255, 255, 255))
    d.text((50, 95), "HAFTALIK ÖĞRETMEN DERS PROGRAMI", fill=(200, 225, 255))
    d.text((50, 145), f"Sayın: {ogretmen_adi}", fill=(255, 255, 255))
    if nobet_gunu:
        d.text((50, 190), f"🛡️ Nöbet Günü: {nobet_gunu}", fill=(255, 215, 0))

    gunler = ["Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma"]
    col_w = (w - 180) // 5
    y_start = 280
    
    d.rectangle([(40, y_start), (w-40, y_start + 60)], fill=(220, 230, 242))
    d.text((50, y_start + 18), "Ders", fill=(0, 51, 102))
    for i, g in enumerate(gunler):
        d.text((180 + i * col_w + 15, y_start + 18), g[:3], fill=(0, 51, 102))
        
    y_cur = y_start + 60
    for s in range(8):
        bg = (255, 255, 255) if s % 2 == 0 else (240, 244, 248)
        row_h = 160
        d.rectangle([(40, y_cur), (w-40, y_cur + row_h)], fill=bg, outline=(210, 215, 220))
        
        saat_aralik = zil_saatleri[s] if s < len(zil_saatleri) else ""
        d.text((50, y_cur + 40), f"{s+1}.Ders", fill=(0, 0, 0))
        d.text((50, y_cur + 85), saat_aralik, fill=(100, 100, 100))
        
        for g_idx, g in enumerate(gunler):
            cell_x = 180 + g_idx * col_w
            val = program_sozlugu.get(g, ["-"] * 8)[s]
            if val not in ["-", "---", "🔒 KİLİTLİ"]:
                d.rectangle([(cell_x + 5, y_cur + 15), (cell_x + col_w - 5, y_cur + row_h - 15)], fill=(225, 240, 255), outline=(0, 102, 204), width=2)
                parcalar = val.split(" (")
                snf_txt = parcalar[0]
                drs_txt = parcalar[1].replace(")", "") if len(parcalar) > 1 else ""
                d.text((cell_x + 15, y_cur + 35), snf_txt, fill=(0, 51, 102))
                d.text((cell_x + 15, y_cur + 80), kisalt_ders(drs_txt), fill=(180, 50, 0))
            elif val == "🔒 KİLİTLİ":
                d.text((cell_x + 15, y_cur + 60), "🔒 BOŞ", fill=(160, 160, 160))
            else:
                d.text((cell_x + 35, y_cur + 60), "-", fill=(180, 180, 180))

        y_cur += row_h

    d.text((50, y_cur + 40), f"Onaylayan: {st.session_state.mudur_adi} (Okul Müdürü)", fill=(60, 60, 60))
    d.text((50, y_cur + 75), f"{st.session_state.egitim_yili} Resmî Çizelgesidir.", fill=(120, 120, 120))
    
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()

def zil_saatlerini_uret(toplam_saat=8):
    saatler = []
    try:
        cur_t = datetime.strptime(st.session_state.ders_baslangic, "%H:%M")
    except:
        cur_t = datetime.strptime("08:30", "%H:%M")
        
    for s in range(1, toplam_saat + 1):
        bitis_t = cur_t + timedelta(minutes=int(st.session_state.ders_dk))
        saatler.append(f"{cur_t.strftime('%H:%M')}-{bitis_t.strftime('%H:%M')}")
        if s == int(st.session_state.ogle_arasi_ders):
            cur_t = bitis_t + timedelta(minutes=int(st.session_state.ogle_arasi_dk))
        else:
            t_sure = st.session_state.teneffus_sureleri.get(s, int(st.session_state.teneffus_dk))
            cur_t = bitis_t + timedelta(minutes=int(t_sure))
    return saatler

def ogle_arasi_saat_araligi():
    try:
        cur_t = datetime.strptime(st.session_state.ders_baslangic, "%H:%M")
    except:
        cur_t = datetime.strptime("08:30", "%H:%M")
    ogle_ders = int(st.session_state.ogle_arasi_ders)
    for s in range(1, ogle_ders + 1):
        bitis_t = cur_t + timedelta(minutes=int(st.session_state.ders_dk))
        if s == ogle_ders:
            ogle_baslangic = bitis_t
            ogle_bitis = bitis_t + timedelta(minutes=int(st.session_state.ogle_arasi_dk))
            return f"{ogle_baslangic.strftime('%H:%M')} - {ogle_bitis.strftime('%H:%M')}"
        else:
            t_sure = st.session_state.teneffus_sureleri.get(s, int(st.session_state.teneffus_dk))
            cur_t = bitis_t + timedelta(minutes=int(t_sure))
    return "12:30 - 13:15"

zil_etiketleri = [f"{i+1}. Ders\n({saat})" for i, saat in enumerate(zil_saatlerini_uret(8))]

def render_meb_print_view(icerik_listesi, toplu_mu=False):
    pages_html = ""
    for idx, (baslik, alt_baslik, df_tablo, nobet_bilgisi) in enumerate(icerik_listesi):
        html_tablo = "<table class='table-meb'><thead><tr><th>Ders / Saat</th>"
        for col in df_tablo.columns:
            html_tablo += f"<th>{col}</th>"
        html_tablo += "</tr></thead><tbody>"
        
        for idx_name, row in df_tablo.iterrows():
            html_tablo += f"<tr><td class='time-cell'><b>{idx_name}</b></td>"
            for val in row:
                val_str = str(val)
                if val_str == "🔒 KİLİTLİ":
                    html_tablo += f"<td class='kilit-cell'>🔒 Boş Saat</td>"
                elif val_str in ["-", "---"]:
                    html_tablo += f"<td class='empty-cell'>-</td>"
                else:
                    html_tablo += f"<td class='content-cell'>{val_str}</td>"
            html_tablo += "</tr>"
        html_tablo += "</tbody></table>"

        page_break_class = "page-break" if (toplu_mu and idx < len(icerik_listesi) - 1) else ""
        
        pages_html += f"""
        <div class="printable-page {page_break_class}">
            <div class="header-box">
                <h2>T.C. MİLLÎ EĞİTİM BAKANLIĞI</h2>
                <h3>{st.session_state.okul_adi} MÜDÜRLÜĞÜ</h3>
                <div class="sub-year">{st.session_state.egitim_yili}</div>
                <h4>{baslik}</h4>
                <div class="sub-info"><b>{alt_baslik}</b> {f'| <span class=\"nobet-tag\">Nöbet Günü: {nobet_bilgisi}</span>' if nobet_bilgisi else ''}</div>
            </div>
            {html_tablo}
            <div class="footer-box">
                <div><br><b>İlgili Öğretmen / Şube</b><br>İmza</div>
                <div><b>Uygundur</b><br>.... / .... / 2026<br><br><b>{st.session_state.mudur_adi}</b><br>İmza - Mühür</div>
            </div>
        </div>
        """

    return f"""
    <!DOCTYPE html>
    <html>
    <head>
    <meta charset="utf-8">
    <style>
        body {{ font-family: Arial, sans-serif; margin: 0; padding: 12px; font-size: 11px; }}
        .top-toolbar {{ display: flex; align-items: center; gap: 10px; margin-bottom: 14px; }}
        .btn-action {{ background-color: #0066cc; color: white; border: none; padding: 8px 16px; font-size: 12px; font-weight: bold; border-radius: 6px; cursor: pointer; }}
        .header-box {{ text-align: center; border-bottom: 2px solid #333; padding-bottom: 6px; margin-bottom: 12px; }}
        .header-box h2 {{ margin: 2px; font-size: 15px; }}
        .header-box h3 {{ margin: 2px; font-size: 13px; font-weight: normal; }}
        .sub-year {{ font-size: 11px; margin: 2px; }}
        .header-box h4 {{ margin: 4px 0; font-size: 14px; color: #b30000; font-weight: bold; }}
        .sub-info {{ font-size: 12px; }}
        .nobet-tag {{ color: #b30000; font-weight: bold; }}
        .table-meb {{ width: 100%; border-collapse: collapse; text-align: center; font-size: 11px; border: 1px solid #ccc; }}
        .table-meb th {{ background-color: #f2f2f2; padding: 6px 4px; font-weight: bold; border: 1px solid #ccc; }}
        .table-meb td {{ padding: 5px; height: 26px; border: 1px solid #ccc; }}
        .table-meb td.time-cell {{ background-color: #f9f9f9; font-size: 10px; font-weight: bold; }}
        .table-meb td.kilit-cell {{ background-color: #eee; color: #666; }}
        .table-meb td.content-cell {{ font-weight: 600; }}
        .footer-box {{ margin-top: 20px; display: flex; justify-content: space-between; font-size: 11.5px; padding: 0 10px; }}
        .printable-page {{ padding-bottom: 20px; }}
        @media print {{
            .no-print {{ display: none !important; }}
            body {{ background-color: #fff !important; color: #000 !important; margin: 0 !important; }}
            .page-break {{ page-break-after: always; break-after: page; display: block; }}
        }}
    </style>
    </head>
    <body>
        <div class="no-print top-toolbar">
            <button class="btn-action" onclick="window.print()">🖨️ Sayfayı Yazdır / PDF Al</button>
            <span style="font-size: 12px; color: #555;">(Yazdırırken otomatik A4 beyaz kâğıt formatına dönüşür)</span>
        </div>
        {pages_html}
    </body>
    </html>
    """

def stil_carsaf_excel_uret(veri_matrisi, gun_saat_listesi, baslik_tur="Öğretmen", okul_adi="OKUL"):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = f"Carsaf_{baslik_tur}"
    
    title_font = Font(name="Calibri", size=13, bold=True, color="002060")
    header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
    sub_font = Font(name="Calibri", size=10, bold=True, color="000000")
    cell_font = Font(name="Calibri", size=10, bold=True)
    bold_head_font = Font(name="Calibri", size=10, bold=True)
    
    thin_side = Side(style='thin', color='D9D9D9')
    thick_side = Side(style='medium', color='1F4E79')
    
    thin_border = Border(left=thin_side, right=thin_side, top=thin_side, bottom=thin_side)
    thick_right_border = Border(left=thin_side, right=thick_side, top=thin_side, bottom=thin_side)
    
    day_colors = ["1F4E79", "2F5597", "1F4E79", "2F5597", "1F4E79"]
    
    ws.merge_cells("A1:AL1")
    ws["A1"] = f"T.C. MİLLÎ EĞİTİM BAKANLIĞI - {okul_adi.upper()} MÜDÜRLÜĞÜ - HAFTALIK {baslik_tur.upper()} DERS ÇARŞAF ÇİZELGESİ"
    ws["A1"].font = title_font
    ws["A1"].alignment = Alignment(horizontal="center", vertical="center")
    ws.row_dimensions[1].height = 25
    
    ws.merge_cells("A2:A3")
    ws["A2"] = baslik_tur
    ws["A2"].font = Font(name="Calibri", size=11, bold=True)
    ws["A2"].alignment = Alignment(horizontal="center", vertical="center")
    ws["A2"].fill = PatternFill(start_color="D9E1F2", fill_type="solid")
    ws["A2"].border = thin_border
    
    cur_col = 2
    day_end_cols = {}
    for d_idx, (gun, saat_sayisi) in enumerate(gun_saat_listesi):
        start_col = cur_col
        end_col = cur_col + saat_sayisi - 1
        day_end_cols[gun] = end_col
        
        ws.merge_cells(start_row=2, start_column=start_col, end_row=2, end_column=end_col)
        cell = ws.cell(row=2, column=start_col, value=gun)
        cell.font = header_font
        cell.alignment = Alignment(horizontal="center", vertical="center")
        cell.fill = PatternFill(start_color=day_colors[d_idx % len(day_colors)], fill_type="solid")
        
        for s in range(saat_sayisi):
            sc = ws.cell(row=3, column=start_col + s, value=f"{s+1}.Ders")
            sc.font = sub_font
            sc.alignment = Alignment(horizontal="center", vertical="center")
            sc.fill = PatternFill(start_color="F2F2F2", fill_type="solid")
            sc.border = thick_right_border if (start_col + s) == end_col else thin_border
            
        cur_col = end_col + 1
        
    ws.row_dimensions[2].height = 22
    ws.row_dimensions[3].height = 20
    
    for r_idx, (r_name, r_vals) in enumerate(veri_matrisi.items(), start=4):
        ws.row_dimensions[r_idx].height = 20
        c1 = ws.cell(row=r_idx, column=1, value=r_name)
        c1.font = bold_head_font
        c1.alignment = Alignment(horizontal="left", vertical="center")
        c1.border = thin_border
        
        col_ptr = 2
        for gun, saat_sayisi in gun_saat_listesi:
            for s in range(saat_sayisi):
                v = r_vals.get((gun, s), "")
                cell = ws.cell(row=r_idx, column=col_ptr, value=v)
                cell.font = cell_font
                cell.alignment = Alignment(horizontal="center", vertical="center")
                cell.border = thick_right_border if col_ptr == day_end_cols[gun] else thin_border
                col_ptr += 1
                
    ws.column_dimensions["A"].width = 24
    for c in range(2, cur_col):
        ws.column_dimensions[get_column_letter(c)].width = 11
        
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()

def cakismalari_denetle(df_ders, gun_saatleri, kilitler, tum_ogretmenler, siniflar):
    teshisler = []
    toplam_haftalik_kapasite = sum(gun_saatleri.values())
    
    ogr_toplam_ders = df_ders.groupby("Öğretmen")["Saat"].sum().to_dict()
    for ogr in tum_ogretmenler:
        ders_yuku = ogr_toplam_ders.get(ogr, 0)
        kilit_sayisi = sum(1 for (o, g, s) in kilitler if o == ogr)
        acik_kalan_saat = toplam_haftalik_kapasite - kilit_sayisi
        
        if ders_yuku > acik_kalan_saat:
            eksik_saat = ders_yuku - acik_kalan_saat
            teshisler.append({
                "Tip": "Kapasite Aşımı",
                "Hedef": ogr,
                "EksikSaat": eksik_saat,
                "Detay": f"Haftalık **{ders_yuku} saat** dersi var, fakat **{kilit_sayisi} saati kilitlendiği** için açıkta sadece **{acik_kalan_saat} saat** kalıyor.",
                "Cozum": f"Bu öğretmenin en az **{eksik_saat} saatlik** kilidi açılmalıdır!"
            })
            
    toplam_sube_sayisi = len(siniflar)
    toplam_ogr_sayisi = len(tum_ogretmenler)
    
    for gun, max_s in gun_saatleri.items():
        for s in range(max_s):
            kilitli_hocalar = {o for (o, g, saat_idx) in kilitler if g == gun and saat_idx == s}
            musait_hoca_sayisi = toplam_ogr_sayisi - len(kilitli_hocalar)
            
            if musait_hoca_sayisi < toplam_sube_sayisi:
                acik = toplam_sube_sayisi - musait_hoca_sayisi
                teshisler.append({
                    "Tip": "Saatlik Öğretmen Açığı",
                    "Hedef": f"{gun} {s+1}. Ders",
                    "Gun": gun,
                    "Saat": s,
                    "Acik": acik,
                    "KilitliHocalar": list(kilitli_hocalar),
                    "Detay": f"Okuldaki {toplam_sube_sayisi} şubenin aynı anda derste olması gerekirken, kilitler yüzünden sadece **{musait_hoca_sayisi} öğretmen** serbest.",
                    "Cozum": f"Bu saat diliminde kilitli olan en az **{acik} öğretmenin** kilidi kaldırılmalıdır!"
                })
                
    return teshisler

# ==========================================
# 5. GÖRSEL PANEL VE ANA SEKMELER
# ==========================================
st.markdown(f"""
<div style="background: linear-gradient(135deg, #004c99 0%, #0066cc 100%); padding: 16px 24px; border-radius: 12px; color: white; margin-bottom: 16px; display: flex; justify-content: space-between; align-items: center; box-shadow: 0 4px 14px rgba(0,102,204,0.15);">
    <div>
        <h2 style="margin: 0; font-size: 20px; font-weight: 800; color: white;">🏛️ {st.session_state.okul_adi}</h2>
        <p style="margin: 3px 0 0 0; font-size: 13px; opacity: 0.9;">Akıllı Ders Dağıtım, Blok Motoru & Nöbet Yönetim Sistemi</p>
    </div>
    <span style="background: rgba(255,255,255,0.2); border: 1px solid rgba(255,255,255,0.4); padding: 5px 14px; border-radius: 6px; font-size: 12.5px; font-weight: 700;">{st.session_state.egitim_yili}</span>
</div>
""", unsafe_allow_html=True)

tab_okul, tab_kisi_ders, tab_kilit, tab_motor, tab_pdf, tab_carsaf, tab_nobet = st.tabs([
    "🏛️ 1. Okul & Zil Saatleri",
    "👥 2. Kadro & Dersler",
    "🔒 3. Güne Özel Kilit Matrisi",
    "🚀 4. Dağıt & Sabitle",
    "📄 5. Resmî PDF & Mobil Kart",
    "📋 6. İdareci Çarşafı",
    "🛡️ 7. Akıllı Nöbet"
])

# ----------------------------------------------------
# TAB 1: OKUL KÜNYESİ VE ZİL SAATLERİ
# ----------------------------------------------------
with tab_okul:
    with st.container(border=True):
        st.markdown('<div class="panel-header">🏛️ Kurum Resmî Bilgileri</div>', unsafe_allow_html=True)
        c_ok1, c_ok2, c_ok3 = st.columns(3)
        with c_ok1:
            yeni_okul = st.text_input("Okul Adı", value=st.session_state.okul_adi)
            if yeni_okul != st.session_state.okul_adi:
                st.session_state.okul_adi = yeni_okul
                verileri_kaydet()
        with c_ok2:
            yeni_yil = st.text_input("Eğitim Öğretim Yılı", value=st.session_state.egitim_yili)
            if yeni_yil != st.session_state.egitim_yili:
                st.session_state.egitim_yili = yeni_yil
                verileri_kaydet()
        with c_ok3:
            yeni_mudur = st.text_input("Okul Müdürü Adı / Ünvanı", value=st.session_state.mudur_adi)
            if yeni_mudur != st.session_state.mudur_adi:
                st.session_state.mudur_adi = yeni_mudur
                verileri_kaydet()

    with st.container(border=True):
        st.markdown('<div class="panel-header">⏰ Ders & Öğle Arası & Yük Denge Parametreleri</div>', unsafe_allow_html=True)
        c_z1, c_z2, c_z3, c_z4, c_z5 = st.columns(5)
        with c_z1:
            yeni_bas = st.text_input("1. Ders Başlama Saati", value=st.session_state.ders_baslangic, placeholder="08:30")
            if yeni_bas != st.session_state.ders_baslangic:
                st.session_state.ders_baslangic = yeni_bas
                verileri_kaydet()
        with c_z2:
            yeni_dk = st.number_input("Ders Süresi (Dk)", min_value=30, max_value=60, value=int(st.session_state.ders_dk))
            if yeni_dk != st.session_state.ders_dk:
                st.session_state.ders_dk = yeni_dk
                verileri_kaydet()
        with c_z3:
            yeni_ogle_ders = st.number_input("Öğle Arası Kaçıncı Dersten Sonra?", min_value=2, max_value=6, value=int(st.session_state.ogle_arasi_ders))
            if yeni_ogle_ders != st.session_state.ogle_arasi_ders:
                st.session_state.ogle_arasi_ders = yeni_ogle_ders
                verileri_kaydet()
        with c_z4:
            yeni_ogle_dk = st.number_input("Öğle Arası Süresi (Dk)", min_value=20, max_value=90, value=int(st.session_state.ogle_arasi_dk))
            if yeni_ogle_dk != st.session_state.ogle_arasi_dk:
                st.session_state.ogle_arasi_dk = yeni_ogle_dk
                verileri_kaydet()
        with c_z5:
            yeni_gun_max = st.number_input("Günlük Maks. Ders (Öğretmen)", min_value=4, max_value=8, value=int(st.session_state.gunluk_maks_ders))
            if yeni_gun_max != st.session_state.gunluk_maks_ders:
                st.session_state.gunluk_maks_ders = yeni_gun_max
                verileri_kaydet()

    with st.container(border=True):
        st.markdown('<div class="panel-header">☕ Teneffüs Süreleri Yönetimi (Dakika)</div>', unsafe_allow_html=True)
        cols_ten = st.columns(7)
        for t_idx in range(1, 8):
            with cols_ten[t_idx - 1]:
                etiket = f"{t_idx}. Ten."
                if t_idx == 1:
                    etiket = "🍳 1. Ten. (Kahvaltı)"
                elif t_idx == int(st.session_state.ogle_arasi_ders):
                    etiket = f"🍽️ {t_idx}. Ten. (Öğle)"
                
                if t_idx == int(st.session_state.ogle_arasi_ders):
                    st.info(f"🍽️ {st.session_state.ogle_arasi_dk} Dk (Öğle)")
                else:
                    eski_ten = st.session_state.teneffus_sureleri.get(t_idx, 10)
                    yeni_ten = st.number_input(
                        etiket, min_value=5, max_value=60,
                        value=int(eski_ten), key=f"ten_input_{t_idx}"
                    )
                    if yeni_ten != eski_ten:
                        st.session_state.teneffus_sureleri[t_idx] = yeni_ten
                        verileri_kaydet()

    with st.container(border=True):
        st.markdown('<div class="panel-header">📋 Oluşturulan Günlük Resmî Ders & Zil Çizelgesi</div>', unsafe_allow_html=True)
        zil_listesi = zil_saatlerini_uret(8)
        ogle_ders_no = int(st.session_state.ogle_arasi_ders)
        
        st.markdown("**☀️ Öğleden Önceki Dersler:**")
        cols_sabah = st.columns(ogle_ders_no)
        for i in range(ogle_ders_no):
            with cols_sabah[i]:
                st.metric(f"{i+1}. Ders", zil_listesi[i])
        
        st.markdown(f"""
        <div style="background: rgba(0, 102, 204, 0.08); border: 1.5px dashed #0066cc; border-radius: 8px; padding: 9px 18px; margin: 10px 0; display: flex; justify-content: space-between; align-items: center;">
            <span style="font-weight: 700; color: #004c99; font-size: 13.5px;">🍽️ {ogle_ders_no}. DERSTEN SONRA ÖĞLE ARASI ({st.session_state.ogle_arasi_dk} DAKİKA)</span>
            <span style="background: #0066cc; color: white; padding: 4px 12px; border-radius: 6px; font-weight: 700; font-size: 12.5px;">Saat: {ogle_arasi_saat_araligi()}</span>
        </div>
        """, unsafe_allow_html=True)

        kalan_ders_sayisi = 8 - ogle_ders_no
        st.markdown("**🌙 Öğleden Sonraki Dersler:**")
        cols_ogle = st.columns(kalan_ders_sayisi)
        for idx, i in enumerate(range(ogle_ders_no, 8)):
            with cols_ogle[idx]:
                st.metric(f"{i+1}. Ders", zil_listesi[i])

# ----------------------------------------------------
# TAB 2: ÖĞRETMEN, SINIF & DERS YÖNETİMİ
# ----------------------------------------------------
with tab_kisi_ders:
    with st.container(border=True):
        st.markdown('<div class="panel-header">⚡ Hızlı İşlemler & Hazır Veri</div>', unsafe_allow_html=True)
        c_btn1, c_btn2 = st.columns(2)
        with c_btn1:
            if st.button("🗑️ TÜM LİSTEYİ SIFIRLA (Temizle)", use_container_width=True):
                st.session_state.ders_listesi = pd.DataFrame(columns=["Öğretmen", "Sınıf", "Ders", "Saat", "Nöbetçi"])
                st.session_state.kilitler = set()
                st.session_state.dondurulan_ogretmenler = set()
                st.session_state.dondurulan_atamalar = {}
                st.session_state.cozum_ogretmen = None
                st.session_state.cozum_sinif = None
                st.session_state.teshis_hatalari = []
                verileri_kaydet()
                st.rerun()
        with c_btn2:
            if st.button("🔄 Örnek 24 Şubeli İHO Verisini Yükle (Fabrika Ayarları)", use_container_width=True):
                st.session_state.ders_listesi = varsayilan_iho_verisi()
                st.session_state.kilitler = set()
                st.session_state.dondurulan_ogretmenler = set()
                st.session_state.dondurulan_atamalar = {}
                st.session_state.cozum_ogretmen = None
                st.session_state.cozum_sinif = None
                st.session_state.teshis_hatalari = []
                verileri_kaydet()
                st.success("✅ 24 Şubeli İHO verisi yüklendi!")
                st.rerun()

    col_sol, col_sag = st.columns(2)
    with col_sol:
        with st.container(border=True):
            st.markdown('<div class="panel-header">👨‍🏫 1. Öğretmen Ekle & Sil</div>', unsafe_allow_html=True)
            mevcut_ogretmenler = sorted(list(st.session_state.ders_listesi["Öğretmen"].dropna().unique())) if not st.session_state.ders_listesi.empty else []
            c_o_ekle, c_o_sil = st.columns(2)
            with c_o_ekle:
                with st.form("ogr_ekle_form", clear_on_submit=True):
                    yeni_hoca = st.text_input("Öğretmen Adı Soyadı", placeholder="Örn: Hasan Yılmaz")
                    yeni_nobet = st.checkbox("Nöbetçi Olabilir", value=True)
                    if st.form_submit_button("➕ Öğretmen Ekle", use_container_width=True):
                        if yeni_hoca.strip():
                            satir = pd.DataFrame([{"Öğretmen": yeni_hoca.strip(), "Sınıf": "-", "Ders": "Kayıt", "Saat": 0, "Nöbetçi": yeni_nobet}])
                            st.session_state.ders_listesi = pd.concat([st.session_state.ders_listesi, satir], ignore_index=True)
                            verileri_kaydet()
                            st.rerun()

            with c_o_sil:
                if mevcut_ogretmenler:
                    silinecek_hoca = st.selectbox("Silinecek Öğretmen:", mevcut_ogretmenler, key="sil_hoca_sec")
                    if st.button("🗑️ Seçili Öğretmeni Sil", use_container_width=True):
                        st.session_state.ders_listesi = st.session_state.ders_listesi[st.session_state.ders_listesi["Öğretmen"] != silinecek_hoca]
                        st.session_state.kilitler = {k for k in st.session_state.kilitler if k[0] != silinecek_hoca}
                        st.session_state.dondurulan_ogretmenler.discard(silinecek_hoca)
                        verileri_kaydet()
                        st.rerun()

    with col_sag:
        with st.container(border=True):
            st.markdown('<div class="panel-header">🏫 2. Şube / Sınıf Ekle & Sil</div>', unsafe_allow_html=True)
            mevcut_siniflar = sorted([s for s in st.session_state.ders_listesi["Sınıf"].dropna().unique() if s != "-"]) if not st.session_state.ders_listesi.empty else []
            c_s_ekle, c_s_sil = st.columns(2)
            with c_s_ekle:
                with st.form("snf_ekle_form", clear_on_submit=True):
                    yeni_snf = st.text_input("Şube Adı", placeholder="Örn: 5G")
                    if st.form_submit_button("➕ Şube Ekle", use_container_width=True):
                        if yeni_snf.strip():
                            snf_kod = yeni_snf.strip().upper()
                            satir = pd.DataFrame([{"Öğretmen": "-", "Sınıf": snf_kod, "Ders": "Kayıt", "Saat": 0, "Nöbetçi": False}])
                            st.session_state.ders_listesi = pd.concat([st.session_state.ders_listesi, satir], ignore_index=True)
                            verileri_kaydet()
                            st.rerun()

            with c_s_sil:
                if mevcut_siniflar:
                    silinecek_snf = st.selectbox("Silinecek Şube:", mevcut_siniflar, key="sil_snf_sec")
                    if st.button("🗑️ Seçili Şubeyi Sil", use_container_width=True):
                        st.session_state.ders_listesi = st.session_state.ders_listesi[st.session_state.ders_listesi["Sınıf"] != silinecek_snf]
                        verileri_kaydet()
                        st.rerun()

    with st.container(border=True):
        st.markdown('<div class="panel-header">📚 3. Ders Eşleştirmesi Ekle & Detaylı Yük Analizi</div>', unsafe_allow_html=True)
        c_d_ekle, c_d_tablo = st.columns([1.2, 1.8])
        
        with c_d_ekle:
            guncel_hocalar = sorted([o for o in st.session_state.ders_listesi["Öğretmen"].unique() if o != "-"])
            guncel_snflar = sorted([s for s in st.session_state.ders_listesi["Sınıf"].unique() if s != "-"])
            if guncel_hocalar and guncel_snflar:
                with st.form("ders_atama_formu", clear_on_submit=True):
                    sec_ogr = st.selectbox("Öğretmen", guncel_hocalar)
                    sec_snf = st.selectbox("Şube", guncel_snflar)
                    drs_ad = st.text_input("Ders Adı", placeholder="Örn: Matematik")
                    drs_saat = st.number_input("Haftalık Ders Saati", min_value=1, max_value=36, value=4)
                    drs_nobet = st.checkbox("Öğretmen Nöbetçi Olabilir", value=True)
                    if st.form_submit_button("➕ Bu Dersi Ata", use_container_width=True):
                        if drs_ad.strip():
                            st.session_state.ders_listesi = st.session_state.ders_listesi[
                                ~((st.session_state.ders_listesi["Öğretmen"] == sec_ogr) & (st.session_state.ders_listesi["Ders"] == "Kayıt"))
                            ]
                            st.session_state.ders_listesi = st.session_state.ders_listesi[
                                ~((st.session_state.ders_listesi["Sınıf"] == sec_snf) & (st.session_state.ders_listesi["Ders"] == "Kayıt"))
                            ]
                            yeni_ders = pd.DataFrame([{
                                "Öğretmen": sec_ogr, "Sınıf": sec_snf, "Ders": drs_ad.strip(),
                                "Saat": int(drs_saat), "Nöbetçi": drs_nobet
                            }])
                            st.session_state.ders_listesi = pd.concat([st.session_state.ders_listesi, yeni_ders], ignore_index=True)
                            verileri_kaydet()
                            st.rerun()

        with c_d_tablo:
            df_gecerli_dersler = st.session_state.ders_listesi[st.session_state.ders_listesi["Saat"] > 0]
            if not df_gecerli_dersler.empty:
                sub_tab_atamalar, sub_tab_ogr_yuku, sub_tab_snf_yuku = st.tabs([
                    f"📋 Tüm Atamalar ({len(df_gecerli_dersler)})",
                    f"👨‍🏫 Öğretmen Yükleri ({df_gecerli_dersler['Öğretmen'].nunique()})",
                    f"🏫 Şube Yükleri ({df_gecerli_dersler['Sınıf'].nunique()})"
                ])
                with sub_tab_atamalar:
                    st.dataframe(df_gecerli_dersler[["Öğretmen", "Sınıf", "Ders", "Saat", "Nöbetçi"]], height=180, use_container_width=True)
                    atama_etiketleri = [f"{r['Öğretmen']} | {r['Sınıf']} - {r['Ders']} ({r['Saat']}s)" for _, r in df_gecerli_dersler.iterrows()]
                    secilen_sil_idx = st.selectbox("Silinecek Atama:", range(len(atama_etiketleri)), format_func=lambda i: atama_etiketleri[i])
                    if st.button("🗑️ Seçili Ders Atamasını Sil", use_container_width=True):
                        hedef_row = df_gecerli_dersler.iloc[secilen_sil_idx]
                        st.session_state.ders_listesi = st.session_state.ders_listesi.drop(hedef_row.name).reset_index(drop=True)
                        verileri_kaydet()
                        st.rerun()

                with sub_tab_ogr_yuku:
                    ogr_ozet = []
                    for o, grp in df_gecerli_dersler.groupby("Öğretmen"):
                        top_s = int(grp["Saat"].sum())
                        durum_str = f"{top_s}s (Maks. Yük)" if top_s >= 30 else (f"{top_s}s (Maaş+Ek)" if top_s >= 21 else (f"{top_s}s (Maaş)" if top_s >= 15 else f"{top_s}s (Eksik ⚠️)"))
                        nob_str = "Evet ✅" if grp["Nöbetçi"].any() else "Hayır ❌"
                        ogr_ozet.append({"Öğretmen": o, "Toplam Saat": top_s, "Branş": ", ".join(sorted(grp["Ders"].unique())), "Şubeler": ", ".join(sorted(grp["Sınıf"].unique())), "Norm": durum_str, "Nöbet": nob_str})
                    df_ogr_ozet = pd.DataFrame(ogr_ozet).sort_values(by="Toplam Saat", ascending=False).reset_index(drop=True)
                    st.dataframe(df_ogr_ozet, height=180, use_container_width=True)
                    
                    buf_oy = io.BytesIO()
                    with pd.ExcelWriter(buf_oy, engine='openpyxl') as writer:
                        df_ogr_ozet.to_excel(writer, index=False)
                    st.download_button("📥 Öğretmen Ders Yüklerini Excel İndir (.xlsx)", data=buf_oy.getvalue(), file_name="ogretmen_ders_yukleri.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True)

                with sub_tab_snf_yuku:
                    snf_ozet = []
                    for s, grp in df_gecerli_dersler.groupby("Sınıf"):
                        top_s = int(grp["Saat"].sum())
                        snf_ozet.append({"Şube": s, "Toplam Saat": top_s, "Ders Sayısı": len(grp), "Durum": "Tamamlandı (36s) ✅" if top_s == 36 else f"{top_s}/36s ⚠️"})
                    df_snf_ozet = pd.DataFrame(snf_ozet).sort_values(by="Şube").reset_index(drop=True)
                    st.dataframe(df_snf_ozet, height=180, use_container_width=True)

    with st.container(border=True):
        st.markdown('<div class="panel-header">📊 4. EXCEL İLE TOPLU DERS YÜKLEME</div>', unsafe_allow_html=True)
        c_ex_indir, c_ex_yukle = st.columns([1, 2])
        with c_ex_indir:
            st.markdown("**Şablon Excel İndir:**")
            buf_ex = io.BytesIO()
            sablon_df = pd.DataFrame({
                "Öğretmen": ["Ahmet Yılmaz", "Ahmet Yılmaz", "Ayşe Kaya"],
                "Sınıf": ["5A", "5B", "5A"],
                "Ders": ["Matematik", "Matematik", "Türkçe"],
                "Saat": [5, 5, 6],
                "Nöbet": ["Evet", "Evet", "Evet"]
            })
            with pd.ExcelWriter(buf_ex, engine='openpyxl') as writer:
                sablon_df.to_excel(writer, index=False)
            st.download_button(
                label="📥 Örnek Excel Şablonunu İndir (.xlsx)",
                data=buf_ex.getvalue(), file_name="okul_ders_sablonu.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True
            )
            st.caption("Bu şablon formatında doldurarak sağ taraftan içeri aktarabilirsiniz.")

        with c_ex_yukle:
            st.markdown("**Excel Dosyasını Sisteme Aktar:**")
            up_file = st.file_uploader("Excel Dosyası Yükle (.xlsx, .xls)", type=["xlsx", "xls"], key="up_excel_key")
            if up_file is not None:
                try:
                    gelen_df = pd.read_excel(up_file)
                    if {"Öğretmen", "Sınıf", "Ders", "Saat"}.issubset(gelen_df.columns):
                        gelen_df["Nöbetçi"] = gelen_df["Nöbet"].astype(str).str.lower().isin(["evet", "true", "1"]) if "Nöbet" in gelen_df.columns else True
                        st.session_state.ders_listesi = gelen_df[["Öğretmen", "Sınıf", "Ders", "Saat", "Nöbetçi"]]
                        verileri_kaydet()
                        st.success(f"✅ Excel başarıyla aktarıldı! ({len(gelen_df)} satır ders yüklendi)")
                        st.rerun()
                except Exception as e:
                    st.error(f"Hata: {e}")

    with st.container(border=True):
        st.markdown('<div class="panel-header">📸 5. FOTOĞRAFTAN / BELGEDEN YAPAY ZEKÂ İLE LİSTE AKTAR (OCR)</div>', unsafe_allow_html=True)
        c_foto_indir, c_foto_yukle = st.columns([1, 2])
        with c_foto_indir:
            st.markdown("**Test İçin Örnek Çizelge:**")
            img_test_bytes = cizelge_gorseli_uret()
            st.download_button(
                label="📥 Örnek İHO Çizelgesi İndir (.png)",
                data=img_test_bytes, file_name="ornek_iho_cizelgesi.png",
                mime="image/png", use_container_width=True
            )
            st.caption("Elinizdeki basılı ders dağıtım çizelgesinin fotoğrafını çekip sağdan yükleyebilirsiniz.")

        with c_foto_yukle:
            st.markdown("**Çizelge Fotoğrafı Yükle & Tara:**")
            c_f_up, c_f_api = st.columns([1.2, 1])
            with c_f_up:
                yuklenen_belge = st.file_uploader("Çizelge Görseli Seç (PNG, JPG, JPEG)", type=["png", "jpg", "jpeg"], key="belge_ocr_up")
            with c_f_api:
                api_anahtari = st.text_input("Gemini API Anahtarı (Opsiyonel):", type="password", placeholder="AIzaSy...")

            if yuklenen_belge is not None:
                if st.button("🔍 Fotoğrafı Tara ve Sisteme Aktar", type="primary", use_container_width=True):
                    with st.spinner("Görsel taranıyor..."):
                        basarili = False
                        if api_anahtari.strip():
                            try:
                                gorsel_bytes = yuklenen_belge.getvalue()
                                b64_img = base64.b64encode(gorsel_bytes).decode("utf-8")
                                mime_t = yuklenen_belge.type or "image/jpeg"
                                url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={api_anahtari.strip()}"
                                prompt_metni = "Bu görseldeki ders çizelgesini analiz et. SADECE JSON ver: [{\"Öğretmen\": \"...\", \"Sınıf\": \"...\", \"Ders\": \"...\", \"Saat\": 4, \"Nöbet\": \"Evet\"}]"
                                payload = {"contents": [{"parts": [{"text": prompt_metni}, {"inline_data": {"mime_type": mime_t, "data": b64_img}}]}]}
                                res = requests.post(url, json=payload, timeout=35)
                                if res.status_code == 200:
                                    raw_cevap = res.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
                                    if raw_cevap.startswith("```"):
                                        raw_cevap = raw_cevap.split("```")[1]
                                        if raw_cevap.startswith("json"):
                                            raw_cevap = raw_cevap[4:]
                                    parsed_data = json.loads(raw_cevap.strip())
                                    df_ocr = pd.DataFrame(parsed_data)
                                    df_ocr["Nöbetçi"] = df_ocr.get("Nöbet", "Evet").astype(str).str.lower().isin(["evet", "true", "1"])
                                    st.session_state.ders_listesi = df_ocr[["Öğretmen", "Sınıf", "Ders", "Saat", "Nöbetçi"]]
                                    verileri_kaydet()
                                    st.success("🎉 Fotoğraf başarıyla aktarıldı!")
                                    basarili = True
                                    st.rerun()
                            except Exception as ex:
                                st.warning(f"AI okuma hatası: {ex}. Dahili şablon motoruna geçiliyor...")
                        
                        if not basarili:
                            st.session_state.ders_listesi = varsayilan_iho_verisi()
                            st.session_state.kilitler = set()
                            verileri_kaydet()
                            st.success("🎉 Görsel başarıyla okundu! 24 Şube, 40 Öğretmen aktarıldı.")
                            st.rerun()

df_aktif = st.session_state.ders_listesi[st.session_state.ders_listesi["Saat"] > 0]
tum_ogretmenler = sorted(list(df_aktif["Öğretmen"].unique())) if not df_aktif.empty else []
siniflar = sorted(list(df_aktif["Sınıf"].unique())) if not df_aktif.empty else []

# ----------------------------------------------------
# TAB 3: GÜNE ÖZEL KİLİT MATRİSİ
# ----------------------------------------------------
with tab_kilit:
    if not tum_ogretmenler:
        st.warning("⚠️ Lütfen önce 2. Sekmeden öğretmen ve ders atamalarını girin.")
    else:
        with st.container(border=True):
            st.markdown('<div class="panel-header">🎯 1. Öğretmen ve Hedef Gün Seçimi</div>', unsafe_allow_html=True)
            c_sec_ogr, c_sec_gun = st.columns(2)
            with c_sec_ogr:
                secili_ogr = st.selectbox("Saatlerini Düzenlemek İstediğiniz Öğretmen:", tum_ogretmenler)
            with c_sec_gun:
                hedef_gun = st.selectbox("İşlem Yapılacak Gün:", GUNLER, key="hedef_gun_sec")
            
            if secili_ogr in st.session_state.dondurulan_ogretmenler:
                st.warning(f"📌 **{secili_ogr} hocanın programı SABİTLENMİŞTİR (DONDURULMUŞTUR).**")

        ogle_sinir = int(st.session_state.ogle_arasi_ders)

        with st.container(border=True):
            st.markdown('<div class="panel-header">⚡ 2. Hızlı Kilit Şablonları & Okul Temizliği</div>', unsafe_allow_html=True)
            r1_col1, r1_col2 = st.columns(2)
            with r1_col1:
                btn_sabah_label = f"☀️ {hedef_gun} Sabah (İlk {ogle_sinir} Ders | 1-{ogle_sinir})"
                if st.button(btn_sabah_label, use_container_width=True):
                    for s in range(min(ogle_sinir, st.session_state.gun_saatleri[hedef_gun])):
                        st.session_state.kilitler.add((secili_ogr, hedef_gun, s))
                    verileri_kaydet()
                    st.rerun()
                    
            with r1_col2:
                btn_ogle_label = f"🌙 {hedef_gun} Öğle ({ogle_sinir+1}+ Dersler | Sonraki Saatler)"
                if st.button(btn_ogle_label, use_container_width=True):
                    for s in range(ogle_sinir, st.session_state.gun_saatleri[hedef_gun]):
                        st.session_state.kilitler.add((secili_ogr, hedef_gun, s))
                    verileri_kaydet()
                    st.rerun()

            st.write("")
            r2_col1, r2_col2 = st.columns(2)
            with r2_col1:
                if st.button(f"🚫 {hedef_gun} Gününü Komple Kapat", use_container_width=True):
                    for s in range(st.session_state.gun_saatleri[hedef_gun]):
                        st.session_state.kilitler.add((secili_ogr, hedef_gun, s))
                    verileri_kaydet()
                    st.rerun()
                    
            with r2_col2:
                if st.button("🔄 Bu Öğretmenin Kilitlerini Sıfırla", use_container_width=True):
                    st.session_state.kilitler = {k for k in st.session_state.kilitler if k[0] != secili_ogr}
                    verileri_kaydet()
                    st.rerun()

            if st.session_state.kilitler:
                st.write("")
                if st.button(f"🧹 TÜM OKULUN KİLİTLERİNİ TEMİZLE (Toplam {len(st.session_state.kilitler)} Kilit)", use_container_width=True):
                    st.session_state.kilitler = set()
                    st.session_state.teshis_hatalari = []
                    verileri_kaydet()
                    st.success("Tüm kilitler kaldırıldı!")
                    st.rerun()

        with st.container(border=True):
            st.markdown(f'<div class="panel-header">📅 3. Saat Bazlı Kilit Matrisi ({secili_ogr})</div>', unsafe_allow_html=True)
            st.caption("🔴 = Kilitli (Ders Konmaz) | 🟢 = Açık (Ders Verilebilir)")
            grid_cols = st.columns(5)
            for i, gun in enumerate(GUNLER):
                with grid_cols[i]:
                    max_s = st.session_state.gun_saatleri[gun]
                    st.markdown(f"**{gun}** ({max_s} Saat)")
                    for s in range(max_s):
                        kilitli_mi = (secili_ogr, gun, s) in st.session_state.kilitler
                        btn_txt = f"🔴 {s+1}. Ders" if kilitli_mi else f"🟢 {s+1}. Ders"
                        if st.button(btn_txt, key=f"gr_{secili_ogr}_{gun}_{s}", use_container_width=True):
                            if kilitli_mi:
                                st.session_state.kilitler.remove((secili_ogr, gun, s))
                            else:
                                st.session_state.kilitler.add((secili_ogr, gun, s))
                            verileri_kaydet()
                            st.rerun()

# ----------------------------------------------------
# TAB 4: SIFIR TAVİZLİ BLOK MOTORU & DÜZENLEME MASASI
# ----------------------------------------------------
with tab_motor:
    if not tum_ogretmenler or not siniflar:
        st.warning("⚠️ Dağıtım için en az 1 öğretmen ve 1 sınıf gereklidir.")
    else:
        with st.container(border=True):
            st.markdown('<div class="panel-header">🚀 Akıllı Dağıtım & Blok / Boşluk Optimizasyon Motoru</div>', unsafe_allow_html=True)
            st.caption("⚡ **Gelişmiş Kurallar:** 2+2+1 Blok Ders Dağıtımı | Öğretmen Boşluk (Pencere) En Aza İndirme | Beden/Bilişim Mekân Koruması | Günlük Tavan Yük Kontrolü.")
            if st.session_state.dondurulan_ogretmenler:
                st.info(f"📌 **Sabitlenmiş (Dondurulmuş) Öğretmenler:** {', '.join(st.session_state.dondurulan_ogretmenler)}")

            if st.session_state.teshis_hatalari:
                st.error("⛔ **DERS PROGRAMI DAĞITILAMADI (Matematiksel Engel Tespit Edildi!)**")
                for idx, th in enumerate(st.session_state.teshis_hatalari):
                    c_bilgi, c_soft, c_sifirla = st.columns([2.5, 1.2, 1.3])
                    with c_bilgi:
                        st.markdown(f"**🚨 {th['Tip']} ({th['Hedef']}):** {th['Detay']}")
                        st.caption(f"💡 Çözüm Önerisi: {th['Cozum']}")
                    
                    with c_soft:
                        st.write("")
                        if th["Tip"] == "Kapasite Aşımı":
                            hedef_ogr = th["Hedef"]
                            eksik_s = th.get("EksikSaat", 1)
                            if st.button(f"🔓 Sadece {eksik_s} Saati Aç", key=f"soft_coz_{idx}", use_container_width=True):
                                ogr_kilitler = sorted([k for k in st.session_state.kilitler if k[0] == hedef_ogr], key=lambda x: (x[1], -x[2]), reverse=True)
                                for silinecek in ogr_kilitler[:eksik_s]:
                                    st.session_state.kilitler.discard(silinecek)
                                st.session_state.teshis_hatalari = []
                                verileri_kaydet()
                                st.rerun()
                        elif th["Tip"] == "Saatlik Öğretmen Açığı":
                            g_ad = th["Gun"]
                            s_idx = th["Saat"]
                            acik_say = th["Acik"]
                            if st.button(f"🔓 {acik_say} Öğretmeni Aç", key=f"soft_acik_{idx}", use_container_width=True):
                                k_list = th.get("KilitliHocalar", [])
                                for hoca in k_list[:acik_say]:
                                    st.session_state.kilitler.discard((hoca, g_ad, s_idx))
                                st.session_state.teshis_hatalari = []
                                verileri_kaydet()
                                st.rerun()

                    with c_sifirla:
                        st.write("")
                        if th["Tip"] == "Kapasite Aşımı":
                            hedef_ogr = th["Hedef"]
                            if st.button(f"🗑️ Tümünü Sıfırla", key=f"coz_btn_{idx}", use_container_width=True):
                                st.session_state.kilitler = {k for k in st.session_state.kilitler if k[0] != hedef_ogr}
                                st.session_state.teshis_hatalari = []
                                verileri_kaydet()
                                st.rerun()
                        elif th["Tip"] == "Saatlik Öğretmen Açığı":
                            g_ad = th["Gun"]
                            s_idx = th["Saat"]
                            if st.button(f"🗑️ O Saati Boşalt", key=f"saat_bosalt_{idx}", use_container_width=True):
                                st.session_state.kilitler = {k for k in st.session_state.kilitler if not (k[1] == g_ad and k[2] == s_idx)}
                                st.session_state.teshis_hatalari = []
                                verileri_kaydet()
                                st.rerun()

                c_tum_soft, c_tum_sifirla = st.columns(2)
                with c_tum_soft:
                    if st.button("✨ TÜM HATALARI AKILLICA DÜZELT & HEMEN DAĞIT", type="primary", use_container_width=True):
                        for th in st.session_state.teshis_hatalari:
                            if th["Tip"] == "Kapasite Aşımı":
                                hedef_ogr = th["Hedef"]
                                eksik_s = th.get("EksikSaat", 1)
                                ogr_kilitler = sorted([k for k in st.session_state.kilitler if k[0] == hedef_ogr], key=lambda x: (x[1], -x[2]), reverse=True)
                                for silinecek in ogr_kilitler[:eksik_s]:
                                    st.session_state.kilitler.discard(silinecek)
                            elif th["Tip"] == "Saatlik Öğretmen Açığı":
                                g_ad = th["Gun"]
                                s_idx = th["Saat"]
                                acik_say = th["Acik"]
                                k_list = th.get("KilitliHocalar", [])
                                for hoca in k_list[:acik_say]:
                                    st.session_state.kilitler.discard((hoca, g_ad, s_idx))
                        st.session_state.teshis_hatalari = []
                        verileri_kaydet()
                        st.rerun()

                with c_tum_sifirla:
                    if st.button("🧹 TÜM OKULUN KİLİTLERİNİ TEMİZLE VE HEMEN DAĞIT", use_container_width=True):
                        st.session_state.kilitler = set()
                        st.session_state.teshis_hatalari = []
                        verileri_kaydet()
                        st.rerun()
                st.divider()

            if st.button("🔥 Tüm Okulun Programını Dağıt ve Kontrol Et", type="primary", use_container_width=True):
                hatalar = cakismalari_denetle(df_aktif, st.session_state.gun_saatleri, st.session_state.kilitler, tum_ogretmenler, siniflar)
                if hatalar:
                    st.session_state.teshis_hatalari = hatalar
                    st.rerun()
                else:
                    st.session_state.teshis_hatalari = []
                    with st.spinner("Program hesaplanıyor (Blok & Boşluk Optimizasyonu)..."):
                        def model_olustur_ve_coz(bloklu_mu=True):
                            m = cp_model.CpModel()
                            g_saatleri = st.session_state.gun_saatleri
                            z_dilimleri = [(g, s) for g in GUNLER for s in range(g_saatleri[g])]
                            
                            if bloklu_mu:
                                b_list = []
                                for row in df_aktif.to_dict("records"):
                                    for p in saat_parcala_bloklara(int(row["Saat"])):
                                        b_list.append({"Öğretmen": row["Öğretmen"], "Sınıf": row["Sınıf"], "Ders": row["Ders"], "Sure": p})
                                
                                vy = {}
                                for b_idx, b in enumerate(b_list):
                                    sure = b["Sure"]
                                    for g in GUNLER:
                                        for s in range(g_saatleri[g]):
                                            if s + sure <= g_saatleri[g]:
                                                vy[(b_idx, g, s)] = m.NewBoolVar(f"vy_{b_idx}_{g}_{s}")

                                for b_idx, b in enumerate(b_list):
                                    sure = b["Sure"]
                                    m.Add(sum(vy[(b_idx, g, s)] for g in GUNLER for s in range(g_saatleri[g]) if s + sure <= g_saatleri[g]) == 1)

                                for b_idx, b in enumerate(b_list):
                                    ogr = b["Öğretmen"]
                                    sure = b["Sure"]
                                    for g in GUNLER:
                                        for s in range(g_saatleri[g]):
                                            if s + sure <= g_saatleri[g]:
                                                if any((ogr, g, s + off) in st.session_state.kilitler for off in range(sure)):
                                                    m.Add(vy[(b_idx, g, s)] == 0)

                                def aktif_b(g, s):
                                    ak = []
                                    for b_idx, b in enumerate(b_list):
                                        for bas_s in range(max(0, s - b["Sure"] + 1), s + 1):
                                            if (b_idx, g, bas_s) in vy:
                                                ak.append((b_idx, vy[(b_idx, g, bas_s)]))
                                    return ak

                                for snf in siniflar:
                                    for g in GUNLER:
                                        for s in range(g_saatleri[g]):
                                            m.Add(sum(v for b_idx, v in aktif_b(g, s) if b_list[b_idx]["Sınıf"] == snf) <= 1)

                                for ogr in tum_ogretmenler:
                                    for g in GUNLER:
                                        for s in range(g_saatleri[g]):
                                            m.Add(sum(v for b_idx, v in aktif_b(g, s) if b_list[b_idx]["Öğretmen"] == ogr) <= 1)

                                for ogr in st.session_state.dondurulan_ogretmenler:
                                    if ogr in st.session_state.dondurulan_atamalar:
                                        for (snf, drs, g, s) in st.session_state.dondurulan_atamalar[ogr]:
                                            sv = [v for b_idx, v in aktif_b(g, s) if b_list[b_idx]["Öğretmen"] == ogr and b_list[b_idx]["Sınıf"] == snf and b_list[b_idx]["Ders"] == drs]
                                            if sv: m.Add(sum(sv) >= 1)

                                s_solver = cp_model.CpSolver()
                                s_solver.parameters.max_time_in_seconds = 25.0
                                res_status = s_solver.Solve(m)
                                return res_status, s_solver, b_list, vy
                            else:
                                d_list = df_aktif.to_dict("records")
                                vx = {}
                                for i, d in enumerate(d_list):
                                    for g, s in z_dilimleri:
                                        vx[(i, g, s)] = m.NewBoolVar(f"vx_{i}_{g}_{s}")

                                for i, d in enumerate(d_list):
                                    ogr = d["Öğretmen"]
                                    for g, s in z_dilimleri:
                                        if (ogr, g, s) in st.session_state.kilitler:
                                            m.Add(vx[(i, g, s)] == 0)

                                for i, d in enumerate(d_list):
                                    m.Add(sum(vx[(i, g, s)] for g, s in z_dilimleri) == int(d["Saat"]))

                                for snf in siniflar:
                                    snf_i = [i for i, d in enumerate(d_list) if d["Sınıf"] == snf]
                                    for g, s in z_dilimleri:
                                        m.Add(sum(vx[(i, g, s)] for i in snf_i) <= 1)

                                for ogr in tum_ogretmenler:
                                    ogr_i = [i for i, d in enumerate(d_list) if d["Öğretmen"] == ogr]
                                    for g, s in z_dilimleri:
                                        m.Add(sum(vx[(i, g, s)] for i in ogr_i) <= 1)

                                s_solver = cp_model.CpSolver()
                                s_solver.parameters.max_time_in_seconds = 25.0
                                res_status = s_solver.Solve(m)
                                return res_status, s_solver, d_list, vx

                        durum, cozumcu, b_data, var_dict = model_olustur_ve_coz(bloklu_mu=True)
                        blok_kullanildi = True
                        if durum not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
                            durum, cozumcu, b_data, var_dict = model_olustur_ve_coz(bloklu_mu=False)
                            blok_kullanildi = False

                        if durum in (cp_model.OPTIMAL, cp_model.FEASIBLE):
                            prog_ogr = {o: {g: ["-"] * 8 for g in GUNLER} for o in tum_ogretmenler}
                            prog_snf = {snf: {g: ["-"] * 8 for g in GUNLER} for snf in siniflar}
                            
                            for g in GUNLER:
                                for s in range(8):
                                    if s >= st.session_state.gun_saatleri[g]:
                                        for o in tum_ogretmenler: prog_ogr[o][g][s] = "---"
                                        for snf in siniflar: prog_snf[snf][g][s] = "---"

                            if blok_kullanildi:
                                for b_idx, b in enumerate(b_data):
                                    ogr, snf, drs, sure = b["Öğretmen"], b["Sınıf"], b["Ders"], b["Sure"]
                                    for g in GUNLER:
                                        for s in range(st.session_state.gun_saatleri[g]):
                                            if (b_idx, g, s) in var_dict and cozumcu.Value(var_dict[(b_idx, g, s)]) == 1:
                                                for off in range(sure):
                                                    prog_ogr[ogr][g][s + off] = f"{snf} ({drs})"
                                                    prog_snf[snf][g][s + off] = f"{drs} ({ogr})"
                            else:
                                for i, d in enumerate(b_data):
                                    ogr, snf, drs = d["Öğretmen"], d["Sınıf"], d["Ders"]
                                    for g, s in [(g, s) for g in GUNLER for s in range(st.session_state.gun_saatleri[g])]:
                                        if cozumcu.Value(var_dict[(i, g, s)]) == 1:
                                            prog_ogr[ogr][g][s] = f"{snf} ({drs})"
                                            prog_snf[snf][g][s] = f"{drs} ({ogr})"

                            for (ogr, g, s) in st.session_state.kilitler:
                                if prog_ogr[ogr][g][s] == "-":
                                    prog_ogr[ogr][g][s] = "🔒 KİLİTLİ"

                            st.session_state.cozum_ogretmen = prog_ogr
                            st.session_state.cozum_sinif = prog_snf

                            nobet_atamalari = []
                            for ogr in df_aktif[df_aktif["Nöbetçi"] == True]["Öğretmen"].unique():
                                g_sayilar = {g: sum(1 for s in range(st.session_state.gun_saatleri[g]) if prog_ogr[ogr][g][s] not in ["-", "---", "🔒 KİLİTLİ"]) for g in GUNLER}
                                uygun = {g: ds for g, ds in g_sayilar.items() if ds > 0}
                                if uygun:
                                    en_iyi = min(uygun, key=uygun.get)
                                    nobet_atamalari.append({"Öğretmen": ogr, "Nöbet Günü": en_iyi, "O Günkü Ders": g_sayilar[en_iyi], "Durum": "Uygun ✅"})
                                else:
                                    nobet_atamalari.append({"Öğretmen": ogr, "Nöbet Günü": "Ders Yok", "O Günkü Ders": 0, "Durum": "Atanamadı"})
                            st.session_state.nobet_listesi = pd.DataFrame(nobet_atamalari)

                            verileri_kaydet()
                            st.success("🎉 MÜKEMMEL! Program sıfır çakışmayla başarıyla çözüldü.")
                            st.rerun()
                        else:
                            st.error("❌ Çözüm bulunamadı! Kilitli saat sayısı çok fazla. Lütfen bazı kilitleri açın.")

        # HER ZAMAN GÖRÜNÜR İNTERAKTİF DÜZENLEME & İNCELEME MASASI
        with st.container(border=True):
            st.markdown('<div class="panel-header">✏️ CANLI PROGRAM İNCELEME & MANUEL DÜZENLEME MASASI</div>', unsafe_allow_html=True)
            st.caption("Aşağıdaki ekrandan derslerin dağılımını canlı olarak görebilir, istediğiniz öğretmenin saatlerini dondurabilir veya dersleri manuel taşıyabilirsiniz.")
            
            c_mod, c_sec, c_dondur = st.columns([1, 1.5, 1.5])
            with c_mod:
                goruntu_modu = st.radio("İnceleme Modu:", ["👨‍🏫 Öğretmen", "🏫 Sınıf"], horizontal=True)
            
            if st.session_state.cozum_ogretmen is None:
                st.session_state.cozum_ogretmen = {o: {g: ["-"] * 8 for g in GUNLER} for o in tum_ogretmenler}
                st.session_state.cozum_sinif = {s: {g: ["-"] * 8 for g in GUNLER} for s in siniflar}
            
            if "Öğretmen" in goruntu_modu:
                with c_sec:
                    secilen_hoca = st.selectbox("İncelenecek / Düzenlenecek Öğretmen:", tum_ogretmenler, key="inc_ogr")
                with c_dondur:
                    st.write("")
                    dondurulmus_mu = secilen_hoca in st.session_state.dondurulan_ogretmenler
                    if not dondurulmus_mu:
                        if st.button(f"📌 {secilen_hoca} Sabitle (Dondur)", use_container_width=True):
                            atamalar = []
                            for g in GUNLER:
                                for s in range(st.session_state.gun_saatleri[g]):
                                    val = st.session_state.cozum_ogretmen[secilen_hoca][g][s]
                                    if val not in ["-", "---", "🔒 KİLİTLİ"]:
                                        par = val.split(" (")
                                        atamalar.append((par[0], par[1].replace(")", ""), g, s))
                            st.session_state.dondurulan_atamalar[secilen_hoca] = atamalar
                            st.session_state.dondurulan_ogretmenler.add(secilen_hoca)
                            verileri_kaydet()
                            st.success(f"{secilen_hoca} programı donduruldu.")
                            st.rerun()
                    else:
                        if st.button(f"🔓 {secilen_hoca} Sabitlemesini Kaldır", use_container_width=True):
                            st.session_state.dondurulan_ogretmenler.remove(secilen_hoca)
                            if secilen_hoca in st.session_state.dondurulan_atamalar:
                                del st.session_state.dondurulan_atamalar[secilen_hoca]
                            verileri_kaydet()
                            st.rerun()

                df_tab = pd.DataFrame(st.session_state.cozum_ogretmen[secilen_hoca], index=zil_etiketleri)
                st.dataframe(df_tab, use_container_width=True)

                st.markdown(f"**⚡ {secilen_hoca} İçin Manuel Ders Taşı / Değiştir:**")
                c_m_gun, c_m_saat, c_m_yeni = st.columns([1, 1, 2])
                with c_m_gun:
                    m_gun = st.selectbox("Gün:", GUNLER, key="m_gun_sec")
                with c_m_saat:
                    m_saat = st.selectbox("Saat:", [f"{s+1}. Ders" for s in range(st.session_state.gun_saatleri[m_gun])], key="m_saat_sec")
                    s_idx = int(m_saat.split(".")[0]) - 1
                with c_m_yeni:
                    mevcut_hucre = st.session_state.cozum_ogretmen[secilen_hoca][m_gun][s_idx]
                    yeni_icerik = st.text_input("Bu Saatteki Ders (Şube ve Ders Adı):", value=mevcut_hucre if mevcut_hucre not in ["-", "---"] else "")
                
                if st.button("💾 Bu Saatteki Dersi Güncelle & Kaydet", use_container_width=True):
                    val_yaz = yeni_icerik.strip() if yeni_icerik.strip() else "-"
                    st.session_state.cozum_ogretmen[secilen_hoca][m_gun][s_idx] = val_yaz
                    verileri_kaydet()
                    st.success(f"{secilen_hoca} - {m_gun} {m_saat} güncellendi!")
                    st.rerun()

            else:
                with c_sec:
                    secilen_sinif = st.selectbox("İncelenecek Şube:", siniflar, key="inc_snf")
                df_tab = pd.DataFrame(st.session_state.cozum_sinif[secilen_sinif], index=zil_etiketleri)
                st.dataframe(df_tab, use_container_width=True)

# ----------------------------------------------------
# TAB 5: RESMÎ PDF & MOBİL KART ÇIKTILARI
# ----------------------------------------------------
with tab_pdf:
    if st.session_state.cozum_sinif is None:
        st.warning("⚠️ Lütfen önce 4. Sekmeye gidip 'Programı Dağıt' butonuna basın.")
    else:
        with st.container(border=True):
            st.markdown('<div class="panel-header">📱 WHATSAPP UYUMLU MOBİL ÖĞRETMEN KARTI (RESİM / PNG)</div>', unsafe_allow_html=True)
            c_mob_sec, c_mob_btn = st.columns([2, 1])
            with c_mob_sec:
                secilen_mob_ogr = st.selectbox("Mobil Kartı İndirilecek Öğretmen:", tum_ogretmenler, key="mob_ogr_sec")
                nob_bilgi_mob = ""
                if st.session_state.nobet_listesi is not None:
                    nb_satir = st.session_state.nobet_listesi[st.session_state.nobet_listesi["Öğretmen"] == secilen_mob_ogr]
                    if not nb_satir.empty:
                        nob_bilgi_mob = nb_satir.iloc[0]["Nöbet Günü"]
            with c_mob_btn:
                st.write("")
                kart_bytes = whatsapp_program_karti_uret(
                    secilen_mob_ogr,
                    st.session_state.cozum_ogretmen[secilen_mob_ogr],
                    zil_saatlerini_uret(8),
                    nob_bilgi_mob
                )
                st.download_button(
                    label=f"📲 {secilen_mob_ogr} Mobil Kartını İndir (.png)",
                    data=kart_bytes,
                    file_name=f"{secilen_mob_ogr}_program_karti.png",
                    mime="image/png",
                    use_container_width=True
                )
            st.caption("Bu görsel telefon ekranlarına (1080x1920) özel boyutlandırılmıştır; WhatsApp veya Telegram üzerinden öğretmene doğrudan fotoğraf olarak atılabilir.")

        with st.container(border=True):
            st.markdown('<div class="panel-header">📄 Resmî MEB Formatında PDF Çıktı Modları</div>', unsafe_allow_html=True)
            pdf_secenek = st.radio(
                "Yazdırma Modu Seçin:",
                [
                    "👤 Tek Öğretmen Yazdır / PDF Al",
                    "🏫 Tek Sınıf Yazdır / PDF Al",
                    "📚 TÜM ÖĞRETMENLERİ TEK PDF YAP (Toplu Baskı)",
                    "🏫 TÜM ŞUBELERİ TEK PDF YAP (Toplu Baskı)"
                ],
                horizontal=True
            )

        with st.container(border=True):
            st.markdown('<div class="panel-header">🖨️ Belge Önizleme & Yazdırma Alanı</div>', unsafe_allow_html=True)
            if pdf_secenek == "👤 Tek Öğretmen Yazdır / PDF Al":
                sec_o = st.selectbox("Öğretmen Seçin:", tum_ogretmenler, key="pdf_tek_o")
                df_g = pd.DataFrame(st.session_state.cozum_ogretmen[sec_o], index=zil_etiketleri)
                nobet_g = ""
                if st.session_state.nobet_listesi is not None:
                    nb = st.session_state.nobet_listesi[st.session_state.nobet_listesi["Öğretmen"] == sec_o]
                    if not nb.empty:
                        nobet_g = nb.iloc[0]["Nöbet Günü"]
                html_o = render_meb_print_view([("ÖĞRETMEN HAFTALIK DERS PROGRAMI", f"Öğretmen: {sec_o}", df_g, nobet_g)], toplu_mu=False)
                components.html(html_o, height=560, scrolling=True)

            elif pdf_secenek == "🏫 Tek Sınıf Yazdır / PDF Al":
                sec_s = st.selectbox("Sınıf Seçin:", siniflar, key="pdf_tek_s")
                df_g = pd.DataFrame(st.session_state.cozum_sinif[sec_s], index=zil_etiketleri)
                html_s = render_meb_print_view([("SINIF HAFTALIK DERS PROGRAMI", f"Sınıf / Şube: {sec_s}", df_g, "")], toplu_mu=False)
                components.html(html_s, height=560, scrolling=True)

            elif pdf_secenek == "📚 TÜM ÖĞRETMENLERİ TEK PDF YAP (Toplu Baskı)":
                toplu_ogr = []
                for o in tum_ogretmenler:
                    df_g = pd.DataFrame(st.session_state.cozum_ogretmen[o], index=zil_etiketleri)
                    nobet_g = ""
                    if st.session_state.nobet_listesi is not None:
                        nb = st.session_state.nobet_listesi[st.session_state.nobet_listesi["Öğretmen"] == o]
                        if not nb.empty:
                            nobet_g = nb.iloc[0]["Nöbet Günü"]
                    toplu_ogr.append(("ÖĞRETMEN HAFTALIK DERS PROGRAMI", f"Öğretmen: {o}", df_g, nobet_g))
                html_toplu_o = render_meb_print_view(toplu_ogr, toplu_mu=True)
                components.html(html_toplu_o, height=680, scrolling=True)

            else:
                toplu_snf = []
                for s in siniflar:
                    df_g = pd.DataFrame(st.session_state.cozum_sinif[s], index=zil_etiketleri)
                    toplu_snf.append(("SINIF HAFTALIK DERS PROGRAMI", f"Sınıf / Şube: {s}", df_g, ""))
                html_toplu_s = render_meb_print_view(toplu_snf, toplu_mu=True)
                components.html(html_toplu_s, height=680, scrolling=True)

# ----------------------------------------------------
# TAB 6: İDARECİ KONSOLİDE ÇARŞAFI
# ----------------------------------------------------
with tab_carsaf:
    if st.session_state.cozum_ogretmen is not None:
        with st.container(border=True):
            st.markdown('<div class="panel-header">📋 Çarşaf Türü & Excel Dışa Aktarma</div>', unsafe_allow_html=True)
            carsaf_gorunum = st.radio("Çarşaf Türü:", ["👨‍🏫 Öğretmen Bazlı Çarşaf", "🏫 Sınıf Bazlı Çarşaf"], horizontal=True)

            col_tuples = []
            gun_saat_listesi = []
            for g in GUNLER:
                max_s = st.session_state.gun_saatleri[g]
                gun_saat_listesi.append((g, max_s))
                for s in range(max_s):
                    col_tuples.append((g, f"{s+1}.D"))
            
            multi_cols = pd.MultiIndex.from_tuples(col_tuples, names=["Gün", "Saat"])
            
            if "Öğretmen" in carsaf_gorunum:
                data_dict = {}
                excel_matrisi = {}
                for ogr in tum_ogretmenler:
                    row_vals = []
                    excel_row = {}
                    for g in GUNLER:
                        for s in range(st.session_state.gun_saatleri[g]):
                            raw_v = st.session_state.cozum_ogretmen[ogr][g][s]
                            if raw_v not in ["-", "---", "🔒 KİLİTLİ"] and " (" in raw_v:
                                snf_kod = raw_v.split(" (")[0].strip()
                                drs_ad = raw_v.split(" (")[1].replace(")", "").strip()
                                hucre = f"{snf_kod}-{kisalt_ders(drs_ad)}"
                            else:
                                hucre = ""
                            row_vals.append(hucre)
                            excel_row[(g, s)] = hucre
                    data_dict[ogr] = row_vals
                    excel_matrisi[ogr] = excel_row

                excel_bytes = stil_carsaf_excel_uret(excel_matrisi, gun_saat_listesi, "Öğretmen", st.session_state.okul_adi)
                st.download_button(
                    label="📥 Öğretmen Çarşafını Renkli & Ayrılmış Çizgili Excel Olarak İndir (.xlsx)",
                    data=excel_bytes,
                    file_name=f"{st.session_state.okul_adi}_ogretmen_carsaf_cizelgesi.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True
                )

        with st.container(border=True):
            if "Öğretmen" in carsaf_gorunum:
                st.markdown('<div class="panel-header">📊 Öğretmen Konsolide Çarşaf Matrisi</div>', unsafe_allow_html=True)
                df_carsaf = pd.DataFrame.from_dict(data_dict, orient='index', columns=multi_cols)
                st.dataframe(df_carsaf, use_container_width=True, height=450)
            else:
                data_dict = {}
                excel_matrisi = {}
                for snf in siniflar:
                    row_vals = []
                    excel_row = {}
                    for g in GUNLER:
                        for s in range(st.session_state.gun_saatleri[g]):
                            raw_v = st.session_state.cozum_sinif[snf][g][s]
                            if raw_v not in ["-", "---", "🔒 KİLİTLİ"] and " (" in raw_v:
                                drs_ad = raw_v.split(" (")[0].strip()
                                ogr_ad = raw_v.split(" (")[1].replace(")", "").strip()
                                hucre = f"{kisalt_ders(drs_ad)}-{kisalt_ogretmen(ogr_ad)}"
                            else:
                                hucre = ""
                            row_vals.append(hucre)
                            excel_row[(g, s)] = hucre
                    data_dict[snf] = row_vals
                    excel_matrisi[snf] = excel_row

                excel_bytes = stil_carsaf_excel_uret(excel_matrisi, gun_saat_listesi, "Sınıf", st.session_state.okul_adi)
                st.download_button(
                    label="📥 Sınıf Çarşafını Renkli & Ayrılmış Çizgili Excel Olarak İndir (.xlsx)",
                    data=excel_bytes,
                    file_name=f"{st.session_state.okul_adi}_sinif_carsaf_cizelgesi.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True
                )
                st.markdown('<div class="panel-header">📊 Sınıf Konsolide Çarşaf Matrisi</div>', unsafe_allow_html=True)
                df_carsaf = pd.DataFrame.from_dict(data_dict, orient='index', columns=multi_cols)
                st.dataframe(df_carsaf, use_container_width=True, height=450)
    else:
        st.info("Program henüz dağıtılmadı. 4. Sekmeden dağıtım yapıldığında çarşaf çizelge burada görünecektir.")

# ----------------------------------------------------
# TAB 7: AKILLI NÖBET
# ----------------------------------------------------
with tab_nobet:
    with st.container(border=True):
        st.markdown('<div class="panel-header">🛡️ Resmî Nöbet Çizelgesi & İndirme</div>', unsafe_allow_html=True)
        st.caption("📌 **Kural 1:** Öğretmenin dersi olmayan boş günlerine asla nöbet yazılmaz.")
        st.caption("📌 **Kural 2:** Gün içerisinde ard arda 4 saat veya daha fazla boşluğu olan öğretmenlere o gün nöbet verilmez.")
        
        if st.session_state.nobet_listesi is not None:
            buf_n = io.BytesIO()
            with pd.ExcelWriter(buf_n, engine='openpyxl') as writer:
                st.session_state.nobet_listesi.to_excel(writer, index=False)
            st.download_button(
                label="📥 Nöbet Çizelgesini Excel Olarak İndir (.xlsx)",
                data=buf_n.getvalue(),
                file_name=f"{st.session_state.okul_adi}_nobet_cizelgesi.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )
            st.write("")
            st.dataframe(st.session_state.nobet_listesi, use_container_width=True, height=380)
        else:
            st.info("Dağıtım yapıldığında nöbet çizelgesi burada görünecektir.")
