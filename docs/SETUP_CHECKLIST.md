# ✅ Proje Kurulum Kontrol Listesi

Bu belge, değerlendirme sürecinde projenin doğru şekilde çalıştığından emin olmak için bir kontrol listesidir.

---

##  Veritabanı Kurulumu

- [ ] PostgreSQL yüklü (v13+)
- [ ] Veritabanı oluşturuldu:
  ```bash
  createdb case_study
  ```
- [ ] Veritabanı bağlantı bilgileri ayarlandı:
  - `.env` dosyasında veya ortam değişkenlerinde aşağıdaki gibi tanımlandı:
    ```
    DB_URL=postgresql://user:password@localhost:5432/case_study
    ```

---

##  Veritabanı Migrasyon ve Seed

- [ ] Veritabanı şeması ve başlangıç verileri oluşturuldu:
  ```bash
  python -m database.seed
  ```

---

##  API Sunucusu

- [ ] API sunucusu başlatıldı:
  ```bash
  python main.py --api
  ```
- [ ] API dokümantasyonuna erişildi:
  [http://localhost:8000/docs](http://localhost:8000/docs)

---

##  Scraper'ı Test Etme

- [ ] Scraper tek seferlik çalıştırıldı:
  ```bash
  python main.py --scrape
  ```

---

##  Docker ile Çalıştırma

- [ ] Docker ve Docker Compose yüklü
- [ ] Container'lar başlatıldı:
  ```bash
  docker-compose up -d
  ```
- [ ] Veritabanı ve API container'ları çalışıyor:
  ```bash
  docker-compose ps
  ```

---

##  Veritabanı İçeriğini Kontrol Etme

PostgreSQL komut satırı veya GUI aracı (pgAdmin, DBeaver vb.) ile:

```sql
-- Tüm tabloları listele
\dt

-- Kamp alanlarını kontrol et
SELECT * FROM campgrounds LIMIT 10;

-- Scraper log kayıtlarını kontrol et
SELECT * FROM scraper_logs ORDER BY start_time DESC LIMIT 5;

-- İlişkili verileri kontrol et
SELECT c.name, ct.name as camper_type
FROM campgrounds c
JOIN campground_camper_types cct ON c.id = cct.campground_id
JOIN camper_types ct ON cct.camper_type_id = ct.id
LIMIT 10;
```

---

##  Genel Sorun Giderme

- [ ] PostgreSQL servisinin çalıştığını kontrol edin
- [ ] Veritabanı bağlantı bilgilerinin doğru olduğundan emin olun
- [ ] Uygulama loglarını kontrol edin
- [ ] Docker ile çalışırken container loglarını izleyin:
  ```bash
  docker-compose logs -f
  ```
