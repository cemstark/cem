## QR Kod Üreten Python Uygulaması

Bu uygulama çalıştığında bir web sayfası açar ve **QR kodu** üretir.

- **Mod 1 (`info_page`)**: QR → bu uygulamanın `/info` sayfasını açar (bilgilerinizi burada gösterirsiniz).
- **Mod 2 (`target_url`)**: QR → `target_url` alanındaki siteyi açar.

### Kurulum (Windows / PowerShell)

`qr-uygulama` klasörüne girin:

```powershell
cd "$env:USERPROFILE\OneDrive\Masaüstü\qr-uygulama"
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### Çalıştırma

```powershell
.\.venv\Scripts\Activate.ps1
python .\app.py
```

Tarayıcıdan açın:

- Ana sayfa: `http://127.0.0.1:8000/`
- Admin: `http://127.0.0.1:8000/admin?token=...`

Uygulama açılırken terminale admin linkini de yazdırır.

### Bilgileri Nereden Düzenleyeceğim?

İki seçenek var:

- **Web üzerinden**: Admin sayfasından (`/admin?token=...`) başlık/metin/hedef URL düzenleyin.
- **Cursor / dosya üzerinden**: `config.json` içindeki alanları değiştirin.

### config.json Alanları

- **qr_mode**: `"info_page"` veya `"target_url"`
- **info_title**: `/info` sayfa başlığı
- **info_body**: `/info` sayfasında görünen metin (çok satır olabilir)
- **target_url**: dış site (opsiyonel)
- **append_run_id_to_target_url**: `true` ise `target_url` modunda URL’ye `rid=...` ekler
- **admin_token**: admin sayfasına giriş anahtarı (boşsa uygulama otomatik üretir)


