
import streamlit as st
import pandas as pd
from ortools.sat.python import cp_model
from PIL import Image, ImageDraw
import io
import time

st.set_page_config(page_title="İHO Akıllı Ders Dağıtım & Nöbet Sistemi", layout="wide")

# ==========================================
# 1. HAFIZA VE VERİ YAPISI
# ==========================================
GUNLER = ["Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma"]

if "gun_saatleri" not in st.session_state:
    st.session_state.gun_saatleri = {
        "Pazartesi": 7,
        "Salı": 7,
        "Çarşamba": 8,  # İHO MEB Standartı (36 Saat)
        "Perşembe": 7,
        "Cuma": 7
    }

if "kilitler" not in st.session_state:
    st.session_state.kilitler = set()  # (Öğretmen, Gün, Saat)

if "cozum_ogretmen" not in st.session_state:
    st.session_state.cozum_ogretmen = None

if "cozum_sinif" not in st.session_state:
    st.session_state.cozum_sinif = None

if "nobet_listesi" not in st.session_state:
    st.session_state.nobet_listesi = None

# 24 ŞUBELİ İHO VERİ MOTORU
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

if "ders_listesi" not in st.session_state or st.session_state.ders_listesi.empty:
    st.session_state.ders_listesi = varsayilan_iho_verisi()

# ==========================================
# 2. ÜST BAŞLIK VE ANA SEKMELER
# ==========================================
st.title("🕌 İmam Hatip Ortaokulu - Otomatik Ders & Nöbet Dağıtım Sistemi")

tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📥 1. Ders Yükü & Veri",
    "🔒 2. Öğretmen Kilit Matrisi",
    "🚀 3. Programı Oluştur & Dağıt",
    "📅 4. Haftalık Çarşaf Programlar",
    "🛡️ 5. Akıllı Nöbet Çizelgesi"
])

# ----------------------------------------------------
# TAB 1: DERS LİSTESİ VE YÜKLEME
# ----------------------------------------------------
with tab1:
    st.subheader("📋 Okulun Ders Yükü")
    c1, c2, c3, c4 = st.columns(4)
    df_aktif = st.session_state.ders_listesi
    c1.metric("Toplam Şube", f"{len(df_aktif['Sınıf'].unique())} Şube (5A-8F)")
    c2.metric("Toplam Öğretmen", f"{len(df_aktif['Öğretmen'].unique())} Öğretmen")
    c3.metric("Toplam Ders Saati", f"{df_aktif['Saat'].sum()} Saat")
    c4.metric("Haftalık Şube Yükü", "36 Saat (Çarşamba 8, Diğer 7)")
    st.dataframe(df_aktif, use_container_width=True, height=300)

# ----------------------------------------------------
# TAB 2: KİLİT MATRİSİ (ÖĞRETMEN MÜSAİTLİĞİ)
# ----------------------------------------------------
with tab2:
    st.subheader("🔒 Öğretmen İstekleri & Kilit Matrisi")
    st.caption("Öğretmenlerin boş günlerini veya gelemeyecekleri saatleri buradan kilitleyebilirsin.")
    
    tum_ogretmenler = sorted(list(df_aktif["Öğretmen"].unique()))
    secili_ogr = st.selectbox("Saatlerini Kapatmak İstediğiniz Öğretmen:", tum_ogretmenler)
    
    # Hızlı Kilit Butonları
    b1, b2, b3, b4 = st.columns(4)
    with b1:
        kapatilacak_gun = st.selectbox("Günü Komple Boş Bırak:", GUNLER)
        if st.button("🚫 Bu Günü Kapat"):
            for s in range(st.session_state.gun_saatleri[kapatilacak_gun]):
                st.session_state.kilitler.add((secili_ogr, kapatilacak_gun, s))
            st.rerun()
    with b2:
        if st.button("☀️ Sabahları Kapat (1-2. Saatler)"):
            for g in GUNLER:
                st.session_state.kilitler.add((secili_ogr, g, 0))
                st.session_state.kilitler.add((secili_ogr, g, 1))
            st.rerun()
    with b3:
        if st.button("🌙 Öğleden Sonraları Kapat (6+ Saatler)"):
            for g in GUNLER:
                for s in range(5, st.session_state.gun_saatleri[g]):
                    st.session_state.kilitler.add((secili_ogr, g, s))
            st.rerun()
    with b4:
        if st.button("🔄 Bu Öğretmenin Kilitlerini Sıfırla"):
            st.session_state.kilitler = {k for k in st.session_state.kilitler if k[0] != secili_ogr}
            st.rerun()

    st.write(f"*{secili_ogr} için ders verilemeyecek saatleri kırmızı yapın:*")
    grid_cols = st.columns(5)
    for i, gun in enumerate(GUNLER):
        with grid_cols[i]:
            max_s = st.session_state.gun_saatleri[gun]
            st.markdown(f"**{gun}** ({max_s} Saat)")
            for s in range(max_s):
                kilitli_mi = (secili_ogr, gun, s) in st.session_state.kilitler
                btn_txt = f"🔴 {s+1}. Ders" if kilitli_mi else f"🟢 {s+1}. Ders"
                if st.button(btn_txt, key=f"k_{secili_ogr}_{gun}_{s}", use_container_width=True):
                    if kilitli_mi:
                        st.session_state.kilitler.remove((secili_ogr, gun, s))
                    else:
                        st.session_state.kilitler.add((secili_ogr, gun, s))
                    st.rerun()

# ----------------------------------------------------
# TAB 3: OTOMATİK DAĞITIM MOTORU
# ----------------------------------------------------
with tab3:
    st.subheader("🚀 Google OR-Tools Çakışmasız Dağıtım Motoru")
    st.info("📌 Motor; 24 şubenin 864 saatlik dersini, öğretmenlerin çakışmalarını ve belirlediğin kilitleri hesaplayarak optimum programı çıkarır.")
    
    if st.button("🔥 24 Şubenin Programını Şimdi Dağıt ve Oluştur", type="primary", use_container_width=True):
        with st.spinner("Matematiksel optimizasyon motoru çalışıyor, lütfen bekleyin (yaklaşık 10-20 saniye)..."):
            model = cp_model.CpModel()
            
            # Zaman Dilimleri (Pazartesi 0-6 ... Çarşamba 0-7)
            zaman_dilimleri = []
            for g in GUNLER:
                for s in range(st.session_state.gun_saatleri[g]):
                    zaman_dilimleri.append((g, s))
            
            dersler = df_aktif.to_dict("records")
            siniflar = sorted(list(df_aktif["Sınıf"].unique()))
            ogretmenler = sorted(list(df_aktif["Öğretmen"].unique()))
            
            # Karar Değişkenleri
            x = {}
            for i, d in enumerate(dersler):
                for g, s in zaman_dilimleri:
                    x[(i, g, s)] = model.NewBoolVar(f"x_{i}_{g}_{s}")

            # Kural 1: Kilitli saatlere asla ders atama
            for i, d in enumerate(dersler):
                ogr = d["Öğretmen"]
                for g, s in zaman_dilimleri:
                    if (ogr, g, s) in st.session_state.kilitler:
                        model.Add(x[(i, g, s)] == 0)

            # Kural 2: Her dersin haftalık saati eksiksiz verilmeli
            for i, d in enumerate(dersler):
                model.Add(sum(x[(i, g, s)] for g, s in zaman_dilimleri) == int(d["Saat"]))

            # Kural 3: Bir öğretmen aynı anda sadece 1 sınıfta olabilir
            for ogr in ogretmenler:
                ogr_i = [i for i, d in enumerate(dersler) if d["Öğretmen"] == ogr]
                for g, s in zaman_dilimleri:
                    model.Add(sum(x[(i, g, s)] for i in ogr_i) <= 1)

            # Kural 4: Bir sınıf aynı anda sadece 1 derste olabilir
            for snf in siniflar:
                snf_i = [i for i, d in enumerate(dersler) if d["Sınıf"] == snf]
                for g, s in zaman_dilimleri:
                    model.Add(sum(x[(i, g, s)] for i in snf_i) <= 1)

            # Çözücü
            solver = cp_model.CpSolver()
            solver.parameters.max_time_in_seconds = 30.0
            durum = solver.Solve(model)

            if durum in (cp_model.OPTIMAL, cp_model.FEASIBLE):
                st.success("🎉 Mükemmel! 24 şubenin 864 saatlik programı sıfır çakışmayla başarıyla oluşturuldu!")
                
                # Çözümleri Tablolara Dönüştür
                prog_ogr = {o: {g: ["-"] * 8 for g in GUNLER} for o in ogretmenler}
                prog_snf = {snf: {g: ["-"] * 8 for g in GUNLER} for snf in siniflar}
                
                for g in GUNLER:
                    for s in range(8):
                        if s >= st.session_state.gun_saatleri[g]:
                            for o in ogretmenler:
                                prog_ogr[o][g][s] = "---"
                            for snf in siniflar:
                                prog_snf[snf][g][s] = "---"

                for i, d in enumerate(dersler):
                    for g, s in zaman_dilimleri:
                        if solver.Value(x[(i, g, s)]) == 1:
                            prog_ogr[d["Öğretmen"]][g][s] = f"{d['Sınıf']} ({d['Ders']})"
                            prog_snf[d["Sınıf"]][g][s] = f"{d['Ders']} ({d['Öğretmen']})"

                st.session_state.cozum_ogretmen = prog_ogr
                st.session_state.cozum_sinif = prog_snf
                
                # AKILLI NÖBET HESABI: En az dersi olan gün
                nobet_atamalari = []
                nobetci_ogrler = df_aktif[df_aktif["Nöbetçi"] == True]["Öğretmen"].unique()
                
                for ogr in nobetci_ogrler:
                    gun_ders_sayilari = {}
                    for g in GUNLER:
                        toplam_ders = sum(1 for s in range(st.session_state.gun_saatleri[g]) if prog_ogr[ogr][g][s] not in ["-", "---"])
                        gun_ders_sayilari[g] = toplam_ders
                    # En az dersi olduğu gün (ama okulda olduğu günlerden)
                    en_bos_gun = min(gun_ders_sayilari, key=gun_ders_sayilari.get)
                    nobet_atamalari.append({
                        "Öğretmen": ogr,
                        "Nöbet Günü": en_bos_gun,
                        "O Günkü Ders Sayısı": gun_ders_sayilari[en_bos_gun]
                    })
                st.session_state.nobet_listesi = pd.DataFrame(nobet_atamalari)
                
            else:
                st.error("❌ Bu kilitlerle matematiksel olarak program kurulamaz! Lütfen kilitleri biraz gevşetin.")

# ----------------------------------------------------
# TAB 4: HAFTALIK ÇARŞAFLAR
# ----------------------------------------------------
with tab4:
    if st.session_state.cozum_sinif is None:
        st.warning("⚠️ Henüz program oluşturulmadı. Lütfen 3. Sekmeye gidip 'Programı Dağıt' butonuna basın.")
    else:
        goruntu_tipi = st.radio("Program Türü:", ["🏫 Sınıf Programları (5A-8F)", "👨‍🏫 Öğretmen Programları"], horizontal=True)
        
        if "Sınıf" in goruntu_tipi:
            sec_s = st.selectbox("Sınıf Seçin:", sorted(list(st.session_state.cozum_sinif.keys())))
            df_snf_gor = pd.DataFrame(st.session_state.cozum_sinif[sec_s], index=[f"{i+1}. Ders" for i in range(8)])
            st.table(df_snf_gor)
        else:
            sec_o = st.selectbox("Öğretmen Seçin:", sorted(list(st.session_state.cozum_ogretmen.keys())))
            df_ogr_gor = pd.DataFrame(st.session_state.cozum_ogretmen[sec_o], index=[f"{i+1}. Ders" for i in range(8)])
            st.table(df_ogr_gor)

# ----------------------------------------------------
# TAB 5: AKILLI NÖBET LİSTESİ
# ----------------------------------------------------
with tab5:
    st.subheader("🛡️ Otomatik Nöbet Dağıtım Listesi")
    st.caption("Nöbetler, öğretmenlerin haftalık programında en az dersinin / en çok boş saatinin olduğu güne otomatik atanmıştır.")
    
    if st.session_state.nobet_listesi is not None:
        st.dataframe(st.session_state.nobet_listesi, use_container_width=True)
    else:
        st.info("Program henüz dağıtılmadı. 3. Sekmeden dağıtım yapıldığında nöbet listesi burada görünecektir.")
