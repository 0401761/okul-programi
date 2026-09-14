import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
from ortools.sat.python import cp_model
import io

st.set_page_config(page_title="İHO Akıllı Ders Dağıtım & Teşhis Sistemi", layout="wide")

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

df_aktif = st.session_state.ders_listesi

# ==========================================
# 2. ÇAKIŞMA VE DARBOĞAZ TEŞHİS MOTORU
# ==========================================
def cakismalari_teshis_et(df_ders, gun_saatleri, kilitler):
    sorunlar = []
    toplam_haftalik_kapasite = sum(gun_saatleri.values())
    
    # 1. Bireysel Öğretmen Kapasite Aşımı Kontrolü
    ogr_toplam_saat = df_ders.groupby("Öğretmen")["Saat"].sum().to_dict()
    for ogr, saat in ogr_toplam_saat.items():
        kilit_sayisi = sum(1 for (o, g, s) in kilitler if o == ogr)
        kalan_musait_saat = toplam_haftalik_kapasite - kilit_sayisi
        if saat > kalan_musait_saat:
            eksik = saat - kalan_musait_saat
            sorunlar.append({
                "Kategori": "🚨 Öğretmen Kapasite Aşımı",
                "İlgili Kişi / Zaman": ogr,
                "Açıklama": f"Toplam {saat} saat dersi var. Ancak {kilit_sayisi} saati kilitlendiği için sadece {kalan_musait_saat} müsait saati kaldı.",
                "Çözüm Önerisi": f"Bu öğretmenin en az {eksik} saatlik kilidini açmalısınız!"
            })

    # 2. Okul Geneli Saatlik Öğretmen Açığı Kontrolü
    toplam_sube_sayisi = len(df_ders["Sınıf"].unique())
    tum_ogretmenler = set(df_ders["Öğretmen"].unique())
    toplam_ogr_sayisi = len(tum_ogretmenler)

    for gun, max_s in gun_saatleri.items():
        for s in range(max_s):
            o_saatte_kilitli_olanlar = {o for (o, g, saat_idx) in kilitler if g == gun and saat_idx == s}
            o_saatte_musait_ogr_sayisi = toplam_ogr_sayisi - len(o_saatte_kilitli_olanlar)
            
            if o_saatte_musait_ogr_sayisi < toplam_sube_sayisi:
                acik = toplam_sube_sayisi - o_saatte_musait_ogr_sayisi
                sorunlar.append({
                    "Kategori": "⚠️ Genel Saat Darboğazı",
                    "İlgili Kişi / Zaman": f"{gun} - {s+1}. Ders Saati",
                    "Açıklama": f"Bu saatte okulda {toplam_sube_sayisi} şube derste olmak zorunda. Ancak kilitler yüzünden sadece {o_saatte_musait_ogr_sayisi} öğretmen serbest.",
                    "Çözüm Önerisi": f"Bu saat diliminde en az {acik} öğretmenin kilidini kaldırın."
                })

    return sorunlar

# ==========================================
# 3. YAZDIRMA HTML ŞABLONU
# ==========================================
def render_meb_print_view(baslik, alt_baslik, df_tablo, nobet_bilgisi=""):
    tablo_html = df_tablo.to_html(classes="table-meb", border=1)
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
        {tablo_html}
        <div class="footer-box">
            <div><br><b>İlgili Öğretmen / Şube</b><br>İmza</div>
            <div><b>Uygundur</b><br>.... / .... / 2026<br><br><b>Okul Müdürü</b><br>İmza - Mühür</div>
        </div>
    </body>
    </html>
    """

# ==========================================
# 4. GÖRSEL PANEL VE SEKMELER
# ==========================================
st.title("🕌 İHO Akıllı Ders Dağıtım & Teşhis Sistemi")

tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📥 1. Ders Yükü",
    "🔒 2. Öğretmen Kilit Matrisi",
    "🚀 3. Programı Oluştur & Çakışma Teşhisi",
    "📄 4. Resmî PDF Çıktıları",
    "🛡️ 5. Akıllı Nöbet Çizelgesi"
])

# TAB 1
with tab1:
    st.subheader("📋 Okulun Ders Yükü")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Toplam Şube", f"{len(df_aktif['Sınıf'].unique())} Şube (5A-8F)")
    c2.metric("Toplam Öğretmen", f"{len(df_aktif['Öğretmen'].unique())} Öğretmen")
    c3.metric("Toplam Ders Saati", f"{df_aktif['Saat'].sum()} Saat")
    c4.metric("Haftalık Şube Yükü", "36 Saat")
    st.dataframe(df_aktif, use_container_width=True, height=280)

# TAB 2
with tab2:
    st.subheader("🔒 Öğretmen Müsaitlik & Kilit Matrisi")
    tum_ogretmenler = sorted(list(df_aktif["Öğretmen"].unique()))
    secili_ogr = st.selectbox("Saatlerini Kapatmak İstediğiniz Öğretmen:", tum_ogretmenler)
    
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
        if st.button("🔄 Kilitleri Sıfırla"):
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

# TAB 3: DAĞITIM VE TEŞHİS RAPORU
with tab3:
    st.subheader("🚀 Akıllı Dağıtım & Otomatik Çakışma Analizi")
    
    if st.button("🔥 24 Şubenin Programını Şimdi Dağıt ve Oluştur", type="primary", use_container_width=True):
        with st.spinner("Program hesaplanıyor ve çakışma kontrolleri yapılıyor..."):
            
            # 1. ADIM: ÖNCE TEŞHİS MOTORUNU ÇALIŞTIR
            teshis_sonuclari = cakismalari_teshis_et(df_aktif, st.session_state.gun_saatleri, st.session_state.kilitler)
            
            if teshis_sonuclari:
                st.error("🚨 DİKKAT: Kilitlerinizde matematiksel imkansızlık tespit edildi!")
                st.write("Aşağıdaki çakışmaları düzeltmeden program kurulamaz:")
                df_sorun = pd.DataFrame(teshis_sonuclari)
                st.table(df_sorun)
            else:
                # 2. ADIM: TEŞHİS TEMİZSE ÇÖZÜCÜYÜ ÇALIŞTIR
                model = cp_model.CpModel()
                zaman_dilimleri = [(g, s) for g in GUNLER for s in range(st.session_state.gun_saatleri[g])]
                dersler = df_aktif.to_dict("records")
                siniflar = sorted(list(df_aktif["Sınıf"].unique()))
                ogretmenler = sorted(list(df_aktif["Öğretmen"].unique()))
                
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

                for ogr in ogretmenler:
                    ogr_i = [i for i, d in enumerate(dersler) if d["Öğretmen"] == ogr]
                    for g, s in zaman_dilimleri:
                        model.Add(sum(x[(i, g, s)] for i in ogr_i) <= 1)

                for snf in siniflar:
                    snf_i = [i for i, d in enumerate(dersler) if d["Sınıf"] == snf]
                    for g, s in zaman_dilimleri:
                        model.Add(sum(x[(i, g, s)] for i in snf_i) <= 1)

                solver = cp_model.CpSolver()
                solver.parameters.max_time_in_seconds = 30.0
                durum = solver.Solve(model)

                if durum in (cp_model.OPTIMAL, cp_model.FEASIBLE):
                    st.success("🎉 Mükemmel! Çakışma tespit edilmedi ve 24 şubenin programı başarıyla oluşturuldu!")
                    
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
                    
                    # Nöbet Hesabı
                    nobet_atamalari = []
                    nobetci_ogrler = df_aktif[df_aktif["Nöbetçi"] == True]["Öğretmen"].unique()
                    for ogr in nobetci_ogrler:
                        gun_ders_sayilari = {}
                        for g in GUNLER:
                            toplam_ders = sum(1 for s in range(st.session_state.gun_saatleri[g]) if prog_ogr[ogr][g][s] not in ["-", "---"])
                            gun_ders_sayilari[g] = toplam_ders
                        en_bos_gun = min(gun_ders_sayilari, key=gun_ders_sayilari.get)
                        nobet_atamalari.append({
                            "Öğretmen": ogr,
                            "Nöbet Günü": en_bos_gun,
                            "O Günkü Ders Sayısı": gun_ders_sayilari[en_bos_gun]
                        })
                    st.session_state.nobet_listesi = pd.DataFrame(nobet_atamalari)
                else:
                    st.error("❌ Karmaşık bir branş sıkışması oluştu! Lütfen son kapattığınız öğretmen kilitlerini biraz seyreltin.")

# TAB 4
with tab4:
    if st.session_state.cozum_sinif is None:
        st.warning("⚠️ Henüz program oluşturulmadı. Lütfen 3. Sekmeye gidip 'Programı Dağıt' butonuna basın.")
    else:
        tur = st.radio("Çıktı Türü Seçin:", ["👨‍🏫 Öğretmen Haftalık Ders Programı", "🏫 Sınıf Haftalık Ders Programı"], horizontal=True)
        if "Öğretmen" in tur:
            sec_o = st.selectbox("Öğretmen Seçin:", sorted(list(st.session_state.cozum_ogretmen.keys())))
            df_goster = pd.DataFrame(st.session_state.cozum_ogretmen[sec_o], index=[f"{i+1}. Ders" for i in range(8)])
            nobet_gunu = ""
            if st.session_state.nobet_listesi is not None:
                n_bul = st.session_state.nobet_listesi[st.session_state.nobet_listesi["Öğretmen"] == sec_o]
                if not n_bul.empty:
                    nobet_gunu = n_bul.iloc[0]["Nöbet Günü"]

            html_meb = render_meb_print_view("ÖĞRETMEN HAFTALIK DERS PROGRAMI", f"Öğretmen: {sec_o}", df_goster, nobet_gunu)
            components.html(html_meb, height=520, scrolling=True)
        else:
            sec_s = st.selectbox("Sınıf Seçin:", sorted(list(st.session_state.cozum_sinif.keys())))
            df_goster = pd.DataFrame(st.session_state.cozum_sinif[sec_s], index=[f"{i+1}. Ders" for i in range(8)])
            html_meb = render_meb_print_view("SINIF HAFTALIK DERS PROGRAMI", f"Sınıf / Şube: {sec_s}", df_goster)
            components.html(html_meb, height=520, scrolling=True)

# TAB 5
with tab5:
    st.subheader("🛡️ Akıllı Nöbet Çizelgesi")
    if st.session_state.nobet_listesi is not None:
        st.dataframe(st.session_state.nobet_listesi, use_container_width=True)
    else:
        st.info("Program henüz dağıtılmadı. 3. Sekmeden dağıtım yapıldığında nöbet listesi burada görünecektir.")
