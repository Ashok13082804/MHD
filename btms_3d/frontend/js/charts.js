/**
 * Real-Time Telemetry & Charting Module
 * Uses Chart.js to render 5 interactive engineering telemetry charts:
 * 1. Temp vs Time (Max, Min, Avg, Threshold)
 * 2. 50-Cell Distribution (B01-B50 color-coded bars)
 * 3. Coolant Inlet vs Outlet Temperature
 * 4. Heat Generation vs Removal (Watts)
 * 5. Hydraulic Pressure Drop & Nusselt Number
 */

class TelemetryChartsManager {
  constructor() {
    this.canvas = document.getElementById("liveChartCanvas");
    this.activeTab = "tempTime";
    this.chart = null;
    this.maxHistoryLength = 60;

    // Time-series data buffers
    this.history = {
      time: [],
      tMax: [],
      tMin: [],
      tAvg: [],
      threshold: [],
      tInlet: [],
      tOutlet: [],
      qGen: [],
      qCool: [],
      deltaP: [],
      nusselt: []
    };

    this.latestCells = [];

    this.bindTabEvents();
    this.initChart();
  }

  bindTabEvents() {
    const tabBtns = document.querySelectorAll(".chart-tab-btn");
    tabBtns.forEach(btn => {
      btn.addEventListener("click", () => {
        tabBtns.forEach(b => b.classList.remove("active"));
        btn.classList.add("active");
        this.activeTab = btn.getAttribute("data-chart");
        this.initChart();
      });
    });

    const toggleBtn = document.getElementById("btnToggleDrawer");
    const drawer = document.getElementById("bottomDrawer");
    if (toggleBtn && drawer) {
      toggleBtn.addEventListener("click", () => {
        drawer.classList.toggle("collapsed");
        toggleBtn.textContent = drawer.classList.contains("collapsed") ? "▼" : "▲";
      });
    }
  }

  initChart() {
    if (!this.canvas) return;
    if (this.chart) {
      this.chart.destroy();
      this.chart = null;
    }

    const ctx = this.canvas.getContext("2d");

    // Common styling
    const gridColor = "rgba(255, 255, 255, 0.08)";
    const textColor = "#a0aec0";

    if (this.activeTab === "tempTime") {
      this.chart = new Chart(ctx, {
        type: "line",
        data: {
          labels: this.history.time,
          datasets: [
            {
              label: "Max Cell Temp (°C)",
              data: this.history.tMax,
              borderColor: "#ff3366",
              backgroundColor: "rgba(255, 51, 102, 0.15)",
              borderWidth: 2,
              tension: 0.3,
              fill: false
            },
            {
              label: "Avg Cell Temp (°C)",
              data: this.history.tAvg,
              borderColor: "#00f0ff",
              backgroundColor: "rgba(0, 240, 255, 0.1)",
              borderWidth: 2,
              tension: 0.3,
              fill: false
            },
            {
              label: "Min Cell Temp (°C)",
              data: this.history.tMin,
              borderColor: "#00ff88",
              backgroundColor: "transparent",
              borderWidth: 1.5,
              tension: 0.3,
              fill: false
            },
            {
              label: "Threshold Limit (°C)",
              data: this.history.threshold,
              borderColor: "#ffaa00",
              borderDash: [5, 5],
              borderWidth: 1.5,
              pointRadius: 0,
              fill: false
            }
          ]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          animation: false,
          scales: {
            x: {
              grid: { color: gridColor },
              ticks: { color: textColor, maxTicksLimit: 10 }
            },
            y: {
              grid: { color: gridColor },
              ticks: { color: textColor },
              title: { display: true, text: "Temperature (°C)", color: textColor }
            }
          },
          plugins: {
            legend: { labels: { color: "#ffffff", boxWidth: 14 } }
          }
        }
      });

    } else if (this.activeTab === "packDist") {
      const labels = this.latestCells.length > 0
        ? this.latestCells.map(c => c.cell_id)
        : Array.from({ length: 50 }, (_, i) => `B${String(i + 1).padStart(2, "0")}`);
      const data = this.latestCells.map(c => c.temperature_c);
      const bgColors = this.latestCells.map(c => {
        const t = c.temperature_c;
        if (t >= 35.0) return "#ff3366";
        if (t >= 30.0) return "#ffaa00";
        if (t >= 25.0) return "#00ff88";
        return "#00a8ff";
      });

      this.chart = new Chart(ctx, {
        type: "bar",
        data: {
          labels: labels,
          datasets: [{
            label: "Battery Cell Temperature (°C)",
            data: data,
            backgroundColor: bgColors.length > 0 ? bgColors : "#00f0ff",
            borderRadius: 2
          }]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          animation: false,
          scales: {
            x: {
              grid: { display: false },
              ticks: { color: textColor, maxRotation: 90, minRotation: 90, font: { size: 9 } }
            },
            y: {
              grid: { color: gridColor },
              ticks: { color: textColor },
              title: { display: true, text: "Cell Temperature (°C)", color: textColor },
              min: 20
            }
          },
          plugins: {
            legend: { display: false }
          }
        }
      });

    } else if (this.activeTab === "inOutTemp") {
      this.chart = new Chart(ctx, {
        type: "line",
        data: {
          labels: this.history.time,
          datasets: [
            {
              label: "Inlet Coolant Temp (°C)",
              data: this.history.tInlet,
              borderColor: "#00a8ff",
              backgroundColor: "rgba(0, 168, 255, 0.1)",
              borderWidth: 2,
              tension: 0.2
            },
            {
              label: "Outlet Coolant Temp (°C)",
              data: this.history.tOutlet,
              borderColor: "#ff3366",
              backgroundColor: "rgba(255, 51, 102, 0.1)",
              borderWidth: 2,
              tension: 0.2
            }
          ]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          animation: false,
          scales: {
            x: { grid: { color: gridColor }, ticks: { color: textColor, maxTicksLimit: 10 } },
            y: { grid: { color: gridColor }, ticks: { color: textColor }, title: { display: true, text: "Temperature (°C)", color: textColor } }
          },
          plugins: {
            legend: { labels: { color: "#ffffff", boxWidth: 14 } }
          }
        }
      });

    } else if (this.activeTab === "heatBalance") {
      this.chart = new Chart(ctx, {
        type: "line",
        data: {
          labels: this.history.time,
          datasets: [
            {
              label: "Total Heat Generation (W)",
              data: this.history.qGen,
              borderColor: "#ffaa00",
              backgroundColor: "rgba(255, 170, 0, 0.15)",
              borderWidth: 2,
              fill: true,
              tension: 0.3
            },
            {
              label: "Total Heat Removed (W)",
              data: this.history.qCool,
              borderColor: "#00ff88",
              backgroundColor: "rgba(0, 255, 136, 0.15)",
              borderWidth: 2,
              fill: true,
              tension: 0.3
            }
          ]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          animation: false,
          scales: {
            x: { grid: { color: gridColor }, ticks: { color: textColor, maxTicksLimit: 10 } },
            y: { grid: { color: gridColor }, ticks: { color: textColor }, title: { display: true, text: "Thermal Power (Watts)", color: textColor } }
          },
          plugins: {
            legend: { labels: { color: "#ffffff", boxWidth: 14 } }
          }
        }
      });

    } else if (this.activeTab === "hydraulic") {
      this.chart = new Chart(ctx, {
        type: "line",
        data: {
          labels: this.history.time,
          datasets: [
            {
              label: "Pressure Drop ΔP (Pa)",
              data: this.history.deltaP,
              borderColor: "#ff0077",
              yAxisID: "yP",
              borderWidth: 2,
              tension: 0.2
            },
            {
              label: "Nusselt Number Nu",
              data: this.history.nusselt,
              borderColor: "#00f0ff",
              yAxisID: "yNu",
              borderWidth: 2,
              tension: 0.2
            }
          ]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          animation: false,
          scales: {
            x: { grid: { color: gridColor }, ticks: { color: textColor, maxTicksLimit: 10 } },
            yP: {
              type: "linear",
              position: "left",
              grid: { color: gridColor },
              ticks: { color: "#ff0077" },
              title: { display: true, text: "ΔP (Pa)", color: "#ff0077" }
            },
            yNu: {
              type: "linear",
              position: "right",
              grid: { drawOnChartArea: false },
              ticks: { color: "#00f0ff" },
              title: { display: true, text: "Nusselt Number (Nu)", color: "#00f0ff" }
            }
          },
          plugins: {
            legend: { labels: { color: "#ffffff", boxWidth: 14 } }
          }
        }
      });
    }
  }

  update(simState) {
    if (!simState) return;

    const timeLabel = `${(simState.time_seconds || 0).toFixed(1)}s`;
    const pack = simState.pack_stats || {};
    const hydro = simState.hydrodynamics || {};
    const htr = simState.heat_transfer || {};
    const ctrl = simState.cooling_controller || {};

    this.latestCells = simState.cells || [];

    // Append to histories
    this.history.time.push(timeLabel);
    this.history.tMax.push(pack.t_max_c || 25.0);
    this.history.tMin.push(pack.t_min_c || 25.0);
    this.history.tAvg.push(pack.t_avg_c || 25.0);
    this.history.threshold.push(ctrl.threshold_c || 35.0);

    const p01 = (simState.measurement_points && simState.measurement_points["P01"]) || {};
    const p06 = (simState.measurement_points && simState.measurement_points["P06"]) || {};
    this.history.tInlet.push(p01.temp_c || 25.0);
    this.history.tOutlet.push(p06.temp_c || 25.0);

    this.history.qGen.push(pack.total_heat_generated_w || 0.0);
    this.history.qCool.push(pack.total_heat_removed_w || 0.0);

    this.history.deltaP.push(hydro.pressure_drop_pa || 0.0);
    this.history.nusselt.push(htr.nusselt_number || 4.36);

    // Limit buffer length
    if (this.history.time.length > this.maxHistoryLength) {
      Object.keys(this.history).forEach(k => {
        this.history[k].shift();
      });
    }

    // Refresh active chart
    if (this.chart) {
      if (this.activeTab === "packDist") {
        this.chart.data.labels = this.latestCells.map(c => c.cell_id);
        this.chart.data.datasets[0].data = this.latestCells.map(c => c.temperature_c);
        this.chart.data.datasets[0].backgroundColor = this.latestCells.map(c => {
          const t = c.temperature_c;
          if (t >= (ctrl.threshold_c || 35.0)) return "#ff3366";
          if (t >= 30.0) return "#ffaa00";
          if (t >= 25.0) return "#00ff88";
          return "#00a8ff";
        });
      }
      this.chart.update("none");
    }
  }

  reset() {
    Object.keys(this.history).forEach(k => {
      this.history[k] = [];
    });
    this.initChart();
  }
}

window.TelemetryChartsManager = TelemetryChartsManager;
