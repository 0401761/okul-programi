import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
from ortools.sat.python import cp_model
import io

st.set_page_config(page_title="İHO Akıllı Ders Dağıtım & Görsel Çakışma Paneli", layout="wide")

# ==========================================
# 1. MERKEZİ VERİ HAVUZU
# ==========================================
GUNLER = ["Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma"]

if "gun_saatleri" not in st.session_state:
    st.session_state.gun_saatleri = {
        "Pazartesi": 7,
        "Salı": 7,
        "Çarşamba": 8,  # MEB İHO Standartı (36 Saat)
        "Perşembe": 7,
        "Cuma": 7
    }

if "kilitler" not in st.session_state:
    st.session_state.kilitler = set()  # (Öğretmen, Gün, Saat)

if "cozum_ogretmen" not in st.session_state:
    st.session_state.cozum_ogretmen = None

if "cozum_sinif" not in st.session_state:
    st.session_state.cozum_sinif = None

if "ihlal_edilen_kilitler" not in st.session_state:
    st.session_state.ihlal_edilen_kilitler = []

if "nobet_listesi" not in st.session_state:
    st.session_state.nobet_listesi = None

# 24 ŞUBELİ İHO MÜFREDAT MOTORU
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

df_aktif = st.session_state.ders_listesi
tum_ogretmenler = sorted(list(df_aktif["Öğretmen"].unique()))
siniflar = sorted(list(df_aktif["Sınıf"].unique()))

# ==========================================
# 2. RENKLİ HTML GÖRÜNÜMÜ ŞABLONU
# ==========================================
def render_meb_print_view(baslik, alt_baslik, df_tablo, nobet_bilgisi=""):
    # Hücre içi kırmızı çakışma boyama
    html_tablo = "<table class='table-meb' border='1'><thead><tr><th>Ders</th>"
    for col in df_tablo.columns:
        html_tablo += f"<th>{col}</th>"
    html_tablo += "</tr></thead><tbody>"
    
    for idx_name, row in df_tablo.iterrows():
        html_tablo += f"<tr><td><b>{idx_name}</b></td>"
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

    return f"""
    <!DOCTYPE html>
    <html>
    <head>
    <meta charset="utf-8">
    <style>
        body {{ font-family: Arial, sans-serif; margin: 10px; color: #000; }}
        .header-box {{ text-align: center; border-bottom: 2px solid #000; padding-bottom: 8px; margin-bottom: 12px; }}
        .header-box h2 {{ margin: 2px; font-size: 17px; }}
        .header-box h3 {{ margin: 2px; font-size: 14px; font-weight: normal; }}
        .header-box h4 {{ margin: 3px; font-size: 15px; color: #b30000; }}
        .table-meb {{ width: 100%; border-collapse: collapse; text-align: center; font-size: 12px; }}
        .table-meb th {{ background-color: #f2f2f2; padding: 7px; font-weight: bold; }}
        .table-meb td {{ padding: 6px; height: 32px; }}
        .footer-box {{ margin-top: 25px; display: flex; justify-content: space-between; font-size: 13px; }}
        .btn-print {{ background-color: #0066cc; color: white; border: none; padding: 10px 20px; font-size: 14px; font-weight: bold; border-radius: 5px; cursor: pointer; margin-bottom: 15px; }}
        @media print {{ .no-print {{ display: none; }} body {{ margin: 0; }} }}
    </style>
    </head>
    <body>
        <div class="no-print">
            <button class="btn-print" onclick="window.print()">🖨️ Sayfayı Yazdır / PDF Olarak Kaydet</button>
        </div>
        <div class="header-box">
            <h2>T.C. MİLLÎ EĞİTİM BAKANLIĞI</h2>
            <h3>İMAM HATİP ORTAOKULU MÜDÜRLÜĞÜ</h3>
            <h4>{baslik}</h4>
            <div><b>{alt_baslik}</b> {f'| <span style="color:#d9534f;">Nöbet Günü: {nobet_bilgisi}</span>' if nobet_bilgisi else ''}</div>
        </div>
        {html_tablo}
        <div class="footer-box">
            <div><br><b>İlgili Öğretmen / Şube</b><br>İmza</div>
            <div><b>Uygundur</b><br>.... / .... / 2026<br><br><b>Okul Müdürü</b><br>İmza - Mühür</div>
        </div>
    </body>
    </html>
    """

# ==========================================
# 3. GÖRSEL PANEL VE SEKMELER
# ==========================================
st.title("🕌 İHO Akıllı Ders Dağıtım & Görsel Çakışma Paneli")

tab_kilit, tab_motor, tab_pdf, tab_nobet = st.tabs([
    "🔒 1. Öğretmen Kilit Matrisi",
    "🚀 2. Programı Oluştur & Görsel Çakışmalar",
    "📄 3. Resmî PDF Çıktıları",
    "🛡️ 4. Akıllı Nöbet Çizelgesi"
])

# ----------------------------------------------------
# TAB 1: KİLİT MATRİSİ
# ----------------------------------------------------
with tab_kilit:
    st.subheader("🔒 Öğretmen İstekleri & Boş Gün/Saat Ayarları")
    secili_ogr = st.selectbox("Saatlerini Kapatmak İstediğiniz Öğretmen:", tum_ogretmenler)
    
    b1, b2, b3, b4 = st.columns(4)
    with b1:
        kapat_gun = st.selectbox("Günü Komple Boş Bırak:", GUNLER)
        if st.button("🚫 Bu Günü Kapat"):
            for s in range(st.session_state.gun_saatleri[kapat_gun]):
                st.session_state.kilitler.add((secili_ogr, kapat_gun, s))
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

    # Grid
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
# TAB 2: DAĞITIM MOTORU & GÖRSEL ÇAKIŞMA MASASI
# ----------------------------------------------------
with tab_motor:
    st.subheader("🚀 Asla Vazgeçmeyen Akıllı Dağıtım Motoru")
    st.caption("Motor tüm programı oluşturur; eğer kilitler yüzünden bir ders zorlanıp sıkışırsa bunu tabloda KIRMIZI olarak gösterir.")
    
    if st.button("🔥 24 Şubenin Programını Dağıt ve Çakışmaları Göster", type="primary", use_container_width=True):
        with st.spinner("Optimum ders programı hesaplanıyor..."):
            model = cp_model.CpModel()
            zaman_dilimleri = [(g, s) for g in GUNLER for s in range(st.session_state.gun_saatleri[g])]
            dersler = df_aktif.to_dict("records")
            
            x = {}
            for i, d in enumerate(dersler):
                for g, s in zaman_dilimleri:
                    x[(i, g, s)] = model.NewBoolVar(f"x_{i}_{g}_{s}")

            # Kural 1: Ders saatleri eksiksiz atanmalı (Kesin kural)
            for i, d in enumerate(dersler):
                model.Add(sum(x[(i, g, s)] for g, s in zaman_dilimleri) == int(d["Saat"]))

            # Kural 2: Sınıf çakışması engelle (Kesin kural: 1 sınıf aynı anda 1 derste)
            for snf in siniflar:
                snf_i = [i for i, d in enumerate(dersler) if d["Sınıf"] == snf]
                for g, s in zaman_dilimleri:
                    model.Add(sum(x[(i, g, s)] for i in snf_i) <= 1)

            # Kural 3: Öğretmen çakışması engelle (Kesin kural: 1 öğretmen aynı anda 1 derste)
            for ogr in tum_ogretmenler:
                ogr_i = [i for i, d in enumerate(dersler) if d["Öğretmen"] == ogr]
                for g, s in zaman_dilimleri:
                    model.Add(sum(x[(i, g, s)] for i in ogr_i) <= 1)

            # Kural 4: KİLİTLERİ CEZA PUANI İLE KORU (Soft Constraint)
            # Motor kilitli saatlere ders koymamak için azami çaba harcar.
            ihlal_cezasi = []
            for (ogr, g, s) in st.session_state.kilitler:
                ilgili_i = [i for i, d in enumerate(dersler) if d["Öğretmen"] == ogr]
                for i in ilgili_i:
                    ihlal_cezasi.append(x[(i, g, s)])

            # Amacımız kilit ihlallerini minimuma (mümkünse 0'a) indirmek
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
                            # Bu saat kilitli miydi?
                            if (ogr, g, s) in st.session_state.kilitler:
                                prog_ogr[ogr][g][s] = f"🚨 {snf} ({drs}) [ÇAKIŞMA]"
                                prog_snf[snf][g][s] = f"🚨 {drs} ({ogr}) [ÇAKIŞMA]"
                                tespit_edilen_ihlaller.append({
                                    "Öğretmen": ogr,
                                    "Sınıf": snf,
                                    "Ders": drs,
                                    "Gün": g,
                                    "Saat": s + 1,
                                    "raw_s": s
                                })
                            else:
                                prog_ogr[ogr][g][s] = f"{snf} ({drs})"
                                prog_snf[snf][g][s] = f"{drs} ({ogr})"

                # Boş kilitli saatleri de belirtelim
                for (ogr, g, s) in st.session_state.kilitler:
                    if prog_ogr[ogr][g][s] == "-":
                        prog_ogr[ogr][g][s] = "🔒 KİLİTLİ"

                st.session_state.cozum_ogretmen = prog_ogr
                st.session_state.cozum_sinif = prog_snf
                st.session_state.ihlal_edilen_kilitler = tespit_edilen_ihlaller

                # Nöbet Dağıtımı
                nobet_atamalari = []
                nobetci_ogrler = df_aktif[df_aktif["Nöbetçi"] == True]["Öğretmen"].unique()
                for ogr in nobetci_ogrler:
                    gun_ders_sayilari = {}
                    for g in GUNLER:
                        toplam_ders = sum(1 for s in range(st.session_state.gun_saatleri[g]) if prog_ogr[ogr][g][s] not in ["-", "---", "🔒 KİLİTLİ"])
                        gun_ders_sayilari[g] = toplam_ders
                    en_bos_gun = min(gun_ders_sayilari, key=gun_ders_sayilari.get)
                    nobet_atamalari.append({
                        "Öğretmen": ogr,
                        "Nöbet Günü": en_bos_gun,
                        "O Günkü Ders Sayısı": gun_ders_sayilari[en_bos_gun]
                    })
                st.session_state.nobet_listesi = pd.DataFrame(nobet_atamalari)
                st.rerun()

    # EĞER PROGRAM OLUŞTURULDUYSA SONUÇ VE MÜDAHALE MASASI
    if st.session_state.cozum_ogretmen is not None:
        ihlaller = st.session_state.ihlal_edilen_kilitler
        
        if len(ihlaller) == 0:
            st.success("🎉 MÜKEMMEL! Hiçbir çakışma veya kilit ihlali yok. Tüm dersler ve öğretmen istekleri %100 sağlandı!")
        else:
            st.error(f"🚨 DİKKAT: Toplam {len(ihlaller)} noktada Kilit Çakışması oluştu! Aşağıdaki kırmızı kutulardan doğrudan müdahale edebilirsiniz:")
            
            for idx, h in enumerate(ihlaller):
                c_bilgi, c_aksiyon = st.columns([3, 1])
                with c_bilgi:
                    st.markdown(f"**📍 Çakışma Noktası:** `{h['Öğretmen']}` hocanın kapalı olduğu **{h['Gün']} {h['Saat']}. Ders** saatine **{h['Sınıf']} - {h['Ders']}** dersi yerleştirilmek zorunda kaldı.")
                with c_aksiyon:
                    if st.button(f"⚡ Bu Kilidi Kaldır ve Çöz", key=f"coz_{idx}"):
                        st.session_state.kilitler.remove((h["Öğretmen"], h["Gün"], h["raw_s"]))
                        st.rerun()
            st.divider()

        # HAFTALIK CANLI ÖNİZLEME MASASI
        st.subheader("👁️ Programı Canlı İncele (Çakışmalı Kırmızı Hücreler)")
        goruntu_modu = st.radio("İnceleme Türü:", ["👨‍🏫 Öğretmen Bazlı İncele", "🏫 Sınıf Bazlı İncele"], horizontal=True)
        
        if "Öğretmen" in goruntu_modu:
            secilen_hoca = st.selectbox("İncelenecek Öğretmen:", tum_ogretmenler, key="inc_ogr")
            df_tab = pd.DataFrame(st.session_state.cozum_ogretmen[secilen_hoca], index=[f"{i+1}. Ders" for i in range(8)])
            st.table(df_tab)
        else:
            secilen_sinif = st.selectbox("İncelenecek Sınıf:", siniflar, key="inc_snf")
            df_tab = pd.DataFrame(st.session_state.cozum_sinif[secilen_sinif], index=[f"{i+1}. Ders" for i in range(8)])
            st.table(df_tab)

# ----------------------------------------------------
# TAB 3: RESMÎ PDF ÇIKTILARI
# ----------------------------------------------------
with tab_pdf:
    if st.session_state.cozum_sinif is None:
        st.warning("⚠️ Lütfen önce 2. Sekmeye gidip 'Programı Dağıt' butonuna basın.")
    else:
        tur = st.radio("Çıktı Türü:", ["👨‍🏫 Öğretmen Haftalık Programı", "🏫 Sınıf Haftalık Programı"], horizontal=True)
        if "Öğretmen" in tur:
            sec_o = st.selectbox("Öğretmen Seçin:", tum_ogretmenler, key="pdf_o")
            df_goster = pd.DataFrame(st.session_state.cozum_ogretmen[sec_o], index=[f"{i+1}. Ders" for i in range(8)])
            nobet_gunu = ""
            if st.session_state.nobet_listesi is not None:
                n_bul = st.session_state.nobet_listesi[st.session_state.nobet_listesi["Öğretmen"] == sec_o]
                if not n_bul.empty:
                    nobet_gunu = n_bul.iloc[0]["Nöbet Günü"]
            html_meb = render_meb_print_view("ÖĞRETMEN HAFTALIK DERS PROGRAMI", f"Öğretmen: {sec_o}", df_goster, nobet_gunu)
            components.html(html_meb, height=520, scrolling=True)
        else:
            sec_s = st.selectbox("Sınıf Seçin:", siniflar, key="pdf_s")
            df_goster = pd.DataFrame(st.session_state.cozum_sinif[sec_s], index=[f"{i+1}. Ders" for i in range(8)])
            html_meb = render_meb_print_view("SINIF HAFTALIK DERS PROGRAMI", f"Sınıf / Şube: {sec_s}", df_goster)
            components.html(html_meb, height=520, scrolling=True)

# ----------------------------------------------------
# TAB 4: AKILLI NÖBET
# ----------------------------------------------------
with tab_nobet:
    st.subheader("🛡️ Akıllı Nöbet Çizelgesi")
    if st.session_state.nobet_listesi is not None:
        st.dataframe(st.session_state.nobet_listesi, use_container_width=True)
    else:
        st.info("Program henüz dağıtılmadı. Dağıtım yapıldığında nöbetler burada görünecektir.")
