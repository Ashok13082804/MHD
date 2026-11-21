/**
 * Component and Formula Inspector Module
 * Handles 5-section inspection panel and 24-equation library modal.
 */

const ComponentInspector = {
  selectedComponent: "battery_pack",

  init() {
    this.bindEvents();
    this.loadEquationsLibrary();
  },

  bindEvents() {
    const btnLib = document.getElementById("btnEquationLibrary");
    const modal = document.getElementById("equationModal");
    const btnClose = document.getElementById("btnCloseModal");

    if (btnLib && modal && btnClose) {
      btnLib.addEventListener("click", () => {
        modal.classList.remove("hidden");
      });
      btnClose.addEventListener("click", () => {
        modal.classList.add("hidden");
      });
      modal.addEventListener("click", (e) => {
        if (e.target === modal) modal.classList.add("hidden");
      });
    }
  },

  async inspectComponent(compKey) {
    this.selectedComponent = compKey;
    try {
      const res = await fetch(`/api/component/${compKey}`);
      const json = await res.json();
      if (json.success && json.component) {
        this.renderComponentData(json.component);
      }
    } catch (err) {
      console.warn("Error fetching component details:", err);
    }
  },

  async inspectCell(cellId) {
    this.selectedComponent = cellId;
    try {
      const res = await fetch(`/api/cell/${cellId}`);
      const json = await res.json();
      if (json.success && json.cell) {
        this.renderCellData(json.cell, json.formulas);
      }
    } catch (err) {
      console.warn("Error inspecting cell:", err);
    }
  },

  renderComponentData(comp) {
    // Header
    const titleEl = document.getElementById("inspectorHeaderTitle");
    const badgeEl = document.getElementById("selectedItemIdBadge");
    if (titleEl) titleEl.textContent = comp.name.toUpperCase();
    if (badgeEl) badgeEl.textContent = comp.id;

    // Section A: Component Info
    document.getElementById("ciName").textContent = comp.name;
    document.getElementById("ciId").textContent = comp.id;
    document.getElementById("ciFunction").textContent = comp.function;
    document.getElementById("ciLocation").textContent = comp.location;
    document.getElementById("ciPrinciple").textContent = comp.working_principle;

    // Section B: Physical Properties
    const physGrid = document.getElementById("physicalPropsGrid");
    if (physGrid) {
      physGrid.innerHTML = Object.entries(comp.physical_properties || {}).map(([k, v]) => `
        <div class="info-row"><span class="lbl">${k}:</span><strong class="val font-mono">${v}</strong></div>
      `).join("");
    }

    // Section C: Chemical Properties
    const chemGrid = document.getElementById("chemicalPropsGrid");
    if (chemGrid) {
      chemGrid.innerHTML = Object.entries(comp.chemical_properties || {}).map(([k, v]) => `
        <div class="info-row"><span class="lbl">${k}:</span><span class="val">${v}</span></div>
      `).join("");
    }

    // Section D: Mathematical Model
    const mm = comp.mathematical_model || {};
    document.getElementById("mmEquation").textContent = mm["Governing Equation"] || "N/A";
    document.getElementById("mmVariables").textContent = mm["Key Variables"] || "";

    // Section E: Numerical Results
    const num = comp.numerical_calculation || {};
    const stepsBox = document.getElementById("numStepsBox");
    if (stepsBox) {
      stepsBox.innerHTML = Object.entries(num).map(([k, v]) => `
        <div>&bull; <strong>${k}:</strong> ${v}</div>
      `).join("");
    }
    const ansEl = document.getElementById("numFinalAnswer");
    if (ansEl) ansEl.textContent = num["Pack Heat Output"] || num["Current C-Rate"] || "CALCULATED";
  },

  renderCellData(cell, formulas) {
    const titleEl = document.getElementById("inspectorHeaderTitle");
    const badgeEl = document.getElementById("selectedItemIdBadge");
    if (titleEl) titleEl.textContent = `BATTERY CELL ${cell.cell_id}`;
    if (badgeEl) badgeEl.textContent = cell.cell_id;

    // Section A
    document.getElementById("ciName").textContent = `Lithium-Ion NMC Pouch Cell (${cell.cell_id})`;
    document.getElementById("ciId").textContent = cell.cell_id;
    document.getElementById("ciFunction").textContent = `Electrochemical storage (Row ${cell.row+1}, Col ${cell.col+1})`;
    document.getElementById("ciLocation").textContent = `Pack Module 5x10 Array Coordinate (${cell.row}, ${cell.col})`;
    document.getElementById("ciPrinciple").textContent = "Lithium intercalation into graphite anode / NMC-811 cathode under load";

    // Section B
    const physGrid = document.getElementById("physicalPropsGrid");
    if (physGrid) {
      physGrid.innerHTML = `
        <div class="info-row"><span class="lbl">Temperature:</span><strong class="val font-mono text-success">${cell.temperature_c} °C (${cell.temperature_k} K)</strong></div>
        <div class="info-row"><span class="lbl">Heat Generation:</span><strong class="val font-mono">${cell.heat_generation_w} W (${cell.heat_generation_w_m3} W/m³)</strong></div>
        <div class="info-row"><span class="lbl">Cooling Extraction:</span><strong class="val font-mono">${cell.cooling_rate_w} W</strong></div>
        <div class="info-row"><span class="lbl">C-Rate:</span><span class="val font-mono">${cell.c_rate} C</span></div>
        <div class="info-row"><span class="lbl">Conductivity (In-plane):</span><span class="val font-mono">${cell.thermal_conductivity_kx} W/(m*K)</span></div>
        <div class="info-row"><span class="lbl">Conductivity (Through):</span><span class="val font-mono">${cell.thermal_conductivity_kz} W/(m*K)</span></div>
        <div class="info-row"><span class="lbl">Bulk Density:</span><span class="val font-mono">${cell.density} kg/m³</span></div>
        <div class="info-row"><span class="lbl">Specific Heat:</span><span class="val font-mono">${cell.specific_heat} J/(kg*K)</span></div>
        <div class="info-row"><span class="lbl">Cell Mass:</span><span class="val font-mono">${cell.mass_kg} kg</span></div>
      `;
    }

    // Section C
    const chemGrid = document.getElementById("chemicalPropsGrid");
    if (chemGrid) {
      chemGrid.innerHTML = `
        <div class="info-row"><span class="lbl">Cathode Chemistry:</span><span class="val">LiNi0.8Mn0.1Co0.1O2 (NMC-811)</span></div>
        <div class="info-row"><span class="lbl">Anode Chemistry:</span><span class="val">Synthetic Graphite (C6)</span></div>
        <div class="info-row"><span class="lbl">Electrolyte:</span><span class="val">1M LiPF6 in EC:DMC + 2% VC</span></div>
        <div class="info-row"><span class="lbl">Thermal State:</span><span class="val font-mono">${cell.thermal_status.toUpperCase()}</span></div>
        <div class="info-row"><span class="lbl">Safety Limit:</span><span class="val font-mono">55.0 °C</span></div>
      `;
    }

    // Section D
    document.getElementById("mmEquation").textContent = "q_gen = (I / V_cell) * [(U_ocv - V_cell) - T * (dU_ocv/dT)]";
    document.getElementById("mmVariables").textContent = "Bernardi electrochemical heat equation: I (current), U_ocv (open-circuit), V_cell (operating), T (cell temp), dU_ocv/dT (entropic coefficient).";

    // Section E
    const stepsBox = document.getElementById("numStepsBox");
    if (stepsBox && formulas && formulas.length > 1) {
      const eq2 = formulas[1]; // Bernardi
      stepsBox.innerHTML = (eq2.steps || []).map(s => `<div>&bull; ${s}</div>`).join("");
    }
    const ansEl = document.getElementById("numFinalAnswer");
    if (ansEl) ansEl.textContent = `${cell.heat_generation_w} W (${cell.temperature_c} °C)`;
  },

  async loadEquationsLibrary() {
    try {
      const res = await fetch("/api/equations");
      const json = await res.json();
      if (json.success && json.equations) {
        const container = document.getElementById("allEquationsContainer");
        if (!container) return;

        container.innerHTML = json.equations.map(eq => `
          <div class="equation-card">
            <div class="eq-card-header">
              <span class="eq-num-badge">EQ ${eq.id}</span>
              <span class="eq-card-title">${eq.name}</span>
            </div>
            <div class="eq-card-formula">${eq.formula}</div>
            <div class="eq-card-desc"><strong>Domain:</strong> ${eq.domain}<br>${eq.meaning}</div>
            <div class="eq-card-citation">Ref: ${eq.citation.author} (${eq.citation.year}), ${eq.citation.title}</div>
          </div>
        `).join("");
      }
    } catch (err) {
      console.warn("Error loading equations library:", err);
    }
  }
};
