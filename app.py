import streamlit as st
import pandas as pd
import io

st.set_page_config(page_title="Akıllı Okul Yönetim & Dağıtım Sistemi", layout="wide")

# ==========================================
# 1. MERKEZİ VERİ HAVUZU
# ==========================================
if "gun_saatleri" not in st.session_state:
    st.session_state.gun_saatleri = {
        "Pazartesi": 7,
        "Salı": 7,
        "Çarşamba": 8,  # Standart kural
        "Perşembe": 7,
        "Cuma": 7
    }

if "ders_listesi" not in st.session_state:
    st.session_state.ders_listesi = pd.DataFrame([
        {"Öğretmen": "Ahmet Yılmaz", "Sınıf": "5A", "Ders": "Matematik", "Saat": 6, "Nöbetçi": True},
        {"Öğretmen": "Ayşe Kaya", "Sınıf": "5A", "Ders": "Türkçe", "Saat": 6, "Nöbetçi": True},
        {"Öğretmen": "Mehmet Demir", "Sınıf": "6B", "Ders": "Fen Bilimleri", "Saat": 4, "Nöbetçi": False}
    ])

st.title("🏫 Akıllı Okul Ders Dağıtım & Nöbet Sistemi")

# ==========================================
# 2. ANA SEKMELER
# ==========================================
tab_veri, tab_zaman, tab_onizleme = st.tabs([
    "📥 1. Veri Girişi (Excel / Fotoğraf / Manuel)",
    "⏰ 2. Günlük Ders Saatleri (1-12 Saat)",
    "📋 3. Yüklü Ders & Öğretmen Listesi"
])

# ----------------------------------------------------
# 1. VERİ GİRİŞİ: EXCEL & FOTOĞRAF & MANUEL
# ----------------------------------------------------
with tab_veri:
    yontem = st.radio(
        "Verileri sisteme nasıl aktarmak istersin?",
        ["📊 Excel ile Toplu Yükle", "📸 Fotoğraf / Belge Yükle", "✍️ Elle Manuel Ekle"],
        horizontal=True
    )
    st.divider()

    # YÖNTEM 1: EXCEL YÜKLEME
    if yontem == "📊 Excel ile Toplu Yükle":
        col1, col2 = st.columns([1, 2])
        with col1:
            st.write("**1. Şablon Dosyayı İndir:**")
            sablon_df = pd.DataFrame({
                "Öğretmen": ["Ahmet Yılmaz", "Ahmet Yılmaz", "Fatma Demir", "Ali Çelik"],
                "Sınıf": ["5A", "6B", "5A", "8C"],
                "Ders": ["Matematik", "Matematik", "Türkçe", "Bilişim"],
                "Saat": [6, 6, 6, 2],
                "Nöbet": ["Evet", "Evet", "Evet", "Hayır"]
            })
            buf = io.BytesIO()
            with pd.ExcelWriter(buf, engine='openpyxl') as writer:
                sablon_df.to_excel(writer, index=False)
            
            st.download_button(
                label="📄 Örnek Excel Şablonu İndir",
                data=buf.getvalue(),
                file_name="ders_ve_ogretmen_sablonu.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
            st.caption("Bu dosyayı indirip okulundaki tüm öğretmen ve şubeleri alt alta yazabilirsin.")

        with col2:
            st.write("**2. Doldurduğun Excel Dosyasını Yükle:**")
            yuklenen_excel = st.file_uploader("Excel Dosyası (.xlsx)", type=["xlsx", "xls"])
            if yuklenen_excel is not None:
                try:
                    df_gelen = pd.read_excel(yuklenen_excel)
                    beklenen = {"Öğretmen", "Sınıf", "Ders", "Saat"}
                    if beklenen.issubset(df_gelen.columns):
                        if "Nöbet" in df_gelen.columns:
                            df_gelen["Nöbetçi"] = df_gelen["Nöbet"].astype(str).str.lower().isin(["evet", "true", "1"])
                        else:
                            df_gelen["Nöbetçi"] = True
                        
                        st.session_state.ders_listesi = df_gelen[["Öğretmen", "Sınıf", "Ders", "Saat", "Nöbetçi"]]
                        st.success(f"✅ Harika! Toplam {len(df_gelen)} satırlık okul ders dağıtımı başarıyla yüklendi.")
                    else:
                        st.error("Excel başlıkları şunlar olmalıdır: Öğretmen, Sınıf, Ders, Saat")
                except Exception as e:
                    st.error(f"Dosya okunurken hata: {e}")

    # YÖNTEM 2: FOTOĞRAFTAN YÜKLEME
    elif yontem == "📸 Fotoğraf / Belge Yükle":
        st.subheader("📸 Ders Çizelgesi veya El Yazısı Listesi Fotoğrafı")
        st.caption("Masandaki basılı ders dağıtım çizelgesinin veya listelerin net bir fotoğrafını yükle:")
        
        yuklenen_foto = st.file_uploader("Fotoğraf Seç (JPG / PNG)", type=["jpg", "jpeg", "png"])
        if yuklenen_foto is not None:
            col_img1, col_img2 = st.columns(2)
            with col_img1:
                st.image(yuklenen_foto, caption="Yüklenen Görsel", use_container_width=True)
            with col_img2:
                st.info("🤖 **Yapay Zekâ Görsel Tanıma Modülü**")
                st.write("Görseldeki ders tablosu taranarak öğretmen, sınıf ve saatler otomatik çıkarılacak.")
                if st.button("🔍 Görseli Tara ve Listeye Dönüştür"):
                    with st.spinner("Görseldeki yazılar taranıyor ve tabloya aktarılıyor..."):
                        # Bu alan vizyon API entegrasyonu ile listeyi doldurur
                        st.warning("⚠️ Görsel okuma motoru hazır! Bir sonraki adımda yapay zekâ vizyon anahtarını bağlayıp doğrudan canlı tabloya dönüştüreceğiz.")

    # YÖNTEM 3: MANUEL GİRİŞ
    else:
        st.subheader("✍️ Tek Tek Elle Ekleme")
        with st.form("manuel_ekle_form", clear_on_submit=True):
            c1, c2, c3, c4, c5 = st.columns([2, 1.5, 2, 1, 1.5])
            with c1:
                ogr_ad = st.text_input("Öğretmen Adı")
            with c2:
                snf_ad = st.text_input("Sınıf (Örn: 7A)")
            with c3:
                drs_ad = st.text_input("Ders Adı")
            with c4:
                saat_sayi = st.number_input("Saat", min_value=1, max_value=30, value=4)
            with c5:
                nobet_mi = st.checkbox("Nöbet Tutabilir", value=True)
            
            if st.form_submit_button("➕ Dersi Ekle"):
                if ogr_ad and snf_ad and drs_ad:
                    yeni_satir = pd.DataFrame([{
                        "Öğretmen": ogr_ad.strip(),
                        "Sınıf": snf_ad.strip().upper(),
                        "Ders": drs_ad.strip(),
                        "Saat": int(saat_sayi),
                        "Nöbetçi": nobet_mi
                    }])
                    st.session_state.ders_listesi = pd.concat([st.session_state.ders_listesi, yeni_satir], ignore_index=True)
                    st.success(f"{ogr_ad} - {snf_ad} eklendi.")
                    st.rerun()

# ----------------------------------------------------
# 2. GÜNLÜK DERS SAATLERİ (1-12 SAAT)
# ----------------------------------------------------
with tab_zaman:
    st.subheader("⏰ Günlük Ders Saat Limitleri")
    cols = st.columns(5)
    for i, gun in enumerate(list(st.session_state.gun_saatleri.keys())):
        with cols[i]:
            yeni_deger = st.number_input(
                f"{gun}",
                min_value=1,
                max_value=12,
                value=int(st.session_state.gun_saatleri[gun]),
                key=f"saat_{gun}"
            )
            st.session_state.gun_saatleri[gun] = yeni_deger

    st.info(f"📌 Haftalık Toplam Ders Kapasitesi: **{sum(st.session_state.gun_saatleri.values())} Saat**")

# ----------------------------------------------------
# 3. YÜKLÜ LİSTE ÖNİZLEME
# ----------------------------------------------------
with tab_onizleme:
    st.subheader("📋 Sisteme Aktarılmış Güncel Okul Tablosu")
    if not st.session_state.ders_listesi.empty:
        st.dataframe(st.session_state.ders_listesi, use_container_width=True)
        
        c_m1, c_m2, c_m3 = st.columns(3)
        c_m1.metric("Toplam Ders Saati", f"{st.session_state.ders_listesi['Saat'].sum()} Saat")
        c_m2.metric("Toplam Öğretmen Sayısı", len(st.session_state.ders_listesi['Öğretmen'].unique()))
        c_m3.metric("Toplam Şube Sayısı", len(st.session_state.ders_listesi['Sınıf'].unique()))
        
        if st.button("🗑️ Tüm Listeyi Temizle"):
            st.session_state.ders_listesi = pd.DataFrame(columns=["Öğretmen", "Sınıf", "Ders", "Saat", "Nöbetçi"])
            st.rerun()
    else:
        st.warning("Henüz sisteme eklenmiş bir ders bulunmuyor.")
