import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
from ortools.sat.python import cp_model
import io

st.set_page_config(page_title="İHO Akıllı Ders Dağıtım & İdareci Yönetim Sistemi", layout="wide")

# ==========================================
# 1. MERKEZİ VERİ VE HAFIZA HAVUZU
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

if "dondurulan_ogretmenler" not in st.session_state:
    st.session_state.dondurulan_ogretmenler = set()  # Dondurulan öğretmen isimleri

if "dondurulan_atamalar" not in st.session_state:
    st.session_state.dondurulan_atamalar = {}  # {ogr: [(sinif, ders, gun, saat)]}

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
# 2. MEB BASKI VE TOPLU PDF ŞABLONU
# ==========================================
def render_meb_print_view(icerik_listesi, toplu_mu=False):
    # icerik_listesi = [(baslik, alt_baslik, df_tablo, nobet_bilgisi)]
    pages_html = ""
    for idx, (baslik, alt_baslik, df_tablo, nobet_bilgisi) in enumerate(icerik_listesi):
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

        page_break_class = "page-break" if (toplu_mu and idx < len(icerik_listesi) - 1) else ""
        
        pages_html += f"""
        <div class="printable-page {page_break_class}">
            <div class="header-box">
                <h2>T.C. MİLLÎ EĞİTİM BAKANLIĞI</h2>
                <h3>İMAM HATİP ORTAOKULU MÜDÜRLÜĞÜ</h3>
                <h4>{baslik}</h4>
                <div><b>{alt_baslik}</b> {f'| <span style=\"color:#d9534f;\">Nöbet Günü: {nobet_bilgisi}</span>' if nobet_bilgisi else ''}</div>
            </div>
            {html_tablo}
            <div class="footer-box">
                <div><br><b>İlgili Öğretmen / Şube</b><br>İmza</div>
                <div><b>Uygundur</b><br>.... / .... / 2026<br><br><b>Okul Müdürü</b><br>İmza - Mühür</div>
            </div>
        </div>
        """

    tam_html = f"""
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
    return tam_html

# ==========================================
# 3. GÖRSEL PANEL VE SEKMELER
# ==========================================
st.title("🕌 İHO Akıllı Ders Dağıtım & İdareci Yönetim Sistemi")

tab_kilit, tab_motor, tab_pdf, tab_carsaf, tab_nobet = st.tabs([
    "🔒 1. Güne Özel Kilit Matrisi",
    "🚀 2. Programı Oluştur & Dondur",
    "📄 3. Resmî PDF Çıktıları (Tekli / Toplu)",
    "📋 4. Tüm Okulun Çarşaf Çizelgesi",
    "🛡️ 5. Akıllı Nöbet Çizelgesi"
])

# ----------------------------------------------------
# TAB 1: GÜNE ÖZEL KİLİT MATRİSİ
# ----------------------------------------------------
with tab_kilit:
    st.subheader("🔒 Öğretmen İstekleri & Güne Özel Boş Zaman Ayarları")
    secili_ogr = st.selectbox("Saatlerini Düzenlemek İstediğiniz Öğretmen:", tum_ogretmenler)
    
    # Dondurulmuş mu kontrolü
    if secili_ogr in st.session_state.dondurulan_ogretmenler:
        st.warning(f"📌 **{secili_ogr} öğretmenin programı şu anda SABİTLENMİŞ (DONDURULMUŞ) durumdadır.** Dağıtımda saatleri değişmez.")

    st.write("---")
    st.markdown("#### ⚡ Güne Özel Hızlı Kilit İşlemleri")
    col_gun, col_b1, col_b2, col_b3, col_rst = st.columns([1.5, 1.2, 1.3, 1.3, 1.2])
    
    with col_gun:
        hedef_gun = st.selectbox("İşlem Yapılacak Gün:", GUNLER, key="hedef_gun_sec")
    with col_b1:
        st.write("")
        if st.button(f"🚫 {hedef_gun}'ü Komple Kapat", use_container_width=True):
            for s in range(st.session_state.gun_saatleri[hedef_gun]):
                st.session_state.kilitler.add((secili_ogr, hedef_gun, s))
            st.rerun()
    with col_b2:
        st.write("")
        if st.button(f"☀️ {hedef_gun} Sabahı Kapat (1-4)", use_container_width=True):
            for s in range(min(4, st.session_state.gun_saatleri[hedef_gun])):
                st.session_state.kilitler.add((secili_ogr, hedef_gun, s))
            st.rerun()
    with col_b3:
        st.write("")
        if st.button(f"🌙 {hedef_gun} Öğleden Sonrayı Kapat (5+)", use_container_width=True):
            for s in range(4, st.session_state.gun_saatleri[hedef_gun]):
                st.session_state.kilitler.add((secili_ogr, hedef_gun, s))
            st.rerun()
    with col_rst:
        st.write("")
        if st.button("🔄 Kilitleri Sıfırla", use_container_width=True):
            st.session_state.kilitler = {k for k in st.session_state.kilitler if k[0] != secili_ogr}
            st.rerun()

    st.write("---")
    st.write(f"*{secili_ogr} için saatleri tek tek açıp kapatabilirsiniz (🔴 = Kilitli/Boş, 🟢 = Açık):*")
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
# TAB 2: DAĞITIM & ÖĞRETMEN DONDURMA (SABİTLEME)
# ----------------------------------------------------
with tab_motor:
    st.subheader("🚀 Akıllı Dağıtım & Program Dondurma (Sabitleme)")
    
    # Dondurulan Öğretmen Bilgi Paneli
    if st.session_state.dondurulan_ogretmenler:
        st.info(f"📌 **Şu Anda Dondurulmuş (Sabitlenmiş) Öğretmenler:** {', '.join(st.session_state.dondurulan_ogretmenler)} (Bu öğretmenlerin saatleri dağıtımda asla bozulmaz)")

    if st.button("🔥 24 Şubenin Programını Dağıt / Yeniden Hesapla", type="primary", use_container_width=True):
        with st.spinner("Optimum ders programı hesaplanıyor..."):
            model = cp_model.CpModel()
            zaman_dilimleri = [(g, s) for g in GUNLER for s in range(st.session_state.gun_saatleri[g])]
            dersler = df_aktif.to_dict("records")
            
            x = {}
            for i, d in enumerate(dersler):
                for g, s in zaman_dilimleri:
                    x[(i, g, s)] = model.NewBoolVar(f"x_{i}_{g}_{s}")

            # Kural 1: Ders saatleri eksiksiz atanmalı
            for i, d in enumerate(dersler):
                model.Add(sum(x[(i, g, s)] for g, s in zaman_dilimleri) == int(d["Saat"]))

            # Kural 2: Sınıf çakışması engelle
            for snf in siniflar:
                snf_i = [i for i, d in enumerate(dersler) if d["Sınıf"] == snf]
                for g, s in zaman_dilimleri:
                    model.Add(sum(x[(i, g, s)] for i in snf_i) <= 1)

            # Kural 3: Öğretmen çakışması engelle
            for ogr in tum_ogretmenler:
                ogr_i = [i for i, d in enumerate(dersler) if d["Öğretmen"] == ogr]
                for g, s in zaman_dilimleri:
                    model.Add(sum(x[(i, g, s)] for i in ogr_i) <= 1)

            # Kural 4: DONDURULMUŞ (SABİTLENMİŞ) ÖĞRETMENLERİ AYNEN KORU
            for ogr in st.session_state.dondurulan_ogretmenler:
                if ogr in st.session_state.dondurulan_atamalar:
                    for (snf, drs, g, s) in st.session_state.dondurulan_atamalar[ogr]:
                        # İlgili ders indeksini bul ve zorunlu yap
                        for i, d in enumerate(dersler):
                            if d["Öğretmen"] == ogr and d["Sınıf"] == snf and d["Ders"] == drs:
                                model.Add(x[(i, g, s)] == 1)
                                break

            # Kural 5: Kilitleri ceza puanıyla koru
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

                for (ogr, g, s) in st.session_state.kilitler:
                    if prog_ogr[ogr][g][s] == "-":
                        prog_ogr[ogr][g][s] = "🔒 KİLİTLİ"

                st.session_state.cozum_ogretmen = prog_ogr
                st.session_state.cozum_sinif = prog_snf
                st.session_state.ihlal_edilen_kilitler = tespit_edilen_ihlaller

                # MEB Uyumlu Akıllı Nöbet Dağıtımı
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

    # PROGRAM İNCELEME & DONDURMA İŞLEMLERİ
    if st.session_state.cozum_ogretmen is not None:
        st.divider()
        st.subheader("👁️ Programı Canlı İncele & Öğretmen Sabitle")
        
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
                    if st.button(f"📌 {secilen_hoca} Programını Dondur (Sabitle)", type="secondary", use_container_width=True):
                        # Öğretmenin mevcut atamalarını kaydet
                        atamalar = []
                        for g in GUNLER:
                            for s in range(st.session_state.gun_saatleri[g]):
                                val = st.session_state.cozum_ogretmen[secilen_hoca][g][s]
                                if val not in ["-", "---", "🔒 KİLİTLİ"] and "🚨" not in val:
                                    # Format: "5A (Matematik)"
                                    snf_part = val.split(" (")[0]
                                    drs_part = val.split(" (")[1].replace(")", "")
                                    atamalar.append((snf_part, drs_part, g, s))
                        st.session_state.dondurulan_atamalar[secilen_hoca] = atamalar
                        st.session_state.dondurulan_ogretmenler.add(secilen_hoca)
                        st.success(f"{secilen_hoca} programı donduruldu! Yeniden dağıtımlarda yeri asla değişmeyecek.")
                        st.rerun()
                else:
                    if st.button(f"🔓 {secilen_hoca} Dondurmasını Kaldır", type="primary", use_container_width=True):
                        st.session_state.dondurulan_ogretmenler.remove(secilen_hoca)
                        if secilen_hoca in st.session_state.dondurulan_atamalar:
                            del st.session_state.dondurulan_atamalar[secilen_hoca]
                        st.warning(f"{secilen_hoca} program kilidi serbest bırakıldı.")
                        st.rerun()

            df_tab = pd.DataFrame(st.session_state.cozum_ogretmen[secilen_hoca], index=[f"{i+1}. Ders" for i in range(8)])
            st.table(df_tab)
        else:
            with c_sec:
                secilen_sinif = st.selectbox("İncelenecek Sınıf:", siniflar, key="inc_snf")
            df_tab = pd.DataFrame(st.session_state.cozum_sinif[secilen_sinif], index=[f"{i+1}. Ders" for i in range(8)])
            st.table(df_tab)

# ----------------------------------------------------
# TAB 3: RESMÎ PDF ÇIKTILARI (TEKLİ & TOPLU)
# ----------------------------------------------------
with tab_pdf:
    if st.session_state.cozum_sinif is None:
        st.warning("⚠️ Lütfen önce 2. Sekmeye gidip 'Programı Dağıt' butonuna basın.")
    else:
        st.subheader("📄 Resmî MEB Haftalık Program Çıktıları")
        pdf_secenek = st.radio(
            "Yazdırma Formatı Seçin:",
            [
                "👤 Tek Öğretmen Yazdır / PDF Al",
                "🏫 Tek Sınıf Yazdır / PDF Al",
                "📚 TÜM ÖĞRETMENLERİ TEK PDF YAP (Toplu Baskı)",
                "🏫 TÜM ŞUBELERİ TEK PDF YAP (Toplu Baskı)"
            ],
            horizontal=True
        )
        st.divider()

        # 1. TEK ÖĞRETMEN
        if pdf_secenek == "👤 Tek Öğretmen Yazdır / PDF Al":
            sec_o = st.selectbox("Öğretmen Seçin:", tum_ogretmenler, key="tek_pdf_o")
            df_goster = pd.DataFrame(st.session_state.cozum_ogretmen[sec_o], index=[f"{i+1}. Ders" for i in range(8)])
            nobet_gunu = ""
            if st.session_state.nobet_listesi is not None:
                n_bul = st.session_state.nobet_listesi[st.session_state.nobet_listesi["Öğretmen"] == sec_o]
                if not n_bul.empty:
                    nobet_gunu = n_bul.iloc[0]["Nöbet Günü"]
            
            html_tek_o = render_meb_print_view([("ÖĞRETMEN HAFTALIK DERS PROGRAMI", f"Öğretmen: {sec_o}", df_goster, nobet_gunu)], toplu_mu=False)
            components.html(html_tek_o, height=520, scrolling=True)

        # 2. TEK SINIF
        elif pdf_secenek == "🏫 Tek Sınıf Yazdır / PDF Al":
            sec_s = st.selectbox("Sınıf Seçin:", siniflar, key="tek_pdf_s")
            df_goster = pd.DataFrame(st.session_state.cozum_sinif[sec_s], index=[f"{i+1}. Ders" for i in range(8)])
            html_tek_s = render_meb_print_view([("SINIF HAFTALIK DERS PROGRAMI", f"Sınıf / Şube: {sec_s}", df_goster, "")], toplu_mu=False)
            components.html(html_tek_s, height=520, scrolling=True)

        # 3. TÜM ÖĞRETMENLER TOPLU
        elif pdf_secenek == "📚 TÜM ÖĞRETMENLERİ TEK PDF YAP (Toplu Baskı)":
            st.info("📌 Okulun tüm öğretmenleri (40 Öğretmen) alt alta hazırlandı. 'Yazdır / PDF Olarak Kaydet' butonuna bastığınızda her öğretmen ayrı bir A4 sayfasına çıkacaktır.")
            toplu_ogr_icerik = []
            for ogr in tum_ogretmenler:
                df_ogr = pd.DataFrame(st.session_state.cozum_ogretmen[ogr], index=[f"{i+1}. Ders" for i in range(8)])
                nobet_g = ""
                if st.session_state.nobet_listesi is not None:
                    nb = st.session_state.nobet_listesi[st.session_state.nobet_listesi["Öğretmen"] == ogr]
                    if not nb.empty:
                        nobet_g = nb.iloc[0]["Nöbet Günü"]
                toplu_ogr_icerik.append(("ÖĞRETMEN HAFTALIK DERS PROGRAMI", f"Öğretmen: {ogr}", df_ogr, nobet_g))
            
            html_toplu_ogr = render_meb_print_view(toplu_ogr_icerik, toplu_mu=True)
            components.html(html_toplu_ogr, height=650, scrolling=True)

        # 4. TÜM SINIFLAR TOPLU
        else:
            st.info("📌 Okulun tüm şubeleri (24 Şube: 5A-8F) hazırlandı. Yazdır butonuna bastığınızda her sınıf ayrı bir A4 sayfasına çıkacaktır.")
            toplu_snf_icerik = []
            for snf in siniflar:
                df_snf = pd.DataFrame(st.session_state.cozum_sinif[snf], index=[f"{i+1}. Ders" for i in range(8)])
                toplu_snf_icerik.append(("SINIF HAFTALIK DERS PROGRAMI", f"Sınıf / Şube: {snf}", df_snf, ""))
            
            html_toplu_snf = render_meb_print_view(toplu_snf_icerik, toplu_mu=True)
            components.html(html_toplu_snf, height=650, scrolling=True)

# ----------------------------------------------------
# TAB 4: TÜM OKULUN ÇARŞAF ÇİZELGESİ (İDARECİ DEV PANO LİSTESİ)
# ----------------------------------------------------
with tab_carsaf:
    st.subheader("📋 Tüm Okulun Genel Çarşaf Çizelgesi (İdareci Masası)")
    st.caption("Tüm öğretmenlerin gün ve saat bazında haftalık dağılımını tek bir tabloda görün:")
    
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
        
        # Excel Olarak İndir
        buf_c = io.BytesIO()
        with pd.ExcelWriter(buf_c, engine='openpyxl') as writer:
            df_carsaf.to_excel(writer, index=False)
        st.download_button(
            label="📥 Tüm Okul Çarşafını Excel Olarak İndir (.xlsx)",
            data=buf_c.getvalue(),
            file_name="okul_genel_carsaf_cizelgesi.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    else:
        st.info("Program henüz dağıtılmadı. 2. Sekmeden dağıtım yapıldığında çarşaf çizelge burada oluşacaktır.")

# ----------------------------------------------------
# TAB 5: AKILLI NÖBET
# ----------------------------------------------------
with tab_nobet:
    st.subheader("🛡️ Akıllı Nöbet Çizelgesi")
    st.caption("Öğretmenlerin boş günlerine asla nöbet yazılmaz. Nöbetler sadece fiilen okulda oldukları günler arasından en az dersi olan güne yazılır.")
    if st.session_state.nobet_listesi is not None:
        st.dataframe(st.session_state.nobet_listesi, use_container_width=True)
    else:
        st.info("Program henüz dağıtılmadı. Dağıtım yapıldığında nöbetler burada görünecektir.")
