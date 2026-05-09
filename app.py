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
    chart_data = data.get('chart_data', [])

    # --- Premium Color Palette ---
    C_NAVY = (10, 15, 36)
    C_ROYAL = (59, 73, 223)
    C_GOLD = (212, 175, 55)
    C_WHITE = (255, 255, 255)
    C_OFF_WHITE = (245, 246, 250)
    C_LIGHT_GRAY = (230, 232, 238)
    C_MID_GRAY = (140, 148, 165)
    C_DARK_TEXT = (28, 35, 55)
    C_GREEN = (16, 185, 129)
    C_RED = (239, 68, 68)
    C_AMBER = (245, 158, 11)

    # Pre-calculate metrics
    total_missing = sum(insights.get('missing_values', {}).values()) if insights.get('missing_values') else 0
    total_records = insights.get('rows', 0)
    total_features = insights.get('columns', 0)
    dtypes = insights.get('dtypes', {})
    stats_data = insights.get('stats', {})
    cat_values = insights.get('categorical_values', {})
    total_cells = total_records * total_features
    quality_pct = ((total_cells - total_missing) / total_cells * 100) if total_cells > 0 else 100
    numeric_count = sum(1 for c in insights.get('col_names', []) if 'int' in dtypes.get(c, '').lower() or 'float' in dtypes.get(c, '').lower())
    categorical_count = total_features - numeric_count

    class ReportPDF(FPDF):
        def footer(self):
            self.set_y(-12)
            self.set_font("Helvetica", 'I', 7)
            self.set_text_color(*C_MID_GRAY)
            self.set_draw_color(*C_LIGHT_GRAY)
            self.line(15, self.get_y(), 195, self.get_y())
            self.cell(90, 8, "InsightFlow Premium Analytics", 0, 0, 'L')
            self.cell(90, 8, f"Page {self.page_no()}", 0, 0, 'R')

    def section_header(pdf, number, title):
        if pdf.get_y() > 230:
            pdf.add_page()
        pdf.ln(6)
        pdf.set_fill_color(*C_ROYAL)
        pdf.rect(15, pdf.get_y(), 3, 10, 'F')
        pdf.set_xy(22, pdf.get_y())
        pdf.set_font("Helvetica", 'B', 13)
        pdf.set_text_color(*C_NAVY)
        pdf.cell(0, 10, f"{number}. {title}", ln=True)
        pdf.set_draw_color(*C_LIGHT_GRAY)
        pdf.line(15, pdf.get_y(), 195, pdf.get_y())
        pdf.ln(5)

    def metric_card(pdf, x, y, label, value, color):
        w = 42
        pdf.set_fill_color(*C_OFF_WHITE)
        pdf.set_draw_color(*C_LIGHT_GRAY)
        pdf.rect(x, y, w, 22, 'DF')
        pdf.set_fill_color(*color)
        pdf.rect(x, y, w, 1.5, 'F')
        pdf.set_xy(x + 2, y + 4)
        pdf.set_font("Helvetica", 'B', 14)
        pdf.set_text_color(*C_NAVY)
        pdf.cell(w - 4, 7, str(value), 0, 0, 'C')
        pdf.set_xy(x + 2, y + 12)
        pdf.set_font("Helvetica", size=7)
        pdf.set_text_color(*C_MID_GRAY)
        pdf.cell(w - 4, 5, label, 0, 0, 'C')

    def fmt(v):
        try:
            if float(v).is_integer():
                return f"{int(v):,}"
            return f"{float(v):,.2f}"
        except:
            return str(v)

    pdf = ReportPDF()
    pdf.set_auto_page_break(auto=True, margin=18)
    pdf.add_page()

    # ===================== COVER HEADER =====================
    pdf.set_fill_color(*C_NAVY)
    pdf.rect(0, 0, 210, 52, 'F')
    pdf.set_fill_color(*C_GOLD)
    pdf.rect(0, 52, 210, 1.5, 'F')

    pdf.set_font("Helvetica", 'B', 30)
    pdf.set_text_color(*C_WHITE)
    pdf.set_xy(15, 10)
    pdf.cell(0, 14, "INSIGHTFLOW", ln=True)
    pdf.set_font("Helvetica", size=10)
    pdf.set_text_color(*C_GOLD)
    pdf.set_xy(15, 24)
    pdf.cell(0, 8, "Data Analysis Report", ln=True)
    pdf.set_font("Helvetica", 'I', 8)
    pdf.set_text_color(180, 185, 210)
    pdf.set_xy(15, 34)
    pdf.cell(0, 6, f"Dataset: {filename}  |  Generated: {pd.Timestamp.now().strftime('%B %d, %Y at %H:%M')}", ln=True)

    pdf.set_y(60)

    # ===================== METRIC CARDS =====================
    card_y = pdf.get_y()
    metric_card(pdf, 15, card_y, "RECORDS", f"{total_records:,}", C_ROYAL)
    metric_card(pdf, 60, card_y, "FEATURES", str(total_features), C_GOLD)
    metric_card(pdf, 105, card_y, "MISSING", f"{total_missing:,}", C_RED if total_missing > 0 else C_GREEN)
    metric_card(pdf, 150, card_y, "QUALITY", f"{quality_pct:.0f}%", C_GREEN if quality_pct >= 80 else C_AMBER)
    pdf.set_y(card_y + 28)

    # ===================== 1. OVERVIEW =====================
    section_header(pdf, 1, "REPORT OVERVIEW")
    pdf.set_x(15)
    pdf.set_font("Helvetica", size=10)
    pdf.set_text_color(*C_DARK_TEXT)
    pdf.multi_cell(180, 5.5, (
        f"This report presents a comprehensive analysis of '{filename}', containing "
        f"{total_records:,} records across {total_features} features ({numeric_count} numeric, "
        f"{categorical_count} categorical). Overall data quality stands at {quality_pct:.1f}%, "
        f"with {total_missing:,} missing values detected. The sections below detail data health, "
        f"statistical distributions, column types, chart insights, and actionable recommendations."
    ))

    # ===================== 2. BASIC INFORMATIONS =====================
    section_header(pdf, 2, "BASIC INFORMATIONS & SUMMARY")
    box_y = pdf.get_y()
    pdf.set_fill_color(*C_OFF_WHITE)
    pdf.set_draw_color(*C_ROYAL)
    pdf.set_line_width(0.4)
    pdf.rect(15, box_y, 180, 32, 'DF')
    pdf.set_line_width(0.2)
    pdf.set_fill_color(*C_ROYAL)
    pdf.rect(15, box_y, 2.5, 32, 'F')

    pdf.set_xy(22, box_y + 4)
    for label, val in [["Dataset:", filename], ["Records:", f"{total_records:,}"], ["Features:", str(total_features)], ["Generated:", pd.Timestamp.now().strftime("%Y-%m-%d %H:%M")]]:
        pdf.set_x(22)
        pdf.set_font("Helvetica", 'B', 10)
        pdf.set_text_color(*C_NAVY)
        pdf.cell(35, 5.5, label)
        pdf.set_font("Helvetica", size=10)
        pdf.set_text_color(*C_MID_GRAY)
        pdf.cell(0, 5.5, val, ln=True)
    pdf.set_y(box_y + 38)

    # ===================== 3. DATA HEALTH =====================
    section_header(pdf, 3, "DATA HEALTH REPORT")
    pdf.set_x(15)
    pdf.set_font("Helvetica", 'B', 9)
    pdf.set_fill_color(*C_NAVY)
    pdf.set_text_color(*C_WHITE)
    pdf.set_draw_color(*C_NAVY)
    pdf.cell(80, 9, "  Column Name", 1, 0, 'L', True)
    pdf.cell(50, 9, "Missing Values", 1, 0, 'C', True)
    pdf.cell(50, 9, "Completeness", 1, 1, 'C', True)

    pdf.set_font("Helvetica", size=9)
    fill = False
    for col, missing in insights.get('missing_values', {}).items():
        rows = max(insights.get('rows', 1), 1)
        completeness = ((rows - missing) / rows) * 100
        pdf.set_x(15)
        pdf.set_fill_color(*C_OFF_WHITE) if fill else pdf.set_fill_color(*C_WHITE)
        pdf.set_text_color(*C_DARK_TEXT)
        pdf.set_draw_color(*C_LIGHT_GRAY)
        col_d = col if len(col) < 35 else col[:32] + "..."
        pdf.cell(80, 8, f"  {col_d}", 1, 0, 'L', fill)
        pdf.set_text_color(*C_RED) if missing > 0 else pdf.set_text_color(*C_GREEN)
        pdf.cell(50, 8, f"{missing:,}", 1, 0, 'C', fill)
        pdf.set_text_color(*C_RED) if completeness < 100 else pdf.set_text_color(*C_GREEN)
        pdf.cell(50, 8, f"{completeness:.1f}%", 1, 1, 'C', fill)
        fill = not fill
    pdf.ln(6)

    # ===================== 4. NUMERICAL ANALYSIS =====================
    if stats_data:
        section_header(pdf, 4, "NUMERICAL ANALYSIS")
        pdf.set_x(15)
        pdf.set_font("Helvetica", 'B', 9)
        pdf.set_fill_color(*C_NAVY)
        pdf.set_text_color(*C_WHITE)
        pdf.set_draw_color(*C_NAVY)
        ws = [45, 34, 33, 33, 35]
        for i, h in enumerate(["Column", "Mean", "Min", "Max", "Std Dev"]):
            pdf.cell(ws[i], 9, h, 1, 0, 'C', True)
        pdf.ln()
        pdf.set_font("Helvetica", size=9)
        fill = False
        for cn in insights.get('col_names', []):
            if cn not in stats_data:
                continue
            pdf.set_x(15)
            pdf.set_fill_color(*C_OFF_WHITE) if fill else pdf.set_fill_color(*C_WHITE)
            pdf.set_text_color(*C_DARK_TEXT)
            pdf.set_draw_color(*C_LIGHT_GRAY)
            cd = cn if len(cn) < 22 else cn[:19] + "..."
            pdf.cell(ws[0], 8, f"  {cd}", 1, 0, 'L', fill)
            s = stats_data[cn]
            pdf.cell(ws[1], 8, fmt(s.get('mean', 0)), 1, 0, 'C', fill)
            pdf.cell(ws[2], 8, fmt(s.get('min', 0)), 1, 0, 'C', fill)
            pdf.cell(ws[3], 8, fmt(s.get('max', 0)), 1, 0, 'C', fill)
            pdf.cell(ws[4], 8, fmt(s.get('std', 0)), 1, 1, 'C', fill)
            fill = not fill
        pdf.ln(6)

    # ===================== 5. COLUMN TYPE BREAKDOWN =====================
    section_header(pdf, 5, "COLUMN TYPE BREAKDOWN")
    pdf.set_x(15)
    pdf.set_font("Helvetica", 'B', 9)
    pdf.set_fill_color(*C_NAVY)
    pdf.set_text_color(*C_WHITE)
    pdf.set_draw_color(*C_NAVY)
    pdf.cell(10, 9, "#", 1, 0, 'C', True)
    pdf.cell(60, 9, "  Column Name", 1, 0, 'L', True)
    pdf.cell(30, 9, "Type", 1, 0, 'C', True)
    pdf.cell(25, 9, "Missing", 1, 0, 'C', True)
    pdf.cell(55, 9, "Key Statistic", 1, 1, 'C', True)

    pdf.set_font("Helvetica", size=8)
    fill = False
    for idx, cn in enumerate(insights.get('col_names', []), 1):
        pdf.set_x(15)
        pdf.set_fill_color(*C_OFF_WHITE) if fill else pdf.set_fill_color(*C_WHITE)
        pdf.set_text_color(*C_DARK_TEXT)
        pdf.set_draw_color(*C_LIGHT_GRAY)
        pdf.cell(10, 8, str(idx), 1, 0, 'C', fill)
        cd = cn if len(cn) < 26 else cn[:23] + "..."
        pdf.cell(60, 8, f"  {cd}", 1, 0, 'L', fill)
        dt = dtypes.get(cn, '').lower()
        tn = "Integer" if 'int' in dt else "Decimal" if 'float' in dt else "Date" if 'date' in dt else "Boolean" if 'bool' in dt else "Text"
        pdf.set_text_color(*C_ROYAL)
        pdf.cell(30, 8, tn, 1, 0, 'C', fill)
        mc = insights.get('missing_values', {}).get(cn, 0)
        pdf.set_text_color(*C_RED) if mc > 0 else pdf.set_text_color(*C_GREEN)
        pdf.cell(25, 8, str(mc), 1, 0, 'C', fill)
        pdf.set_text_color(*C_MID_GRAY)
        if cn in stats_data:
            try:
                ks = f"Avg: {float(stats_data[cn].get('mean', 0)):,.2f}"
            except:
                ks = "-"
        elif cn in cat_values:
            ks = f"Unique: {len(cat_values[cn])}"
        else:
            ks = "-"
        pdf.cell(55, 8, ks, 1, 1, 'C', fill)
        fill = not fill
    pdf.ln(6)

    # ===================== 6. VISUAL INSIGHTS =====================
    if chart_data:
        section_header(pdf, 6, "VISUAL INSIGHTS SUMMARY")
        pdf.set_x(15)
        pdf.set_font("Helvetica", 'I', 9)
        pdf.set_text_color(*C_MID_GRAY)
        pdf.multi_cell(180, 5, "Summaries derived from charts generated during data analysis:")
        pdf.ln(3)

        for i, chart in enumerate(chart_data, 1):
            ct = chart.get('type', '')
            ctitle = chart.get('title', '')
            cl = chart.get('labels', [])
            cd_list = chart.get('data', [])

            cy = pdf.get_y()
            if cy > 250:
                pdf.add_page()
                cy = pdf.get_y()
            pdf.set_fill_color(*C_OFF_WHITE)
            pdf.set_draw_color(*C_LIGHT_GRAY)
            pdf.rect(15, cy, 180, 16, 'DF')
            pdf.set_fill_color(*C_GOLD)
            pdf.rect(15, cy, 2.5, 16, 'F')

            pdf.set_xy(22, cy + 2)
            pdf.set_font("Helvetica", 'B', 9)
            pdf.set_text_color(*C_NAVY)
            pdf.cell(0, 5, f"Chart {i}: {ctitle}", ln=True)

            pdf.set_x(22)
            pdf.set_font("Helvetica", size=8)
            pdf.set_text_color(*C_MID_GRAY)
            desc = ""
            try:
                if ct in ['bar', 'pie', 'doughnut'] and cl and cd_list and not isinstance(cd_list[0], dict):
                    nd = [float(x) for x in cd_list]
                    desc = f"{ct.capitalize()} | {len(cd_list)} categories | Peak: '{cl[nd.index(max(nd))]}' ({max(nd):,.2f})"
                elif ct == 'line' and cd_list and not isinstance(cd_list[0], dict):
                    nd = [float(x) for x in cd_list]
                    trend = "Upward" if nd[-1] > nd[0] else "Downward"
                    desc = f"Line | {len(cd_list)} points | Trend: {trend} | Range: {min(nd):,.2f} - {max(nd):,.2f}"
                elif ct == 'scatter' and cd_list:
                    desc = f"Scatter | {len(cd_list)} points | {chart.get('xLabel', 'X')} vs {chart.get('yLabel', 'Y')}"
                else:
                    desc = f"{ct.capitalize()} chart | See interactive dashboard for details"
            except Exception:
                desc = f"{ct.capitalize()} chart | Data processed"
            pdf.cell(0, 5, desc, ln=True)
            pdf.set_y(cy + 18)

    # ===================== 7. KEY FINDINGS =====================
    section_header(pdf, 7, "KEY FINDINGS & RECOMMENDATIONS")

    q_label = "EXCELLENT" if quality_pct >= 95 else "GOOD" if quality_pct >= 80 else "NEEDS ATTENTION" if quality_pct >= 50 else "POOR"
    q_color = C_GREEN if quality_pct >= 80 else C_AMBER if quality_pct >= 50 else C_RED

    by = pdf.get_y()
    pdf.set_fill_color(*C_NAVY)
    pdf.rect(15, by, 180, 22, 'F')
    pdf.set_fill_color(*C_GOLD)
    pdf.rect(15, by, 180, 1.5, 'F')

    pdf.set_xy(20, by + 4)
    pdf.set_font("Helvetica", size=9)
    pdf.set_text_color(180, 185, 210)
    pdf.cell(50, 5, "OVERALL DATA QUALITY")
    pdf.set_font("Helvetica", 'B', 18)
    pdf.set_text_color(*q_color)
    pdf.cell(40, 5, f"{quality_pct:.1f}%")
    pdf.set_font("Helvetica", 'B', 10)
    pdf.set_text_color(*C_GOLD)
    pdf.cell(0, 5, q_label, ln=True)

    pdf.set_xy(20, by + 13)
    pdf.set_font("Helvetica", size=8)
    pdf.set_text_color(160, 165, 185)
    pdf.cell(0, 5, f"{total_records:,} records  |  {numeric_count} numeric + {categorical_count} categorical  |  {total_missing:,} missing values", ln=True)

    pdf.set_y(by + 28)

    pdf.set_x(15)
    pdf.set_font("Helvetica", 'B', 10)
    pdf.set_text_color(*C_NAVY)
    pdf.cell(0, 7, "Recommendations", ln=True)
    pdf.ln(2)

    recs = []
    cols_with_missing = [c for c, v in insights.get('missing_values', {}).items() if v > 0]
    if total_missing == 0:
        recs.append("The dataset is fully complete with zero missing values -- ready for modeling.")
    else:
        if len(cols_with_missing) <= 3:
            recs.append(f"Missing values in: {', '.join(cols_with_missing)}. Apply imputation or drop incomplete rows.")
        else:
            recs.append(f"{len(cols_with_missing)} columns have missing data. Use Auto Clean on the dashboard.")
    if numeric_count > 0:
        recs.append(f"{numeric_count} numeric column(s) detected. Check distributions for outliers.")
    if categorical_count > 0:
        recs.append(f"{categorical_count} categorical column(s). Verify class balance before classification.")
    if quality_pct >= 95:
        recs.append("Excellent quality -- suitable for statistical modeling and ML workflows.")
    elif quality_pct < 80:
        recs.append("Quality below 80%. Data cleaning strongly recommended before analytics.")

    pdf.set_font("Helvetica", size=9)
    pdf.set_text_color(*C_DARK_TEXT)
    for r in recs:
        if pdf.get_y() > 265:
            pdf.add_page()
        pdf.set_fill_color(*C_OFF_WHITE)
        pdf.set_draw_color(*C_LIGHT_GRAY)
        pdf.rect(15, pdf.get_y(), 180, 8, 'DF')
        pdf.set_fill_color(*C_ROYAL)
        pdf.rect(15, pdf.get_y(), 2, 8, 'F')
        pdf.set_xy(20, pdf.get_y() + 1.5)
        pdf.cell(0, 5, r, ln=True)
        pdf.set_y(pdf.get_y() + 3)

    pdf.ln(8)

    # ===================== DISCLAIMER =====================
    if pdf.get_y() > 260:
        pdf.add_page()
    pdf.set_draw_color(*C_LIGHT_GRAY)
    pdf.line(15, pdf.get_y(), 195, pdf.get_y())
    pdf.ln(3)
    pdf.set_x(15)
    pdf.set_font("Helvetica", 'I', 7)
    pdf.set_text_color(*C_MID_GRAY)
    pdf.multi_cell(180, 3.5,
        "Disclaimer: This report was auto-generated by InsightFlow Data Analytics Platform. "
        "The insights and recommendations are based on statistical analysis of the uploaded dataset "
        "and should be reviewed by a domain expert before making critical business decisions. "
        f"Report generated on {pd.Timestamp.now().strftime('%Y-%m-%d at %H:%M:%S')}."
    )

    # Return PDF
    output = io.BytesIO()
    pdf_bytes = pdf.output(dest='S')
    if isinstance(pdf_bytes, str):
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
