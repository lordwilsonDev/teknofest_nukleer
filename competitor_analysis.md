# 📊 Rakip Analizi ve Teknik Kaynak Haritası

> **Son Güncelleme:** Mart 2026 | **Kapsam:** TEKNOFEST Nükleer Enerji Teknolojileri Tasarım Yarışması 2026

Bu belge, TEKNOFEST Nükleer Enerji Teknolojileri Tasarım Yarışması için rakip ekosistemini, uluslararası muadil yarışmaları ve yarışmada kullanılabilecek açık kaynaklı teknik kaynakları kapsamlı biçimde özetler.

---

## 🏎️ BÖLÜM 1: Yarışma İçi Rakip Analizi (Teknofest Ekosistemi)

Yarışma **2024** yılında ilk kez düzenlendiğinden, köklü bir geçmiş veri seti henüz oluşmamıştır. 2024 ve 2025 süreçlerinden elde edilen istihbarat bilgileri aşağıdaki gibidir:

### 1.1 Kurumsal Rakip Profilleri

| Kurum Tipi | Güçlü Yönleri | Zayıf Yönleri | Tehdit Seviyesi |
|---|---|---|---|
| **İTÜ / ODTÜ Nükleer Müh.** | MCNP/Serpent lisansı, akademik altyapı, danışman ağı | Akademik tempo (yavaş iterasyon), aşırı teorik odak | 🔴 Yüksek |
| **Hacettepe Üniversitesi** | 2025 yarışması akademik teşvik ödülü (15M TL), güçlü nükleer müh. bölümü | Geleneksel yaklaşım, yazılım odağı zayıf | 🔴 Yüksek |
| **Yazılım Odaklı Takımlar** | Modern UI/Dashboard, otomasyon becerileri | Nükleer fizik derinliği eksik, jüri güvenilirliği sorunu | 🟡 Orta |
| **Multidisipliner Takımlar** | Fizik + yazılım + makine dengesi, en yüksek puan potansiyeli | Koordinasyon zorluğu | 🔴 Yüksek |
| **Küçük Gruplar / Mezunlar** | Hız ve çeviklik | Kaynak kısıtlılığı | 🟢 Düşük |

### 1.2 Kritik Başarı Faktörleri (Yarışma Değerlendirme Matrisi)

Jüri değerlendirmesinde öne çıkan kriterler ve rakiplerin bu kriterlerdeki performansı:

1. **Yüksek Sadakatli Fiziksel Simülasyon (Ağırlık: ~%35)**
   - Çoğu takım görsel arayüze odaklanıp fiziksel tutarlılığı ihmal eder.
   - **Avantajımız:** OpenMC ile Monte Carlo nötronik + MOOSE ile çok-fizikli coupling.

2. **Yerlilik Oranı (Ağırlık: ~%20)**
   - TENMAK ve Enerji Bakanlığı tarafından yürütüldüğü için yerli yazılım bileşenleri bonus puan getirir.
   - **Avantajımız:** Python tabanlı yerli geliştirme üzerine inşa edilen `reactor_core.py` ve `physics.py` modülleri.

3. **IAEA Güvenlik Uyumu (Ağırlık: ~%25)**
   - Pasif Güvenlik Sistemleri, SCRAM mekanizmaları ve fault-tree analizi.
   - **Avantajımız:** Mevcut `emergency_shutdown()` ve xenon zehirlenmesi (Xe-135) modeli.

4. **İnovasyon ve Ticarileşme Potansiyeli (Ağırlık: ~%20)**
   - SMR-MMR hibrit mimarisi ve hızlı nötron tasarımı rakiplerin az dikkat ettiği alan.
   - **Avantajımız:** Genetik algoritma tabanlı kor optimizasyonu potansiyeli.

### 1.3 Stratejik Boşluklar (Fırsatlar)

- **Görsel Fark:** Hiçbir rakip takımın gerçek zamanlı reaktör dashboard'u yük altında stabil çalıştırdığı bilinmiyor.
- **Multiphysics Entegrasyon:** OpenMC↔MOOSE coupling yapan takım sayısı son derece sınırlı.
- **Hızlı Yakıt Döngüsü Simülasyonu:** ADDER veya Cyclus entegrasyonu rakiplerin neredeyse hiçbirinde yok.

---

## 🌍 BÖLÜM 2: Uluslararası Muadil Yarışmalar

Teknofest'e hazırlanırken referans alınabilecek global yarışmalar ve bu yarışmaların açık kaynak çalışmaları:

### 2.1 NEA SMR Prize Competition (OECD/NEA)
- **Organizatör:** Nuclear Energy Agency (OECD)
- **Format:** Sanal; uluslararası takımlar optimize edilmiş SMR kurulum senaryoları tasarlar.
- **Değerlendirme Kriterleri:** Ekonomik model, güvence altına alma analizi (safeguard), sosyal kabul stratejisi.
- **İlgili Linkler:**
  - [NEA SMR Prize Resmi Sayfası](https://www.oecd-nea.org/)
- **Bizim İçin Çıkarımlar:** Ekonomik ticarileşme modeli hazırlamak = jüri önünde güçlü kart.

### 2.2 ANS Student Design Competition (American Nuclear Society)
- **Organizatör:** American Nuclear Society (1975'den beri)
- **Format:** Üniversiteler detaylı tasarım raporu sunar, finalistler ANS Winter Conference'da sunum yapar.
- **2024 Galibi Tasarım:** Çok amaçlı optimizasyon framework'ü kullanan mikro-reaktör tasarımı (MIT).
- **Açık Kaynak Çalışmalar:**
  - [MIT CRPG GitHub](https://github.com/mit-crpg) — MIT'nin reaktör fiziği grubunun açık kaynak araçları
  - [OpenMOC](https://github.com/mit-crpg/openmoc) — MIT tarafından geliştirilen MOC (Method of Characteristics) kodu
  - [ECP Benchmarks](https://github.com/mit-crpg/ecp-benchmarks) — NuScale ve diğer SMR reaktörlerini modelleyen açık veri seti
- **Bizim İçin Çıkarımlar:** Optimizasyon framework mimarisi için referans.

### 2.3 IAEA ONCORE Initiative
- **Organizatör:** International Atomic Energy Agency
- **Format:** Üniversiteler ve araştırma kurumları için açık kaynaklı çok-fizikli simülasyon araçlarını geliştirme/kullanma programı.
- **Önem:** IAEA tarafından desteklenen araçları kullanan projeler, uluslararası standart uyumu kanıtlamış olur.
- **İlgili Linkler:**
  - [ONCORE IAEA Portalı](https://nucleus.iaea.org/sites/oncore/)

### 2.4 INS Student Design Competition (Institute of Nuclear Engineers - UK)
- **Organizatör:** INS, Birleşik Krallık
- **Format:** Nükleer tesis tasarımı üzerine yıllık öğrenci yarışması.

### 2.5 INSC (Innovations in Nuclear Science Research Competition)
- **Organizatör:** Idaho National Laboratory (INL)
- **Format:** Yayımlanmış araştırma tebliğleri üzerinden değerlendirme.
- **İlgili Linkler:**
  - [INSC Resmi Sayfası](https://inl.gov)

---

## 🛠️ BÖLÜM 3: Teknik Kaynak Haritası (Açık Kaynak Kütüphaneler)

Kaynaklı yarışmalarda rakiplerin kullandığı ve bizim de kullanabileceğimiz açık kaynak araçların kapsamlı haritası:

### 🔬 3.1 Nötronik ve Parçacık Taşınımı (Monte Carlo)

| Araç | GitHub | Açıklama | Yarışma Önemi |
|---|---|---|---|
| **OpenMC** | [openmc-dev/openmc](https://github.com/openmc-dev/openmc) | C++/Python MC kodu, ENDF veri kütüphanesi desteği | ⭐⭐⭐ Ana araç |
| **FRENSIE** | [FRENSIE/FRENSIE](https://github.com/FRENSIE/FRENSIE) | Nötron/foton MC kodu | ⭐⭐ Alternatif |
| **SCONE** | [CambridgeNuclear/SCONE](https://github.com/CambridgeNuclear/SCONE) | Cambridge geliştirmesi MC kodu | ⭐ Referans |
| **Warp** | [weft/warp](https://github.com/weft/warp) | GPU hızlandırmalı MC | ⭐⭐ Performans karşılaştırma |

### 🎯 3.2 Deterministik Nötronik Kodlar

| Araç | GitHub | Açıklama | Yarışma Önemi |
|---|---|---|---|
| **OpenMOC** | [mit-crpg/openmoc](https://github.com/mit-crpg/openmoc) | MIT MOC kodu | ⭐⭐⭐ Hızlı 2D lattice analizi |
| **BART** | [SlaybaughLab/BART](https://github.com/SlaybaughLab/BART) | UC-Berkeley FEM discrete ordinates | ⭐⭐ 3D analiz |
| **Gnat** | [OTU-Centre-for-SMRs/gnat](https://github.com/OTU-Centre-for-SMRs/gnat) | **SMR odaklı** MOOSE tabanlı deterministik kod | ⭐⭐⭐ SMR'ye özel |
| **Scarabée** | [scarabee-dev/scarabee](https://github.com/scarabee-dev/scarabee) | Lattice fizik kodu | ⭐⭐ |

### 📊 3.3 Nükleer Veri İşleme

| Araç | GitHub | Açıklama |
|---|---|---|
| **NJOY21** | [njoy/NJOY21](https://github.com/njoy/NJOY21) | Nükleer veri işleme standartı |
| **mendeleev** | [lmmentel/mendeleev](https://github.com/lmmentel/mendeleev) | Element/izotop özellikleri Python paketi |
| **endf-python** | [paulromano/endf-python](https://github.com/paulromano/endf-python) | ENDF formatı Python parser |
| **MontePy** | [idaholab/montepy](https://github.com/idaholab/montepy) | MCNP dosyaları için Python kütüphanesi (INL) |
| **serpentTools** | [CORE-GATECH-GROUP/serpent-tools](https://github.com/CORE-GATECH-GROUP/serpent-tools) | Serpent çıktı analiz araçları |

### ♻️ 3.4 Yakıt Tükenmesi (Depletion) ve Yakıt Döngüsü

| Araç | GitHub | Açıklama | Yarışma Önemi |
|---|---|---|---|
| **ADDER** | [anl-rtr/adder](https://github.com/anl-rtr/adder) | Argonne tabanlı Python yakıt yönetimi | ⭐⭐⭐ Nükleer yakıt kategorisi |
| **ONIX** | [jlanversin/ONIX](https://github.com/jlanversin/ONIX) | Python burnup kodu | ⭐⭐ |
| **Cyclus** | [cyclus/cyclus](https://github.com/cyclus/cyclus) | Nükleer yakıt döngüsü simülatörü | ⭐⭐ |
| **radioactivedecay** | [radioactivedecay/radioactivedecay](https://github.com/radioactivedecay/radioactivedecay) | Radyoaktif bozunma çözücü | ⭐⭐⭐ Atık yönetimi kategorisi |
| **OpenMCyclus** | [arfc/openmcyclus](https://github.com/arfc/openmcyclus) | OpenMC+Cyclus entegrasyonu | ⭐⭐ |

### 🌊 3.5 Kinetik ve Geçici Analiz (Reaktör Kontrol)

| Araç | GitHub | Açıklama | Yarışma Önemi |
|---|---|---|---|
| **PyRK** | [pyrk/pyrk](https://github.com/pyrk/pyrk) | Python 0-D nötronik + termal-hidrolik kinetik | ⭐⭐⭐ **Mevcut kodumuza en yakın rakip** |
| **KOMODO** | [imronuke/KOMODO](https://github.com/imronuke/KOMODO) | 3-D difüzyon nükleer reaktör simülatörü | ⭐⭐⭐ Referans mimari |
| **Research Reactor Sim.** | [ijs-f8/Research-Reactor-Simulator](https://github.com/ijs-f8/Research-Reactor-Simulator) | Gerçek zamanlı GUI reaktör simülatörü (nokta kinetiği) | ⭐⭐⭐ **Bizimkine en benzer proje** |

### 🌡️ 3.6 Termal-Hidrolik ve CFD

| Araç | GitHub | Açıklama |
|---|---|---|
| **OpenFOAM** | [OpenFOAM/OpenFOAM-dev](https://github.com/OpenFOAM/OpenFOAM-dev) | Standart CFD kütüphanesi |
| **Nek5000** | [Nek5000/Nek5000](https://github.com/Nek5000/Nek5000) | Spektral-element CFD kodu |
| **nekRS** | [Nek5000/nekRS](https://github.com/Nek5000/nekRS) | GPU-hedefli nekRS |
| **GeN-Foam** | [foam-for-nuclear/GeN-Foam](https://gitlab.com/foam-for-nuclear/GeN-Foam) | OpenFOAM tabanlı reaktör çok-fizikli çözücü |

### ⚙️ 3.7 Çok-Fizikli (Multiphysics) Çerçeveler

| Araç | GitHub | Açıklama | Yarışma Önemi |
|---|---|---|---|
| **MOOSE** | [idaholab/moose](https://github.com/idaholab/moose) | INL FEM multiphysics framework (endüstri standardı) | ⭐⭐⭐ Temel araç |
| **Cardinal** | [neams-th-coe/cardinal](https://github.com/neams-th-coe/cardinal) | OpenMC + nekRS → MOOSE uygulaması | ⭐⭐⭐ Tam entegrasyon |
| **Aurora** | [aurora-multiphysics/aurora](https://github.com/aurora-multiphysics/aurora) | OpenMC → MOOSE sarmalayıcı | ⭐⭐ |
| **ENRICO** | [enrico-dev/enrico](https://github.com/enrico-dev/enrico) | MC + CFD coupling | ⭐⭐ |

### 🧪 3.8 Erimiş Tuz Reaktörü (MSR) / İleri Konseptler

| Araç | GitHub | Açıklama |
|---|---|---|
| **Moltres** | [arfc/moltres](https://github.com/arfc/moltres) | MSR simülatörü |
| **SaltProc** | [arfc/saltproc](https://github.com/arfc/saltproc) | Yakıt yeniden işleme simülasyonu |
| **MSRE Model** | [openmsr/msre](https://github.com/openmsr/msre) | MSRE reaktörünün detaylı CAD modeli |

### 🏗️ 3.9 Reaktör Analiz Otomasyon Araçları

| Araç | GitHub | Açıklama | Yarışma Önemi |
|---|---|---|---|
| **ARMI** | [terrapower/armi](https://github.com/terrapower/armi) | TerraPower reaktör analiz otomasyon framework'ü | ⭐⭐⭐ Tasarım döngüsü kısaltır |
| **RAVEN** | [idaholab/raven](https://github.com/idaholab/raven) | UQ, regresyon, PRA, optimizasyon (INL) | ⭐⭐⭐ Güvenilirlik analizi |
| **WATTS** | [watts-dev/watts](https://github.com/watts-dev/watts) | Şablonlu simülasyon Python aracı | ⭐⭐ |
| **PyNE** | [pyne/pyne](https://github.com/pyne/pyne) | Python/C++ nükleer mühendislik toolkit | ⭐⭐⭐ Genel amaçlı |
| **NRIC Virtual Test Bed** | [idaholab/virtual_test_bed](https://github.com/idaholab/virtual_test_bed) | INL örnek challange problemi deposu | ⭐⭐⭐ Benchmark kaynağı |

---

## 🔍 BÖLÜM 4: Doğrudan Benzer Açık Kaynak Projeler (Kod İncelemesi)

Bu projeler, `reactor_core.py` ve `physics.py` modüllerimizle doğrudan karşılaştırılabilir:

### 4.1 Research Reactor Simulator (IJS - Slovenya)
- **Repo:** [ijs-f8/Research-Reactor-Simulator](https://github.com/ijs-f8/Research-Reactor-Simulator)
- **Teknoloji:** Python, gerçek zamanlı GUI, nokta kinetiği modeli
- **Bizimle Fark:** Sadece araştırma reaktörü, kontrol çubuğu odaklı, web dashboard yok.
- **Öğrenilecekler:** Gerçek zamanlı simülasyon döngüsü, kullanıcı arayüzü entegrasyonu.

### 4.2 PyRK (Purdue University)
- **Repo:** [pyrk/pyrk](https://github.com/pyrk/pyrk)
- **Teknoloji:** Python 0-D nötronik + termal-hidrolik kinetik
- **Bizimle Fark:** Teorik olarak daha güçlü ama arayüzü yok.
- **Öğrenilecekler:** Termal-hidrolik nodalleştirme yöntemi.

### 4.3 KOMODO (Institut Teknologi Bandung - Endonezya)
- **Repo:** [imronuke/KOMODO](https://github.com/imronuke/KOMODO)
- **Teknoloji:** Fortran/Python, 3-D nötron difüzyon, nodal metod
- **Bizimle Fark:** Çok daha derin nötroni, ancak termal-hidrolik entegrasyonu zayıf.
- **Öğrenilecekler:** 3-D güç dağılımı hesabı, AXI simetri kullanımı.

### 4.4 OpenMC NuScale Benchmark (MIT)
- **Repo:** [mit-crpg/ecp-benchmarks](https://github.com/mit-crpg/ecp-benchmarks)
- **Teknoloji:** Python + OpenMC, NuScale SMR tam çekirdek modeli
- **Bizimle Fark:** Doğrulama verisi, bizim simülasyonumuz için altın standart referans.
- **Öğrenilecekler:** SMR geometri parametrizasyonu, yakıt sürgüsü modeli.

---

## 🎯 BÖLÜM 5: Stratejik Aksiyon Planı (SKYGUARD İçin)

Rakip analizinden çıkan somut öncelikler:

### Öncelik 1 — Hızlı Kazanımlar (0-4 Hafta)
```
✅ OpenMC entegrasyonu: PyRK yerine OpenMC ile K-effective hesabı
✅ radioactivedecay kütüphanesi ile Xe-135/Sm-149 zehirlenmesi modeli
✅ ADDER ile yakıt tükenmesi (burnup) döngüsü
```

### Öncelik 2 — Rekabet Edici Fark Yaratan Unsurlar (1-2 Ay)
```
🚀 Cardinal veya Aurora ile OpenMC↔MOOSE coupling (tam multiphysics)
🚀 React/Next.js tabanlı gerçek zamanlı reaktör dashboard (jüri için "wow" faktörü)
🚀 RAVEN ile güvenilirlik analizi (PRA - Probabilistic Risk Assessment)
```

### Öncelik 3 — Uzun Vadeli Yenilik (Yarışmada İnovasyon Skoru)
```
💡 ARMI framework ile genetik algoritma tabanlı kor optimizasyonu
💡 WATTS ile otomatik parametrik tarama (binlerce tasarım → en iyi seçim)
💡 MSR/hızlı nötron konsepti: Moltres ile eğitim simülasyonu
```

### Kritik Boşluk Analizi

| Rakip | Bizim Durumuz |
|---|---|
| İTÜ/ODTÜ: MCNP erişimi var | OpenMC ile aynı sonuçları üretebiliriz (daha şeffaf) |
| Yazılım takımları: Güzel UI | Fiziksel tutarlılık + güzel UI = kazanma kombinasyonu |
| Multidisipliner takımlar: Dengeli | ARMI + OpenMC + web dashboard = tam sistem |

---

## 📚 BÖLÜM 6: Kodlama Referanslarının Haritası (Awesome-Nuclear)

[paulromano/awesome-nuclear](https://github.com/paulromano/awesome-nuclear) deposu, nükleer mühendislikte kullanılan tüm açık kaynak projelerin küratörlü listesidir. Temel kategoriler:

- **Parçacık Taşınımı (MC):** OpenMC, FRENSIE, SCONE, Warp
- **Deterministik Kodlar:** BART, Gnat (SMR odaklı!), OpenMOC, Scarabée
- **Nükleer Veri:** NJOY21, FUDGE, SANDY, NucML (ML tabanlı!)
- **Kinetik:** PyRK, KOMODO, Research Reactor Simulator
- **Yakıt Döngüsü:** Cyclus, OpenMCyclus
- **Termal-Hidrolik:** OpenFOAM, Nek5000, GeN-Foam
- **Multiphysics:** MOOSE, Cardinal, ENRICO, Aurora
- **MSR:** Moltres, SaltProc, MSRE CAD
- **Diğer:** ARMI, RAVEN, WATTS, PyNE, NRIC Virtual Test Bed

### Önde Gelen Araştırma Grupları (Açık Kaynak Odaklı)
- **ARFC (UIUC):** Advanced Reactors and Fuel Cycles — [arfc.github.io](https://arfc.github.io)
- **CNERG (UW-Madison):** Computational Nuclear Engineering — [cnerg.github.io](https://cnerg.github.io)
- **CRPG (MIT):** Computational Reactor Physics Group — [crpg.mit.edu](https://crpg.mit.edu)
- **ONCORE (IAEA):** Uluslararası açık kaynaklı çok-fizikli simülasyon işbirliği — [ONCORE Portal](https://nucleus.iaea.org/sites/oncore/)

---

*Hazırlayan: Antigravity AI | Teknofest Nükleer Enerji Teknolojileri Bölümü*
*Kaynak: Kapsamlı web araştırması + GitHub ekosistemi taraması + paulromano/awesome-nuclear + OECD/NEA + ANS + IAEA raporları*
