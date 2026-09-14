import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
from ortools.sat.python import cp_model
from datetime import datetime, timedelta
import io

st.set_page_config(page_title="Akıllı Okul Ders Dağıtım & Yönetim Sistemi", layout="wide")

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

# Zil Saatleri Parametreleri
if "ders_baslangic" not in st.session_state:
    st.session_state.ders_baslangic = "08:30"
if "ders_dk" not in st.session_state:
    st.session_state.ders_dk = 40
if "teneffus_dk" not in st.session_state:
    st.session_state.teneffus_dk = 10
if "ogle_arasi_ders" not in st.session_state:
    st.session_state.ogle_arasi_ders = 4
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

if "ihlal_edilen_kilitler" not in st.session_state:
    st.session_state.ihlal_edilen_kilitler = []

if "nobet_listesi" not in st.session_state:
    st.session_state.nobet_listesi = None

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
            cur_t = bitis_t + timedelta(minutes=int(st.session_state.teneffus_dk))
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
                if "🚨" in val_str:
                    html_tablo += f"<td style='background-color:#ffe6e6; color:#cc0000; font-weight:bold;'>{val_str}</td>"
                elif val_str == "🔒 KİLİTLİ":
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
# 3. GÖRSEL PANEL VE ANA SEKMELER
# ==========================================
st.title(f"🏫 {st.session_state.okul_adi} - Akıllı Ders & Nöbet Dağıtım")

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
# TAB 1: OKUL KÜNYESİ VE ZİL SAATLERİ
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
    st.subheader("⏰ Otomatik Zil Saatleri & Öğle Arası Yapılandırması")
    st.caption("Buradaki süreler tüm öğretmen/sınıf programlarına ve PDF çıktılarına otomatik yansır:")
    
    c_z1, c_z2, c_z3, c_z4, c_z5 = st.columns(5)
    with c_z1:
        st.session_state.ders_baslangic = st.text_input("1. Ders Başlama", value=st.session_state.ders_baslangic, placeholder="08:30")
    with c_z2:
        st.session_state.ders_dk = st.number_input("Ders Süresi (Dk)", min_value=30, max_value=60, value=int(st.session_state.ders_dk))
    with c_z3:
        st.session_state.teneffus_dk = st.number_input("Teneffüs (Dk)", min_value=5, max_value=30, value=int(st.session_state.teneffus_dk))
    with c_z4:
        st.session_state.ogle_arasi_ders = st.number_input("Öğle Arası Kaçıncı Dersten Sonra?", min_value=2, max_value=6, value=int(st.session_state.ogle_arasi_ders))
    with c_z5:
        st.session_state.ogle_arasi_dk = st.number_input("Öğle Arası Süresi (Dk)", min_value=20, max_value=90, value=int(st.session_state.ogle_arasi_dk))

    # Hesaplanan Saatlerin Önizlemesi
    st.write("📋 **Oluşturulan Resmî Günlük Zaman Çizelgesi:**")
    zil_listesi = zil_saatlerini_uret(8)
    cols_zil_gor = st.columns(8)
    for i, z in enumerate(zil_listesi):
        with cols_zil_gor[i]:
            st.metric(f"{i+1}. Ders", z)

# ----------------------------------------------------
# TAB 2: ÖĞRETMEN, SINIF & DERS YÖNETİMİ (TAM CRUD)
# ----------------------------------------------------
with tab_kisi_ders:
    st.subheader("👥 Kadro, Sınıf ve Ders Tanımlama Masası")
    
    # Sıfırlama ve Örnek Yükleme Butonları
    c_btn1, c_btn2, c_btn3 = st.columns([1.5, 1.5, 3])
    with c_btn1:
        if st.button("🗑️ TÜM LİSTEYİ SIFIRLA (Temizle)", use_container_width=True):
            st.session_state.ders_listesi = pd.DataFrame(columns=["Öğretmen", "Sınıf", "Ders", "Saat", "Nöbetçi"])
            st.session_state.kilitler = set()
            st.session_state.dondurulan_ogretmenler = set()
            st.session_state.cozum_ogretmen = None
            st.session_state.cozum_sinif = None
            st.rerun()
    with c_btn2:
        if st.button("🔄 Örnek 24 Şubeli İHO Verisini Yükle", use_container_width=True):
            st.session_state.ders_listesi = varsayilan_iho_verisi()
            st.session_state.cozum_ogretmen = None
            st.session_state.cozum_sinif = None
            st.rerun()

    st.write("---")
    col_sol, col_sag = st.columns(2)

    # 1. ÖĞRETMEN EKLE / SİL
    with col_sol:
        st.markdown("#### 👨‍🏫 1. Öğretmen Ekle & Sil")
        mevcut_ogretmenler = sorted(list(st.session_state.ders_listesi["Öğretmen"].dropna().unique())) if not st.session_state.ders_listesi.empty else []
        
        c_o_ekle, c_o_sil = st.columns(2)
        with c_o_ekle:
            with st.form("ogr_ekle_form", clear_on_submit=True):
                yeni_hoca = st.text_input("Öğretmen Adı Soyadı", placeholder="Örn: Hasan Yılmaz")
                yeni_nobet = st.checkbox("Nöbet Tutabilir", value=True)
                if st.form_submit_button("➕ Öğretmeni Ekle"):
                    if yeni_hoca.strip():
                        # Dummy 0 saatlik bir ders ekleyerek havuza kaydedebiliriz
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
                    st.warning(f"{silinecek_hoca} ve tüm dersleri sistemden silindi.")
                    st.rerun()
            else:
                st.info("Kayıtlı öğretmen yok.")

    # 2. SINIF EKLE / SİL
    with col_sag:
        st.markdown("#### 🏫 2. Sınıf / Şube Ekle & Sil")
        mevcut_siniflar = sorted([s for s in st.session_state.ders_listesi["Sınıf"].dropna().unique() if s != "-"]) if not st.session_state.ders_listesi.empty else []
        
        c_s_ekle, c_s_sil = st.columns(2)
        with c_s_ekle:
            with st.form("snf_ekle_form", clear_on_submit=True):
                yeni_snf = st.text_input("Şube Adı", placeholder="Örn: 5G veya 8A")
                if st.form_submit_button("➕ Şubeyi Ekle"):
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
    # 3. DERS ATAMASI EKLE & SİL
    st.markdown("#### 📚 3. Ders Eşleştirmesi Ekle & Sil")
    c_d_ekle, c_d_tablo = st.columns([1.2, 2])
    
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
                
                if st.form_submit_button("➕ Bu Dersi Ata"):
                    if drs_ad.strip():
                        # Geçici kayıt satırlarını temizle
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
            st.dataframe(df_gecerli_dersler[["Öğretmen", "Sınıf", "Ders", "Saat", "Nöbetçi"]], height=240, use_container_width=True)
            
            # Tekil Ders Ataması Silme
            atama_etiketleri = [f"{r['Öğretmen']} | {r['Sınıf']} - {r['Ders']} ({r['Saat']} Saat)" for _, r in df_gecerli_dersler.iterrows()]
            secilen_sil_idx = st.selectbox("Listeden Çıkarılacak Ders Ataması:", range(len(atama_etiketleri)), format_func=lambda i: atama_etiketleri[i])
            if st.button("🗑️ Seçili Ders Atamasını Sil"):
                hedef_row = df_gecerli_dersler.iloc[secilen_sil_idx]
                st.session_state.ders_listesi = st.session_state.ders_listesi.drop(hedef_row.name).reset_index(drop=True)
                st.rerun()
        else:
            st.info("Henüz atanmış aktif bir ders saati bulunmuyor.")

    # 4. EXCEL İLE TOPLU YÜKLEME
    st.write("---")
    st.markdown("#### 📊 Excel ile Toplu Yükleme")
    col_ex1, col_ex2 = st.columns(2)
    with col_ex1:
        st.write("**Boş Excel Şablonu İndir:**")
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
            label="📥 Excel Şablonunu İndir (.xlsx)",
            data=buf_ex.getvalue(),
            file_name="okul_ders_sablonu.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    with col_ex2:
        st.write("**Doldurduğun Exceli Yükle:**")
        up_file = st.file_uploader("Excel Dosyası (.xlsx)", type=["xlsx", "xls"])
        if up_file is not None:
            try:
                gelen_df = pd.read_excel(up_file)
                if {"Öğretmen", "Sınıf", "Ders", "Saat"}.issubset(gelen_df.columns):
                    if "Nöbet" in gelen_df.columns:
                        gelen_df["Nöbetçi"] = gelen_df["Nöbet"].astype(str).str.lower().isin(["evet", "true", "1"])
                    else:
                        gelen_df["Nöbetçi"] = True
                    st.session_state.ders_listesi = gelen_df[["Öğretmen", "Sınıf", "Ders", "Saat", "Nöbetçi"]]
                    st.success(f"✅ Excel başarıyla aktarıldı! Toplam {len(gelen_df)} ders satırı yüklendi.")
                    st.rerun()
                else:
                    st.error("Excel sütunları: Öğretmen, Sınıf, Ders, Saat olmalıdır.")
            except Exception as e:
                st.error(f"Hata: {e}")

# Filtrelenmiş Aktif Veri Seti
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
        st.subheader("🔒 Öğretmen İstekleri & Güne Özel Boş Zaman Ayarları")
        secili_ogr = st.selectbox("Saatlerini Düzenlemek İstediğiniz Öğretmen:", tum_ogretmenler)
        
        if secili_ogr in st.session_state.dondurulan_ogretmenler:
            st.warning(f"📌 **{secili_ogr} hocanın programı SABİTLENMİŞTİR.**")

        st.markdown("#### ⚡ Güne Özel Hızlı Kilit İşlemleri")
        col_gun, col_b1, col_b2, col_b3, col_rst = st.columns([1.5, 1.2, 1.3, 1.3, 1.2])
        with col_gun:
            hedef_gun = st.selectbox("Gün Seç:", GUNLER, key="hedef_gun_sec")
        with col_b1:
            st.write("")
            if st.button(f"🚫 {hedef_gun}'ü Kapat", use_container_width=True):
                for s in range(st.session_state.gun_saatleri[hedef_gun]):
                    st.session_state.kilitler.add((secili_ogr, hedef_gun, s))
                st.rerun()
        with col_b2:
            st.write("")
            if st.button(f"☀️ {hedef_gun} Sabah (1-4)", use_container_width=True):
                for s in range(min(4, st.session_state.gun_saatleri[hedef_gun])):
                    st.session_state.kilitler.add((secili_ogr, hedef_gun, s))
                st.rerun()
        with col_b3:
            st.write("")
            if st.button(f"🌙 {hedef_gun} Öğle (5+)", use_container_width=True):
                for s in range(4, st.session_state.gun_saatleri[hedef_gun]):
                    st.session_state.kilitler.add((secili_ogr, hedef_gun, s))
                st.rerun()
        with col_rst:
            st.write("")
            if st.button("🔄 Kilitleri Sıfırla", use_container_width=True):
                st.session_state.kilitler = {k for k in st.session_state.kilitler if k[0] != secili_ogr}
                st.rerun()

        st.write("---")
        st.write(f"*{secili_ogr} için tekli saat kutuları (🔴 = Kilitli/Boş, 🟢 = Açık):*")
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
                        st.rerun()

# ----------------------------------------------------
# TAB 4: DAĞITIM VE SABİTLEME (DONDURMA)
# ----------------------------------------------------
with tab_motor:
    if not tum_ogretmenler or not siniflar:
        st.warning("⚠️ Dağıtım için en az 1 öğretmen ve 1 sınıf gereklidir.")
    else:
        st.subheader("🚀 Akıllı Dağıtım & Öğretmen Sabitleme (Dondurma)")
        if st.session_state.dondurulan_ogretmenler:
            st.info(f"📌 **Sabitlenmiş Öğretmenler:** {', '.join(st.session_state.dondurulan_ogretmenler)}")

        if st.button("🔥 Tüm Okulun Programını Dağıt / Yeniden Hesapla", type="primary", use_container_width=True):
            with st.spinner("Optimum ders programı hesaplanıyor..."):
                model = cp_model.CpModel()
                zaman_dilimleri = [(g, s) for g in GUNLER for s in range(st.session_state.gun_saatleri[g])]
                dersler = df_aktif.to_dict("records")
                
                x = {}
                for i, d in enumerate(dersler):
                    for g, s in zaman_dilimleri:
                        x[(i, g, s)] = model.NewBoolVar(f"x_{i}_{g}_{s}")

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

                # Dondurulmuş öğretmenleri zorunlu tut
                for ogr in st.session_state.dondurulan_ogretmenler:
                    if ogr in st.session_state.dondurulan_atamalar:
                        for (snf, drs, g, s) in st.session_state.dondurulan_atamalar[ogr]:
                            for i, d in enumerate(dersler):
                                if d["Öğretmen"] == ogr and d["Sınıf"] == snf and d["Ders"] == drs:
                                    model.Add(x[(i, g, s)] == 1)
                                    break

                # Kilitleri soft ceza ile koru
                ihlal_cezasi = []
                for (ogr, g, s) in st.session_state.kilitler:
                    ilgili_i = [i for i, d in enumerate(dersler) if d["Öğretmen"] == ogr]
                    for i in ilgili_i:
                        ihlal_cezasi.append(x[(i, g, s)])

                if ihlal_cezasi:
                    model.Minimize(sum(ihlal_cezasi))

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

                    tespit_edilen_ihlaller = []
                    for i, d in enumerate(dersler):
                        ogr = d["Öğretmen"]
                        snf = d["Sınıf"]
                        drs = d["Ders"]
                        for g, s in zaman_dilimleri:
                            if solver.Value(x[(i, g, s)]) == 1:
                                if (ogr, g, s) in st.session_state.kilitler:
                                    prog_ogr[ogr][g][s] = f"🚨 {snf} ({drs})"
                                    prog_snf[snf][g][s] = f"🚨 {drs} ({ogr})"
                                    tespit_edilen_ihlaller.append({
                                        "Öğretmen": ogr, "Sınıf": snf, "Ders": drs,
                                        "Gün": g, "Saat": s + 1, "raw_s": s
                                    })
                                else:
                                    prog_ogr[ogr][g][s] = f"{snf} ({drs})"
                                    prog_snf[snf][g][s] = f"{drs} ({ogr})"

                    for (ogr, g, s) in st.session_state.kilitler:
                        if prog_ogr[ogr][g][s] == "-":
                            prog_ogr[ogr][g][s] = "🔒 KİLİTLİ"

                    st.session_state.cozum_ogretmen = prog_ogr
                    st.session_state.cozum_sinif = prog_snf
                    st.session_state.ihlal_edilen_kilitler = tespit_edilen_ihlaller

                    # Nöbet Hesaplaması (Boş günlere asla nöbet yazılmaz)
                    nobet_atamalari = []
                    nobetci_ogrler = df_aktif[df_aktif["Nöbetçi"] == True]["Öğretmen"].unique()
                    for ogr in nobetci_ogrler:
                        gun_ders_sayilari = {}
                        for g in GUNLER:
                            fiili_ders = sum(1 for s in range(st.session_state.gun_saatleri[g]) 
                                            if prog_ogr[ogr][g][s] not in ["-", "---", "🔒 KİLİTLİ"])
                            gun_ders_sayilari[g] = fiili_ders
                        
                        okulda_oldugu_gunler = {g: ders_s for g, ders_s in gun_ders_sayilari.items() if ders_s > 0}
                        if okulda_oldugu_gunler:
                            en_uygun_nobet_gunu = min(okulda_oldugu_gunler, key=okulda_oldugu_gunler.get)
                            nobet_atamalari.append({
                                "Öğretmen": ogr,
                                "Nöbet Günü": en_uygun_nobet_gunu,
                                "O Günkü Ders Saati": okulda_oldugu_gunler[en_uygun_nobet_gunu],
                                "Boş Gün Korundu": "Evet ✅"
                            })
                    st.session_state.nobet_listesi = pd.DataFrame(nobet_atamalari)
                    st.rerun()

        # İnceleme & Dondurma
        if st.session_state.cozum_ogretmen is not None:
            st.divider()
            c_mod, c_sec, c_dondur = st.columns([1.5, 2, 2])
            with c_mod:
                goruntu_modu = st.radio("İnceleme Modu:", ["👨‍🏫 Öğretmen Programı", "🏫 Sınıf Programı"])
            
            if "Öğretmen" in goruntu_modu:
                with c_sec:
                    secilen_hoca = st.selectbox("İncelenecek Öğretmen:", tum_ogretmenler, key="inc_ogr")
                with c_dondur:
                    st.write("")
                    dondurulmus_mu = secilen_hoca in st.session_state.dondurulan_ogretmenler
                    if not dondurulmus_mu:
                        if st.button(f"📌 {secilen_hoca} Programını Sabitle (Dondur)", use_container_width=True):
                            atamalar = []
                            for g in GUNLER:
                                for s in range(st.session_state.gun_saatleri[g]):
                                    val = st.session_state.cozum_ogretmen[secilen_hoca][g][s]
                                    if val not in ["-", "---", "🔒 KİLİTLİ"] and "🚨" not in val:
                                        snf_part = val.split(" (")[0]
                                        drs_part = val.split(" (")[1].replace(")", "")
                                        atamalar.append((snf_part, drs_part, g, s))
                            st.session_state.dondurulan_atamalar[secilen_hoca] = atamalar
                            st.session_state.dondurulan_ogretmenler.add(secilen_hoca)
                            st.success(f"{secilen_hoca} donduruldu.")
                            st.rerun()
                    else:
                        if st.button(f"🔓 {secilen_hoca} Sabitlemesini Kaldır", use_container_width=True):
                            st.session_state.dondurulan_ogretmenler.remove(secilen_hoca)
                            if secilen_hoca in st.session_state.dondurulan_atamalar:
                                del st.session_state.dondurulan_atamalar[secilen_hoca]
                            st.rerun()

                df_tab = pd.DataFrame(st.session_state.cozum_ogretmen[secilen_hoca], index=zil_etiketleri)
                st.table(df_tab)
            else:
                with c_sec:
                    secilen_sinif = st.selectbox("İncelenecek Sınıf:", siniflar, key="inc_snf")
                df_tab = pd.DataFrame(st.session_state.cozum_sinif[secilen_sinif], index=zil_etiketleri)
                st.table(df_tab)

# ----------------------------------------------------
# TAB 5: RESMÎ PDF ÇIKTILARI (TEKLİ & TOPLU)
# ----------------------------------------------------
with tab_pdf:
    if st.session_state.cozum_sinif is None:
        st.warning("⚠️ Lütfen önce 4. Sekmeye gidip 'Programı Dağıt' butonuna basın.")
    else:
        st.subheader("📄 Resmî MEB Formatında PDF Çıktıları")
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
        st.divider()

        if pdf_secenek == "👤 Tek Öğretmen Yazdır / PDF Al":
            sec_o = st.selectbox("Öğretmen Seçin:", tum_ogretmenler, key="pdf_tek_o")
            df_g = pd.DataFrame(st.session_state.cozum_ogretmen[sec_o], index=zil_etiketleri)
            nobet_g = ""
            if st.session_state.nobet_listesi is not None:
                nb = st.session_state.nobet_listesi[st.session_state.nobet_listesi["Öğretmen"] == sec_o]
                if not nb.empty:
                    nobet_g = nb.iloc[0]["Nöbet Günü"]
            html_o = render_meb_print_view([("ÖĞRETMEN HAFTALIK DERS PROGRAMI", f"Öğretmen: {sec_o}", df_g, nobet_g)], toplu_mu=False)
            components.html(html_o, height=540, scrolling=True)

        elif pdf_secenek == "🏫 Tek Sınıf Yazdır / PDF Al":
            sec_s = st.selectbox("Sınıf Seçin:", siniflar, key="pdf_tek_s")
            df_g = pd.DataFrame(st.session_state.cozum_sinif[sec_s], index=zil_etiketleri)
            html_s = render_meb_print_view([("SINIF HAFTALIK DERS PROGRAMI", f"Sınıf / Şube: {sec_s}", df_g, "")], toplu_mu=False)
            components.html(html_s, height=540, scrolling=True)

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
            components.html(html_toplu_o, height=650, scrolling=True)

        else:
            toplu_snf = []
            for s in siniflar:
                df_g = pd.DataFrame(st.session_state.cozum_sinif[s], index=zil_etiketleri)
                toplu_snf.append(("SINIF HAFTALIK DERS PROGRAMI", f"Sınıf / Şube: {s}", df_g, ""))
            html_toplu_s = render_meb_print_view(toplu_snf, toplu_mu=True)
            components.html(html_toplu_s, height=650, scrolling=True)

# ----------------------------------------------------
# TAB 6: İDARECİ KONSOLİDE ÇARŞAFI
# ----------------------------------------------------
with tab_carsaf:
    st.subheader("📋 Tüm Okulun Genel Çarşaf Çizelgesi (İdareci Masası)")
    if st.session_state.cozum_ogretmen is not None:
        carsaf_rows = []
        for ogr in tum_ogretmenler:
            row = {"Öğretmen": ogr}
            for g in GUNLER:
                for s in range(st.session_state.gun_saatleri[g]):
                    val = st.session_state.cozum_ogretmen[ogr][g][s]
                    row[f"{g[:3]} {s+1}"] = val if val not in ["-", "---"] else ""
            carsaf_rows.append(row)
        
        df_carsaf = pd.DataFrame(carsaf_rows)
        st.dataframe(df_carsaf, use_container_width=True, height=450)
        
        buf_c = io.BytesIO()
        with pd.ExcelWriter(buf_c, engine='openpyxl') as writer:
            df_carsaf.to_excel(writer, index=False)
        st.download_button(
            label="📥 Tüm Okul Çarşafını Excel Olarak İndir (.xlsx)",
            data=buf_c.getvalue(),
            file_name=f"{st.session_state.okul_adi}_carsaf_cizelgesi.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    else:
        st.info("Program henüz dağıtılmadı.")

# ----------------------------------------------------
# TAB 7: AKILLI NÖBET
# ----------------------------------------------------
with tab_nobet:
    st.subheader("🛡️ Akıllı Nöbet Çizelgesi")
    st.caption("Öğretmenlerin boş günlerine asla nöbet yazılmaz. Nöbetler sadece fiilen okulda oldukları günler arasından en az dersi olan güne atanır.")
    if st.session_state.nobet_listesi is not None:
        st.dataframe(st.session_state.nobet_listesi, use_container_width=True)
    else:
        st.info("Program henüz dağıtılmadı.")
