# The Dyrt Campground Scraper

Bu proje, [The Dyrt](https://thedyrt.com) web sitesinden kamp alanı verilerini toplayarak bir PostgreSQL veritabanına kaydeden bir web scraper uygulamasıdır.

##  Özellikler

-  The Dyrt API'sinden otomatik kamp alanı veri toplama
-  Verilerin PostgreSQL veritabanında depolanması
-  RESTful API aracılığıyla verilere erişim
-  Zamanlanmış düzenli veri toplama işlemi
-  Docker ve Docker Compose desteği

##  Veritabanı Yapısı

Proje aşağıdaki tablolardan oluşan bir veritabanı yapısı kullanır:

- `campgrounds`: Ana kamp alanı bilgileri
- `camper_types`: Desteklenen kampçı türleri
- `accommodation_types`: Konaklama türleri
- `photo_urls`: Kamp alanı fotoğrafları
- `scraper_logs`: Scraper çalışma kayıtları

> **Not:** ER diyagramı için [`docs/db_schema.png`](docs/db_schema.png) dosyasına göz atabilirsiniz.

##  Kurulum

### Gereksinimler

- Python 3.11+
- PostgreSQL 13+
- Docker & Docker Compose (opsiyonel)

###  Yerel Kurulum

1. Repoyu klonlayın:

   ```bash
   git clone https://github.com/aysenurarslann/dyrt-campground-scraper.git
   cd dyrt-scraper
   ```

2. Sanal ortam oluşturun ve bağımlılıkları yükleyin:

   ```bash
   python -m venv venv
   source venv/bin/activate  
   pip install -r requirements.txt
   ```

3. PostgreSQL veritabanını oluşturun:

   ```bash
   createdb case_study
   ```

4. `.env` dosyasını oluşturun ve ayarları yapın:

   ```env
   DB_URL=postgresql://username:password@localhost:5432/case_study
   API_PORT=8000
   API_HOST=0.0.0.0
   SCHEDULE_INTERVAL=24
   ```

###  Docker ile Kurulum

```bash
docker-compose up -d
```

##  Kullanım

### Scraper'ı Çalıştırma

```bash
python main.py --scrape
```

### API Sunucusunu Başlatma

```bash
python main.py --api
```



### Zamanlanmış Scraper'ı Başlatma

```bash
python main.py --schedule
```

##  API Endpointleri

| Yöntem | Endpoint | Açıklama |
|--------|----------|----------|
| `GET`  | `/` | API bilgisi |
| `POST` | `/scraper/run` | Scraper'ı çalıştırır |
| `GET`  | `/scraper/status` | Scraper durumu |
| `GET`  | `/campgrounds` | Tüm kamp alanlarını listeler |
| `GET`  | `/campgrounds/{campground_id}` | Belirli kamp alanı detayları |
| `GET`  | `/logs` | Scraper çalışma kayıtları |
| `POST` | `/scheduler/start` | Zamanlanmış scraper'ı başlatır |
| `POST` | `/scheduler/stop` | Zamanlanmış scraper'ı durdurur |

##  Veritabanı Yönetimi

- Bu proje, SQLAlchemy ORM kullanarak veritabanı işlemlerini yönetir.
- Veritabanı şeması uygulama ilk kez çalıştırıldığında otomatik olarak oluşturulur.
- Bağlantı ayarları `src/config.py` üzerinden veya `.env` dosyası ile yapılandırılabilir.


