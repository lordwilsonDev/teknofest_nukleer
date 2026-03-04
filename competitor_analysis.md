# 📊 Rakip Analizi ve Teknik Kaynak Haritası

Bu belge, TEKNOFEST Nükleer Enerji Teknolojileri Tasarım Yarışması için rakip ekosistemini ve kullanılabilecek açık kaynaklı teknik kaynakları özetler.

---

## 🏎️ Rakip Analizi (Teknofest Ekosistemi)

Yarışma ilk kez **2024** yılında düzenlendiği için henüz köklü bir "şampiyonlar" geçmişi oluşmamıştır. Ancak 2024 ve 2025 süreçlerinden çıkarılan dersler şunlardır:

### 1. Rakip Profilleri
- **Üniversite Takımları:** Genelde İTÜ, ODTÜ ve Hacettepe gibi nükleer mühendisliği bölümleri olan üniversitelerden katılım yoğundur. Bu takımlar akademik bilgi birikimi ve simülasyon araçlarına (MCNP, Serpent) erişim avantajına sahiptir.
- **Yazılım Odaklı Takımlar:** Reaktör fiziğinden ziyade kontrol sistemleri ve simülasyon arayüzlerine odaklanarak fark yaratmaya çalışırlar.
- **Multidisipliner Takımlar:** Fizikçiler, yazılımcılar ve makine mühendislerinin birleştiği takımlar en yüksek puanı toplama eğilimindedir.

### 2. Kritik Başarı Faktörleri
- **Yüksek Sadakatli Simülasyon:** Sadece görsel değil, fiziksel olarak tutarlı nötronik ve termal-hidrolik analizler.
- **Yerlilik Oranı:** TENMAK ve Enerji Bakanlığı yürütücü olduğu için yerli yazılım çözümleri ekstra puan getirmektedir.
- **Güvenlik Odaklılık:** "Pasif Güvenlik Sistemleri" kategorisindeki inovatif yaklaşımlar rakiplerin en çok zorlandığı alanlardandır.

---

## 🛠️ Teknik Kaynaklar ve Açık Kaynak Kütüphaneler

Rakiplerin ve endüstrinin kullandığı temel araçlar:

### 🔬 Nötronik ve Fizik Simülasyonu
- **[OpenMC](https://github.com/openmc-dev/openmc):** Modern, C++/Python tabanlı ve tamamen açık kaynaklı Monte Carlo simülasyonu. Rakiplerin birçoğu MCNP'ye erişemediği için OpenMC kullanmaktadır.
- **[SerpentTools](https://github.com/CORE-GATECH-GROUP/serpent-tools):** Serpent çıktılarını analiz etmek için Python tabanlı mükemmel bir araç seti.
- **[PyMCNP](https://github.com/mcnp-dev/mcnpy):** MCNP dosyalarını Python üzerinden okuma ve manipüle etme kütüphanesi.

### 🏗️ SMR/MMR Tasarım ve Optimizasyon
- **[NuScale Benchmark](https://github.com/mit-crpg/ecp-benchmarks):** MIT tarafından hazırlanan ve NuScale (SMR devi) reaktörlerini modelleyen açık kaynaklı bir veri seti.
- **[ARMI](https://github.com/terrapower/armi):** TerraPower tarafından geliştirilen, nükleer reaktör tasarımı ve analizi için açık kaynaklı bir otomasyon framework'ü.

### 🤖 Yazılım ve Kontrol
- **[MOOSE Framework](https://github.com/idaholab/moose):** Idaho National Laboratory tarafından geliştirilen, çok fizikli (multiphysics) simülasyonlar için standart platform.
- **[OpenFOAM](https://github.com/OpenFOAM/OpenFOAM-dev):** Termal-hidrolik analizler için kullanılan CFD (Computational Fluid Dynamics) kütüphanesi.

---

## 🎯 Stratejik Öneriler (SKYGUARD İçin)

1.  **Entegrasyon Gücü:** OpenMC ve MOOSE frameworklerini birleştirerek rakiplerden daha tutarlı bir "Multiphysics" simülasyonu sunulmalıdır.
2.  **Yazılım Arayüzü:** Karmaşık nükleer verileri, operatörün (veya jürinin) kolayca anlayabileceği modern bir Dashboard (React/Next.js) ile görselleştirmek büyük bir avantaj sağlayacaktır.
3.  **Hızlı Prototipleme:** Python arayüzlü OpenMC kullanarak, binlerce farklı kor tasarımı saniyeler içinde simüle edilip en optimum olanı seçilmelidir (Genetik Algoritma ile optimizasyon).

---
*Hazırlayan: Antigravity AI | Teknofest Nükleer Enerji Teknolojileri Bölümü*
