"""
Odoo Quotation Converter
Entry point for running the Flask application
"""
from app import app

if __name__ == '__main__':
    print("=" * 60)
    print("  🚀 Odoo Quotation Converter")
    print("  🌐 Buka http://localhost:5000 di browser")
    print("=" * 60)
    app.run(debug=True, host='0.0.0.0', port=5000)