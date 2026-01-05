window.renderCompanyCharts = function (rawData) {
    if (!Array.isArray(rawData) || rawData.length === 0) return;

    function buildSeries(key) {
        const labels = [];
        const values = [];

        for (const year of rawData) {
            const fy = year.fiscal_year || {};
            const end = (fy.end || "").slice(0, 4);
            if (!end) continue;

            let v = year[key];
            if (v == null) continue;

            if (key === "equity_ratio") v = v * 100;
            labels.push(end);
            values.push(v);
        }
        return { labels, values };
    }

    // Format number with space as thousands separator and comma as decimal separator
    function formatNumber(value) {
        if (!isFinite(value)) return "0";
        const abs = Math.abs(value);
        const parts = abs.toFixed(2).split(".");
        const integerPart = parts[0].replace(/\B(?=(\d{3})+(?!\d))/g, " ");
        return integerPart + "," + parts[1];
    }

    function formatDiff(diff) {
        if (!isFinite(diff)) return "0";
        const sign = diff > 0 ? "+" : diff < 0 ? "−" : "";
        return sign + formatNumber(Math.abs(diff));
    }


    const ChangeLabelPlugin = {
        id: "changeLabelPlugin",
        afterDatasetsDraw(chart) {
            const { ctx } = chart;
            const meta = chart.getDatasetMeta(0);
            const data = chart.data.datasets[0].data;

            if (!meta.data || meta.data.length < 2) return;

            ctx.save();
            ctx.font = "11px Montserrat, sans-serif";
            ctx.textAlign = "center";
            ctx.textBaseline = "bottom";

            for (let i = 1; i < meta.data.length; i++) {
                const point = meta.data[i];
                const diff = data[i] - data[i - 1];
                const text = formatDiff(diff);

                let color = "#fbc02d";
                if (diff > 0) color = "#43a047";
                else if (diff < 0) color = "#e53935";

                ctx.fillStyle = color;
                ctx.fillText(text, point.x, point.y - 6);
            }
            ctx.restore();
        }
    };

    function makeLineChart(id, series) {
        const canvas = document.getElementById(id);
        if (!canvas || series.labels.length === 0) return;

        new Chart(canvas, {
            type: "line",
            data: {
                labels: series.labels,
                datasets: [{
                    data: series.values,
                    tension: 0.2,
                    pointRadius: 3,
                    pointBackgroundColor: "#1976d2",
                    borderWidth: 2,
                    fill: false,
                    segment: {
                        borderColor: (ctx) => {
                            const v0 = ctx.p0.parsed.y;
                            const v1 = ctx.p1.parsed.y;
                            if (v1 > v0) return "#43a047";
                            if (v1 < v0) return "#e53935";
                            return "#fbc02d";
                        }
                    }
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: { legend: { display: false } },
                scales: {
                    x: { ticks: { autoSkip: false } },
                    y: {
                        beginAtZero: false,
                        ticks: {
                            callback: function(value) {
                                return formatNumber(value);
                            }
                        }
                    }
                }
            },
            plugins: [ChangeLabelPlugin]
        });
    }

    // Build + Draw
    makeLineChart("chartTotalAssets", buildSeries("total_assets"));
    makeLineChart("chartEquity", buildSeries("equity"));
    makeLineChart("chartEquityRatio", buildSeries("equity_ratio"));
    makeLineChart("chartCurrentRatio", buildSeries("current_ratio"));
};