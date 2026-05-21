# Odoo Quotation Converter

A Flask application that converts Shopee and Tokopedia order exports into Excel files ready for Odoo Quotation/Sales Order import.

Most operational settings are handled from the web UI. The `.env` file is optional and can be used to override local defaults such as `SECRET_KEY`, upload folder, upload size limit, and default form values.

## Key Features

- Upload `.xlsx` or `.xls` files from Shopee or Tokopedia.
- Generate an Odoo-compatible import file with fields such as `Order Reference`, `Customer`, `Order Date`, `Payment Terms`, `Order Lines/Products`, `Order Lines/Quantity`, and `Order Lines/Unit Price`.
- Use marketplace `No. Pesanan` directly as `Order Reference`.
- Set `Customer` automatically to `Shoppe` or `Tokopedia`.
- Move recipient or buyer name into `Customer Reference`.
- Use `Harga Setelah Diskon` as the product unit price.
- Store `Order Lines/Unit Price` as a numeric value, not apostrophe-prefixed text.
- Add buyer-paid shipping as an `Ongkos Kirim` order line from `Ongkos Kirim Dibayar oleh Pembeli`.
- Download filenames:
  - `quotation_shoppe_YYYY-MM-DD.xlsx`
  - `quotation_tokopedia_YYYY-MM-DD.xlsx`
- Automatically clean runtime files older than 3 days.

## Project Structure

```text
.
|-- app.py                         # Flask web app and upload/download endpoints
|-- main.py                        # Local entry point
|-- config.py                      # Application defaults and env config
|-- core/
|   |-- converter.py               # Excel mapping and conversion logic
|   `-- data/
|       |-- exports/               # Shopee and Tokopedia sample templates
|       `-- imports/               # Odoo import template
|-- templates/
|   `-- index.html                 # Upload and conversion UI
|-- scripts/
|   |-- cleanup_old_files.py       # Runtime file cleanup script
|   `-- register_cleanup_task.ps1  # Windows Task Scheduler registration helper
|-- uploads/                       # Temporary uploaded files
`-- exports/                       # Generated conversion files
```

## Local Installation

Use Python 3.12 or a compatible Python 3 version.

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

To override local defaults, copy `.env.example` to `.env`:

```powershell
Copy-Item .env.example .env
```

Then edit `.env` as needed.

## Local Configuration

The following values can be configured through `.env`:

| Key | Default | Description |
| --- | --- | --- |
| `SECRET_KEY` | `dev-secret-key-change-in-production` | Flask secret key for local/dev usage |
| `UPLOAD_FOLDER` | `uploads` | Temporary upload folder |
| `ALLOWED_EXTENSIONS` | `xlsx,xls` | Allowed file extensions |
| `MAX_CONTENT_LENGTH` | `16777216` | Upload limit in bytes, default 16 MB |
| `DEFAULT_WAREHOUSE` | `Main Warehouse` | Default Warehouse form value |
| `DEFAULT_TEAM` | empty | Default Sales Team form value |
| `DEFAULT_COUNTRY` | `Indonesia` | Default Country form value |
| `DEFAULT_TAX` | `0` | Default Tax form value |
| `DEFAULT_PAYMENT_TERM` | `Immediate Payment` | Default Payment Terms form value |

Values from `.env` are only initial defaults. Users can still override several fields from the web UI during conversion.

## Running The App

```powershell
python main.py
```

Open this URL in your browser:

```text
http://localhost:5000
```

If port `5000` is already in use, run the app directly on another port:

```powershell
.\venv\Scripts\python.exe -c "from app import app; app.run(host='127.0.0.1', port=5001, debug=False)"
```

## Usage

1. Choose the source marketplace: Shopee or Tokopedia.
2. Upload the marketplace Excel export.
3. Adjust basic settings if needed:
   - Warehouse
   - Sales Team, empty by default
   - Tax
   - Payment Terms, default `Immediate Payment`
4. Click `Konversi Sekarang`.
5. Download the generated Odoo file.
6. Import the file into Odoo.

## Important Mapping

| Odoo Output | Source / Rule |
| --- | --- |
| `Order Reference` | `No. Pesanan` |
| `Customer` | `Shoppe` or `Tokopedia` |
| `Customer Reference` | `Nama Penerima` |
| `Order Date` | `Waktu Pesanan Dibuat` |
| `Expiration` | `Pesanan Harus Dikirimkan Sebelum` |
| `Payment Terms` | Web UI value, default `Immediate Payment` |
| `Order Lines/Products` | `Nama Produk` |
| `Order Lines/Quantity` | `Jumlah` |
| `Order Lines/Unit Price` | `Harga Setelah Diskon` |
| `Sales Team` | Web UI value, empty by default |

A shipping line is created once per order when `Ongkos Kirim Dibayar oleh Pembeli` is greater than 0.

## Monetary Columns

Shopee and Tokopedia exports may contain these monetary columns:

- `Harga Awal`
- `Harga Setelah Diskon`
- `Subtotal Pesanan`
- `Total Diskon`
- `Ongkos Kirim Dibayar oleh Pembeli`
- `Estimasi Potongan Biaya Pengiriman`
- `Perkiraan Ongkos Kirim`
- `Total Pembayaran`

For Odoo import, the app uses `Harga Setelah Diskon` as the product price and `Ongkos Kirim Dibayar oleh Pembeli` as the shipping line price. The other monetary columns are useful for reconciliation but are not automatically written as product prices.

## Runtime File Cleanup

Runtime files in `uploads/` and `exports/` are cleaned automatically when they are older than 3 days.

To run cleanup manually:

```powershell
.\venv\Scripts\python.exe scripts\cleanup_old_files.py --days 3
```

To preview cleanup without deleting files:

```powershell
.\venv\Scripts\python.exe scripts\cleanup_old_files.py --days 3 --dry-run
```

To register the Windows Task Scheduler job again at 00:00:

```powershell
.\scripts\register_cleanup_task.ps1 -TaskName "QuotationConverterCleanup" -At "00:00" -RetentionDays 3
```

If the app is deployed to a Linux server, use cron:

```cron
0 0 * * * cd /path/to/quotation_converter && ./venv/bin/python scripts/cleanup_old_files.py --days 3
```

## File Notes

- `.env` is for local config and should remain ignored by git.
- `.env.example` is kept as the config template.
- `SPEC.md` has been replaced by this README.
