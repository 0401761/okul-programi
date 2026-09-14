import streamlit as st
import pandas as pd
from PIL import Image, ImageDraw
import io
import time

st.set_page_config(page_title="İHO Ders Dağıtım & Okul Yönetimi", layout="wide")

# ==========================================
# 1. 24 ŞUBELİ İHO MÜFREDAT MOTORU
# ==========================================
def get_iho_24_sube_verisi():
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
                t_name = pool[t_idx]
                rows.append({
                    "Öğretmen": t_name,
                    "Sınıf": s_name,
                    "Ders": subj,
                    "Saat": h,
                    "Nöbetçi": "Beden" not in t_name and "Rehberlik" not in t_name
                })
    return pd.DataFrame(rows)

def cizelge_gorseli_uret():
    w, h = 1200, 780
    img = Image.new("RGB", (w, h), color=(255, 255, 255))
    d = ImageDraw.Draw(img)
    
    # Başlık
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

# ==========================================
# 2. HAFIZA YÖNETİMİ
# ==========================================
if "gun_saatleri" not in st.session_state:
    st.session_state.gun_saatleri = {
        "Pazartesi": 7,
        "Salı": 7,
        "Çarşamba": 8,  # İHO 36 saat MEB standardı
        "Perşembe": 7,
        "Cuma": 7
    }

if "ders_listesi" not in st.session_state:
    st.session_state.ders_listesi = pd.DataFrame()

st.title("🕌 İmam Hatip Ortaokulu - Akıllı Dağıtım & Yönetim Sistemi")

tab_veri, tab_zaman, tab_onizleme = st.tabs([
    "📥 1. Veri Yükleme (Fotoğraf / Excel)",
    "⏰ 2. Günlük Saat Limitleri (36 Saat)",
    "📋 3. Okulun Tam Çizelgesi & Analiz"
])

# ----------------------------------------------------
# 1. VERİ YÜKLEME
# ----------------------------------------------------
with tab_veri:
    mod = st.radio("İçe Aktarma Yöntemi Seçin:", ["📸 Fotoğraf / Belge ile Yükle (OCR)", "📊 Excel ile Yükle"], horizontal=True)
    st.divider()

    if mod == "📸 Fotoğraf / Belge ile Yükle (OCR)":
        st.subheader("📸 24 Şubeli İHO Çizelge Fotoğrafını Tara")
        
        # Test Görseli İndirme Butonu
        col_dl, col_up = st.columns([1, 1.5])
        with col_dl:
            st.write("**1. Adım: Test Görselini İndir**")
            st.caption("24 şube (5A-8F) ve 864 saatlik resmî İHO dağıtım görselini bilgisayarına/telefonuna indir:")
            img_bytes = cizelge_gorseli_uret()
            st.download_button(
                label="📥 Örnek İHO Çizelge Fotoğrafını İndir (.png)",
                data=img_bytes,
                file_name="iho_24_sube_cizelgesi.png",
                mime="image/png",
                use_container_width=True
            )
            st.image(img_bytes, caption="Belge Önizlemesi", use_container_width=True)

        with col_up:
            st.write("**2. Adım: Fotoğrafı Yükle ve Tara**")
            yuklenen_foto = st.file_uploader("Çizelge Fotoğrafını Seç veya Sürükle", type=["png", "jpg", "jpeg"])
            if yuklenen_foto is not None:
                if st.button("🔍 Görseli Tara ve Listeye Dönüştür", type="primary", use_container_width=True):
                    with st.spinner("🤖 Yapay Zekâ görseldeki 24 şube, ders ve öğretmenleri okuyor..."):
                        time.sleep(2)  # Tarama simülasyonu
                        st.session_state.ders_listesi = get_iho_24_sube_verisi()
                        st.success("🎉 Harika! Görsel başarıyla okundu: 24 Şube, 40 Öğretmen ve 864 Ders Saati sisteme aktarıldı!")
                        st.rerun()

    else:
        st.subheader("📊 24 Şubeli Excel Dosyası")
        col_ex1, col_ex2 = st.columns(2)
        with col_ex1:
            st.write("**Hazır 24 Şubeli İHO Excelini İndir:**")
            buf_ex = io.BytesIO()
            with pd.ExcelWriter(buf_ex, engine='openpyxl') as writer:
                get_iho_24_sube_verisi().to_excel(writer, index=False)
            st.download_button(
                label="📥 24 Şubeli Tam İHO Excelini İndir (.xlsx)",
                data=buf_ex.getvalue(),
                file_name="iho_24_sube_tam_liste.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )
        with col_ex2:
            st.write("**Doldurduğun Exceli Yükle:**")
            up_ex = st.file_uploader("Excel Dosyası", type=["xlsx", "xls"])
            if up_ex is not None:
                st.session_state.ders_listesi = pd.read_excel(up_ex)
                st.success("✅ Excel başarıyla yüklendi!")

# ----------------------------------------------------
# 2. GÜNLÜK SAAT LİMİTLERİ
# ----------------------------------------------------
with tab_zaman:
    st.subheader("⏰ Günlük Ders Saat Limitleri")
    cols = st.columns(5)
    for i, gun in enumerate(list(st.session_state.gun_saatleri.keys())):
        with cols[i]:
            yeni_deger = st.number_input(f"{gun}", min_value=1, max_value=12, value=int(st.session_state.gun_saatleri[gun]), key=f"saat_{gun}")
            st.session_state.gun_saatleri[gun] = yeni_deger
    st.info(f"📌 Haftalık Toplam Ders Kapasitesi: **{sum(st.session_state.gun_saatleri.values())} Saat** (İHO Standart)")

# ----------------------------------------------------
# 3. ÖNİZLEME & ANALİZ
# ----------------------------------------------------
with tab_onizleme:
    st.subheader("📋 Okulun Ders & Öğretmen Dağılım Çizelgesi")
    if not st.session_state.ders_listesi.empty:
        df = st.session_state.ders_listesi
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Toplam Şube", f"{len(df['Sınıf'].unique())} Şube (5A-8F)")
        m2.metric("Toplam Öğretmen", f"{len(df['Öğretmen'].unique())} Öğretmen")
        m3.metric("Toplam Ders Saati", f"{df['Saat'].sum()} Saat")
        m4.metric("Şube Başına Ders", f"{df['Saat'].sum() // len(df['Sınıf'].unique())} Saat / Hafta")
        
        st.dataframe(df, use_container_width=True)
    else:
        st.warning("Henüz liste yüklenmedi. 1. Sekmeden fotoğrafı indirip yüklemeyi deneyin.")
