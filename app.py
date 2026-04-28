import os
import pandas as pd
from flask import Flask, render_template, request, jsonify, flash, redirect, url_for
from werkzeug.utils import secure_filename
from utils.analyzer import DataAnalyzer
from fpdf import FPDF
from flask import send_file
import io

app = Flask(__name__)
app.secret_key = 'insightflow_secret'
app.config['UPLOAD_FOLDER'] = os.path.join(os.getcwd(), 'uploads')
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16 MB limit

# Ensure upload folder exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

ALLOWED_EXTENSIONS = {'csv', 'xlsx'}

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/dashboard')
def dashboard():
    return render_template('dashboard.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
    
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        
        # Process data
        try:
            analyzer = DataAnalyzer(filepath)
            insights = analyzer.get_summary()
            chart_data = analyzer.get_chart_data()
            return jsonify({
                'success': True,
                'insights': insights,
                'chart_data': chart_data,
                'filename': filename
            })
        except Exception as e:
            return jsonify({'error': str(e)}), 500
            
    return jsonify({'error': 'Invalid file type'}), 400

@app.route('/export-pdf', methods=['POST'])
def export_pdf():
    data = request.json
    filename = data.get('filename')
    insights = data.get('insights')
    
    pdf = FPDF()
    pdf.add_page()
    
    # Header
    pdf.set_fill_color(30, 31, 35) # Dark theme color
    pdf.rect(0, 0, 210, 40, 'F')
    
    pdf.set_font("Helvetica", 'B', 24)
    pdf.set_text_color(86, 205, 12) # Primary Green
    pdf.set_xy(10, 10)
    pdf.cell(0, 20, "INSIGHTFLOW", ln=True)
    
    pdf.set_font("Helvetica", size=10)
    pdf.set_text_color(200, 200, 200)
    pdf.set_xy(10, 25)
    pdf.cell(0, 10, "DATA ANALYSIS REPORT", ln=True)
    
    pdf.ln(20)
    
    # Executive Summary Section
    pdf.set_text_color(0, 0, 0)
    pdf.set_font("Helvetica", 'B', 16)
    pdf.cell(0, 10, "1. EXECUTIVE SUMMARY", ln=True)
    pdf.set_draw_color(86, 205, 12)
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
    pdf.ln(5)
    
    pdf.set_font("Helvetica", size=11)
    summary_data = [
        ["Dataset Name:", filename],
        ["Total Records:", str(insights['rows'])],
        ["Total Features:", str(insights['columns'])],
        ["Date Generated:", pd.Timestamp.now().strftime("%Y-%m-%d %H:%M")]
    ]
    
    for label, val in summary_data:
        pdf.set_font("Helvetica", 'B', 11)
        pdf.cell(40, 8, label)
        pdf.set_font("Helvetica", size=11)
        pdf.cell(0, 8, val, ln=True)
    
    pdf.ln(10)
    
    # Data Health Section
    pdf.set_font("Helvetica", 'B', 16)
    pdf.cell(0, 10, "2. DATA HEALTH REPORT", ln=True)
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
    pdf.ln(5)
    
    pdf.set_font("Helvetica", 'B', 10)
    pdf.set_fill_color(240, 240, 240)
    pdf.cell(80, 10, "Column Name", 1, 0, 'C', True)
    pdf.cell(50, 10, "Missing Values", 1, 0, 'C', True)
    pdf.cell(50, 10, "Completeness (%)", 1, 1, 'C', True)
    
    pdf.set_font("Helvetica", size=10)
    for col, missing in insights['missing_values'].items():
        completeness = ((insights['rows'] - missing) / insights['rows']) * 100
        pdf.cell(80, 8, col, 1)
        pdf.cell(50, 8, str(missing), 1, 0, 'C')
        pdf.cell(50, 8, f"{completeness:.1f}%", 1, 1, 'C')
        
    pdf.ln(10)
    
    # Detailed Statistics Section
    if insights.get('stats'):
        # Check if we need a new page
        if pdf.get_y() > 200:
            pdf.add_page()
            
        pdf.set_font("Helvetica", 'B', 16)
        pdf.cell(0, 10, "3. NUMERICAL ANALYSIS", ln=True)
        pdf.line(10, pdf.get_y(), 200, pdf.get_y())
        pdf.ln(5)
        
        pdf.set_font("Helvetica", 'B', 9)
        cols = ["Column", "Mean", "Min", "Max", "Std Dev"]
        widths = [50, 35, 30, 30, 35]
        
        for i, col in enumerate(cols):
            pdf.cell(widths[i], 10, col, 1, 0, 'C', True)
        pdf.ln()
        
        pdf.set_font("Helvetica", size=8)
        # Transpose stats back to readable format
        stats_data = insights['stats']
        # The stats dictionary from describe() has nested keys: metric -> column -> value
        # Or column -> metric -> value depending on how it was converted
        # insights['stats'] was created via df.describe().to_dict()
        
        metrics = ["mean", "min", "max", "std"]
        for col_name in insights['col_names']:
            # Check if this column has stats
            if col_name not in stats_data:
                continue
                
            pdf.cell(widths[0], 8, col_name, 1)
            pdf.cell(widths[1], 8, f"{stats_data[col_name].get('mean', 0):.2f}", 1, 0, 'R')
            pdf.cell(widths[2], 8, f"{stats_data[col_name].get('min', 0):.2f}", 1, 0, 'R')
            pdf.cell(widths[3], 8, f"{stats_data[col_name].get('max', 0):.2f}", 1, 0, 'R')
            pdf.cell(widths[4], 8, f"{stats_data[col_name].get('std', 0):.2f}", 1, 1, 'R')

    # Footer
    pdf.set_y(-15)
    pdf.set_font("Helvetica", 'I', 8)
    pdf.set_text_color(150, 150, 150)
    pdf.cell(0, 10, f"Page {pdf.page_no()} | Generated by InsightFlow Premium Data Service", 0, 0, 'C')
    
    # Return as response
    output = io.BytesIO()
    # fpdf1 uses dest='S' for bytes output
    pdf_bytes = pdf.output(dest='S')
    
    if isinstance(pdf_bytes, str):
        # fpdf1 might return latin-1 string
        pdf_bytes = pdf_bytes.encode('latin-1')
        
    output.write(pdf_bytes)
    output.seek(0)
    
    base_filename = os.path.splitext(filename)[0]
    return send_file(
        output,
        mimetype='application/pdf',
        as_attachment=True,
        download_name=f"Report_{base_filename}.pdf"
    )

@app.route('/filter-data', methods=['POST'])
def filter_data():
    data = request.json
    filename = data.get('filename')
    filters = data.get('filters', {})
    
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    if not os.path.exists(filepath):
        return jsonify({'error': 'File not found'}), 404
        
    try:
        analyzer = DataAnalyzer(filepath)
        # Simple client-side filtering logic
        for col, val in filters.items():
            if val != 'all' and val is not None:
                analyzer.df = analyzer.df[analyzer.df[col].astype(str) == str(val)]
        
        # Search filter (across all columns)
        search_query = data.get('search', '').lower()
        if search_query:
            mask = analyzer.df.astype(str).apply(lambda x: x.str.contains(search_query, case=False)).any(axis=1)
            analyzer.df = analyzer.df[mask]

        if analyzer.df.empty:
            return jsonify({'error': 'No data matches the selected filters'}), 400

        insights = analyzer.get_summary()
        chart_data = analyzer.get_chart_data()
        return jsonify({
            'success': True,
            'insights': insights,
            'chart_data': chart_data
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/clean-data', methods=['POST'])
def clean_data():
    data = request.json
    filename = data.get('filename')
    instructions = data.get('instructions', {})
    
    if not filename:
        return jsonify({'error': 'Filename is required'}), 400
        
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    if not os.path.exists(filepath):
        return jsonify({'error': 'File not found'}), 404
        
    try:
        analyzer = DataAnalyzer(filepath)
        analyzer.clean_data(instructions, filepath)
        
        # Reload to get updated stats
        analyzer = DataAnalyzer(filepath)
        insights = analyzer.get_summary()
        chart_data = analyzer.get_chart_data()
        
        return jsonify({
            'success': True,
            'insights': insights,
            'chart_data': chart_data
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    app.run(debug=True)
