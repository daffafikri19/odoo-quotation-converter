"""Flask web application for converting marketplace orders to Odoo imports."""

import os
import uuid
from datetime import datetime
from flask import Flask, render_template, request, jsonify, send_file
from werkzeug.utils import secure_filename
import pandas as pd

from config import Config
from core.converter import convert_file, SourceType
from openpyxl import Workbook

app = Flask(__name__)
app.config.from_object(Config)

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs('exports', exist_ok=True)

conversions = {}


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']


def get_output_filename_pair(source_type: str, created_at: datetime, unique_id: str = '') -> dict:
    """Build the stored filename and the user-facing download filename."""
    source_label = 'shoppe' if source_type == 'shopee' else 'tokopedia'
    download_timestamp = created_at.strftime('%Y-%m-%d')
    storage_timestamp = created_at.strftime('%Y-%m-%d_%H-%M-%S')
    storage_suffix = f"_{unique_id[:8]}" if unique_id else ''

    return {
        'storage': f"quotation_{source_label}_{storage_timestamp}{storage_suffix}.xlsx",
        'download': f"quotation_{source_label}_{download_timestamp}.xlsx",
    }


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/api/upload', methods=['POST'])
def upload_file():
    """Upload and convert a marketplace export file."""
    if 'file' not in request.files:
        return jsonify({'success': False, 'error': 'Tidak ada file yang diupload'})

    file = request.files['file']
    source_type = request.form.get('source_type', 'shopee')

    if file.filename == '':
        return jsonify({'success': False, 'error': 'Nama file kosong'})

    if not allowed_file(file.filename):
        return jsonify({'success': False, 'error': 'Format file tidak didukung. Gunakan .xlsx atau .xls'})

    filename = secure_filename(file.filename)
    unique_id = str(uuid.uuid4())
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], f"{unique_id}_{filename}")
    file.save(filepath)

    config = {
        'warehouse': request.form.get('warehouse', app.config['DEFAULT_WAREHOUSE']),
        'team': request.form.get('team', app.config['DEFAULT_TEAM']),
        'country': request.form.get('country', app.config['DEFAULT_COUNTRY']),
        'tax': request.form.get('tax', app.config['DEFAULT_TAX']),
        'payment_term': request.form.get('payment_term', app.config['DEFAULT_PAYMENT_TERM']),
        'salesperson': request.form.get('salesperson', ''),
    }

    source = SourceType.SHOPEE if source_type == 'shopee' else SourceType.TOKOPEDIA

    def progress_callback(percent, message):
        if unique_id not in conversions:
            conversions[unique_id] = {'progress': 0, 'message': '', 'status': 'processing'}
        conversions[unique_id]['progress'] = percent
        conversions[unique_id]['message'] = message

    try:
        report = convert_file(filepath, source, config, progress_callback)

        output_filenames = get_output_filename_pair(source_type, datetime.now(), unique_id)
        output_filename = output_filenames['storage']
        output_path = os.path.join('exports', output_filename)

        if report.output_data is not None:
            wb = Workbook()
            ws = wb.active
            ws.title = 'Quotations'

            for col_idx, col_name in enumerate(report.output_data.columns, 1):
                ws.cell(row=1, column=col_idx, value=col_name)

            for row_idx, row in enumerate(report.output_data.itertuples(index=False), 2):
                for col_idx, value in enumerate(row, 1):
                    cell = ws.cell(row=row_idx, column=col_idx)
                    column_name = report.output_data.columns[col_idx - 1]
                    if isinstance(value, str):
                        cell.value = value
                        cell.data_type = 's'
                    else:
                        cell.value = value
                    if column_name == 'Order Lines/Unit Price':
                        cell.number_format = '#,##0.00'

            wb.save(output_path)

        conversions[unique_id]['status'] = 'completed'
        conversions[unique_id]['output_file'] = output_filename
        conversions[unique_id]['download_file'] = output_filenames['download']
        conversions[unique_id]['report'] = {
            'total_rows': report.total_rows,
            'success_count': report.success_count,
            'failed_count': report.failed_count,
            'results': [
                {'success': r.success, 'message': r.message, 'row': r.row_index}
                for r in report.results
            ],
            'errors': report.errors
        }

        os.remove(filepath)

        return jsonify({
            'success': True,
            'conversion_id': unique_id,
            'report': conversions[unique_id]['report']
        })

    except Exception as e:
        conversions[unique_id]['status'] = 'failed'
        conversions[unique_id]['error'] = str(e)
        return jsonify({
            'success': False,
            'error': str(e),
            'conversion_id': unique_id
        })


@app.route('/api/progress/<conversion_id>')
def get_progress(conversion_id):
    """Return conversion progress for the given conversion id."""
    if conversion_id not in conversions:
        return jsonify({'status': 'not_found'})

    conv = conversions[conversion_id]
    return jsonify({
        'status': conv.get('status', 'processing'),
        'progress': conv.get('progress', 0),
        'message': conv.get('message', ''),
        'output_file': conv.get('output_file'),
        'download_file': conv.get('download_file'),
        'error': conv.get('error')
    })


@app.route('/api/report/<conversion_id>')
def get_report(conversion_id):
    """Return the conversion report."""
    if conversion_id not in conversions:
        return jsonify({'error': 'Conversion not found'}), 404

    conv = conversions[conversion_id]
    return jsonify({
        'status': conv.get('status'),
        'report': conv.get('report'),
        'output_file': conv.get('output_file'),
        'download_file': conv.get('download_file')
    })


@app.route('/api/download/<conversion_id>')
def download_file(conversion_id):
    """Download the generated Odoo import file."""
    if conversion_id not in conversions:
        return jsonify({'error': 'Conversion not found'}), 404

    conv = conversions[conversion_id]
    output_file = conv.get('output_file')

    if not output_file:
        return jsonify({'error': 'File not available'}), 404

    output_path = os.path.join('exports', output_file)
    if not os.path.exists(output_path):
        return jsonify({'error': 'File not found'}), 404

    return send_file(
        output_path,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        download_name=conv.get('download_file', output_file)
    )


@app.route('/api/columns', methods=['POST'])
def analyze_columns():
    """Inspect uploaded file columns."""
    if 'file' not in request.files:
        return jsonify({'success': False, 'error': 'Tidak ada file'})

    file = request.files['file']

    if not allowed_file(file.filename):
        return jsonify({'success': False, 'error': 'Format tidak didukung'})

    try:
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(file.filename))
        file.save(filepath)

        df = pd.read_excel(filepath, sheet_name=0, dtype=str, keep_default_na=False)
        columns = list(df.columns)
        sample_data = df.head(3).to_dict('records')

        os.remove(filepath)

        return jsonify({
            'success': True,
            'columns': columns,
            'sample_data': sample_data,
            'total_rows': len(df)
        })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@app.route('/templates/shopee')
def get_shopee_template():
    """Download the Shopee sample template."""
    template_path = os.path.join('core', 'data', 'exports', 'shoppe', 'penjualan_shoppe.xlsx')
    if os.path.exists(template_path):
        return send_file(template_path, as_attachment=True, download_name='Template_Shopee.xlsx')
    return jsonify({'error': 'Template not found'}), 404


@app.route('/templates/tokopedia')
def get_tokopedia_template():
    """Download the Tokopedia sample template."""
    template_path = os.path.join('core', 'data', 'exports', 'tokopedia', 'penjualan_tokopedia.xlsx')
    if os.path.exists(template_path):
        return send_file(template_path, as_attachment=True, download_name='Template_Tokopedia.xlsx')
    return jsonify({'error': 'Template not found'}), 404


@app.route('/templates/odoo')
def get_odoo_template():
    """Download the Odoo import template."""
    template_path = os.path.join('core', 'data', 'imports', 'quotations_import_template.xlsx')
    if os.path.exists(template_path):
        return send_file(template_path, as_attachment=True, download_name='Template_Odoo_Import.xlsx')
    return jsonify({'error': 'Template not found'}), 404


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
