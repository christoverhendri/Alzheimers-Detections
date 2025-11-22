// ========= GLOBAL CHART STYLE =========
Chart.defaults.font.family = "'Inter', sans-serif";
Chart.defaults.color = "#444";
Chart.defaults.animation = {
    duration: 1200,
    easing: "easeOutQuart"
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
                borderWidth: 0,
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: { legend: { display: false } },
            scales: {
                x: { grid: { display: false } },
                y: { grid: { color: "#eee" } }
            }
        }
    });
}

function elegantRadar(ctx, labels, datasets) {
    return new Chart(ctx, {
        type: "radar",
        data: { labels, datasets },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                r: {
                    beginAtZero: true,
                    grid: { color: "#ddd" }
                }
            }
        }
    });
}

// ============ MAIN LOADER ============

document.addEventListener("DOMContentLoaded", async () => {

    // ---- SUMMARY ----
    const summary = await fetchJson("/api/summary");
    const s = document.getElementById("summary-cards");
    s.innerHTML = `
        <div class="summ-card"><div>${summary.total}</div><span>Total Patients</span></div>
        <div class="summ-card"><div>${summary.percent_alzheimer}%</div><span>Alzheimer %</span></div>
        <div class="summ-card"><div>${summary.mean_age}</div><span>Mean Age</span></div>
        <div class="summ-card gender-card">
            <div>
                <div class="gender-row male">Male: ${summary.gender_male}%</div>
                <div class="gender-row female">Female: ${summary.gender_female}%</div>
            </div>
            <span>Gender Ratio</span>
        </div>

    `;

    // ---- DIAGNOSIS COUNT ----
    const diag = await fetchJson("/api/diagnosis_counts");
    elegantBar(
        document.getElementById("diagnosisChart").getContext("2d"),
        diag.labels,
        diag.values,
        "Diagnosis Count",
        "#4CC9F0", "#4895EF"
    );

    // ---- AGE ----
    const age = await fetchJson("/api/age_distribution");
    elegantBar(
        document.getElementById("ageChart").getContext("2d"),
        age.labels,
        age.counts,
        "Age Distribution",
        "#80ED99", "#38A3A5"
    );

    // ---- BMI ----
    const bmi = await fetchJson("/api/bmi_stats");
    const bmiLabels = Object.keys(bmi);
    const bmiMeans = bmiLabels.map(k => bmi[k].mean);

    elegantBar(
        document.getElementById("bmiChart").getContext("2d"),
        bmiLabels,
        bmiMeans,
        "Mean BMI",
        "#FFB703", "#FB8500"
    );

    // ---- EDUCATION ----
    const edu = await fetchJson("/api/education_vs_diagnosis");
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
    const smoke = await fetchJson("/api/smoking_by_diag");
    elegantBar(
        document.getElementById("smokeChart").getContext("2d"),
        Object.keys(smoke),
        Object.values(smoke),
        "Smoking (mean)",
        "#72EFDD", "#56CFE1"
    );

    // ---- ALCOHOL ----
    const alc = await fetchJson("/api/alcohol_stats");
    const alcLabels = Object.keys(alc);
    const alcMeds = alcLabels.map(k => alc[k].median);

    elegantBar(
        document.getElementById("alcoholChart").getContext("2d"),
        alcLabels,
        alcMeds,
        "Alcohol (median)",
        "#FFAFCC", "#FF8FA3"
    );

    // ---- ACTIVITY ----
    const act = await fetchJson("/api/activity_by_diag");
    elegantBar(
        document.getElementById("activityChart").getContext("2d"),
        Object.keys(act),
        Object.values(act),
        "Physical Activity",
        "#B5E48C", "#76C893"
    );  

    // ---- COGNITIVE ----
    const cognitive = await fetchJson("/api/cognitive_stats");
    const mmseLabels = Object.keys(cognitive);
    const mmseMeans = mmseLabels.map(k => cognitive[k]["MMSE"].mean);

    elegantBar(
        document.getElementById("mmseChart").getContext("2d"),
        mmseLabels,
        mmseMeans,
        "MMSE Mean",
        "#3A86FF", "#8338EC"
    );

    // ---- RADAR ----
    const radar = await fetchJson("/api/radar_data");
    elegantRadar(
        document.getElementById("radarChart").getContext("2d"),
        radar.labels,
        radar.datasets
    );

    // ---- CORRELATION (Top 5 by absolute value) ----
    const corr = await fetchJson("/api/correlation_diagnosis");

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


});
