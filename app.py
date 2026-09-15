import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
from ortools.sat.python import cp_model
from datetime import datetime, timedelta
from PIL import Image, ImageDraw
import openpyxl
from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
from openpyxl.utils import get_column_letter
import requests
import base64
import json
import os
import io

st.set_page_config(page_title="Akıllı Okul Yönetim & Ders Dağıtım Paneli", layout="wide")

# ==========================================
# 0. ULTRA-MODERN KURUMSAL YÖNETİM PANELİ (CSS)
# ==========================================
st.markdown("""
<style>
    html, body, [class*="css"] {
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    }
    /* Genel Kart Yapıları */
    .dashboard-card {
        background: rgba(255, 255, 255, 0.02);
        border: 1px solid rgba(128, 128, 128, 0.15);
        padding: 20px;
        border-radius: 14px;
        box-shadow: 0 4px 20px rgba(0,0,0,0.03);
        margin-bottom: 20px;
    }
    .stButton > button {
        width: 100% !important;
        border-radius: 10px !important;
        min-height: 48px !important;
        font-weight: 600 !important;
        font-size: 13px !important;
        box-shadow: 0 2px 6px rgba(0,0,0,0.04);
        transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
        border: 1px solid rgba(128, 128, 128, 0.2);
    }
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 16px rgba(0,0,0,0.08);
    }
    div[data-testid="metric-container"] {
        background: rgba(255, 255, 255, 0.03);
        border: 1px solid rgba(128, 128, 128, 0.18);
        padding: 16px 20px;
        border-radius: 14px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.02);
        transition: all 0.3s ease;
    }
    div[data-testid="metric-container"]:hover {
        border-color: rgba(0, 102, 204, 0.4);
        box-shadow: 0 4px 12px rgba(0, 102, 204, 0.05);
    }
    div[data-testid="stMetricValue"] {
        font-size: 1.6rem !important;
        font-weight: 700 !important;
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 10px;
        background-color: transparent;
        padding-bottom: 10px;
    }
    .stTabs [data-baseweb="tab"] {
        border-radius: 10px;
        padding: 10px 18px;
        font-weight: 600;
        border: 1px solid rgba(128, 128, 128, 0.15);
        background: rgba(128, 128, 128, 0.02);
        transition: all 0.2s ease;
    }
    .stTabs [aria-selected="true"] {
        background: #0066cc !important;
        color: white !important;
        border-color: #0066cc !important;
        box-shadow: 0 4px 12px rgba(0, 102, 204, 0.25);
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
        "teneffus_sureleri": {str(k): v for k, v in st.session_state.teneffus_sureleri.items()},
        "gun_saatleri": st.session_state.gun_saatleri,
        "kilitler": list(st.session_state.kilitler),
        "dondurulan_ogretmenler": list(st.session_state.dondurulan_ogretmenler),
        "ders_listesi": st.session_state.ders_listesi.to_dict(orient="records")
    }
    try:
        with open(VERI_DOSYASI, "w", encoding="utf-8") as f:
            json.dump(veri, f, ensure_ascii=False, indent=4)
    except Exception as e:
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
                st.session_state.teneffus_sureleri = {int(k): v for k, v in veri.get("teneffus_sureleri", {1:20, 2:10, 3:10, 4:10, 5:10, 6:10, 7:10}).items()}
                st.session_state.gun_saatleri = veri.get("gun_saatleri", {"Pazartesi":7, "Salı":7, "Çarşamba":8, "Perşembe":7, "Cuma":7})
                st.session_state.kilitler = set(tuple(k) for k in veri.get("kilitler", []))
                st.session_state.dondurulan_ogretmenler = set(veri.get("dondurulan_ogretmenler", []))
                if "ders_listesi" in veri:
                    st.session_state.ders_listesi = pd.DataFrame(veri["ders_listesi"])
                return True
        except Exception as e:
            pass
    return False

# Session State Başlatma & Yükleme Kontrolü
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
        :root {{
            --bg-page: #ffffff;
            --card-bg: #ffffff;
            --text-main: #111827;
            --text-muted: #4b5563;
            --border-color: #d1d5db;
            --th-bg: #f3f4f6;
            --th-text: #111827;
            --time-bg: #f9fafb;
            --kilit-bg: #f3f4f6;
            --kilit-text: #6b7280;
            --empty-text: #9ca3af;
            --header-red: #b30000;
            --nobet-color: #d9534f;
        }}
        @media (prefers-color-scheme: dark) {{
            :root {{
                --bg-page: #0e1117;
                --card-bg: #161a23;
                --text-main: #f9fafb;
                --text-muted: #9ca3af;
                --border-color: #374151;
                --th-bg: #1f2937;
                --th-text: #f9fafb;
                --time-bg: #1a1e29;
                --kilit-bg: #262c38;
                --kilit-text: #d1d5db;
                --empty-text: #4b5563;
                --header-red: #ff6b6b;
                --nobet-color: #f87171;
            }}
        }}
        body.dark-theme {{
            --bg-page: #0e1117 !important;
            --card-bg: #161a23 !important;
            --text-main: #f9fafb !important;
            --text-muted: #9ca3af !important;
            --border-color: #374151 !important;
            --th-bg: #1f2937 !important;
            --th-text: #f9fafb !important;
            --time-bg: #1a1e29 !important;
            --kilit-bg: #262c38 !important;
            --kilit-text: #d1d5db !important;
            --empty-text: #4b5563 !important;
            --header-red: #ff6b6b !important;
            --nobet-color: #f87171 !important;
        }}
        body.light-theme {{
            --bg-page: #ffffff !important;
            --card-bg: #ffffff !important;
            --text-main: #111827 !important;
            --text-muted: #4b5563 !important;
            --border-color: #d1d5db !important;
            --th-bg: #f3f4f6 !important;
            --th-text: #111827 !important;
            --time-bg: #f9fafb !important;
            --kilit-bg: #f3f4f6 !important;
            --kilit-text: #6b7280 !important;
            --empty-text: #9ca3af !important;
            --header-red: #b30000 !important;
            --nobet-color: #d9534f !important;
        }}
        body {{ font-family: Arial, sans-serif; margin: 0; padding: 12px; background-color: var(--bg-page); color: var(--text-main); transition: background-color 0.2s ease, color 0.2s ease; }}
        .top-toolbar {{ display: flex; align-items: center; gap: 12px; margin-bottom: 16px; }}
        .btn-action {{ background-color: #0066cc; color: white; border: none; padding: 10px 18px; font-size: 13px; font-weight: bold; border-radius: 6px; cursor: pointer; }}
        .btn-action:hover {{ background-color: #004c99; }}
        .btn-theme {{ background-color: var(--th-bg); color: var(--text-main); border: 1px solid var(--border-color); padding: 9px 15px; font-size: 13px; font-weight: 600; border-radius: 6px; cursor: pointer; }}
        .header-box {{ text-align: center; border-bottom: 2px solid var(--border-color); padding-bottom: 8px; margin-bottom: 14px; }}
        .header-box h2 {{ margin: 2px; font-size: 16px; color: var(--text-main); }}
        .header-box h3 {{ margin: 2px; font-size: 13px; font-weight: normal; color: var(--text-muted); }}
        .sub-year {{ font-size: 11px; color: var(--text-muted); margin: 2px; }}
        .header-box h4 {{ margin: 4px 0; font-size: 15px; color: var(--header-red); font-weight: bold; }}
        .sub-info {{ color: var(--text-main); font-size: 13px; }}
        .nobet-tag {{ color: var(--nobet-color); font-weight: bold; }}
        .table-meb {{ width: 100%; border-collapse: collapse; text-align: center; font-size: 11px; border: 1px solid var(--border-color); background-color: var(--card-bg); }}
        .table-meb th {{ background-color: var(--th-bg); color: var(--th-text); padding: 8px 6px; font-weight: bold; border: 1px solid var(--border-color); }}
        .table-meb td {{ padding: 6px; height: 30px; border: 1px solid var(--border-color); color: var(--text-main); }}
        .table-meb td.time-cell {{ background-color: var(--time-bg); font-size: 10px; font-weight: bold; color: var(--text-muted); }}
        .table-meb td.kilit-cell {{ background-color: var(--kilit-bg); color: var(--kilit-text); font-weight: 500; }}
        .table-meb td.empty-cell {{ color: var(--empty-text); }}
        .table-meb td.content-cell {{ font-weight: 600; color: var(--text-main); }}
        .footer-box {{ margin-top: 25px; display: flex; justify-content: space-between; font-size: 12px; color: var(--text-main); padding: 0 10px; }}
        .printable-page {{ padding-bottom: 25px; }}
        @media print {{
            .no-print {{ display: none !important; }}
            body {{ background-color: #ffffff !important; color: #000000 !important; margin: 0 !important; padding: 0 !important; }}
            .header-box h2, .header-box h3, .sub-info, .footer-box {{ color: #000000 !important; }}
            .header-box {{ border-bottom: 2px solid #000000 !important; }}
            .header-box h4 {{ color: #b30000 !important; }}
            .nobet-tag {{ color: #b30000 !important; }}
            .table-meb {{ border: 1px solid #000000 !important; background-color: #ffffff !important; }}
            .table-meb th {{ background-color: #f2f2f2 !important; color: #000000 !important; border: 1px solid #000000 !important; }}
            .table-meb td {{ border: 1px solid #000000 !important; color: #000000 !important; background-color: #ffffff !important; }}
            .table-meb td.time-cell {{ background-color: #f9f9f9 !important; color: #333333 !important; }}
            .table-meb td.kilit-cell {{ background-color: #f0f0f0 !important; color: #555555 !important; }}
            .page-break {{ page-break-after: always; break-after: page; display: block; }}
        }}
    </style>
    <script>
        function applyAutoTheme() {{
            try {{
                const pBody = window.parent.document.body;
                const pBg = window.getComputedStyle(pBody).backgroundColor;
                if (pBody.classList.contains('dark') || isDark(pBg)) {{
                    document.body.className = 'dark-theme';
                    return;
                }}
            }} catch(e) {{}}
            if (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches) {{
                document.body.className = 'dark-theme';
            }} else {{
                document.body.className = 'light-theme';
            }}
        }}
        function isDark(rgbStr) {{
            if (!rgbStr || rgbStr.indexOf('rgb') === -1) return false;
            const nums = rgbStr.match(/\\d+/g);
            if (nums && nums.length >= 3) {{
                const b = (parseInt(nums[0])*299 + parseInt(nums[1])*587 + parseInt(nums[2])*114) / 1000;
                return b < 128;
            }}
            return false;
        }}
        function toggleTheme() {{
            if (document.body.classList.contains('dark-theme')) {{
                document.body.className = 'light-theme';
            }} else {{
                document.body.className = 'dark-theme';
            }}
        }}
        window.addEventListener('DOMContentLoaded', applyAutoTheme);
    </script>
    </head>
    <body>
        <div class="no-print top-toolbar">
            <button class="btn-action" onclick="window.print()">🖨️ Sayfayı Yazdır / PDF Olarak Kaydet</button>
            <button class="btn-theme" onclick="toggleTheme()">🌗 Tema Değiştir (Koyu / Açık)</button>
            <span style="font-size: 12px; color: var(--text-muted);">(Yazdırırken otomatik A4 beyaz kâğıt formatına dönüşür)</span>
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
# 5. YÖNETİM PANELİ & ANA SEKMELER
# ==========================================
st.markdown(f"""
<div style="background: linear-gradient(135deg, #004c99 0%, #0066cc 100%); padding: 22px 28px; border-radius: 16px; color: white; margin-bottom: 25px; box-shadow: 0 8px 24px rgba(0,102,204,0.2);">
    <h1 style="margin: 0; font-size: 26px; font-weight: 800; display: flex; align-items: center; gap: 12px;">
        🏛️ {st.session_state.okul_adi}
    </h1>
    <p style="margin: 6px 0 0 0; font-size: 14px; opacity: 0.9;">
        Akıllı Ders Dağıtım, Çakışma Yönetimi & Nöbet Planlama Kontrol Paneli • <span style="background: rgba(255,255,255,0.2); padding: 2px 8px; border-radius: 6px;">{st.session_state.egitim_yili}</span>
    </p>
</div>
""", unsafe_allow_html=True)

tab_okul, tab_kisi_ders, tab_kilit, tab_motor, tab_pdf, tab_carsaf, tab_nobet = st.tabs([
    "🏛️ 1. Okul & Zil",
    "👥 2. Kadro & Dersler",
    "🔒 3. Kilit Matrisi",
    "🚀 4. Dağıtım Motoru",
    "📄 5. Resmî PDF",
    "📋 6. İdareci Çarşafı",
    "🛡️ 7. Akıllı Nöbet"
])

# ----------------------------------------------------
# TAB 1: OKUL KÜNYESİ VE ZİL SAATLERİ
# ----------------------------------------------------
with tab_okul:
    st.markdown('<div class="dashboard-card">', unsafe_allow_html=True)
    st.subheader("🏛️ Kurum Bilgileri & Başlıklar")
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
        yeni_mudur = st.text_input("Okul Müdürü / Ünvanı", value=st.session_state.mudur_adi)
        if yeni_mudur != st.session_state.mudur_adi:
            st.session_state.mudur_adi = yeni_mudur
            verileri_kaydet()
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="dashboard-card">', unsafe_allow_html=True)
    st.subheader("⏰ Ders ve Zaman Parametreleri")
    c_z1, c_z2, c_z3, c_z4 = st.columns(4)
    with c_z1:
        yeni_bas = st.text_input("1. Ders Başlama", value=st.session_state.ders_baslangic, placeholder="08:30")
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

    st.write("---")
    st.markdown("#### ☕ Teneffüs Süreleri Yönetimi")
    cols_ten = st.columns(7)
    for t_idx in range(1, 8):
        with cols_ten[t_idx - 1]:
            etiket = f"{t_idx}. Teneffüs"
            if t_idx == 1:
                etiket = "🍳 1. Ten. (Kahvaltı)"
            elif t_idx == int(st.session_state.ogle_arasi_ders):
                etiket = f"🍽️ {t_idx}. Ten. (Öğle)"
            
            if t_idx == int(st.session_state.ogle_arasi_ders):
                st.info(f"{st.session_state.ogle_arasi_dk} Dk\n(Öğle)")
            else:
                eski_ten = st.session_state.teneffus_sureleri.get(t_idx, 10)
                yeni_ten = st.number_input(
                    etiket, min_value=5, max_value=60,
                    value=int(eski_ten), key=f"ten_input_{t_idx}"
                )
                if yeni_ten != eski_ten:
                    st.session_state.teneffus_sureleri[t_idx] = yeni_ten
                    verileri_kaydet()

    st.write("📋 **Oluşturulan Resmî Günlük Zaman Çizelgesi:**")
    zil_listesi = zil_saatlerini_uret(8)
    cols_zil_gor = st.columns(8)
    for i, z in enumerate(zil_listesi):
        with cols_zil_gor[i]:
            st.metric(f"{i+1}. Ders", z)
    st.markdown('</div>', unsafe_allow_html=True)

# ----------------------------------------------------
# TAB 2: ÖĞRETMEN, SINIF & DERS YÖNETİMİ
# ----------------------------------------------------
with tab_kisi_ders:
    st.markdown('<div class="dashboard-card">', unsafe_allow_html=True)
    st.subheader("👥 Kadro, Sınıf ve Ders Tanımlama Masası")
    
    c_btn1, c_btn2 = st.columns(2)
    with c_btn1:
        if st.button("🗑️ TÜM LİSTEYİ SIFIRLA", use_container_width=True):
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
        if st.button("🔄 Örnek 24 Şubeli İHO Verisini Yükle", use_container_width=True):
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
    st.markdown('</div>', unsafe_allow_html=True)

    col_sol, col_sag = st.columns(2)
    with col_sol:
        st.markdown('<div class="dashboard-card">', unsafe_allow_html=True)
        st.markdown("#### 👨‍🏫 Öğretmen Ekle & Sil")
        mevcut_ogretmenler = sorted(list(st.session_state.ders_listesi["Öğretmen"].dropna().unique())) if not st.session_state.ders_listesi.empty else []
        c_o_ekle, c_o_sil = st.columns(2)
        with c_o_ekle:
            with st.form("ogr_ekle_form", clear_on_submit=True):
                yeni_hoca = st.text_input("Öğretmen Adı Soyadı", placeholder="Örn: Hasan Yılmaz")
                yeni_nobet = st.checkbox("Nöbet Tutabilir", value=True)
                if st.form_submit_button("➕ Öğretmeni Ekle", use_container_width=True):
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
        st.markdown('</div>', unsafe_allow_html=True)

    with col_sag:
        st.markdown('<div class="dashboard-card">', unsafe_allow_html=True)
        st.markdown("#### 🏫 Şube Ekle & Sil")
        mevcut_siniflar = sorted([s for s in st.session_state.ders_listesi["Sınıf"].dropna().unique() if s != "-"]) if not st.session_state.ders_listesi.empty else []
        c_s_ekle, c_s_sil = st.columns(2)
        with c_s_ekle:
            with st.form("snf_ekle_form", clear_on_submit=True):
                yeni_snf = st.text_input("Şube Adı", placeholder="Örn: 5G")
                if st.form_submit_button("➕ Şubeyi Ekle", use_container_width=True):
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
        st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="dashboard-card">', unsafe_allow_html=True)
    st.markdown("#### 📚 Ders Eşleştirmesi & Detaylı Yük Analizi")
    c_d_ekle, c_d_tablo = st.columns(2)
    
    with c_d_ekle:
        guncel_hocalar = sorted([o for o in st.session_state.ders_listesi["Öğretmen"].unique() if o != "-"])
        guncel_snflar = sorted([s for s in st.session_state.ders_listesi["Sınıf"].unique() if s != "-"])
        
        if guncel_hocalar and guncel_snflar:
            with st.form("ders_atama_formu", clear_on_submit=True):
                sec_ogr = st.selectbox("Öğretmen", guncel_hocalar)
                sec_snf = st.selectbox("Sınıf / Şube", guncel_snflar)
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
                        st.success(f"{sec_ogr} -> {sec_snf} {drs_ad} eklendi.")
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
                st.dataframe(df_gecerli_dersler[["Öğretmen", "Sınıf", "Ders", "Saat", "Nöbetçi"]], height=210, use_container_width=True)
                atama_etiketleri = [f"{r['Öğretmen']} | {r['Sınıf']} - {r['Ders']} ({r['Saat']} Saat)" for _, r in df_gecerli_dersler.iterrows()]
                secilen_sil_idx = st.selectbox("Listeden Çıkarılacak Ders Ataması:", range(len(atama_etiketleri)), format_func=lambda i: atama_etiketleri[i])
                if st.button("🗑️ Seçili Ders Atamasını Sil", use_container_width=True):
                    hedef_row = df_gecerli_dersler.iloc[secilen_sil_idx]
                    st.session_state.ders_listesi = st.session_state.ders_listesi.drop(hedef_row.name).reset_index(drop=True)
                    verileri_kaydet()
                    st.rerun()

            with sub_tab_ogr_yuku:
                ogr_ozet = []
                for o, grp in df_gecerli_dersler.groupby("Öğretmen"):
                    top_s = int(grp["Saat"].sum())
                    d_adlar = ", ".join(sorted(grp["Ders"].unique()))
                    s_adlar = ", ".join(sorted(grp["Sınıf"].unique()))
                    nob_str = "Evet ✅" if grp["Nöbetçi"].any() else "Hayır ❌"
                    durum_str = f"{top_s}s (Maks)" if top_s >= 30 else (f"{top_s}s (Maaş+Ek)" if top_s >= 21 else f"{top_s}s (Eksik ⚠️)")
                    ogr_ozet.append({"Öğretmen": o, "Toplam Saat": top_s, "Branş": d_adlar, "Şubeler": s_adlar, "Norm": durum_str, "Nöbet": nob_str})
                df_ogr_ozet = pd.DataFrame(ogr_ozet).sort_values(by="Toplam Saat", ascending=False).reset_index(drop=True)
                st.dataframe(df_ogr_ozet, height=210, use_container_width=True)
                
                buf_oy = io.BytesIO()
                with pd.ExcelWriter(buf_oy, engine='openpyxl') as writer:
                    df_ogr_ozet.to_excel(writer, index=False)
                st.download_button("📥 Yükleri Excel İndir (.xlsx)", data=buf_oy.getvalue(), file_name="ogretmen_ders_yukleri.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True)

            with sub_tab_snf_yuku:
                snf_ozet = []
                for s, grp in df_gecerli_dersler.groupby("Sınıf"):
                    top_s = int(grp["Saat"].sum())
                    snf_ozet.append({"Şube": s, "Toplam Saat": top_s, "Ders Sayısı": len(grp), "Durum": "Tamam (36s) ✅" if top_s == 36 else f"{top_s}/36s ⚠️"})
                df_snf_ozet = pd.DataFrame(snf_ozet).sort_values(by="Şube").reset_index(drop=True)
                st.dataframe(df_snf_ozet, height=240, use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)

df_aktif = st.session_state.ders_listesi[st.session_state.ders_listesi["Saat"] > 0]
tum_ogretmenler = sorted(list(df_aktif["Öğretmen"].unique())) if not df_aktif.empty else []
siniflar = sorted(list(df_aktif["Sınıf"].unique())) if not df_aktif.empty else []

# ----------------------------------------------------
# TAB 3: GÜNE ÖZEL KİLİT MATRİSİ
# ----------------------------------------------------
with tab_kilit:
    if not tum_ogretmenler:
        st.warning("⚠️ Lütfen önce kadro ve ders atamalarını girin.")
    else:
        st.markdown('<div class="dashboard-card">', unsafe_allow_html=True)
        st.subheader("🔒 Öğretmen Kısıt & Kilit Matrisi")
        c_sec_ogr, c_sec_gun = st.columns(2)
        with c_sec_ogr:
            secili_ogr = st.selectbox("Seçili Öğretmen:", tum_ogretmenler)
        with c_sec_gun:
            hedef_gun = st.selectbox("Hedef Gün:", GUNLER, key="hedef_gun_sec")
        
        ogle_sinir = int(st.session_state.ogle_arasi_ders)
        st.markdown("#### ⚡ Hızlı Gün Kısıtları")
        r1_col1, r1_col2 = st.columns(2)
        with r1_col1:
            if st.button(f"☀️ {hedef_gun} Öğleden Önceleri Kapat (1-{ogle_sinir})", use_container_width=True):
                for s in range(min(ogle_sinir, st.session_state.gun_saatleri[hedef_gun])):
                    st.session_state.kilitler.add((secili_ogr, hedef_gun, s))
                verileri_kaydet()
                st.rerun()
        with r1_col2:
            if st.button(f"🌙 {hedef_gun} Öğleden Sonraları Kapat ({ogle_sinir+1}+)", use_container_width=True):
                for s in range(ogle_sinir, st.session_state.gun_saatleri[hedef_gun]):
                    st.session_state.kilitler.add((secili_ogr, hedef_gun, s))
                verileri_kaydet()
                st.rerun()

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

        st.write("---")
        st.write(f"*{secili_ogr} için saat bazlı kilit durumu (🔴 = Kilitli/Boş, 🟢 = Açık/Müsait):*")
        grid_cols = st.columns(5)
        for i, gun in enumerate(GUNLER):
            with grid_cols[i]:
                max_s = st.session_state.gun_saatleri[gun]
                st.markdown(f"**{gun}** ({max_s}s)")
                for s in range(max_s):
                    kilitli_mi = (secili_ogr, gun, s) in st.session_state.kilitler
                    btn_txt = f"🔴 {s+1}.D" if kilitli_mi else f"🟢 {s+1}.D"
                    if st.button(btn_txt, key=f"gr_{secili_ogr}_{gun}_{s}", use_container_width=True):
                        if kilitli_mi:
                            st.session_state.kilitler.remove((secili_ogr, gun, s))
                        else:
                            st.session_state.kilitler.add((secili_ogr, gun, s))
                        verileri_kaydet()
                        st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

# ----------------------------------------------------
# TAB 4: DAĞITIM MOTORU
# ----------------------------------------------------
with tab_motor:
    if not tum_ogretmenler or not siniflar:
        st.warning("⚠️ Dağıtım için öğretmen ve sınıf gereklidir.")
    else:
        st.markdown('<div class="dashboard-card">', unsafe_allow_html=True)
        st.subheader("🚀 Akıllı Optimizasyon Motoru")
        
        if st.session_state.teshis_hatalari:
            st.error("⛔ **DERS PROGRAMI Çakışma veya Kapasite Engeline Takıldı!**")
            for idx, th in enumerate(st.session_state.teshis_hatalari):
                c_bilgi, c_soft = st.columns([3, 1])
                with c_bilgi:
                    st.markdown(f"**🚨 {th['Tip']} ({th['Hedef']}):** {th['Detay']}")
                with c_soft:
                    if st.button("🔓 Kilidi Aç", key=f"soft_coz_{idx}", use_container_width=True):
                        if th["Tip"] == "Kapasite Aşımı":
                            hedef_ogr = th["Hedef"]
                            ogr_kilitler = sorted([k for k in st.session_state.kilitler if k[0] == hedef_ogr], key=lambda x: (x[1], -x[2]), reverse=True)
                            for silinecek in ogr_kilitler[:th.get("EksikSaat", 1)]:
                                st.session_state.kilitler.discard(silinecek)
                        st.session_state.teshis_hatalari = []
                        verileri_kaydet()
                        st.rerun()
            st.divider()

        if st.button("🔥 Tüm Okulun Programını Dağıt ve Çöz", type="primary", use_container_width=True):
            hatalar = cakismalari_denetle(df_aktif, st.session_state.gun_saatleri, st.session_state.kilitler, tum_ogretmenler, siniflar)
            if hatalar:
                st.session_state.teshis_hatalari = hatalar
                st.session_state.cozum_ogretmen = None
                st.session_state.cozum_sinif = None
                st.rerun()
            else:
                st.session_state.teshis_hatalari = []
                with st.spinner("OR-Tools ile çakışmasız program hesaplanıyor..."):
                    model = cp_model.CpModel()
                    zaman_dilimleri = [(g, s) for g in GUNLER for s in range(st.session_state.gun_saatleri[g])]
                    dersler = df_aktif.to_dict("records")
                    
                    x = {}
                    for i, d in enumerate(dersler):
                        for g, s in zaman_dilimleri:
                            x[(i, g, s)] = model.NewBoolVar(f"x_{i}_{g}_{s}")

                    for i, d in enumerate(dersler):
                        ogr = d["Öğretmen"]
                        for g, s in zaman_dilimleri:
                            if (ogr, g, s) in st.session_state.kilitler:
                                model.Add(x[(i, g, s)] == 0)

                    for i, d in enumerate(dersler):
                        model.Add(sum(x[(i, g, s)] for g, s in zaman_dilimleri) == int(d["Saat"]))

                    for snf in siniflar:
                        snf_i = [i for i, d in enumerate(dersler) if d["Sınıf"] == snf]
                        for g, s in zaman_dilimleri:
                            model.Add(sum(x[(i, g, s)] for i in snf_i) <= 1)

                    for ogr in tum_ogretmenler:
                        ogr_i = [i for i, d in enumerate(dersler) if d["Öğretmen"] == ogr]
                        for g, s in zaman_dilimleri:
                            model.Add(sum(x[(i, g, s)] for i in ogr_i) <= 1)

                    solver = cp_model.CpSolver()
                    solver.parameters.max_time_in_seconds = 30.0
                    durum = solver.Solve(model)

                    if durum in (cp_model.OPTIMAL, cp_model.FEASIBLE):
                        prog_ogr = {o: {g: ["-"] * 8 for g in GUNLER} for o in tum_ogretmenler}
                        prog_snf = {snf: {g: ["-"] * 8 for g in GUNLER} for snf in siniflar}
                        
                        for g in GUNLER:
                            for s in range(8):
                                if s >= st.session_state.gun_saatleri[g]:
                                    for o in tum_ogretmenler:
                                        prog_ogr[o][g][s] = "---"
                                    for snf in siniflar:
                                        prog_snf[snf][g][s] = "---"

                        for i, d in enumerate(dersler):
                            ogr = d["Öğretmen"]
                            snf = d["Sınıf"]
                            drs = d["Ders"]
                            for g, s in zaman_dilimleri:
                                if solver.Value(x[(i, g, s)]) == 1:
                                    prog_ogr[ogr][g][s] = f"{snf} ({drs})"
                                    prog_snf[snf][g][s] = f"{drs} ({ogr})"

                        for (ogr, g, s) in st.session_state.kilitler:
                            if prog_ogr[ogr][g][s] == "-":
                                prog_ogr[ogr][g][s] = "🔒 KİLİTLİ"

                        st.session_state.cozum_ogretmen = prog_ogr
                        st.session_state.cozum_sinif = prog_snf

                        # Nöbet Hesaplama
                        nobet_atamalari = []
                        nobetci_ogrler = df_aktif[df_aktif["Nöbetçi"] == True]["Öğretmen"].unique()
                        for ogr in nobetci_ogrler:
                            gun_ders_sayilari = {}
                            for g in GUNLER:
                                max_s = st.session_state.gun_saatleri[g]
                                ds = sum(1 for s in range(max_s) if prog_ogr[ogr][g][s] not in ["-", "---", "🔒 KİLİTLİ"])
                                gun_ders_sayilari[g] = ds
                            uygun = {g: ds for g, ds in gun_ders_sayilari.items() if ds > 0}
                            if uygun:
                                en_iyigun = min(uygun, key=uygun.get)
                                nobet_atamalari.append({"Öğretmen": ogr, "Nöbet Günü": en_iyigun, "O Günkü Ders": gun_ders_sayilari[en_iyigun], "Durum": "Uygun ✅"})
                            else:
                                nobet_atamalari.append({"Öğretmen": ogr, "Nöbet Günü": "Ders Yok", "O Günkü Ders": 0, "Durum": "Atanamadı"})
                        st.session_state.nobet_listesi = pd.DataFrame(nobet_atamalari)

                        st.success("🎉 MÜKEMMEL! Program sıfır çakışmayla başarıyla dağıtıldı.")
                        st.rerun()
                    else:
                        st.error("❌ Çözüm bulunamadı, kısıtları gözden geçirin.")

        if st.session_state.cozum_ogretmen is not None:
            st.divider()
            c_mod, c_sec = st.columns([1, 2])
            with c_mod:
                goruntu_modu = st.radio("İnceleme Modu:", ["👨‍🏫 Öğretmen", "🏫 Şube"])
            if "Öğretmen" in goruntu_modu:
                with c_sec:
                    secilen_hoca = st.selectbox("Öğretmen Programı:", tum_ogretmenler, key="inc_ogr")
                st.table(pd.DataFrame(st.session_state.cozum_ogretmen[secilen_hoca], index=zil_etiketleri))
            else:
                with c_sec:
                    secilen_sinif = st.selectbox("Şube Programı:", siniflar, key="inc_snf")
                st.table(pd.DataFrame(st.session_state.cozum_sinif[secilen_sinif], index=zil_etiketleri))
        st.markdown('</div>', unsafe_allow_html=True)

# ----------------------------------------------------
# TAB 5: RESMÎ PDF ÇIKTILARI
# ----------------------------------------------------
with tab_pdf:
    if st.session_state.cozum_sinif is None:
        st.warning("⚠️ Lütfen önce 4. Sekmeden programı dağıtın.")
    else:
        st.markdown('<div class="dashboard-card">', unsafe_allow_html=True)
        st.subheader("📄 Resmî MEB Formatında Çıktılar")
        pdf_secenek = st.radio("Yazdırma Modu:", ["👤 Tek Öğretmen", "🏫 Tek Şube", "📚 Tüm Öğretmenler (Toplu)", "🏫 Tüm Şubeler (Toplu)"], horizontal=True)
        st.divider()

        if pdf_secenek == "👤 Tek Öğretmen":
            sec_o = st.selectbox("Öğretmen:", tum_ogretmenler, key="pdf_tek_o")
            df_g = pd.DataFrame(st.session_state.cozum_ogretmen[sec_o], index=zil_etiketleri)
            nobet_g = ""
            if st.session_state.nobet_listesi is not None:
                nb = st.session_state.nobet_listesi[st.session_state.nobet_listesi["Öğretmen"] == sec_o]
                if not nb.empty: nobet_g = nb.iloc[0]["Nöbet Günü"]
            components.html(render_meb_print_view([("ÖĞRETMEN HAFTALIK DERS PROGRAMI", f"Öğretmen: {sec_o}", df_g, nobet_g)]), height=560, scrolling=True)

        elif pdf_secenek == "🏫 Tek Şube":
            sec_s = st.selectbox("Şube:", siniflar, key="pdf_tek_s")
            df_g = pd.DataFrame(st.session_state.cozum_sinif[sec_s], index=zil_etiketleri)
            components.html(render_meb_print_view([("SINIF HAFTALIK DERS PROGRAMI", f"Şube: {sec_s}", df_g, "")]), height=560, scrolling=True)

        elif pdf_secenek == "📚 Tüm Öğretmenler (Toplu)":
            toplu_ogr = []
            for o in tum_ogretmenler:
                df_g = pd.DataFrame(st.session_state.cozum_ogretmen[o], index=zil_etiketleri)
                nobet_g = ""
                if st.session_state.nobet_listesi is not None:
                    nb = st.session_state.nobet_listesi[st.session_state.nobet_listesi["Öğretmen"] == o]
                    if not nb.empty: nobet_g = nb.iloc[0]["Nöbet Günü"]
                toplu_ogr.append(("ÖĞRETMEN HAFTALIK DERS PROGRAMI", f"Öğretmen: {o}", df_g, nobet_g))
            components.html(render_meb_print_view(toplu_ogr, toplu_mu=True), height=680, scrolling=True)

        else:
            toplu_snf = []
            for s in siniflar:
                df_g = pd.DataFrame(st.session_state.cozum_sinif[s], index=zil_etiketleri)
                toplu_snf.append(("SINIF HAFTALIK DERS PROGRAMI", f"Şube: {s}", df_g, ""))
            components.html(render_meb_print_view(toplu_snf, toplu_mu=True), height=680, scrolling=True)
        st.markdown('</div>', unsafe_allow_html=True)

# ----------------------------------------------------
# TAB 6: İDARECİ KONSOLİDE ÇARŞAFI
# ----------------------------------------------------
with tab_carsaf:
    st.markdown('<div class="dashboard-card">', unsafe_allow_html=True)
    st.subheader("📋 İdareci Konsolide Çarşaf Çizelgesi")
    if st.session_state.cozum_ogretmen is not None:
        carsaf_gorunum = st.radio("Çarşaf Türü:", ["👨‍🏫 Öğretmen Bazlı", "🏫 Şube Bazlı"], horizontal=True)
        
        col_tuples = []
        gun_saat_listesi = []
        for g in GUNLER:
            max_s = st.session_state.gun_saatleri[g]
            gun_saat_listesi.append((g, max_s))
            for s in range(max_s):
                col_tuples.append((g, f"{s+1}.D"))
        multi_cols = pd.MultiIndex.from_tuples(col_tuples, names=["Gün", "Saat"])

        if "Öğretmen" in carsaf_gorunum:
            data_dict, excel_matrisi = {}, {}
            for ogr in tum_ogretmenler:
                row_vals, excel_row = [], {}
                for g in GUNLER:
                    for s in range(st.session_state.gun_saatleri[g]):
                        raw_v = st.session_state.cozum_ogretmen[ogr][g][s]
                        hucre = f"{raw_v.split(' (')[0].strip()}-{kisalt_ders(raw_v.split(' (')[1].replace(')', '').strip())}" if raw_v not in ["-", "---", "🔒 KİLİTLİ"] and " (" in raw_v else ""
                        row_vals.append(hucre)
                        excel_row[(g, s)] = hucre
                data_dict[ogr] = row_vals
                excel_matrisi[ogr] = excel_row

            st.dataframe(pd.DataFrame.from_dict(data_dict, orient='index', columns=multi_cols), use_container_width=True, height=450)
            st.download_button("📥 Öğretmen Çarşafını Excel İndir (.xlsx)", data=stil_carsaf_excel_uret(excel_matrisi, gun_saat_listesi, "Öğretmen", st.session_state.okul_adi), file_name="ogretmen_carsaf.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True)
        else:
            data_dict, excel_matrisi = {}, {}
            for snf in siniflar:
                row_vals, excel_row = [], {}
                for g in GUNLER:
                    for s in range(st.session_state.gun_saatleri[g]):
                        raw_v = st.session_state.cozum_sinif[snf][g][s]
                        hucre = f"{kisalt_ders(raw_v.split(' (')[0].strip())}-{kisalt_ogretmen(raw_v.split(' (')[1].replace(')', '').strip())}" if raw_v not in ["-", "---", "🔒 KİLİTLİ"] and " (" in raw_v else ""
                        row_vals.append(hucre)
                        excel_row[(g, s)] = hucre
                data_dict[snf] = row_vals
                excel_matrisi[snf] = excel_row

            st.dataframe(pd.DataFrame.from_dict(data_dict, orient='index', columns=multi_cols), use_container_width=True, height=450)
            st.download_button("📥 Şube Çarşafını Excel İndir (.xlsx)", data=stil_carsaf_excel_uret(excel_matrisi, gun_saat_listesi, "Sınıf", st.session_state.okul_adi), file_name="sube_carsaf.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True)
    else:
        st.info("Program henüz dağıtılmadı.")
    st.markdown('</div>', unsafe_allow_html=True)

# ----------------------------------------------------
# TAB 7: AKILLI NÖBET
# ----------------------------------------------------
with tab_nobet:
    st.markdown('<div class="dashboard-card">', unsafe_allow_html=True)
    st.subheader("🛡️ Akıllı Nöbet Çizelgesi")
    if st.session_state.nobet_listesi is not None:
        st.dataframe(st.session_state.nobet_listesi, use_container_width=True)
        buf_n = io.BytesIO()
        with pd.ExcelWriter(buf_n, engine='openpyxl') as writer:
            st.session_state.nobet_listesi.to_excel(writer, index=False)
        st.download_button("📥 Nöbet Çizelgesini Excel İndir (.xlsx)", data=buf_n.getvalue(), file_name="nobet_cizelgesi.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True)
    else:
        st.info("Dağıtım yapıldığında nöbet çizelgesi burada görünecektir.")
    st.markdown('</div>', unsafe_allow_html=True)
