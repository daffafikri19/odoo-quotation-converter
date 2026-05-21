import re
from datetime import datetime
from typing import Any, Dict, List, Tuple, Optional
from dataclasses import dataclass
from enum import Enum

import pandas as pd


class SourceType(Enum):
    SHOPEE = "shopee"
    TOKOPEDIA = "tokopedia"


@dataclass
class ConversionResult:
    success: bool
    message: str
    row_index: Optional[int] = None
    data: Optional[Dict] = None


@dataclass
class ConversionReport:
    total_rows: int
    success_count: int
    failed_count: int
    results: List[ConversionResult]
    errors: List[Dict]
    output_data: Optional[pd.DataFrame] = None


class OdooFieldMapper:
    """Map marketplace columns to Odoo import fields."""

    ODOO_COLUMNS = [
        'Order Reference',
        'Customer',
        'Order Date',
        'Expiration',
        'Payment Terms',
        'Order Lines/Products',
        'Order Lines/Quantity',
        'Order Lines/Unit Price',
        'Order Lines/Taxes',
        'Sales Team',
        'Customer Reference',
        'Tags'
    ]

    SHOPEE_MAPPINGS = {
        'order_id': ['order_id', 'order number', 'nomor pesanan', 'no. pesanan', 'no pesanan', 'order_no', 'shopee_order_id', 'order_id_shopee'],
        'order_date': ['order_date', 'tanggal pesanan', 'tanggal', 'date', 'order time', 'waktu pesanan', 'create_time', 'waktu pesanan dibuat'],
        'customer_name': ['nama penerima', 'username (pembeli)', 'customer_name', 'nama pembeli', 'pembeli', 'buyer_name', 'recipient_name', 'atas nama'],
        'customer_phone': ['customer_phone', 'phone', 'no. telepon', 'no telepon', 'nomor telepon', 'telepon', 'handphone', 'hp', 'no_hp'],
        'shipping_address': ['shipping_address', 'alamat pengiriman', 'alamat', 'address', 'ship_address', 'receiver_address', 'alamat penerima'],
        'product_name': ['product_name', 'nama produk', 'produk', 'product', 'item_name', 'item', 'nama barang', 'barang'],
        'sku': ['sku', 'product_id', 'product_id_shopee', 'item_id', 'variation_id', 'kode produk', 'kode'],
        'quantity': ['quantity', 'jumlah', 'qty', 'jumlah barang', 'qty_ordered', 'jumlah pesanan'],
        'unit_price': ['harga setelah diskon', 'harga satuan', 'unit_price', 'selling_price', 'product_price', 'price_after_discount', 'harga awal', 'price_before_discount'],
        'total_price': ['subtotal pesanan', 'total_price', 'total pembayaran', 'order_total', 'total_amount', 'amount'],
        'shipping_paid': ['ongkos kirim dibayar oleh pembeli', 'ongkir dibayar pembeli', 'buyer paid shipping fee', 'shipping paid by buyer', 'shipping_fee_paid_by_buyer'],
        'shipping_discount': ['estimasi potongan biaya pengiriman', 'shipping discount estimate', 'shipping_discount'],
        'estimated_shipping': ['perkiraan ongkos kirim', 'estimated shipping fee', 'estimated_shipping'],
        'total_payment': ['total pembayaran', 'total payment', 'payment total'],
        'city': ['city', 'kota', 'kabupaten', 'kota/kabupaten', 'ship_city'],
        'province': ['province', 'provinsi', 'propinsi', 'province_name', 'ship_province'],
        'postal_code': ['postal_code', 'kode pos', 'zip', 'zipcode', 'ship_zipcode', 'zip_code'],
        'status': ['status', 'order_status', 'status pesanan', 'status_order'],
        'expiration': ['pesanan harus dikirimkan sebelum', 'batas kirim', 'shipping_deadline', 'tanggal batas kirim'],
    }

    TOKOPEDIA_MAPPINGS = {
        'order_id': ['order_id', 'order_number', 'nomor pesanan', 'no. pesanan', 'order_no', 'invoice_number', 'nomor invoice', 'invoice_id'],
        'order_date': ['order_date', 'tanggal pesanan', 'tanggal', 'date', 'order_time', 'waktu pesanan', 'created_at'],
        'customer_name': ['nama penerima', 'username (pembeli)', 'customer_name', 'nama pembeli', 'pembeli', 'buyer_name', 'nama recipient', 'recipient_name'],
        'customer_phone': ['customer_phone', 'phone', 'no. telepon', 'no telepon', 'nomor telepon', 'telepon', 'no_hp', 'phone_number'],
        'shipping_address': ['shipping_address', 'alamat pengiriman', 'alamat', 'address', 'alamat lengkap', 'full_address', 'ship_address', 'receiver_address'],
        'product_name': ['product_name', 'nama produk', 'produk', 'product', 'item_name', 'item', 'nama barang', 'product_title'],
        'sku': ['sku', 'product_id', 'item_id', 'variant_id', 'kode produk', 'kode sku', 'sku_id'],
        'quantity': ['quantity', 'jumlah', 'qty', 'jumlah barang', 'qty_ordered', 'quantity_ordered'],
        'unit_price': ['harga setelah diskon', 'harga satuan', 'unit_price', 'selling_price', 'product_price', 'price_after_discount', 'harga awal', 'unit_price_before_discount', 'harga sebelum diskon'],
        'total_price': ['subtotal pesanan', 'total_price', 'total pembayaran', 'order_total', 'total_amount', 'total_item_amount', 'amount'],
        'shipping_paid': ['ongkos kirim dibayar oleh pembeli', 'ongkir dibayar pembeli', 'buyer paid shipping fee', 'shipping paid by buyer', 'shipping_fee_paid_by_buyer'],
        'shipping_discount': ['estimasi potongan biaya pengiriman', 'shipping discount estimate', 'shipping_discount'],
        'estimated_shipping': ['perkiraan ongkos kirim', 'estimated shipping fee', 'estimated_shipping'],
        'total_payment': ['total pembayaran', 'total payment', 'payment total'],
        'city': ['city', 'kota', 'kabupaten', 'kota/kabupaten', 'ship_city', 'destination'],
        'province': ['province', 'provinsi', 'propinsi', 'province_name', 'ship_province', 'region'],
        'postal_code': ['postal_code', 'kode pos', 'zip', 'zipcode', 'zip_code', 'ship_zipcode'],
        'status': ['status', 'order_status', 'status pesanan', 'status_order', 'order_state'],
        'expiration': ['pesanan harus dikirimkan sebelum', 'batas kirim', 'shipping_deadline', 'tanggal batas kirim'],
    }

    def __init__(self, source_type: SourceType, config: Optional[Dict] = None):
        self.source_type = source_type
        self.config = config or {}
        self.mappings = self.TOKOPEDIA_MAPPINGS if source_type == SourceType.TOKOPEDIA else self.SHOPEE_MAPPINGS

    @staticmethod
    def normalize_column_name(value: Any) -> str:
        """Normalize column names for stable matching."""
        value = '' if value is None else str(value)
        return re.sub(r'\s+', ' ', re.sub(r'[^a-z0-9]+', ' ', value.lower())).strip()

    def find_column(self, df_columns: List[str], field: str) -> Optional[str]:
        """Find the best matching source column for a mapped field."""
        search_terms = self.mappings.get(field, [])
        normalized_terms = [self.normalize_column_name(term) for term in search_terms]
        normalized_columns = [
            (col, self.normalize_column_name(col), str(col).lower().strip())
            for col in df_columns
        ]

        # Prefer exact matches so broad names like "Nama Produk" do not beat
        # more specific columns such as "Nama Penerima" or "Harga Setelah Diskon".
        for term_norm in normalized_terms:
            for col, col_norm, _ in normalized_columns:
                if col_norm == term_norm:
                    return col

        for term_norm in normalized_terms:
            for col, col_norm, _ in normalized_columns:
                if not term_norm:
                    continue
                if len(term_norm) < 4:
                    continue
                if term_norm in col_norm or col_norm in term_norm:
                    return col

        for col, _, col_lower in normalized_columns:
            if field == 'order_id' and ('order' in col_lower or 'pesanan' in col_lower or 'invoice' in col_lower):
                if 'id' in col_lower or 'number' in col_lower or 'nomor' in col_lower or 'no' in col_lower:
                    return col
            elif field == 'product_name' and ('product' in col_lower or 'produk' in col_lower or 'barang' in col_lower or 'item' in col_lower):
                if 'name' in col_lower or 'nama' in col_lower or 'title' in col_lower:
                    return col
            elif field == 'customer_name' and ('customer' in col_lower or 'pembeli' in col_lower or 'buyer' in col_lower or 'penerima' in col_lower or 'recipient' in col_lower):
                if 'produk' in col_lower or 'product' in col_lower:
                    continue
                return col
            elif field == 'unit_price' and ('harga' in col_lower or 'price' in col_lower):
                if any(excluded in col_lower for excluded in ['total', 'subtotal', 'ongkos', 'kirim', 'shipping', 'voucher']):
                    continue
                return col
            elif field == 'shipping_paid' and 'ongkos kirim' in col_lower and 'pembeli' in col_lower:
                return col

        return None

    def get_column_value(self, df: pd.DataFrame, row: pd.Series, field: str, default: Any = None) -> Any:
        """Read a value from the mapped source column."""
        col = self.find_column(list(df.columns), field)
        if col is not None:
            return row.get(col, default)
        return default

    def clean_text(self, value: Any) -> str:
        """Return a trimmed string value."""
        if pd.isna(value):
            return ''
        return str(value).strip()

    def parse_date(self, date_str: Any) -> str:
        """Parse a source date into Odoo's YYYY-MM-DD format."""
        if pd.isna(date_str):
            return datetime.now().strftime('%Y-%m-%d')

        date_str = self.clean_text(date_str)
        if not date_str:
            return datetime.now().strftime('%Y-%m-%d')

        formats = [
            '%Y-%m-%d',
            '%d/%m/%Y',
            '%m/%d/%Y',
            '%d-%m-%Y',
            '%Y/%m/%d',
            '%d %B %Y',
            '%B %d, %Y',
            '%Y-%m-%d %H:%M:%S',
            '%Y-%m-%d %H:%M',
            '%d/%m/%Y %H:%M:%S',
        ]

        for fmt in formats:
            try:
                return datetime.strptime(date_str, fmt).strftime('%Y-%m-%d')
            except ValueError:
                continue

        try:
            ts = float(date_str)
            return datetime.fromtimestamp(ts).strftime('%Y-%m-%d')
        except (ValueError, OSError):
            pass

        return datetime.now().strftime('%Y-%m-%d')

    def parse_price(self, price_str: Any) -> float:
        """Parse Indonesian or English formatted prices into a number."""
        if pd.isna(price_str):
            return 0.0

        if isinstance(price_str, (int, float)):
            return float(price_str)

        raw_price = str(price_str).strip()
        if not raw_price:
            return 0.0

        is_negative = '-' in raw_price
        normalized_price = re.sub(r'[^\d,.\-]', '', raw_price).replace('-', '')
        if not normalized_price:
            return 0.0

        has_comma = ',' in normalized_price
        has_dot = '.' in normalized_price

        if has_comma and has_dot:
            last_comma = normalized_price.rfind(',')
            last_dot = normalized_price.rfind('.')
            if last_comma > last_dot:
                normalized_price = normalized_price.replace('.', '').replace(',', '.')
            else:
                normalized_price = normalized_price.replace(',', '')
        elif has_comma:
            parts = normalized_price.split(',')
            if len(parts) == 2 and len(parts[1]) <= 2:
                normalized_price = normalized_price.replace(',', '.')
            else:
                normalized_price = normalized_price.replace(',', '')
        elif has_dot:
            parts = normalized_price.split('.')
            if len(parts) > 2:
                normalized_price = normalized_price.replace('.', '')
            elif len(parts) == 2 and len(parts[1]) == 3:
                normalized_price = normalized_price.replace('.', '')

        try:
            price = float(normalized_price)
            return -price if is_negative else price
        except ValueError:
            return 0.0

    def format_price(self, price: float) -> float | int:
        """Return a numeric value for Odoo imports."""
        if pd.isna(price):
            return 0
        rounded_price = round(float(price), 2)
        return int(rounded_price) if rounded_price.is_integer() else rounded_price

    def format_price_label(self, price: float) -> str:
        """Format a price for conversion log messages."""
        formatted = f"{price:,.0f}".replace(',', 'X').replace('.', ',').replace('X', '.')
        return formatted.replace('X', '.')

    def extract_city_from_address(self, address: str) -> str:
        """Extract a city from a full address."""
        if not address:
            return ''

        address = self.clean_text(address)
        patterns = [
            r',?\s*Kota\s+([^,]+)',
            r',?\s*Kab\.\s*([^,]+)',
            r',?\s*Kabupaten\s+([^,]+)',
            r',\s*([^,]+?)\s*\d{5}',
        ]

        for pattern in patterns:
            match = re.search(pattern, address, re.IGNORECASE)
            if match:
                return match.group(1).strip()

        return ''

    def extract_province_from_address(self, address: str) -> str:
        """Extract a province from a full address."""
        if not address:
            return ''

        address = self.clean_text(address)
        patterns = [
            r',?\s*Prov\.\s*([^,]+)',
            r',?\s*Provinsi\s+([^,]+)',
            r'\b(Jakarta|Yogyakarta|Surabaya|Bandung|Medan|Makassar|Semarang)\b',
            r'\b(Aceh|Sumatera|Bengkulu|Lampung|Palembang|Jambi|Riau)\b',
        ]

        for pattern in patterns:
            match = re.search(pattern, address, re.IGNORECASE)
            if match:
                return match.group(1).strip() if match.lastindex else match.group(0).strip()

        return ''

    def extract_postal_code_from_address(self, address: str) -> str:
        """Extract a postal code from an address."""
        if not address:
            return ''

        match = re.search(r'\b(\d{5})\b', address)
        if match:
            return match.group(1)
        return ''


class QuotationConverter:
    """Convert marketplace rows into Odoo quotation import rows."""

    def __init__(self, source_type: SourceType, config: Optional[Dict] = None):
        self.source_type = source_type
        self.config = config or {}
        self.mapper = OdooFieldMapper(source_type, config)

    def get_order_reference(self, order_id: str) -> str:
        """Use the marketplace order number as the Odoo order reference."""
        return order_id

    def get_payment_term(self, config: Dict) -> str:
        """Normalize payment terms to Odoo values."""
        payment_term = self.mapper.clean_text(
            config.get('payment_term', 'Immediate Payment')
        )
        if payment_term.lower() == 'immediate':
            return 'Immediate Payment'
        return payment_term or 'Immediate Payment'

    def get_order_id(self, df: pd.DataFrame, row: pd.Series, row_index: int) -> str:
        """Read the marketplace order id used to group product and shipping lines."""
        order_id = self.mapper.clean_text(
            self.mapper.get_column_value(df, row, 'order_id', f'AUTO-{row_index}')
        )
        return order_id or f'AUTO-{row_index}'

    def get_marketplace_customer(self) -> str:
        """Return the Odoo customer name for the marketplace channel."""
        if self.source_type == SourceType.TOKOPEDIA:
            return 'Tokopedia'
        return 'Shoppe'

    def get_customer_reference(self, df: pd.DataFrame, row: pd.Series) -> str:
        """Move the recipient or buyer name into Customer Reference."""
        customer_reference = self.mapper.clean_text(
            self.mapper.get_column_value(df, row, 'customer_name', 'Guest')
        )
        return customer_reference or 'Guest'

    def validate_row(self, df: pd.DataFrame, row: pd.Series, row_index: int) -> Tuple[bool, List[str]]:
        """Validate one source row before conversion."""
        errors = []

        required_fields = ['product_name', 'quantity', 'unit_price']
        for field in required_fields:
            col = self.mapper.find_column(list(df.columns), field)
            value = row.get(col) if col else None
            if not col or pd.isna(value) or self.mapper.clean_text(value) == '':
                errors.append(f"Kolom '{field}' tidak ditemukan atau kosong")

        qty_col = self.mapper.find_column(list(df.columns), 'quantity')
        if qty_col:
            qty = self.mapper.parse_price(row.get(qty_col, 0))
            if qty <= 0:
                errors.append(f"Jumlah pesanan harus lebih dari 0 (ditemukan: {qty})")

        price_col = self.mapper.find_column(list(df.columns), 'unit_price')
        if price_col:
            price = self.mapper.parse_price(row.get(price_col, 0))
            if price < 0:
                errors.append(f"Harga tidak boleh negatif (ditemukan: {price})")

        return len(errors) == 0, errors

    def convert_row(self, df: pd.DataFrame, row: pd.Series, row_index: int, config: Dict) -> Dict:
        """Convert one product row to the Odoo import format."""
        odooline = {}

        order_id = self.get_order_id(df, row, row_index)
        odooline['Order Reference'] = self.get_order_reference(order_id)
        odooline['Customer'] = self.get_marketplace_customer()

        odooline['Order Date'] = self.mapper.parse_date(
            self.mapper.get_column_value(df, row, 'order_date')
        )

        odooline['Expiration'] = self.mapper.parse_date(
            self.mapper.get_column_value(df, row, 'expiration')
        )

        odooline['Payment Terms'] = self.get_payment_term(config)

        product_name = self.mapper.get_column_value(df, row, 'product_name', 'Unknown Product')
        odooline['Order Lines/Products'] = self.mapper.clean_text(product_name)

        quantity = self.mapper.parse_price(
            self.mapper.get_column_value(df, row, 'quantity', 1)
        )
        odooline['Order Lines/Quantity'] = int(quantity) if quantity == int(quantity) else quantity

        unit_price = self.mapper.parse_price(
            self.mapper.get_column_value(df, row, 'unit_price', 0)
        )
        odooline['Order Lines/Unit Price'] = self.mapper.format_price(unit_price)

        tax = config.get('tax', '0')
        odooline['Order Lines/Taxes'] = tax

        odooline['Sales Team'] = config.get('team', '')
        odooline['Customer Reference'] = self.get_customer_reference(df, row)
        odooline['Tags'] = ''

        return odooline

    def convert_shipping_row(self, df: pd.DataFrame, row: pd.Series, row_index: int, config: Dict) -> Optional[Dict]:
        """Create one buyer-paid shipping line for an order."""
        shipping_paid = self.mapper.parse_price(
            self.mapper.get_column_value(df, row, 'shipping_paid', 0)
        )
        if shipping_paid <= 0:
            return None

        order_id = self.get_order_id(df, row, row_index)
        shipping_product = config.get('shipping_product', 'Ongkos Kirim')

        odooline = {}
        odooline['Order Reference'] = self.get_order_reference(order_id)
        odooline['Customer'] = self.get_marketplace_customer()
        odooline['Order Date'] = self.mapper.parse_date(
            self.mapper.get_column_value(df, row, 'order_date')
        )
        odooline['Expiration'] = self.mapper.parse_date(
            self.mapper.get_column_value(df, row, 'expiration')
        )
        odooline['Payment Terms'] = self.get_payment_term(config)
        odooline['Order Lines/Products'] = shipping_product
        odooline['Order Lines/Quantity'] = 1
        odooline['Order Lines/Unit Price'] = self.mapper.format_price(shipping_paid)
        odooline['Order Lines/Taxes'] = config.get('shipping_tax', config.get('tax', '0'))
        odooline['Sales Team'] = config.get('team', '')
        odooline['Customer Reference'] = self.get_customer_reference(df, row)
        odooline['Tags'] = ''

        return odooline

    def convert(self, df: pd.DataFrame, config: Optional[Dict] = None,
                progress_callback=None) -> ConversionReport:
        """Convert a source DataFrame to Odoo import rows."""
        config = config or {}
        results = []
        errors = []
        converted_rows = []
        success_count = 0
        failed_count = 0

        total_rows = len(df)
        processed = 0
        last_valid_row_by_order = {}
        shipping_source_row_by_order = {}
        shipping_paid_by_order = {}

        for row_index, row in df.iterrows():
            processed += 1
            order_id = self.get_order_id(df, row, row_index)
            shipping_paid = self.mapper.parse_price(
                self.mapper.get_column_value(df, row, 'shipping_paid', 0)
            )
            if shipping_paid > shipping_paid_by_order.get(order_id, 0):
                shipping_paid_by_order[order_id] = shipping_paid
                shipping_source_row_by_order[order_id] = row

            if progress_callback:
                progress = int((processed / total_rows) * 100)
                progress_callback(progress, f"Memproses baris {processed}/{total_rows}")

            is_valid, validation_errors = self.validate_row(df, row, row_index)

            if not is_valid:
                failed_count += 1
                results.append(ConversionResult(
                    success=False,
                    message=f"Baris {row_index + 2}: {', '.join(validation_errors)}",
                    row_index=row_index
                ))
                errors.append({
                    'row': row_index + 2,
                    'errors': validation_errors,
                    'data': row.to_dict()
                })
                continue

            try:
                odooline = self.convert_row(df, row, row_index, config)
                converted_rows.append({
                    'row_index': row_index,
                    'order_id': order_id,
                    'source_row': row,
                    'odoo_line': odooline,
                })
                last_valid_row_by_order[order_id] = row_index

                product_name = odooline['Order Lines/Products']
                customer_name = odooline['Customer']

                results.append(ConversionResult(
                    success=True,
                    message=f"Berhasil: {product_name} untuk {customer_name} ({odooline['Order Reference']})",
                    row_index=row_index,
                    data=odooline
                ))
                success_count += 1

            except Exception as e:
                failed_count += 1
                error_msg = str(e)
                results.append(ConversionResult(
                    success=False,
                    message=f"Baris {row_index + 2}: {error_msg}",
                    row_index=row_index
                ))
                errors.append({
                    'row': row_index + 2,
                    'errors': [error_msg],
                    'data': row.to_dict()
                })

        output_rows = []
        for converted_row in converted_rows:
            output_rows.append(converted_row['odoo_line'])

            order_id = converted_row['order_id']
            row_index = converted_row['row_index']
            if last_valid_row_by_order.get(order_id) != row_index:
                continue

            shipping_line = self.convert_shipping_row(
                df,
                shipping_source_row_by_order.get(order_id, converted_row['source_row']),
                row_index,
                config
            )
            if shipping_line is None:
                continue

            output_rows.append(shipping_line)
            shipping_price = self.mapper.parse_price(shipping_line['Order Lines/Unit Price'])
            results.append(ConversionResult(
                success=True,
                message=(
                    f"Ditambahkan ongkir: {self.mapper.format_price_label(shipping_price)} "
                    f"untuk {shipping_line['Customer']} ({shipping_line['Order Reference']})"
                ),
                row_index=row_index,
                data=shipping_line
            ))

        output_df = None
        if output_rows:
            output_df = pd.DataFrame(output_rows)
            output_df = output_df[[col for col in OdooFieldMapper.ODOO_COLUMNS if col in output_df.columns]]

        return ConversionReport(
            total_rows=total_rows,
            success_count=success_count,
            failed_count=failed_count,
            results=results,
            errors=errors,
            output_data=output_df
        )


def convert_file(file_path: str, source_type: SourceType, config: Dict,
                progress_callback=None) -> ConversionReport:
    """Read an Excel file and convert it to an Odoo import report."""
    try:
        if progress_callback:
            progress_callback(5, "Membaca file...")

        df = pd.read_excel(file_path, sheet_name=0, dtype=str, keep_default_na=False)

        if progress_callback:
            progress_callback(10, f"File dibaca: {len(df)} baris")

        converter = QuotationConverter(source_type, config)
        report = converter.convert(df, config, progress_callback)

        if progress_callback:
            progress_callback(95, "Konversi selesai")

        return report

    except Exception as e:
        raise Exception(f"Gagal membaca file: {str(e)}")
