# TEKNOFEST Nükleer Enerji Simülasyonu — Mimari Özeti

> **Sürüm:** 2.0 | **Tarih:** Mart 2026

## 🗂️ Proje Yapısı

```
teknofest_nukleer/
├── src/
│   ├── physics.py        ← Fizik motoru (nokta kinetiği, Xe/Sm, termal-hidrolik)
│   └── reactor_core.py   ← Reaktör kontrol ve durum yönetimi
├── tests/
│   ├── test_core.py      ← ReactorCore birim testleri (37 test)
│   └── test_physics.py   ← Fizik modülü birim testleri (30 test)
├── logs/
│   └── reactor.log       ← Çalışma zamanı log dosyası
├── config.json           ← Reaktör konfigürasyonu
├── requirements.txt      ← Bağımlılıklar
└── README.md             ← Proje dokümantasyonu
```

## ⚙️ Katman Mimarisi

```
┌─────────────────────────────────────────────┐
│              Kullanıcı / Dashboard          │  ← Dash / React
├─────────────────────────────────────────────┤
│              ReactorCore (reactor_core.py)   │  ← Kontrol & Güvenlik
│  • AlarmLevel (Normal / Uyarı / Yüksek / SCRAM) │
│  • ReactorState (dataclass snapshot)         │
│  • Burnup takibi / Geçmiş kayıt              │
├─────────────────────────────────────────────┤
│              ReactorPhysics (physics.py)     │  ← Fizik Motoru
│  ┌───────────┐ ┌──────────┐ ┌────────────┐  │
│  │PointKinet.│ │ XenonPoi.│ │ SamariumP. │  │
│  │ 6-grup β  │ │ Bateman  │ │ Pm→Sm149   │  │
│  └───────────┘ └──────────┘ └────────────┘  │
│  ┌───────────────────────────────────────┐   │
│  │       ThermalHydraulics               │   │
│  │  Pasif soğutma / Doğal sirkülasyon    │   │
│  └───────────────────────────────────────┘   │
├─────────────────────────────────────────────┤
│              config.json                     │  ← Parametreler
└─────────────────────────────────────────────┘
```

## 📐 Fizik Modelleri

### Nokta Kinetiği (6 Gecikmeli Nötron Grubu)
Keepin (1965) verilerine dayalı U-235 termal fisyon parametreleri.

```
dN/dt  = [(ρ - β) / Λ] * N  +  Σ λᵢ * Cᵢ
dCᵢ/dt = (βᵢ / Λ) * N  -  λᵢ * Cᵢ
```

### Xenon-135 Zehirlenmesi (Bateman Denklemleri)
```
dI/dt  = γ_I * Φ  -  λ_I * I
dXe/dt = γ_Xe * Φ + λ_I * I - λ_Xe * Xe - σ_a,Xe * Φ * Xe
```
- **Xe-pit etkisi:** Güç kapatma sonrası maksimum 6-8 saat içinde zirveye ulaşır.
- Reaktivite cezası pcm cinsinden `xe_reactivity_pcm` özelliği üzerinden erişilebilir.

### Samaryum-149 Zehirlenmesi
```
dPm/dt = γ_Pm * Φ - λ_Pm * Pm
dSm/dt = λ_Pm * Pm - σ_a,Sm * Φ * Sm
```
- Kararlı izotop — Güç kesilince birikir, güç yeniden verilince yok olur.

### Sıcaklık Geri Bildirimi (Negatif Katsayı)
```
ρ_T = α_Doppler * (T - T_ref) + α_moderator * (T - T_ref)
α_Doppler   = -3.8×10⁻⁵ Δk/k per K
α_moderatör = -1.5×10⁻⁵ Δk/k per K
```

### Kontrol Çubuğu Reaktivitesi (S-Eğrisi)
Çubukların ortadaki hareketi daha fazla reaktivite değişimine neden olur (nötron önem fonksiyonu):
```python
rod_factor = sin(π * x) * 0.4 + x * 0.6   # x = rod_pos / 100
ρ_rod = rod_worth_total * (rod_factor - 0.5)
```

### Yakıt Tükenmesi (Burnup)
```
BU (MWd/MTU) = P_thermal × t_days / M_HM
```

## 🛡️ Güvenlik Sistemi (Çok Kademeli)

| Seviye | Tetikleyici | Eylem |
|--------|------------|-------|
| 0 — Normal | T < 610 K, P < 175 bar | — |
| 1 — Uyarı | T > 580 K | Log + konsol mesajı |
| 2 — Yüksek Alarm | T > 610 K, P > 175 bar, Güç > 160 MWth | Log + alarm |
| 3 — SCRAM | T > 623 K, P > 180 bar | Çubuklar içeri, soğutucu max |

## 🔌 API Özeti

```python
# Başlatma
reactor = ReactorCore("config.json")
reactor.initialize_steady_state()

# Kontrol
reactor.update_control_rods(75)   # % konumlandırma
reactor.update_coolant_flow(80)   # % akış
reactor.borate(0.02)              # Acil borlama (Δρ = 0.02)

# Simülasyon
reactor.step(dt=1.0)              # 1 saniyelik adım

# Veri
status  = reactor.get_status()           # Anlık durum sözlüğü
history = reactor.get_history_as_dicts() # Tüm geçmiş
events  = reactor.get_last_events(50)    # Son 50 olay

# Context Manager
with ReactorCore() as r:
    r.step(dt=1.0)
```

## 🧪 Test Çalıştırma

```bash
pytest tests/ -v --tb=short
pytest tests/ --cov=src --cov-report=html
```

---
*SKYGUARD AMR-OS | Nükleer Enerji Division*
