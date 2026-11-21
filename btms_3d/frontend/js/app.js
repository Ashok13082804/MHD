/**
 * Master Application Controller for 3D BTMS Simulation
 * Connects WebGL Three.js rendering, nanoparticle circulation,
 * camera controls, inspection HUD, telemetry, and Flask REST API.
 */

class BTMSApplication {
  constructor() {
    this.container = document.getElementById("canvas-container");
    this.latestState = null;
    this.clock = new THREE.Clock();
    this.raycaster = new THREE.Raycaster();
    this.mouse = new THREE.Vector2();
    this.selectedObject = null;

    this.initThree();
    this.initSceneBuilder();
    this.initNanoparticles();
    this.initEventListeners();
    this.initUIControls();

    // Start simulation polling and render loop
    this.pollStatus();
    this.startSimulationLoop();
    this.animate();
  }

  initThree() {
    this.scene = new THREE.Scene();
    this.scene.background = new THREE.Color(0x0a0e17);

    this.camera = new THREE.PerspectiveCamera(
      45,
      window.innerWidth / window.innerHeight,
      0.05,
      50
    );
    this.camera.position.set(1.4, 1.2, 1.4);

    this.renderer = new THREE.WebGLRenderer({ antialias: true, powerPreference: "high-performance" });
    this.renderer.setSize(window.innerWidth, window.innerHeight);
    this.renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    this.renderer.shadowMap.enabled = true;
    this.container.appendChild(this.renderer.domElement);

    if (window.THREE && THREE.OrbitControls) {
      this.controls = new THREE.OrbitControls(this.camera, this.renderer.domElement);
      this.controls.enableDamping = true;
      this.controls.dampingFactor = 0.08;
      this.controls.target.set(0, 0.1, 0);
      this.controls.maxPolarAngle = Math.PI / 2 + 0.1;
      this.controls.minDistance = 0.4;
      this.controls.maxDistance = 5.0;
    }
  }

  initSceneBuilder() {
    this.sceneBuilder = new BTMS3DSceneBuilder(this.scene);
  }

  initNanoparticles() {
    this.nanoparticles = new NanoparticleCirculationEngine(
      this.scene,
      this.sceneBuilder.pipelinePoints
    );
  }

  initEventListeners() {
    window.addEventListener("resize", () => this.onWindowResize());

    // 3D Raycasting for component inspection
    this.container.addEventListener("pointerdown", (e) => {
      this.pointerDownTime = performance.now();
    });

    this.container.addEventListener("pointerup", (e) => {
      // Differentiate between drag (rotate/pan) and click
      if (performance.now() - this.pointerDownTime > 250) return;

      const rect = this.renderer.domElement.getBoundingClientRect();
      this.mouse.x = ((e.clientX - rect.left) / rect.width) * 2 - 1;
      this.mouse.y = -((e.clientY - rect.top) / rect.height) * 2 + 1;

      this.raycaster.setFromCamera(this.mouse, this.camera);
      const intersects = this.raycaster.intersectObjects(this.sceneBuilder.clickableObjects, true);

      if (intersects.length > 0) {
        let hitObj = intersects[0].object;
        while (hitObj.parent && !hitObj.userData.component_id && hitObj.parent !== this.scene) {
          hitObj = hitObj.parent;
        }
        if (hitObj.userData.component_id) {
          this.inspectComponent(hitObj.userData.component_id);
        }
      }
    });
  }

  initUIControls() {
    // Camera View Buttons
    document.getElementById("btn-view-iso")?.addEventListener("click", () => this.setCameraView("iso"));
    document.getElementById("btn-view-top")?.addEventListener("click", () => this.setCameraView("top"));
    document.getElementById("btn-view-front")?.addEventListener("click", () => this.setCameraView("front"));
    document.getElementById("btn-view-side")?.addEventListener("click", () => this.setCameraView("side"));
    document.getElementById("btn-view-reset")?.addEventListener("click", () => this.setCameraView("iso"));

    // Exploded View & Casing
    document.getElementById("btn-exploded")?.addEventListener("click", () => {
      this.sceneBuilder.toggleExplodedView();
      document.getElementById("btn-exploded").classList.toggle("active");
    });
    document.getElementById("btn-casing")?.addEventListener("click", () => {
      this.sceneBuilder.toggleTransparentCasing();
      document.getElementById("btn-casing").classList.toggle("active");
    });

    // Control Sliders
    const thresholdSlider = document.getElementById("slider-threshold");
    thresholdSlider?.addEventListener("input", (e) => {
      const val = parseFloat(e.target.value);
      document.getElementById("val-threshold").innerText = val.toFixed(1) + " °C";
      this.sendControlUpdate({ threshold_c: val });
    });

    const crateSlider = document.getElementById("slider-crate");
    crateSlider?.addEventListener("input", (e) => {
      const val = parseFloat(e.target.value);
      document.getElementById("val-crate").innerText = val.toFixed(1) + " C";
      this.sendControlUpdate({ c_rate: val });
    });

    const velocitySlider = document.getElementById("slider-velocity");
    velocitySlider?.addEventListener("input", (e) => {
      const val = parseFloat(e.target.value);
      document.getElementById("val-velocity").innerText = val.toFixed(3) + " m/s";
      this.sendControlUpdate({ inlet_velocity: val });
    });

    const b0Slider = document.getElementById("slider-b0");
    b0Slider?.addEventListener("input", (e) => {
      const val = parseFloat(e.target.value);
      document.getElementById("val-b0").innerText = val.toFixed(2) + " T";
      this.sendControlUpdate({ B0: val });
    });

    const phi1Slider = document.getElementById("slider-phi1");
    phi1Slider?.addEventListener("input", (e) => {
      const val = parseFloat(e.target.value);
      document.getElementById("val-phi1").innerText = (val * 100).toFixed(1) + " %";
      this.sendControlUpdate({ phi1: val });
    });

    const phi2Slider = document.getElementById("slider-phi2");
    phi2Slider?.addEventListener("input", (e) => {
      const val = parseFloat(e.target.value);
      document.getElementById("val-phi2").innerText = (val * 100).toFixed(1) + " %";
      this.sendControlUpdate({ phi2: val });
    });

    // Mode Buttons
    document.querySelectorAll(".btn-mode").forEach(btn => {
      btn.addEventListener("click", () => {
        document.querySelectorAll(".btn-mode").forEach(b => b.classList.remove("active"));
        btn.classList.add("active");
        const mode = btn.dataset.mode;
        this.sendControlUpdate({ mode: mode });
      });
    });

    // Simulation Action Buttons
    document.getElementById("btn-play-pause")?.addEventListener("click", () => {
      const isRunning = (document.getElementById("btn-play-pause").innerText.includes("PAUSE"));
      this.sendControlUpdate({ is_running: !isRunning });
      document.getElementById("btn-play-pause").innerText = isRunning ? "▶ RESUME" : "⏸ PAUSE";
    });

    document.getElementById("btn-reset")?.addEventListener("click", () => {
      fetch("/api/reset", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ initial_temp_c: 25.0 }) })
        .then(res => res.json())
        .then(() => this.pollStatus());
    });

    document.getElementById("btn-export-csv")?.addEventListener("click", () => {
      window.location.href = "/api/export";
    });

    // Modals
    document.getElementById("btn-open-equations")?.addEventListener("click", () => this.openEquationsModal());
    document.getElementById("btn-close-equations")?.addEventListener("click", () => {
      document.getElementById("equations-modal").classList.remove("show");
    });

    document.getElementById("btn-open-dataset")?.addEventListener("click", () => {
      document.getElementById("dataset-modal").classList.add("show");
    });
    document.getElementById("btn-close-dataset")?.addEventListener("click", () => {
      document.getElementById("dataset-modal").classList.remove("show");
    });

    document.getElementById("btn-close-inspect")?.addEventListener("click", () => {
      document.getElementById("inspection-modal").classList.remove("show");
    });

    // File Drop Zone
    this.initFileDropZone();
  }

  initFileDropZone() {
    const dropZone = document.getElementById("drop-zone");
    const fileInput = document.getElementById("dataset-file-input");

    dropZone?.addEventListener("click", () => fileInput?.click());

    fileInput?.addEventListener("change", (e) => {
      if (e.target.files && e.target.files[0]) {
        this.uploadDatasetFile(e.target.files[0]);
      }
    });

    dropZone?.addEventListener("dragover", (e) => {
      e.preventDefault();
      dropZone.classList.add("dragover");
    });

    dropZone?.addEventListener("dragleave", () => dropZone.classList.remove("dragover"));

    dropZone?.addEventListener("drop", (e) => {
      e.preventDefault();
      dropZone.classList.remove("dragover");
      if (e.dataTransfer.files && e.dataTransfer.files[0]) {
        this.uploadDatasetFile(e.dataTransfer.files[0]);
      }
    });
  }

  uploadDatasetFile(file) {
    const formData = new FormData();
    formData.append("file", file);

    const statusEl = document.getElementById("dataset-status");
    if (statusEl) statusEl.innerText = `Uploading and validating '${file.name}'...`;

    fetch("/api/dataset/upload", { method: "POST", body: formData })
      .then(res => res.json())
      .then(report => {
        if (!report.success) {
          if (statusEl) statusEl.innerText = `Validation Error: ${report.error}`;
          return;
        }

        if (statusEl) {
          statusEl.innerText = `Validated: ${report.valid_records_count} valid records out of ${report.total_records}.`;
        }

        // Render preview table
        this.renderDatasetPreview(report.preview, report.records);
      })
      .catch(err => {
        if (statusEl) statusEl.innerText = `Upload Error: ${err.message}`;
      });
  }

  renderDatasetPreview(preview, fullRecords) {
    const container = document.getElementById("dataset-table-container");
    if (!container || !preview || preview.length === 0) return;

    const cols = Object.keys(preview[0]);
    let html = `<table class="dataset-table"><thead><tr>`;
    cols.forEach(c => html += `<th>${c}</th>`);
    html += `<th>Action</th></tr></thead><tbody>`;

    preview.forEach((row, idx) => {
      html += `<tr>`;
      cols.forEach(c => html += `<td>${row[c]}</td>`);
      html += `<td><button class="btn-action primary" style="padding:4px 8px;font-size:9px;" onclick="window.btmsApp.applyRecord(${idx})">Apply</button></td></tr>`;
    });
    html += `</tbody></table>`;
    container.innerHTML = html;
    this.currentRecords = fullRecords;
  }

  applyRecord(idx) {
    if (!this.currentRecords || !this.currentRecords[idx]) return;
    const record = this.currentRecords[idx];

    fetch("/api/dataset/apply_record", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ record: record })
    })
      .then(res => res.json())
      .then(data => {
        document.getElementById("dataset-modal")?.classList.remove("show");
        this.pollStatus();
      });
  }

  setCameraView(viewName) {
    if (!this.controls) return;
    switch (viewName) {
      case "top":
        this.camera.position.set(0, 2.4, 0.001);
        break;
      case "front":
        this.camera.position.set(0, 0.4, 2.0);
        break;
      case "side":
        this.camera.position.set(2.0, 0.4, 0);
        break;
      case "iso":
      default:
        this.camera.position.set(1.4, 1.2, 1.4);
        break;
    }
    this.controls.target.set(0, 0.1, 0);
    this.controls.update();
  }

  inspectComponent(componentId) {
    fetch(`/api/inspect/${componentId}`)
      .then(res => res.json())
      .then(data => {
        if (!data.success) return;
        this.displayInspectionModal(data);
      });
  }

  displayInspectionModal(data) {
    const modal = document.getElementById("inspection-modal");
    if (!modal) return;

    document.getElementById("inspect-title").innerText = data.properties.name || data.component_id;
    this.currentInspectionData = data;
    this.showInspectTab("physical");
    modal.classList.add("show");
  }

  showInspectTab(tabName) {
    const data = this.currentInspectionData;
    if (!data) return;

    document.querySelectorAll(".inspect-tab").forEach(t => t.classList.remove("active"));
    document.getElementById(`tab-${tabName}`)?.classList.add("active");

    const body = document.getElementById("inspect-body");
    let html = "";

    if (tabName === "physical") {
      const p = data.properties.physical || {};
      for (let k in p) {
        html += `<div class="prop-row"><span class="prop-name">${k.replace(/_/g, " ").toUpperCase()}</span><span class="prop-val">${p[k]}</span></div>`;
      }
    } else if (tabName === "chemical") {
      const c = data.properties.chemical || {};
      for (let k in c) {
        html += `<div class="prop-row"><span class="prop-name">${k.replace(/_/g, " ").toUpperCase()}</span><span class="prop-val">${c[k]}</span></div>`;
      }
    } else if (tabName === "thermal") {
      const th = data.live_thermal_data || {};
      for (let k in th) {
        if (k !== "temperature_history") {
          html += `<div class="prop-row"><span class="prop-name">${k.replace(/_/g, " ").toUpperCase()}</span><span class="prop-val">${th[k]}</span></div>`;
        }
      }
    } else if (tabName === "equations") {
      const eqs = data.applicable_equations || [];
      if (eqs.length === 0) {
        html = "<p style='color:#8b949e;'>No individual equation registered for this accessory.</p>";
      } else {
        eqs.forEach(eq => {
          html += `
            <div class="equation-card">
              <div class="eq-title">${eq.name} (Eq ${eq.id})</div>
              <div class="eq-formula">${eq.latex}</div>
              <div class="eq-subst">${eq.substitution}</div>
              <div class="eq-result">Calculated Result: ${typeof eq.result === 'number' ? eq.result.toFixed(4) : eq.result} ${eq.unit}</div>
            </div>
          `;
        });
      }
    }
    body.innerHTML = html;
  }

  openEquationsModal() {
    fetch("/api/equations")
      .then(res => res.json())
      .then(data => {
        if (!data.success) return;
        const modal = document.getElementById("equations-modal");
        const list = document.getElementById("all-equations-list");
        let html = "";
        data.equations.forEach(eq => {
          html += `
            <div class="equation-card" style="margin-bottom:14px;">
              <div class="eq-title">${eq.id}. ${eq.name} &bull; <span style="color:#00d2ff;font-size:10px;">${eq.domain}</span></div>
              <div class="eq-formula">${eq.latex}</div>
              <div style="font-size:11px;color:#8b949e;margin-bottom:4px;">${eq.explanation}</div>
              <div class="eq-subst"><b>Live Substitution:</b> ${eq.substitution}</div>
              <div class="eq-result">Result: <b>${typeof eq.result === 'number' ? eq.result.toFixed(4) : eq.result} ${eq.unit}</b></div>
            </div>
          `;
        });
        list.innerHTML = html;
        modal.classList.add("show");
      });
  }

  sendControlUpdate(payload) {
    fetch("/api/control", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
  }

  pollStatus() {
    fetch("/api/status")
      .then(res => res.json())
      .then(data => {
        if (data.success && data.state) {
          this.latestState = data.state;
          this.updateHUD(data.state);
        }
      });
  }

  startSimulationLoop() {
    setInterval(() => {
      fetch("/api/step", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ dt: 0.1 })
      })
        .then(res => res.json())
        .then(data => {
          if (data.success && data.state) {
            this.latestState = data.state;
            this.updateHUD(data.state);
          }
        });
    }, 100);
  }

  updateHUD(state) {
    if (!state) return;

    // Header badges
    document.getElementById("hud-sim-time").innerText = state.simulation_time.toFixed(1) + " s";
    const modeBadge = document.getElementById("hud-mode");
    if (modeBadge) modeBadge.innerText = (state.controller?.mode || "active").toUpperCase().replace(/_/g, " ");

    const coolBadge = document.getElementById("hud-cooling-state");
    const coolDot = document.getElementById("hud-cooling-dot");
    if (state.controller?.cooling_active) {
      coolBadge.innerText = "ACTIVE COOLING";
      coolDot.className = "indicator-dot active";
    } else {
      coolBadge.innerText = "STANDBY";
      coolDot.className = "indicator-dot";
    }

    // Telemetry Grid
    const pack = state.battery_pack || {};
    document.getElementById("val-tmax").innerText = (pack.T_max || 25.0).toFixed(1);
    document.getElementById("val-tavg").innerText = (pack.T_avg || 25.0).toFixed(1);
    document.getElementById("val-tmin").innerText = (pack.T_min || 25.0).toFixed(1);
    document.getElementById("val-delta-t").innerText = (pack.delta_T || 0.0).toFixed(1);

    // Overheating badge
    const overheatCard = document.getElementById("card-overheat");
    if (pack.overheating_count > 0) {
      overheatCard?.classList.add("alert");
      document.getElementById("val-overheat-count").innerText = `${pack.overheating_count} CELLS`;
    } else {
      overheatCard?.classList.remove("alert");
      document.getElementById("val-overheat-count").innerText = "0 CELLS";
    }

    // Actuators
    const ctrl = state.controller || {};
    document.getElementById("val-pump-rpm").innerText = (ctrl.pump_rpm || 0).toFixed(0);
    document.getElementById("gauge-pump").style.width = `${Math.min((ctrl.pump_rpm || 0) / 45.0, 100)}%`;

    document.getElementById("val-fan-rpm").innerText = (ctrl.fan_rpm || 0).toFixed(0);
    document.getElementById("gauge-fan").style.width = `${Math.min((ctrl.fan_rpm || 0) / 28.0, 100)}%`;

    const hydro = state.hydraulics || {};
    document.getElementById("val-fluid-vel").innerText = (hydro.velocity_m_s || 0.0).toFixed(3);
    document.getElementById("val-nu").innerText = (hydro.nusselt_number || 4.36).toFixed(1);
    document.getElementById("val-qgen").innerText = (pack.total_heat_gen_w || 0.0).toFixed(0);
    document.getElementById("val-qrem").innerText = (pack.total_heat_removed_w || 0.0).toFixed(0);

    // Update 3D scene meshes
    this.sceneBuilder.updateVisuals(state);
  }

  animate() {
    requestAnimationFrame(() => this.animate());

    const delta = this.clock.getDelta();

    if (this.controls) this.controls.update();

    if (this.latestState && this.nanoparticles) {
      const vel = this.latestState.hydraulics?.velocity_m_s || 0.05;
      const phi1 = this.latestState.nanofluid?.phi1_al2o3 || 0.02;
      const phi2 = this.latestState.nanofluid?.phi2_cuo || 0.01;
      const coolingActive = this.latestState.controller?.cooling_active || false;
      this.nanoparticles.update(delta, vel, phi1, phi2, coolingActive);
    }

    this.renderer.render(this.scene, this.camera);
  }

  onWindowResize() {
    this.camera.aspect = window.innerWidth / window.innerHeight;
    this.camera.updateProjectionMatrix();
    this.renderer.setSize(window.innerWidth, window.innerHeight);
  }
}

// Global bootstrap
window.addEventListener("DOMContentLoaded", () => {
  window.btmsApp = new BTMSApplication();
});
