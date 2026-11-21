/**
 * 10 Interactive Pipeline Measurement Points (P01 - P10)
 * Visualizes sensor points along the BTMS circulation loop and handles data inspection.
 */

class MeasurementPointsManager {
  constructor(scene) {
    this.scene = scene;
    this.markers = new Map(); // pid -> THREE.Mesh
    this.pointsData = {};

    // 3D coordinates aligned with the BTMS physical layout
    this.coordinates = {
      P01: new THREE.Vector3(-3.2, 0.5, 2.0),   // Coolant Inlet Port
      P02: new THREE.Vector3(-2.3, 0.35, 1.3),  // Cooling Plate Entry Manifold
      P03: new THREE.Vector3(-1.8, 0.2, 0.8),   // Channel 1 Entrance
      P04: new THREE.Vector3(0.0, 0.2, 0.0),    // Mid-Pack Channel (MHD/Porous Zone)
      P05: new THREE.Vector3(1.8, 0.2, -0.8),   // Channel 11 Exit
      P06: new THREE.Vector3(2.3, 0.35, -1.3),  // Cooling Plate Exit Manifold
      P07: new THREE.Vector3(3.0, 0.5, -2.0),   // Heat Exchanger Inlet
      P08: new THREE.Vector3(3.2, 0.6, -0.6),   // Heat Exchanger Outlet
      P09: new THREE.Vector3(1.6, 0.8, 2.4),    // Radiator Inlet
      P10: new THREE.Vector3(-0.6, 0.7, 2.7)    // Radiator Outlet / Reservoir Return
    };

    this.initMarkers();
  }

  initMarkers() {
    const sphereGeo = new THREE.SphereGeometry(0.12, 16, 16);
    const ringGeo = new THREE.RingGeometry(0.14, 0.18, 24);

    Object.entries(this.coordinates).forEach(([pid, pos]) => {
      const group = new THREE.Group();
      group.position.copy(pos);
      group.userData = { type: "measurement_point", id: pid };

      // Core sensor sphere
      const sphereMat = new THREE.MeshStandardMaterial({
        color: 0x00f0ff,
        emissive: 0x0088cc,
        emissiveIntensity: 0.8,
        roughness: 0.2,
        metalness: 0.8
      });
      const sphere = new THREE.Mesh(sphereGeo, sphereMat);
      sphere.userData = { type: "measurement_point", id: pid };
      group.add(sphere);

      // Outer glowing ring
      const ringMat = new THREE.MeshBasicMaterial({
        color: 0x00f0ff,
        side: THREE.DoubleSide,
        transparent: true,
        opacity: 0.7
      });
      const ring = new THREE.Mesh(ringGeo, ringMat);
      ring.rotation.x = Math.PI / 2;
      group.add(ring);

      // Label sprite
      const canvas = document.createElement("canvas");
      canvas.width = 128;
      canvas.height = 64;
      const ctx = canvas.getContext("2d");
      ctx.fillStyle = "rgba(7, 13, 25, 0.85)";
      ctx.fillRect(0, 0, 128, 64);
      ctx.strokeStyle = "#00f0ff";
      ctx.lineWidth = 3;
      ctx.strokeRect(2, 2, 124, 60);
      ctx.fillStyle = "#ffffff";
      ctx.font = "bold 28px Consolas, monospace";
      ctx.textAlign = "center";
      ctx.textBaseline = "middle";
      ctx.fillText(pid, 64, 32);

      const texture = new THREE.CanvasTexture(canvas);
      const spriteMat = new THREE.SpriteMaterial({ map: texture, transparent: true });
      const sprite = new THREE.Sprite(spriteMat);
      sprite.position.set(0, 0.35, 0);
      sprite.scale.set(0.6, 0.3, 1.0);
      group.add(sprite);

      this.scene.add(group);
      this.markers.set(pid, { group, sphere, ring, sprite, canvas, ctx, texture });
    });
  }

  update(pointsData, simTime) {
    if (!pointsData) return;
    this.pointsData = pointsData;

    Object.entries(pointsData).forEach(([pid, data]) => {
      const marker = this.markers.get(pid);
      if (!marker) return;

      // Color based on temperature
      const tempC = data.temp_c || 25.0;
      let col = new THREE.Color(0x00f0ff);
      if (tempC >= 35.0) col.setHex(0xff3366);
      else if (tempC >= 30.0) col.setHex(0xffaa00);
      else if (tempC >= 25.0) col.setHex(0x00ff88);
      else col.setHex(0x00a8ff);

      marker.sphere.material.color.copy(col);
      marker.sphere.material.emissive.copy(col);
      marker.ring.material.color.copy(col);

      // Pulsing effect
      const pulse = 1.0 + 0.15 * Math.sin(simTime * 4.0 + pid.charCodeAt(2));
      marker.ring.scale.set(pulse, pulse, 1.0);

      // Update text with temperature
      const ctx = marker.ctx;
      ctx.fillStyle = "rgba(7, 13, 25, 0.9)";
      ctx.fillRect(0, 0, 128, 64);
      ctx.strokeStyle = "#" + col.getHexString();
      ctx.lineWidth = 3;
      ctx.strokeRect(2, 2, 124, 60);
      ctx.fillStyle = "#ffffff";
      ctx.font = "bold 22px Consolas, monospace";
      ctx.textAlign = "center";
      ctx.fillText(pid, 64, 22);
      ctx.fillStyle = "#" + col.getHexString();
      ctx.font = "bold 20px Consolas, monospace";
      ctx.fillText(`${tempC.toFixed(1)}°C`, 64, 46);
      marker.texture.needsUpdate = true;
    });
  }

  getClickableObjects() {
    const list = [];
    this.markers.forEach((m) => {
      list.push(m.sphere);
    });
    return list;
  }

  async inspectPoint(pid) {
    try {
      const res = await fetch(`/api/measurement_point/${pid}`);
      const json = await res.json();
      if (!json.success || !json.point) return;

      const pt = json.point;
      const formulas = json.formulas || [];

      // Update Header
      const titleEl = document.getElementById("inspectorHeaderTitle");
      const badgeEl = document.getElementById("selectedItemIdBadge");
      if (titleEl) titleEl.textContent = `PIPELINE POINT ${pt.id}: ${pt.name.toUpperCase()}`;
      if (badgeEl) badgeEl.textContent = pt.id;

      // Section A: Component Info
      document.getElementById("ciName").textContent = `Measurement Point ${pt.id} - ${pt.name}`;
      document.getElementById("ciId").textContent = pt.id;
      document.getElementById("ciFunction").textContent = "In-line hydrodynamic and thermodynamic state measurement";
      document.getElementById("ciLocation").textContent = pt.location;
      document.getElementById("ciPrinciple").textContent = "Local thermal energy balance: T_p = T_in + (Q_absorbed / (m_dot * Cp))";

      // Section B: Physical Properties
      const physGrid = document.getElementById("physicalPropsGrid");
      if (physGrid) {
        physGrid.innerHTML = `
          <div class="info-row"><span class="lbl">Fluid Temperature:</span><strong class="val font-mono text-success">${pt.temp_c} °C (${pt.temp_k} K)</strong></div>
          <div class="info-row"><span class="lbl">Static Pressure:</span><strong class="val font-mono">${(pt.pressure_pa / 1000).toFixed(2)} kPa (${pt.pressure_pa} Pa)</strong></div>
          <div class="info-row"><span class="lbl">Local Velocity:</span><strong class="val font-mono">${pt.velocity_m_s} m/s</strong></div>
          <div class="info-row"><span class="lbl">Density (rho_hnf):</span><span class="val font-mono">${pt.density_kg_m3} kg/m³</span></div>
          <div class="info-row"><span class="lbl">Viscosity (mu_hnf):</span><span class="val font-mono">${pt.viscosity_pa_s} Pa·s</span></div>
          <div class="info-row"><span class="lbl">Conductivity (k_hnf):</span><span class="val font-mono">${pt.thermal_conductivity_w_m_k} W/(m·K)</span></div>
          <div class="info-row"><span class="lbl">Heat Flux:</span><span class="val font-mono">${pt.heat_flux_w_m2} W/m²</span></div>
        `;
      }

      // Section C: Chemical Properties
      const chemGrid = document.getElementById("chemicalPropsGrid");
      if (chemGrid) {
        chemGrid.innerHTML = `
          <div class="info-row"><span class="lbl">Fluid Phase:</span><span class="val">Liquid Suspension</span></div>
          <div class="info-row"><span class="lbl">Nanoparticles:</span><span class="val">Al2O3 + Cu Hybrid</span></div>
          <div class="info-row"><span class="lbl">Base Fluid:</span><span class="val">Water / Ethylene Glycol</span></div>
          <div class="info-row"><span class="lbl">Corrosion Inhibitor:</span><span class="val">Sodium Benzoate (1.5 wt%)</span></div>
          <div class="info-row"><span class="lbl">pH Stability:</span><span class="val">7.8 - 8.4</span></div>
        `;
      }

      // Section D: Mathematical Model
      document.getElementById("mmEquation").textContent = pt.governing_equation;
      document.getElementById("mmVariables").textContent = "Conservation of mass and energy: rho * u * Cp * dT/dx = q''_wall * P / A_cross";

      // Section E: Step-by-Step Numerical Results
      const stepsBox = document.getElementById("numStepsBox");
      if (stepsBox && formulas.length > 0) {
        stepsBox.innerHTML = formulas.map(f => `
          <div style="margin-bottom: 8px;">
            <div style="color: #00f0ff; font-weight: bold;">[EQ ${f.id}] ${f.name}</div>
            <div style="font-family: monospace; font-size: 0.85rem; color: #a0aec0;">${f.substituted_formula}</div>
            <div style="font-size: 0.85rem; color: #00ff88;">Result: ${f.formatted_result}</div>
          </div>
        `).join("");
      }
      const ansEl = document.getElementById("numFinalAnswer");
      if (ansEl) ansEl.textContent = `${pt.temp_c} °C | ${(pt.pressure_pa / 1000).toFixed(2)} kPa`;

    } catch (err) {
      console.warn("Error inspecting measurement point:", err);
    }
  }
}

window.MeasurementPointsManager = MeasurementPointsManager;
