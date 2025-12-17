// ========= GLOBAL CHART STYLE & CONFIG =========
Chart.defaults.font.family = "'Poppins', 'Inter', sans-serif";
Chart.defaults.color = "#666";
Chart.defaults.animation = {
    duration: 1000,
    easing: "easeOutQuart"
};

// Color Palette (Professional Gradients)
const colors = {
    primary: "#1e3a5f",
    secondary: "#00bcd4",
    accent: "#64b5f6",
    success: "#4caf50",
    warning: "#ff9800",
    error: "#f44336",
    neutral: "#e0e4e8"
};

// Diagnosis label mapping
const diagnosisMap = {
    "0": "No Dementia",
    "1": "Dementia"
};

async function fetchJson(url) {
    const r = await fetch(url);
    if (!r.ok) throw new Error(`Fetch failed: ${url}`);
    return await r.json();
}

function gradient(ctx, c1, c2) {
    const g = ctx.createLinearGradient(0, 0, 0, 300);
    g.addColorStop(0, c1);
    g.addColorStop(1, c2);
    return g;
}

function horizontalGradient(ctx, c1, c2) {
    const g = ctx.createLinearGradient(0, 0, 400, 0);
    g.addColorStop(0, c1);
    g.addColorStop(1, c2);
    return g;
}

function elegantBar(ctx, labels, data, label, c1, c2) {
    return new Chart(ctx, {
        type: "bar",
        data: {
            labels: labels,
            datasets: [{
                label: label,
                data: data,
                backgroundColor: (e) => gradient(e.chart.ctx, c1, c2),
                borderRadius: 12,
                borderSkipped: false,
                borderWidth: 0,
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: { 
                legend: { display: false },
                tooltip: {
                    backgroundColor: colors.primary,
                    padding: 12,
                    titleFont: { size: 14, weight: 600 },
                    bodyFont: { size: 13 },
                    borderColor: colors.secondary,
                    borderWidth: 1
                }
            },
            scales: {
                x: { 
                    grid: { display: false },
                    ticks: { font: { size: 12, weight: 500 } }
                },
                y: { 
                    grid: { color: "rgba(0,0,0,0.05)", drawBorder: false },
                    ticks: { font: { size: 12 } }
                }
            }
        }
    });
}

function elegantRadar(ctx, labels, datasets) {
    // Assign colors to datasets
    const dsColors = [
        { border: colors.secondary, bg: "rgba(0, 188, 212, 0.1)" },
        { border: colors.primary, bg: "rgba(30, 58, 95, 0.1)" }
    ];

    datasets.forEach((ds, i) => {
        ds.borderColor = dsColors[i]?.border || colors.accent;
        ds.backgroundColor = dsColors[i]?.bg || "rgba(100, 181, 246, 0.1)";
        ds.borderWidth = 2;
        ds.pointBackgroundColor = dsColors[i]?.border || colors.accent;
        ds.pointBorderColor = "#fff";
        ds.pointBorderWidth = 2;
        ds.pointRadius = 5;
        ds.pointHoverRadius = 7;
    });

    return new Chart(ctx, {
        type: "radar",
        data: { labels, datasets },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: true,
                    position: "bottom",
                    labels: { font: { size: 12, weight: 500 }, padding: 15 }
                },
                tooltip: {
                    backgroundColor: colors.primary,
                    padding: 12,
                    titleFont: { size: 13, weight: 600 },
                    bodyFont: { size: 12 },
                    borderColor: colors.secondary,
                    borderWidth: 1
                }
            },
            scales: {
                r: {
                    beginAtZero: true,
                    grid: { color: "rgba(0,0,0,0.08)" },
                    ticks: { font: { size: 11 } }
                }
            }
        }
    });
}

// ============ MAIN LOADER ============

document.addEventListener("DOMContentLoaded", () => {
    // helper to show a top-level error message
    function showDashboardError(msg) {
        const el = document.getElementById('dashboardError');
        if (!el) return console.error('dashboardError element missing:', msg);
        el.style.display = 'block';
        el.textContent = msg;
    }

    (async function loadAll() {
        try {
            // ---- SUMMARY ----
            const summary = await fetchJson("http://10.16.127.86:5000/api/summary");
            const s = document.getElementById("summary-cards");
            s.innerHTML = `
                <div class="summ-card">
                    <div>👥</div>
                    <div>${summary.total}</div>
                    <span>Total Patients</span>
                </div>
                <div class="summ-card">
                    <div>🏥</div>
                    <div>${summary.percent_alzheimer}%</div>
                    <span>Alzheimer %</span>
                </div>
                <div class="summ-card">
                    <div>📅</div>
                    <div>${summary.mean_age}</div>
                    <span>Mean Age</span>
                </div>
                <div class="summ-card">
                    <div>⚖️</div>
                    <div style="font-size: 1.2rem;">
                        <div class="gender-row male">M: ${summary.gender_male}%</div>
                        <div class="gender-row female">F: ${summary.gender_female}%</div>
                    </div>
                    <span>Gender Ratio</span>
                </div>
            `;

            // ---- DIAGNOSIS COUNT ----
            const diag = await fetchJson("http://10.16.127.86:5000/api/diagnosis_counts");
            elegantBar(
                document.getElementById("diagnosisChart").getContext("2d"),
                diag.labels,
                diag.values,
                "Diagnosis Distribution",
                "#4CC9F0", "#4895EF"
            );

            // ---- AGE ----
            const age = await fetchJson("http://10.16.127.86:5000/api/age_distribution");
            elegantBar(
                document.getElementById("ageChart").getContext("2d"),
                age.labels,
                age.counts,
                "Age Distribution",
                "#80ED99", "#38A3A5"
            );

            // ---- BMI ----
            const bmi = await fetchJson("http://10.16.127.86:5000/api/bmi_stats");
            const bmiLabels = Object.keys(bmi).map(k => diagnosisMap[k] || k);
            const bmiMeans = Object.keys(bmi).map(k => bmi[k].mean);

            elegantBar(
                document.getElementById("bmiChart").getContext("2d"),
                bmiLabels,
                bmiMeans,
                "Mean BMI",
                "#FFB703", "#FB8500"
            );

            // ---- EDUCATION ----
            const edu = await fetchJson("http://10.16.127.86:5000/api/education_vs_diagnosis");
            new Chart(document.getElementById("eduChart"), {
                type: "bar",
                data: {
                    labels: edu.labels,
                    datasets: [
                        { label: "No Dementia", data: edu.no_dementia, backgroundColor: "#4CC9F0" },
                        { label: "Dementia", data: edu.dementia, backgroundColor: "#F72585" }
                    ]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    scales: { x: { stacked: true }, y: { stacked: true } }
                }
            });

            // ---- SMOKING ----
            try {
                const smoke = await fetchJson("http://10.16.127.86:5000/api/smoking_by_diag");
                const smokeLabels = Object.keys(smoke).map(k => diagnosisMap[k] || k);
                const smokeValues = Object.keys(smoke).map(k => smoke[k]);
                elegantBar(
                    document.getElementById("smokeChart").getContext("2d"),
                    smokeLabels,
                    smokeValues,
                    "Smoking (mean)",
                    "#72EFDD", "#56CFE1"
                );
            } catch (e) {
                console.warn('smoking_by_diag failed', e);
            }

            // ---- ALCOHOL ----
            try {
                const alc = await fetchJson("http://localhost:5000/api/alcohol_stats");
                const alcLabels = Object.keys(alc).map(k => diagnosisMap[k] || k);
                const alcMeds = Object.keys(alc).map(k => alc[k].median);
                elegantBar(
                    document.getElementById("alcoholChart").getContext("2d"),
                    alcLabels,
                    alcMeds,
                    "Alcohol (median)",
                    "#FFAFCC", "#FF8FA3"
                );
            } catch (e) {
                console.warn('alcohol_stats failed', e);
            }

            // ---- ACTIVITY ----
            try {
                const act = await fetchJson("http://localhost:5000/api/activity_by_diag");
                const actLabels = Object.keys(act).map(k => diagnosisMap[k] || k);
                const actValues = Object.keys(act).map(k => act[k]);
                elegantBar(
                    document.getElementById("activityChart").getContext("2d"),
                    actLabels,
                    actValues,
                    "Physical Activity",
                    "#B5E48C", "#76C893"
                );
            } catch (e) {
                console.warn('activity_by_diag failed', e);
            }

            // ---- COGNITIVE ----
            const cognitive = await fetchJson("http://10.16.127.86:5000/api/cognitive_stats");
            const mmseLabels = Object.keys(cognitive).map(k => diagnosisMap[k] || k);
            const mmseMeans = Object.keys(cognitive).map(k => cognitive[k]["MMSE"].mean);

            elegantBar(
                document.getElementById("mmseChart").getContext("2d"),
                mmseLabels,
                mmseMeans,
                "MMSE Mean",
                "#3A86FF", "#8338EC"
            );

            // ---- RADAR ----
            const radar = await fetchJson("http://10.16.127.86:5000/api/radar_data");
            elegantRadar(
                document.getElementById("radarChart").getContext("2d"),
                radar.labels,
                radar.datasets
            );

            // ---- CORRELATION (Top 5 by absolute value) ----
            const corr = await fetchJson("http://10.16.127.86:5000/correlation_diagnosis");

            // gabungkan fitur + nilai
            let pairs = corr.features.map((f, i) => ({
                feature: f,
                value: corr.values[i]
            }));

            // sort by absolute correlation (descending)
            pairs.sort((a, b) => Math.abs(b.value) - Math.abs(a.value));

            // ambil top 5
            const top5 = pairs.slice(0, 5);

            let html = `
            <table class="corr">
                <tr><th>Feature</th><th>Correlation</th></tr>
            `;

            top5.forEach(p => {
                const v = p.value;
                const color = v > 0 
                    ? `rgba(255, 99, 132, ${Math.abs(v)})`      // merah jika positif
                    : `rgba(54, 162, 235, ${Math.abs(v)})`;     // biru jika negatif

                html += `
                    <tr>
                        <td>${p.feature}</td>
                        <td style="background:${color}; color:white; font-weight:600;">
                            ${v}
                        </td>
                    </tr>
                `;
            });

            html += "</table>";

            document.getElementById("corrTable").innerHTML = html;

        } catch (err) {
            console.error('Dashboard load failed', err);
            showDashboardError('Failed to load dashboard data — check backend is running and open DevTools → Network for details.');
        }
    })();

});
