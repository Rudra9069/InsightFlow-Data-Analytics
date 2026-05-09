document.addEventListener('DOMContentLoaded', () => {
    const uploadForm = document.getElementById('upload-form');
    const fileInput = document.getElementById('file-input');
    const dropZone = document.getElementById('drop-zone');
    const fileNameDisplay = document.getElementById('file-name-display');
    const analyzeBtn = document.getElementById('analyze-btn');
    const loadingDiv = document.getElementById('loading');
    const resultsSection = document.getElementById('results');
    const chartsContainer = document.getElementById('charts-container');
    const reuploadBtn = document.getElementById('reupload-btn');

    // Modal elements
    const cleanModal = document.getElementById('clean-modal');
    const openCleanModalBtn = document.getElementById('open-clean-modal-btn');
    const closeCleanModalBtn = document.getElementById('close-modal-btn');
    const cancelCleanBtn = document.getElementById('cancel-clean-btn');
    const applyCleanBtn = document.getElementById('apply-clean-btn');
    const cleanModalTbody = document.getElementById('clean-modal-tbody');

    // Drag and drop logic
    dropZone.onclick = () => fileInput.click();
    
    fileInput.onchange = (e) => {
        if (e.target.files.length > 0) {
            const file = e.target.files[0];
            fileNameDisplay.textContent = `Selected: ${file.name}`;
            analyzeBtn.disabled = false;
            reuploadBtn.style.display = 'inline-block';
            // Add a "pressed" effect to the dropzone
            dropZone.style.boxShadow = 'inset 8px 8px 16px var(--shadow-dark), inset -8px -8px 16px var(--shadow-light)';
        }
    };

    let currentChartData = [];
    let activeCharts = [];
    let currentInsights = null;
    let currentFilename = null;

    reuploadBtn.onclick = () => {
        resultsSection.style.display = 'none';
        chartsContainer.innerHTML = '';
        currentChartData = [];
        activeCharts.forEach(c => c.destroy());
        activeCharts = [];
        fileInput.value = '';
        fileNameDisplay.innerHTML = 'Drag & Drop your file or <span style="color:var(--primary-color); text-decoration: underline;">Browse</span>';
        dropZone.style.boxShadow = '';
        analyzeBtn.disabled = true;
        reuploadBtn.style.display = 'none';
        window.scrollTo({ top: 0, behavior: 'smooth' });
    };

    uploadForm.onsubmit = async (e) => {
        e.preventDefault();
        const formData = new FormData(uploadForm);
        
        loadingDiv.style.display = 'none'; 
        resultsSection.style.display = 'none';
        analyzeBtn.disabled = true;

        const progressContainer = document.getElementById('progress-container');
        const progressBar = document.getElementById('progress-bar');
        const progressText = document.getElementById('progress-text');
        
        let progressInterval;
        const startTime = Date.now();
        const MIN_DURATION = 5000; // Force at least 5 seconds

        if (progressContainer) {
            progressContainer.style.display = 'block';
            progressBar.style.width = '0%';
            progressText.textContent = '0%';
            
            let progress = 0;
            progressInterval = setInterval(() => {
                if (progress < 90) {
                    progress += Math.floor(Math.random() * 4) + 2; // Add 2-5% per tick
                    if (progress > 90) progress = 90;
                    progressBar.style.width = `${progress}%`;
                    progressText.textContent = `${progress}%`;
                }
            }, 200);
        }

        try {
            const response = await fetch('/upload', {
                method: 'POST',
                body: formData
            });
            const data = await response.json();

            if (data.success) {
                const timeElapsed = Date.now() - startTime;
                const timeRemaining = Math.max(0, MIN_DURATION - timeElapsed);

                setTimeout(() => {
                    if (progressContainer) {
                        clearInterval(progressInterval);
                        progressBar.style.width = '100%';
                        progressText.textContent = '100%';
                        
                        setTimeout(() => {
                            progressContainer.style.display = 'none';
                            currentChartData = data.chart_data;
                            renderResults(data);
                            analyzeBtn.disabled = false;
                        }, 500);
                    } else {
                        currentChartData = data.chart_data;
                        renderResults(data);
                        analyzeBtn.disabled = false;
                    }
                }, timeRemaining);
            } else {
                alert('Error: ' + data.error);
                if (progressContainer) {
                    clearInterval(progressInterval);
                    progressContainer.style.display = 'none';
                }
                analyzeBtn.disabled = false;
            }
        } catch (err) {
            alert('Upload failed: ' + err.message);
            if (progressContainer) {
                clearInterval(progressInterval);
                progressContainer.style.display = 'none';
            }
            analyzeBtn.disabled = false;
        }
    };

    function renderResults(data) {
        currentInsights = data.insights;
        currentFilename = data.filename;
        resultsSection.style.display = 'block';
        document.getElementById('current-filename').textContent = data.filename;
        updateStats(data.insights);
        renderOverview(data.insights);

        // Populate Category Filter
        const catFilter = document.getElementById('category-filter');
        catFilter.innerHTML = '<option value="all">All Categories</option>';
        
        // Use first categorical column for now
        const firstCat = Object.keys(data.insights.categorical_values)[0];
        if (firstCat) {
            data.insights.categorical_values[firstCat].forEach(val => {
                const opt = document.createElement('option');
                opt.value = val;
                opt.textContent = val;
                catFilter.appendChild(opt);
            });
            catFilter.dataset.column = firstCat;
        }

        // Clear and render charts
        chartsContainer.innerHTML = '';
        activeCharts.forEach(c => c.destroy());
        activeCharts = [];

        currentChartData.forEach((chart, index) => {
            renderChart(chart, index);
        });

        // Trigger animation
        resultsSection.classList.add('animate-in');

        // Wire up Filters
        const applyBtn = document.getElementById('apply-filters');
        const resetBtn = document.getElementById('reset-filters');
        const searchInput = document.getElementById('search-filter');

        applyBtn.onclick = async () => {
            const filters = {};
            if (catFilter.value !== 'all') {
                filters[catFilter.dataset.column] = catFilter.value;
            }
            
            applyBtn.disabled = true;
            applyBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Filtering...';

            try {
                const res = await fetch('/filter-data', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        filename: data.filename,
                        filters: filters,
                        search: searchInput.value
                    })
                });
                const filterResult = await res.json();
                if (filterResult.success) {
                    currentChartData = filterResult.chart_data;
                    currentInsights = filterResult.insights;
                    updateStats(filterResult.insights);
                    renderOverview(filterResult.insights);
                    chartsContainer.innerHTML = '';
                    activeCharts.forEach(c => c.destroy());
                    currentChartData.forEach((c, idx) => renderChart(c, idx));
                } else {
                    alert(filterResult.error || 'Filter failed');
                }
            } catch (err) {
                alert('Filter error');
            } finally {
                applyBtn.disabled = false;
                applyBtn.innerHTML = 'Apply Filters';
            }
        };

        resetBtn.onclick = () => {
            catFilter.value = 'all';
            searchInput.value = '';
            applyBtn.click();
        };

        // Export PDF Handler
        const exportBtn = document.getElementById('export-pdf-btn');
        exportBtn.onclick = async () => {
            exportBtn.disabled = true;
            exportBtn.textContent = 'Generating...';
            try {
                const response = await fetch('/export-pdf', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        filename: currentFilename,
                        insights: currentInsights,
                        chart_data: currentChartData
                    })
                });
                const blob = await response.blob();
                const url = window.URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                const baseName = data.filename.split('.').slice(0, -1).join('.') || data.filename;
                a.download = `Report_${baseName}.pdf`;
                document.body.appendChild(a);
                a.click();
                a.remove();
            } catch (err) {
                alert('Export failed');
            } finally {
                exportBtn.disabled = false;
                exportBtn.textContent = 'Export Report (PDF)';
            }
        };
    }

    function updateStats(insights) {
        document.getElementById('row-count').textContent = insights.rows;
        document.getElementById('col-count').textContent = insights.columns;
        const totalMissing = Object.values(insights.missing_values).reduce((a, b) => a + b, 0);
        document.getElementById('missing-count').textContent = totalMissing;
    }

    function renderOverview(insights) {
        const rows = insights.rows;
        const cols = insights.col_names;
        const dtypes = insights.dtypes || {};
        const missing = insights.missing_values;
        const stats = insights.stats || {};
        const catValues = insights.categorical_values || {};

        // Count column types
        let numericCount = 0, categoricalCount = 0;
        cols.forEach(col => {
            const dt = (dtypes[col] || '').toLowerCase();
            if (dt.includes('int') || dt.includes('float')) numericCount++;
            else categoricalCount++;
        });

        // Data quality = overall completeness
        const totalCells = rows * cols.length;
        const totalMissing = Object.values(missing).reduce((a, b) => a + b, 0);
        const quality = totalCells > 0 ? ((totalCells - totalMissing) / totalCells * 100) : 0;

        // Complete rows % (rows with zero missing)
        const colsMissingArr = Object.values(missing);
        const maxPossibleMissing = colsMissingArr.reduce((a, b) => a + b, 0);
        const completeRowsPct = totalCells > 0 ? ((totalCells - maxPossibleMissing) / totalCells * 100) : 0;

        // Update summary cards
        document.getElementById('quality-score').textContent = quality.toFixed(1) + '%';
        document.getElementById('numeric-cols-count').textContent = numericCount;
        document.getElementById('categorical-cols-count').textContent = categoricalCount;
        document.getElementById('complete-rows').textContent = completeRowsPct.toFixed(1) + '%';

        // Always show the button
        document.getElementById('open-clean-modal-btn').style.display = 'block';

        // Populate table
        const tbody = document.getElementById('overview-table-body');
        tbody.innerHTML = '';

        cols.forEach((col, i) => {
            const dt = dtypes[col] || 'unknown';
            const missingCount = missing[col] || 0;
            const completeness = rows > 0 ? ((rows - missingCount) / rows * 100) : 0;

            // Determine friendly type name and icon
            let typeName, typeIcon, typeColor;
            const dtLower = dt.toLowerCase();
            if (dtLower.includes('int')) {
                typeName = 'Integer'; typeIcon = 'fa-hashtag'; typeColor = '#4a90e2';
            } else if (dtLower.includes('float')) {
                typeName = 'Decimal'; typeIcon = 'fa-percentage'; typeColor = '#fcc419';
            } else if (dtLower.includes('datetime') || dtLower.includes('date')) {
                typeName = 'Date'; typeIcon = 'fa-calendar'; typeColor = '#ff922b';
            } else if (dtLower.includes('bool')) {
                typeName = 'Boolean'; typeIcon = 'fa-toggle-on'; typeColor = '#845ef7';
            } else {
                typeName = 'Text'; typeIcon = 'fa-font'; typeColor = '#51cf66';
            }

            // Key stats
            let keyStats = '';
            if (stats[col]) {
                const s = stats[col];
                keyStats = `Mean: ${Number(s.mean).toFixed(2)} &nbsp;|&nbsp; Min: ${Number(s.min).toFixed(2)} &nbsp;|&nbsp; Max: ${Number(s.max).toFixed(2)}`;
            } else if (catValues[col]) {
                const uniqueCount = catValues[col].length;
                const topVal = catValues[col][0] || '—';
                keyStats = `Unique: ${uniqueCount} &nbsp;|&nbsp; Top: ${topVal}`;
            } else {
                keyStats = '—';
            }

            // Completeness bar color
            let barColor = '#56cd0c';
            if (completeness < 50) barColor = '#ef4444';
            else if (completeness < 80) barColor = '#fcc419';

            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td style="padding: 0.8rem 1rem; border-bottom: 1px solid #2a2c31; color: #666;">${i + 1}</td>
                <td style="padding: 0.8rem 1rem; border-bottom: 1px solid #2a2c31; font-weight: 600;">${col}</td>
                <td style="padding: 0.8rem 1rem; border-bottom: 1px solid #2a2c31;">
                    <span style="display: inline-flex; align-items: center; gap: 0.5rem; padding: 0.25rem 0.7rem; border-radius: 8px; background: ${typeColor}18; color: ${typeColor}; font-size: 0.8rem; font-weight: 500;">
                        <i class="fa-solid ${typeIcon}"></i> ${typeName}
                    </span>
                </td>
                <td style="padding: 0.8rem 1rem; border-bottom: 1px solid #2a2c31; color: ${missingCount > 0 ? '#ef4444' : '#56cd0c'}; font-weight: 600;">${missingCount}</td>
                <td style="padding: 0.8rem 1rem; border-bottom: 1px solid #2a2c31;">
                    <div style="display: flex; align-items: center; gap: 0.8rem;">
                        <div style="flex: 1; height: 6px; background: #2a2c31; border-radius: 3px; overflow: hidden;">
                            <div style="width: ${completeness}%; height: 100%; background: ${barColor}; border-radius: 3px; transition: width 0.8s ease;"></div>
                        </div>
                        <span style="font-size: 0.8rem; color: #888; min-width: 45px; text-align: right;">${completeness.toFixed(0)}%</span>
                    </div>
                </td>
                <td style="padding: 0.8rem 1rem; border-bottom: 1px solid #2a2c31; color: #aaa; font-size: 0.82rem;">${keyStats}</td>
            `;
            tbody.appendChild(tr);
        });
    }

    function getChartColors(index, type) {
        const palettes = [
            { primary: '#56cd0c', secondary: 'rgba(86, 205, 12, 0.1)', multi: ['#56cd0c', '#4a90e2', '#ff6b6b', '#51cf66', '#fcc419', '#ff922b', '#845ef7'] },
            { primary: '#4a90e2', secondary: 'rgba(74, 144, 226, 0.1)', multi: ['#4a90e2', '#56cd0c', '#ff6b6b', '#ff922b', '#fcc419', '#845ef7', '#51cf66'] },
            { primary: '#ff6b6b', secondary: 'rgba(255, 107, 107, 0.1)', multi: ['#ff6b6b', '#fcc419', '#4a90e2', '#56cd0c', '#845ef7', '#51cf66', '#ff922b'] },
            { primary: '#fcc419', secondary: 'rgba(252, 196, 25, 0.1)', multi: ['#fcc419', '#ff922b', '#56cd0c', '#4a90e2', '#845ef7', '#ff6b6b', '#51cf66'] },
            { primary: '#845ef7', secondary: 'rgba(132, 94, 247, 0.1)', multi: ['#845ef7', '#ff6b6b', '#4a90e2', '#56cd0c', '#fcc419', '#51cf66', '#ff922b'] }
        ];

        const palette = palettes[index % palettes.length];
        
        if (['pie', 'doughnut'].includes(type)) {
            return { bg: palette.multi, border: 'transparent' };
        } else if (type === 'line') {
            return { bg: palette.secondary, border: palette.primary };
        } else {
            return { bg: palette.primary, border: 'transparent' };
        }
    }

    function renderChart(chart, index) {
        const wrapper = document.createElement('div');
        wrapper.className = 'card-inset chart-card animate-in';
        wrapper.style.animationDelay = `${index * 0.1}s`;
        
        const controls = document.createElement('div');
        controls.className = 'chart-controls';
        
        const types = [
            { id: 'bar', icon: 'fa-chart-bar' },
            { id: 'line', icon: 'fa-chart-line' },
            { id: 'pie', icon: 'fa-chart-pie' },
            { id: 'doughnut', icon: 'fa-circle-dot' },
            { id: 'scatter', icon: 'fa-braille' }
        ];

        types.forEach(t => {
            const btn = document.createElement('button');
            btn.className = `chart-toggle ${chart.type === t.id ? 'active' : ''}`;
            btn.innerHTML = `<i class="fa-solid ${t.icon}"></i>`;
            btn.onclick = () => updateChartType(index, t.id);
            controls.appendChild(btn);
        });

        const canvas = document.createElement('canvas');
        canvas.id = `chart-${index}`;
        
        wrapper.appendChild(controls);
        wrapper.appendChild(canvas);
        chartsContainer.appendChild(wrapper);

        const colors = getChartColors(index, chart.type);
        const ctx = canvas.getContext('2d');
        
        // Handle data format for scatter if it's not already in x/y format
        let chartData = chart.data;
        let chartLabels = chart.labels || [];

        if (chart.type === 'scatter') {
            if (chart.data.length > 0 && typeof chart.data[0] !== 'object') {
                chartData = chart.data.map((v, i) => ({ x: i, y: v }));
            }
        } else {
            if (chart.data.length > 0 && typeof chart.data[0] === 'object' && 'y' in chart.data[0]) {
                if (chartLabels.length === 0 && 'x' in chart.data[0]) {
                    chartLabels = chart.data.map(v => v.x);
                }
                chartData = chart.data.map(v => v.y);
            }
        }

        const newChart = new Chart(ctx, {
            type: ['pie', 'doughnut'].includes(chart.type) ? chart.type : (chart.type === 'scatter' ? 'scatter' : chart.type),
            data: {
                labels: chartLabels,
                datasets: [{
                    label: chart.title,
                    data: chartData,
                    backgroundColor: colors.bg,
                    borderColor: colors.border,
                    borderWidth: (chart.type === 'line' || chart.type === 'scatter') ? 3 : 0,
                    borderRadius: chart.type === 'bar' ? 8 : 0,
                    fill: chart.type === 'line',
                    tension: 0.4,
                    pointRadius: chart.type === 'scatter' ? 6 : 4
                }]
            },
            options: {
                responsive: true,
                plugins: {
                    legend: { display: ['pie', 'doughnut'].includes(chart.type) || chart.type === 'scatter', labels: { color: '#e8e6e3' } },
                    title: { display: true, text: chart.title, color: '#e8e6e3', font: { size: 16, weight: 'bold' } }
                },
                scales: ['pie', 'doughnut'].includes(chart.type) ? {} : {
                    y: { grid: { color: 'rgba(255,255,255,0.05)' }, border: { display: false }, ticks: { color: '#888' } },
                    x: { grid: { display: false }, border: { display: false }, ticks: { color: '#888' } }
                }
            }
        });
        activeCharts[index] = newChart;
    }

    function updateChartType(index, newType) {
        // Destroy and re-render only the specific chart
        const chartObj = currentChartData[index];
        chartObj.type = newType;
        
        const cards = document.querySelectorAll('.chart-card');
        const targetCard = cards[index];
        
        // Update toggles
        const btns = targetCard.querySelectorAll('.chart-toggle');
        btns.forEach(b => {
            b.classList.remove('active');
            const icon = b.querySelector('i');
            const iconClass = `fa-${newType === 'doughnut' ? 'circle-dot' : (newType === 'scatter' ? 'braille' : 'chart-' + newType)}`;
            if (icon.classList.contains(iconClass)) {
                b.classList.add('active');
            }
        });
        
        // Clear canvas
        const oldCanvas = targetCard.querySelector('canvas');
        const parent = oldCanvas.parentElement;
        oldCanvas.remove();
        
        const newCanvas = document.createElement('canvas');
        parent.appendChild(newCanvas);
        
        activeCharts[index].destroy();
        
        // Re-init chart with new type on new canvas
        renderChartOnCanvas(chartObj, index, newCanvas);
    }

    function renderChartOnCanvas(chart, index, canvas) {
        const colors = getChartColors(index, chart.type);
        const ctx = canvas.getContext('2d');
        
        // Handle data format for scatter if it's not already in x/y format
        let chartData = chart.data;
        let chartLabels = chart.labels || [];

        if (chart.type === 'scatter') {
            if (chart.data.length > 0 && typeof chart.data[0] !== 'object') {
                chartData = chart.data.map((v, i) => ({ x: i, y: v }));
            }
        } else {
            if (chart.data.length > 0 && typeof chart.data[0] === 'object' && 'y' in chart.data[0]) {
                if (chartLabels.length === 0 && 'x' in chart.data[0]) {
                    chartLabels = chart.data.map(v => v.x);
                }
                chartData = chart.data.map(v => v.y);
            }
        }

        const newChart = new Chart(ctx, {
            type: ['pie', 'doughnut'].includes(chart.type) ? chart.type : (chart.type === 'scatter' ? 'scatter' : chart.type),
            data: {
                labels: chartLabels,
                datasets: [{
                    label: chart.title,
                    data: chartData,
                    backgroundColor: colors.bg,
                    borderColor: colors.border,
                    borderWidth: (chart.type === 'line' || chart.type === 'scatter') ? 3 : 0,
                    borderRadius: chart.type === 'bar' ? 8 : 0,
                    fill: chart.type === 'line',
                    tension: 0.4,
                    pointRadius: chart.type === 'scatter' ? 6 : 4
                }]
            },
            options: {
                responsive: true,
                plugins: {
                    legend: { display: ['pie', 'doughnut'].includes(chart.type) || chart.type === 'scatter', labels: { color: '#e8e6e3' } },
                    title: { display: true, text: chart.title, color: '#e8e6e3', font: { size: 16, weight: 'bold' } }
                },
                scales: ['pie', 'doughnut'].includes(chart.type) ? {} : {
                    y: { grid: { color: 'rgba(255,255,255,0.05)' }, border: { display: false }, ticks: { color: '#888' } },
                    x: { grid: { display: false }, border: { display: false }, ticks: { color: '#888' } }
                }
            }
        });
        activeCharts[index] = newChart;
    }

    // Modal Logic
    openCleanModalBtn.onclick = () => {
        populateCleanModal();
        cleanModal.classList.add('active');
    };

    const closeModal = () => cleanModal.classList.remove('active');
    closeCleanModalBtn.onclick = closeModal;
    cancelCleanBtn.onclick = closeModal;

    function populateCleanModal() {
        cleanModalTbody.innerHTML = '';
        if (!currentInsights) return;

        const missing = currentInsights.missing_values;
        const dtypes = currentInsights.dtypes;
        let hasMissing = false;

        for (const col of currentInsights.col_names) {
            const missingCount = missing[col] || 0;
            if (missingCount > 0) {
                hasMissing = true;
                const dt = (dtypes[col] || '').toLowerCase();
                const isNumeric = dt.includes('int') || dt.includes('float');
                
                const tr = document.createElement('tr');
                tr.innerHTML = `
                    <td style="padding: 0.8rem; border-bottom: 1px solid #2a2c31; font-weight: 600;">${col}</td>
                    <td style="padding: 0.8rem; border-bottom: 1px solid #2a2c31; color: var(--accent-color); font-weight: 600;">${missingCount}</td>
                    <td style="padding: 0.8rem; border-bottom: 1px solid #2a2c31;">
                        <select class="btn-soft clean-strategy-select" data-col="${col}" style="padding: 0.5rem; width: 100%;">
                            <option value="none" selected>No Action</option>
                            ${isNumeric ? `
                                <option value="mean">Fill with Mean</option>
                                <option value="median">Fill with Median</option>
                            ` : `
                                <option value="mode">Fill with Mode</option>
                                <option value="unknown">Fill with "Unknown"</option>
                            `}
                            <option value="drop_rows">Drop Rows</option>
                            <option value="drop_column">Drop Column</option>
                        </select>
                    </td>
                `;
                cleanModalTbody.appendChild(tr);
            }
        }

        if (!hasMissing) {
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td colspan="3" style="padding: 2rem; text-align: center; color: var(--primary-color);">
                    <i class="fa-solid fa-circle-check" style="font-size: 2rem; margin-bottom: 1rem;"></i><br>
                    Your dataset is clean! No missing values detected.
                </td>
            `;
            cleanModalTbody.appendChild(tr);
            applyCleanBtn.style.display = 'none';
        } else {
            applyCleanBtn.style.display = 'inline-block';
        }
    }

    applyCleanBtn.onclick = async () => {
        const selects = document.querySelectorAll('.clean-strategy-select');
        const instructions = {};
        selects.forEach(sel => {
            if (sel.value !== 'none') {
                instructions[sel.dataset.col] = sel.value;
            }
        });

        if (Object.keys(instructions).length === 0) {
            closeModal();
            return;
        }

        applyCleanBtn.disabled = true;
        applyCleanBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Cleaning...';

        try {
            const res = await fetch('/clean-data', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    filename: currentFilename,
                    instructions: instructions
                })
            });

            const data = await res.json();
            if (data.success) {
                currentChartData = data.chart_data;
                renderResults(data);
                closeModal();
            } else {
                alert('Cleaning failed: ' + data.error);
            }
        } catch (err) {
            alert('Error applying cleaning');
        } finally {
            applyCleanBtn.disabled = false;
            applyCleanBtn.innerHTML = 'Apply Cleaning';
        }
    };
});
