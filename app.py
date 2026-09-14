import streamlit as st
import pandas as pd

st.set_page_config(page_title="Okul Ders & Nöbet Yönetim Sistemi", layout="wide")

# ==========================================
# 1. MERKEZİ VERİ HAVUZU (SESSION STATE)
# ==========================================
if "gun_saatleri" not in st.session_state:
    st.session_state.gun_saatleri = {
        "Pazartesi": 7,
        "Salı": 7,
        "Çarşamba": 8,
        "Perşembe": 7,
        "Cuma": 7
    }

if "ogretmen_listesi" not in st.session_state:
    st.session_state.ogretmen_listesi = [
        {"ad": "Ahmet Yılmaz", "nobetci_olabilir": True},
        {"ad": "Ayşe Kaya", "nobetci_olabilir": True},
        {"ad": "Mehmet Demir", "nobetci_olabilir": False}
    ]

if "sinif_listesi" not in st.session_state:
    st.session_state.sinif_listesi = ["5A", "5B", "6A", "7A", "8A"]

if "ders_atamalari" not in st.session_state:
    st.session_state.ders_atamalari = [
        {"ogretmen": "Ahmet Yılmaz", "sinif": "5A", "ders": "Matematik", "saat": 6},
        {"ogretmen": "Ayşe Kaya", "sinif": "5A", "ders": "Türkçe", "saat": 6},
        {"ogretmen": "Mehmet Demir", "sinif": "6A", "ders": "Fen Bilimleri", "saat": 4}
    ]

# ==========================================
# 2. GÖRSEL PANEL & SEKMELER
# ==========================================
st.title("🏫 Akıllı Okul Yönetim Paneli - Temel Altyapı")

tab_zaman, tab_kisi, tab_ders = st.tabs([
    "⏰ 1. Günlük Saat Limitleri (1-12 Saat)",
    "👥 2. Sınırsız Öğretmen & Şube Yönetimi",
    "📚 3. Ders Tanımlamaları & Özet Tablo"
])

# SEKME 1: DİNAMİK ZAMAN AYARLARI
with tab_zaman:
    st.subheader("Dilediğin Günün Ders Saatini Değiştir")
    st.caption("Her gün için 1 ile 12 saat arasında limit belirleyebilirsin:")
    
    cols = st.columns(5)
    gunler = list(st.session_state.gun_saatleri.keys())
    
    for i, gun in enumerate(gunler):
        with cols[i]:
            yeni_saat = st.number_input(
                f"{gun}",
                min_value=1,
                max_value=12,
                value=int(st.session_state.gun_saatleri[gun]),
                key=f"saat_input_{gun}"
            )
            st.session_state.gun_saatleri[gun] = yeni_saat

    toplam_kapasite = sum(st.session_state.gun_saatleri.values())
    st.info(f"📌 **Haftalık Toplam Okul Kapasitesi:** {toplam_kapasite} Ders Saati")

# SEKME 2: SINIRSIZ ÖĞRETMEN & ŞUBE YÖNETİMİ
with tab_kisi:
    col_ogr, col_snf = st.columns(2)
    
    with col_ogr:
        st.subheader("👨‍🏫 Öğretmen Havuzu")
        with st.form("yeni_ogretmen_formu", clear_on_submit=True):
            yeni_ogr_ad = st.text_input("Öğretmen Adı Soyadı", placeholder="Örn: Fatma Çelik")
            yeni_ogr_nobet = st.checkbox("Bu öğretmen okulda nöbet tutabilir", value=True)
            ekle_ogr_btn = st.form_submit_button("➕ Öğretmeni Ekle")
            
            if ekle_ogr_btn and yeni_ogr_ad.strip():
                if any(o["ad"].lower() == yeni_ogr_ad.strip().lower() for o in st.session_state.ogretmen_listesi):
                    st.warning("Bu isimde bir öğretmen zaten mevcut!")
                else:
                    st.session_state.ogretmen_listesi.append({
                        "ad": yeni_ogr_ad.strip(),
                        "nobetci_olabilir": yeni_ogr_nobet
                    })
                    st.success(f"{yeni_ogr_ad} listeye eklendi.")
                    st.rerun()

        if st.session_state.ogretmen_listesi:
            ogr_df = pd.DataFrame(st.session_state.ogretmen_listesi)
            ogr_df.columns = ["Öğretmen Adı", "Nöbet Tutabilir"]
            st.dataframe(ogr_df, use_container_width=True)
            
            silinecek_ogr = st.selectbox("Listeden Öğretmen Çıkar:", [o["ad"] for o in st.session_state.ogretmen_listesi])
            if st.button("🗑️ Seçili Öğretmeni Sil"):
                st.session_state.ogretmen_listesi = [o for o in st.session_state.ogretmen_listesi if o["ad"] != silinecek_ogr]
                st.session_state.ders_atamalari = [d for d in st.session_state.ders_atamalari if d["ogretmen"] != silinecek_ogr]
                st.rerun()

    with col_snf:
        st.subheader("🏫 Sınıf / Şube Havuzu")
        with st.form("yeni_sinif_formu", clear_on_submit=True):
            yeni_snf_ad = st.text_input("Sınıf / Şube Adı", placeholder="Örn: 8B veya 11C")
            ekle_snf_btn = st.form_submit_button("➕ Şubeyi Ekle")
            
            if ekle_snf_btn and yeni_snf_ad.strip():
                snf_temiz = yeni_snf_ad.strip().upper()
                if snf_temiz in st.session_state.sinif_listesi:
                    st.warning("Bu sınıf zaten mevcut!")
                else:
                    st.session_state.sinif_listesi.append(snf_temiz)
                    st.success(f"{snf_temiz} şubesi eklendi.")
                    st.rerun()

        if st.session_state.sinif_listesi:
            st.write(f"Kayıtlı Şubeler ({len(st.session_state.sinif_listesi)} Adet):")
            st.write(", ".join(st.session_state.sinif_listesi))
            
            silinecek_snf = st.selectbox("Listeden Şube Çıkar:", st.session_state.sinif_listesi)
            if st.button("🗑️ Seçili Şubeyi Sil"):
                st.session_state.sinif_listesi.remove(silinecek_snf)
                st.session_state.ders_atamalari = [d for d in st.session_state.ders_atamalari if d["sinif"] != silinecek_snf]
                st.rerun()

# SEKME 3: DERS ATAMALARI
with tab_ders:
    st.subheader("📚 Öğretmen - Sınıf - Ders Eşleştirmesi")
    ogr_adlari = [o["ad"] for o in st.session_state.ogretmen_listesi]
    
    if not ogr_adlari or not st.session_state.sinif_listesi:
        st.warning("Ders ataması yapabilmek için en az 1 öğretmen ve 1 sınıf olmalı.")
    else:
        with st.form("ders_ekleme_formu", clear_on_submit=True):
            c1, c2, c3, c4 = st.columns([2, 1.5, 2, 1])
            with c1:
                sec_ogr = st.selectbox("Öğretmen", ogr_adlari)
            with c2:
                sec_snf = st.selectbox("Sınıf", st.session_state.sinif_listesi)
            with c3:
                drs_ad = st.text_input("Ders Adı", placeholder="Örn: İngilizce")
            with c4:
                drs_saat = st.number_input("Haftalık Saat", min_value=1, max_value=30, value=4)
            
            if st.form_submit_button("➕ Bu Dersi Eşleştir"):
                if drs_ad.strip():
                    st.session_state.ders_atamalari.append({
                        "ogretmen": sec_ogr,
                        "sinif": sec_snf,
                        "ders": drs_ad.strip(),
                        "saat": int(drs_saat)
                    })
                    st.rerun()

        if st.session_state.ders_atamalari:
            st.write("📋 **Okulun Güncel Ders Dağıtım Listesi:**")
            df_dersler = pd.DataFrame(st.session_state.ders_atamalari)
            df_dersler.columns = ["Öğretmen", "Sınıf", "Ders", "Haftalık Saat"]
            st.dataframe(df_dersler, use_container_width=True)
            st.metric("Toplam Dağıtılacak Ders Saati", f"{df_dersler['Haftalık Saat'].sum()} Saat")
