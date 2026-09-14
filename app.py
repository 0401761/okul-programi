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
import io

st.set_page_config(page_title="Akıllı Okul Ders Dağıtım & Yönetim Sistemi", layout="wide")

# ==========================================
# 0. SİMETRİK GÖRSEL STİL DOKUNUŞU (CSS)
# ==========================================
st.markdown("""
<style>
    .stButton > button {
        width: 100% !important;
        border-radius: 8px !important;
        min-height: 48px !important;
        height: 48px !important;
        font-weight: 600 !important;
        font-size: 14px !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        margin: 0px !important;
    }
    div[data-testid="stMetricValue"] {
        font-size: 1.3rem;
    }
    .custom-card {
        border: 1px solid #e6e9ef;
        border-radius: 8px;
        padding: 15px;
        background-color: #fafbfc;
        margin-bottom: 15px;
    }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 1. MERKEZİ HAFIZA & OKUL KÜNYESİ
# ==========================================
GUNLER = ["Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma"]

if "okul_adi" not in st.session_state:
    st.session_state.okul_adi = "İMAM HATİP ORTAOKULU"

if "egitim_yili" not in st.session_state:
    st.session_state.egitim_yili = "2026-2027 Eğitim Öğretim Yılı"

if "mudur_adi" not in st.session_state:
    st.session_state.mudur_adi = "Okul Müdürü"

# Zil Saatleri Parametreleri (Öğleden önce 5 ders standardı)
if "ders_baslangic" not in st.session_state:
    st.session_state.ders_baslangic = "08:30"
if "ders_dk" not in st.session_state:
    st.session_state.ders_dk = 40
if "teneffus_dk" not in st.session_state:
    st.session_state.teneffus_dk = 10

# Bireysel Teneffüs Süreleri Ekseni (1. Teneffüs 20 dk Kahvaltı / Beslenme)
if "teneffus_sureleri" not in st.session_state:
    st.session_state.teneffus_sureleri = {
        1: 20,
        2: 10,
        3: 10,
        4: 10,
        5: 10,
        6: 10,
        7: 10
    }

# Öğle Arası: 5. Dersten sonra (~12:40)
if "ogle_arasi_ders" not in st.session_state:
    st.session_state.ogle_arasi_ders = 5
if "ogle_arasi_dk" not in st.session_state:
    st.session_state.ogle_arasi_dk = 45

if "gun_saatleri" not in st.session_state:
    st.session_state.gun_saatleri = {
        "Pazartesi": 7,
        "Salı": 7,
        "Çarşamba": 8,
        "Perşembe": 7,
        "Cuma": 7
    }

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

# MEB DERS KISALTMA SÖZLÜĞÜ
DERS_KISALTMALARI = {
    "Türkçe": "TRK",
    "Matematik": "MAT",
    "Fen Bilimleri": "FEN",
    "Sosyal Bilgiler": "SOS",
    "İnkılap Tarihi": "İNK",
    "T.C. İnkılap Tarihi ve Atatürkçülük": "İNK",
    "İngilizce": "İNG",
    "Yabancı Dil": "İNG",
    "Din Kültürü": "DKAB",
    "Din Kültürü ve Ahlak Bilgisi": "DKAB",
    "Kur'an-ı Kerim": "KUR",
    "Peygamberimizin Hayatı": "PEYG",
    "Temel Dini Bilgiler": "TDB",
    "Arapça": "ARP",
    "Beden Eğitimi": "BED",
    "Beden Eğitimi ve Spor": "BED",
    "Bilişim Teknolojileri": "BİL",
    "Bilişim Teknolojileri ve Yazılım": "BİL",
    "Teknoloji ve Tasarım": "TEK",
    "Görsel Sanatlar": "GÖR",
    "Müzik": "MÜZ",
    "Rehberlik": "REH",
    "Rehberlik ve Kariyer Planlama": "REH",
    "Seçmeli Ders": "SEÇ",
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

# Örnek 24 Şubeli Veri Motoru
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
    d.text((40, y + 15), "... [5A-5F, 6A-6F, 7A-7F, 8A-8F Tum Subeler ve 40 Ogretmen Resmi Cizelgesi] ...", fill=(100, 100, 100))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()

if "ders_listesi" not in st.session_state:
    st.session_state.ders_listesi = varsayilan_iho_verisi()

# ZİL SAATLERİ HESAPLAMA MOTORU
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

# ==========================================
# 2. MEB BASKI VE PDF ŞABLONU
# ==========================================
def render_meb_print_view(icerik_listesi, toplu_mu=False):
    pages_html = ""
    for idx, (baslik, alt_baslik, df_tablo, nobet_bilgisi) in enumerate(icerik_listesi):
        html_tablo = "<table class='table-meb' border='1'><thead><tr><th>Ders / Saat</th>"
        for col in df_tablo.columns:
            html_tablo += f"<th>{col}</th>"
        html_tablo += "</tr></thead><tbody>"
        
        for idx_name, row in df_tablo.iterrows():
            html_tablo += f"<tr><td style='background-color:#f9f9f9; font-weight:bold; font-size:10px;'>{idx_name}</td>"
            for val in row:
                val_str = str(val)
                if val_str == "🔒 KİLİTLİ":
                    html_tablo += f"<td style='background-color:#f0f0f0; color:#888;'>🔒 Boş Saat</td>"
                elif val_str in ["-", "---"]:
                    html_tablo += f"<td style='color:#ccc;'>-</td>"
                else:
                    html_tablo += f"<td>{val_str}</td>"
            html_tablo += "</tr>"
        html_tablo += "</tbody></table>"

        page_break_class = "page-break" if (toplu_mu and idx < len(icerik_listesi) - 1) else ""
        
        pages_html += f"""
        <div class="printable-page {page_break_class}">
            <div class="header-box">
                <h2>T.C. MİLLÎ EĞİTİM BAKANLIĞI</h2>
                <h3>{st.session_state.okul_adi} MÜDÜRLÜĞÜ</h3>
                <div><small>{st.session_state.egitim_yili}</small></div>
                <h4>{baslik}</h4>
                <div><b>{alt_baslik}</b> {f'| <span style=\"color:#d9534f;\">Nöbet Günü: {nobet_bilgisi}</span>' if nobet_bilgisi else ''}</div>
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
        body {{ font-family: Arial, sans-serif; margin: 10px; color: #000; }}
        .header-box {{ text-align: center; border-bottom: 2px solid #000; padding-bottom: 8px; margin-bottom: 12px; }}
        .header-box h2 {{ margin: 2px; font-size: 16px; }}
        .header-box h3 {{ margin: 2px; font-size: 13px; font-weight: normal; }}
        .header-box h4 {{ margin: 3px; font-size: 15px; color: #b30000; }}
        .table-meb {{ width: 100%; border-collapse: collapse; text-align: center; font-size: 11px; }}
        .table-meb th {{ background-color: #f2f2f2; padding: 6px; font-weight: bold; }}
        .table-meb td {{ padding: 5px; height: 28px; }}
        .footer-box {{ margin-top: 20px; display: flex; justify-content: space-between; font-size: 12px; }}
        .btn-print {{ background-color: #0066cc; color: white; border: none; padding: 10px 20px; font-size: 14px; font-weight: bold; border-radius: 5px; cursor: pointer; margin-bottom: 15px; }}
        .printable-page {{ padding-bottom: 30px; }}
        @media print {{
            .no-print {{ display: none; }}
            body {{ margin: 0; }}
            .page-break {{ page-break-after: always; break-after: page; display: block; }}
        }}
    </style>
    </head>
    <body>
        <div class="no-print">
            <button class="btn-print" onclick="window.print()">🖨️ Sayfayı Yazdır / PDF Olarak Kaydet</button>
            <span style="font-size: 13px; color: #555; margin-left: 10px;">(Açılan pencerede <b>Hedef: PDF Olarak Kaydet</b> seçebilirsiniz)</span>
        </div>
        {pages_html}
    </body>
    </html>
    """

# ==========================================
# 3. ÖZEL DİZAYNLI ÇARŞAF EXCEL MOTORU
# ==========================================
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

# ==========================================
# 4. ÇAKIŞMA & ENGEL TEŞHİS MOTORU
# ==========================================
def cakismalari_denetle(df_ders, gun_saatleri, kilitler, tum_ogretmenler, siniflar):
    teshisler = []
    toplam_haftalik_kapasite = sum(gun_saatleri.values())
    
    # 1. Bireysel Öğretmen Kapasite Kontrolü
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
                "Detay": f"Haftalık **{ders_yuku} saat** dersi var, fakat **{kilit_sayisi} saati kilitlendiği** için açıkta sadece **{acik_kalan_saat} saat** kalıyor.",
                "Cozum": f"Bu öğretmenin en az **{eksik_saat} saatlik** kilidi açılmalıdır!"
            })
            
    # 2. Okul Geneli Saatlik Öğretmen Açığı Kontrolü
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
                    "Detay": f"Okuldaki {toplam_sube_sayisi} şubenin aynı anda derste olması gerekirken, kilitler yüzünden sadece **{musait_hoca_sayisi} öğretmen** serbest.",
                    "Cozum": f"Bu saat diliminde kilitli olan en az **{acik} öğretmenin** kilidi kaldırılmalıdır!"
                })
                
    return teshisler

# ==========================================
# 5. GÖRSEL PANEL VE ANA SEKMELER
# ==========================================
st.title(f"🏫 {st.session_state.okul_adi} - Akıllı Ders & Nöbet Yönetim Sistemi")

tab_okul, tab_kisi_ders, tab_kilit, tab_motor, tab_pdf, tab_carsaf, tab_nobet = st.tabs([
    "🏛️ 1. Okul & Zil Saatleri",
    "👥 2. Öğretmen, Sınıf & Ders Yönetimi",
    "🔒 3. Güne Özel Kilit Matrisi",
    "🚀 4. Dağıt & Sabitle",
    "📄 5. Resmî PDF Çıktıları",
    "📋 6. İdareci Çarşafı",
    "🛡️ 7. Akıllı Nöbet"
])

# ----------------------------------------------------
# TAB 1: OKUL KÜNYESİ VE ZİL SAATLERİ (SİMETRİK)
# ----------------------------------------------------
with tab_okul:
    st.subheader("🏛️ Okul Genel Bilgileri & Resmî Başlıklar")
    c_ok1, c_ok2, c_ok3 = st.columns(3)
    with c_ok1:
        st.session_state.okul_adi = st.text_input("Okul Adı", value=st.session_state.okul_adi)
    with c_ok2:
        st.session_state.egitim_yili = st.text_input("Eğitim Öğretim Yılı", value=st.session_state.egitim_yili)
    with c_ok3:
        st.session_state.mudur_adi = st.text_input("Okul Müdürü Adı / Ünvanı", value=st.session_state.mudur_adi)

    st.divider()
    st.subheader("⏰ Genel Ders ve Öğle Arası Parametreleri")
    c_z1, c_z2, c_z3, c_z4 = st.columns(4)
    with c_z1:
        st.session_state.ders_baslangic = st.text_input("1. Ders Başlama Saati", value=st.session_state.ders_baslangic, placeholder="08:30")
    with c_z2:
        st.session_state.ders_dk = st.number_input("Ders Süresi (Dk)", min_value=30, max_value=60, value=int(st.session_state.ders_dk))
    with c_z3:
        st.session_state.ogle_arasi_ders = st.number_input("Öğle Arası Kaçıncı Dersten Sonra?", min_value=2, max_value=6, value=int(st.session_state.ogle_arasi_ders))
    with c_z4:
        st.session_state.ogle_arasi_dk = st.number_input("Öğle Arası Süresi (Dk)", min_value=20, max_value=90, value=int(st.session_state.ogle_arasi_dk))

    st.write("---")
    st.markdown("#### ☕ Teneffüs Ayarlama Ekseni (Kahvaltı / Beslenme)")
    st.caption("1. dersten sonraki kahvaltı teneffüsünü 20 dk yapabilir veya diğer teneffüs sürelerini dilediğiniz gibi güncelleyebilirsiniz:")
    
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
                st.session_state.teneffus_sureleri[t_idx] = st.number_input(
                    etiket,
                    min_value=5,
                    max_value=60,
                    value=int(st.session_state.teneffus_sureleri.get(t_idx, 10)),
                    key=f"ten_input_{t_idx}"
                )

    st.write("📋 **Oluşturulan Resmî Günlük Zaman Çizelgesi:**")
    zil_listesi = zil_saatlerini_uret(8)
    cols_zil_gor = st.columns(8)
    for i, z in enumerate(zil_listesi):
        with cols_zil_gor[i]:
            st.metric(f"{i+1}. Ders", z)

# ----------------------------------------------------
# TAB 2: ÖĞRETMEN, SINIF & DERS YÖNETİMİ (SİMETRİK)
# ----------------------------------------------------
with tab_kisi_ders:
    st.subheader("👥 Kadro, Sınıf ve Ders Tanımlama Masası")
    
    c_btn1, c_btn2 = st.columns(2)
    with c_btn1:
        if st.button("🗑️ TÜM LİSTEYİ SIFIRLA (Temizle)", use_container_width=True):
            st.session_state.ders_listesi = pd.DataFrame(columns=["Öğretmen", "Sınıf", "Ders", "Saat", "Nöbetçi"])
            st.session_state.kilitler = set()
            st.session_state.dondurulan_ogretmenler = set()
            st.session_state.cozum_ogretmen = None
            st.session_state.cozum_sinif = None
            st.session_state.teshis_hatalari = []
            st.rerun()
    with c_btn2:
        if st.button("🔄 Örnek 24 Şubeli İHO Verisini Yükle", use_container_width=True):
            st.session_state.ders_listesi = varsayilan_iho_verisi()
            st.session_state.cozum_ogretmen = None
            st.session_state.cozum_sinif = None
            st.session_state.teshis_hatalari = []
            st.rerun()

    st.write("---")
    col_sol, col_sag = st.columns(2)

    with col_sol:
        st.markdown("#### 👨‍🏫 1. Öğretmen Ekle & Sil")
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
                        st.success(f"{yeni_hoca} eklendi.")
                        st.rerun()

        with c_o_sil:
            if mevcut_ogretmenler:
                silinecek_hoca = st.selectbox("Silinecek Öğretmen:", mevcut_ogretmenler, key="sil_hoca_sec")
                if st.button("🗑️ Seçili Öğretmeni Sil", use_container_width=True):
                    st.session_state.ders_listesi = st.session_state.ders_listesi[st.session_state.ders_listesi["Öğretmen"] != silinecek_hoca]
                    st.session_state.kilitler = {k for k in st.session_state.kilitler if k[0] != silinecek_hoca}
                    st.session_state.dondurulan_ogretmenler.discard(silinecek_hoca)
                    st.warning(f"{silinecek_hoca} ve dersleri silindi.")
                    st.rerun()
            else:
                st.info("Kayıtlı öğretmen yok.")

    with col_sag:
        st.markdown("#### 🏫 2. Sınıf / Şube Ekle & Sil")
        mevcut_siniflar = sorted([s for s in st.session_state.ders_listesi["Sınıf"].dropna().unique() if s != "-"]) if not st.session_state.ders_listesi.empty else []
        c_s_ekle, c_s_sil = st.columns(2)
        with c_s_ekle:
            with st.form("snf_ekle_form", clear_on_submit=True):
                yeni_snf = st.text_input("Şube Adı", placeholder="Örn: 5G veya 8A")
                if st.form_submit_button("➕ Şubeyi Ekle", use_container_width=True):
                    if yeni_snf.strip():
                        snf_kod = yeni_snf.strip().upper()
                        satir = pd.DataFrame([{"Öğretmen": "-", "Sınıf": snf_kod, "Ders": "Kayıt", "Saat": 0, "Nöbetçi": False}])
                        st.session_state.ders_listesi = pd.concat([st.session_state.ders_listesi, satir], ignore_index=True)
                        st.success(f"{snf_kod} şubesi eklendi.")
                        st.rerun()

        with c_s_sil:
            if mevcut_siniflar:
                silinecek_snf = st.selectbox("Silinecek Şube:", mevcut_siniflar, key="sil_snf_sec")
                if st.button("🗑️ Seçili Şubeyi Sil", use_container_width=True):
                    st.session_state.ders_listesi = st.session_state.ders_listesi[st.session_state.ders_listesi["Sınıf"] != silinecek_snf]
                    st.warning(f"{silinecek_snf} şubesi silindi.")
                    st.rerun()
            else:
                st.info("Kayıtlı şube yok.")

    st.write("---")
    st.markdown("#### 📚 3. Ders Eşleştirmesi Ekle & Sil")
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
                            "Öğretmen": sec_ogr,
                            "Sınıf": sec_snf,
                            "Ders": drs_ad.strip(),
                            "Saat": int(drs_saat),
                            "Nöbetçi": drs_nobet
                        }])
                        st.session_state.ders_listesi = pd.concat([st.session_state.ders_listesi, yeni_ders], ignore_index=True)
                        st.success(f"{sec_ogr} -> {sec_snf} {drs_ad} ({drs_saat} saat) eklendi.")
                        st.rerun()
        else:
            st.warning("Ders ataması yapmak için en az 1 öğretmen ve 1 şube eklemelisiniz.")

    with c_d_tablo:
        df_gecerli_dersler = st.session_state.ders_listesi[st.session_state.ders_listesi["Saat"] > 0]
        if not df_gecerli_dersler.empty:
            st.write(f"📋 **Kayıtlı Ders Dağılımı ({len(df_gecerli_dersler)} Atama / {df_gecerli_dersler['Saat'].sum()} Saat):**")
            st.dataframe(df_gecerli_dersler[["Öğretmen", "Sınıf", "Ders", "Saat", "Nöbetçi"]], height=210, use_container_width=True)
            
            atama_etiketleri = [f"{r['Öğretmen']} | {r['Sınıf']} - {r['Ders']} ({r['Saat']} Saat)" for _, r in df_gecerli_dersler.iterrows()]
            secilen_sil_idx = st.selectbox("Listeden Çıkarılacak Ders Ataması:", range(len(atama_etiketleri)), format_func=lambda i: atama_etiketleri[i])
            if st.button("🗑️ Seçili Ders Atamasını Sil", use_container_width=True):
                hedef_row = df_gecerli_dersler.iloc[secilen_sil_idx]
                st.session_state.ders_listesi = st.session_state.ders_listesi.drop(hedef_row.name).reset_index(drop=True)
                st.rerun()
        else:
            st.info("Henüz atanmış aktif bir ders saati bulunmuyor.")

    st.write("---")
    st.markdown("#### 📊 4. Excel ile Toplu Yükleme & 📸 5. Fotoğraftan OCR")
    col_ex, col_foto = st.columns(2)
    
    with col_ex:
        st.markdown("**Excel ile Toplu Yükleme:**")
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
            data=buf_ex.getvalue(),
            file_name="okul_ders_sablonu.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True
        )
        up_file = st.file_uploader("Excel Dosyası (.xlsx)", type=["xlsx", "xls"], key="up_excel_key")
        if up_file is not None:
            try:
                gelen_df = pd.read_excel(up_file)
                if {"Öğretmen", "Sınıf", "Ders", "Saat"}.issubset(gelen_df.columns):
                    gelen_df["Nöbetçi"] = gelen_df["Nöbet"].astype(str).str.lower().isin(["evet", "true", "1"]) if "Nöbet" in gelen_df.columns else True
                    st.session_state.ders_listesi = gelen_df[["Öğretmen", "Sınıf", "Ders", "Saat", "Nöbetçi"]]
                    st.success(f"✅ Excel başarıyla aktarıldı! ({len(gelen_df)} satır)")
                    st.rerun()
                else:
                    st.error("Excel sütunları: Öğretmen, Sınıf, Ders, Saat olmalıdır.")
            except Exception as e:
                st.error(f"Hata: {e}")

    with col_foto:
        st.markdown("**Fotoğraftan / Belgeden Yapay Zekâ ile Liste Yükle:**")
        yuklenen_belge = st.file_uploader("Ders Çizelgesi Fotoğrafı Seç", type=["png", "jpg", "jpeg"], key="belge_ocr_up")
        img_test_bytes = cizelge_gorseli_uret()
        st.download_button(
            label="📥 Test İçin Örnek İHO Çizelgesi İndir (.png)",
            data=img_test_bytes,
            file_name="ornek_iho_cizelgesi.png",
            mime="image/png",
            use_container_width=True
        )
        api_anahtari = st.text_input("Google Gemini API Anahtarı (Opsiyonel):", type="password", placeholder="AIzaSy...")
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
                                    raw_cevap = raw_cevap.split("
