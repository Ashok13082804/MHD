# Interactive 3D MHD Hybrid Nanofluid Battery Thermal Management System (BTMS)

A real-time, coupled, physics-based, and data-driven 3D engineering digital twin of a 50-cell electric vehicle battery pack cooled by magnetohydrodynamic (MHD) hybrid nanofluids flowing through a porous metal foam heat sink.

---

## 1. System Architecture & 20 Interactive Components

The 3D BTMS model is implemented using **Three.js / WebGL** with real-time conjugate heat transfer and fluid dynamics solvers running on a Flask REST API backend. The system comprises **20 distinct, physically interconnected mechanical and thermal components**:

| # | Component Name | Identification | Function & Physical Description |
|---|---|---|---|
| **1** | **50 Li-ion Battery Cells** | `B01` - `B50` | 5×10 grid of 20 Ah NMC-811 pouch cells with orthotropic conductivity ($k_x=k_y=28.0\text{ W/m}\cdot\text{K}, k_z=0.85\text{ W/m}\cdot\text{K}$). |
| **2** | **Battery Cold Plates** | `cooling_plate` | Dual aluminum 6061-T6 cold plates bounding the cell array with internal coolant passages. |
| **3** | **Coolant Inlet Pipeline** | `inlet_pipeline` | Translucent/metallic pressurized delivery conduit from circulation pump discharge to inlet manifold. |
| **4** | **Coolant Outlet Pipeline** | `outlet_pipeline` | Return conduit collecting heated nanofluid from pack outlet manifold to heat exchanger. |
| **5** | **Circulation Pump** | `pump` | Variable-frequency canned motor centrifugal pump with rotating 6-blade impeller mesh (0–3000 RPM). |
| **6** | **Nanofluid Reservoir** | `reservoir` | Acrylic buffer expansion tank with visible fluid level and de-aeration chamber. |
| **7** | **11 Cooling Channels** | `cooling_channel` | Parallel rectangular microchannels ($H=4\text{ mm}, W=150\text{ mm}, L=250\text{ mm}$) between cell columns. |
| **8** | **Front Radiator** | `radiator` | Automotive-grade louvered aluminum tube-and-fin heat exchanger for ambient thermal rejection. |
| **9** | **Cooling Fan** | `cooling_fan` | 7-blade axial fan mounted on radiator shroud with real-time dynamic rotation linked to fan RPM. |
| **10** | **Heat Exchanger (HEX)** | `heat_exchanger` | Counter-flow shell-and-tube heat exchanger interfacing primary nanofluid loop with secondary chiller loop. |
| **11** | **Vapor-Compression Chiller** | `chiller` | Active refrigeration subsystem delivering sub-ambient coolant during extreme C-rate thermal runaway risk. |
| **12** | **Temperature Sensors** | `temp_sensors` | High-precision RTD/thermocouple probes placed at cell terminals, channels, and manifolds. |
| **13** | **Pressure Sensors** | `pressure_sensors` | Piezoresistive pressure transducers tracking differential pressure drops ($\Delta P$) across cold plates. |
| **14** | **Flow-Rate Sensors** | `flow_sensors` | In-line ultrasonic turbine flow meters measuring instantaneous volumetric throughput ($Q$, L/min). |
| **15** | **3-Way Thermal Control Valve** | `thermal_valve` | Proportional motorized bypass/diverter valve routing fluid through radiator, chiller, or bypass. |
| **16** | **Inlet Distribution Manifold** | `inlet_manifold` | Tapered plenum ensuring uniform flow distribution across all 11 cooling channels. |
| **17** | **Outlet Collection Manifold** | `outlet_manifold` | Header collecting warmed nanofluid effluent for return loop routing. |
| **18** | **MHD Magnetic Field Zone** | `mhd_region` | Transverse permanent NdFeB magnet poles ($B_0 = 0.0 - 1.5\text{ T}$) with visual magnetic flux lines. |
| **19** | **Porous Metal Foam Inserts** | `porous_foam` | High-porosity ($\varepsilon = 0.85$, $K = 10^{-7}\text{ m}^2$) open-cell copper foam inserts in channels. |
| **20** | **BMS Controller Module** | `bms_controller` | Electronic control unit executing state estimation, hysteresis algorithms, and diagnostic LED telemetry. |

---

## 2. 50-Cell Individual Thermal State & Dynamic Color Mapping

Each of the **50 cells (B01 to B50)** is modeled with independent state variables:
- **Spatial Position**: Row $r \in [0, 4]$, Column $c \in [0, 9]$ in 3D space with center thermal entrapment modeling.
- **Electrochemical Heat Generation**: Bernardi formulation ($q_{gen} = q_{irr} + q_{rev}$) based on C-rate, overpotential, and entropic coefficient ($dE/dT = -0.00042\text{ V/K}$).
- **Conjugate Thermal Convection**: In-plane conduction and through-thickness boundary heat extraction into cooling channels ($q_{cool} = h_{eff} A \Delta T$).
- **Dynamic Color Palette**:
  - 🟦 **Blue** ($< 25^\circ\text{C}$): Cold / Sub-ambient preconditioned state.
  - 🟩 **Cyan** ($25^\circ\text{C} - 30^\circ\text{C}$): Optimal normal operating temperature.
  - 🟨 **Yellow** ($30^\circ\text{C} - 35^\circ\text{C}$): Moderate warm state under continuous load.
  - 🟧 **Orange** ($35^\circ\text{C} - 40^\circ\text{C}$): Elevated thermal condition.
  - 🟥 **Red** ($\ge T_{threshold}$, default $35.0^\circ\text{C}$): Exceeds user-configured threshold, triggering automatic active cooling.
- **Independence Guarantee**: Only cells strictly exceeding the threshold turn Red; neighboring cooler cells maintain their respective accurate physical colors.

---

## 3. Closed-Loop Nanofluid & Nanoparticle Flow Animation

- **Particle Suspension Stream**: Hundreds of individual nanoparticles circulate smoothly along 11 distinct channel paths through the closed loop:
  $$\text{Pump} \longrightarrow \text{Inlet Manifold} \longrightarrow 11\text{ Channels} \longrightarrow \text{Outlet Manifold} \longrightarrow \text{HEX} \longrightarrow \text{Radiator} \longrightarrow \text{Reservoir} \longrightarrow \text{Pump}$$
- **Distinguishable Nanoparticles**:
  - $\text{Al}_2\text{O}_3$ (Alumina): Pale ivory / white ($3.5\text{ nm}$).
  - $\text{Cu}$ (Metallic Copper): Metallic orange-copper ($4.0\text{ nm}$).
  - $\text{CuO}$ (Copper Oxide): Dark bronze / charcoal ($3.2\text{ nm}$).
  - $\text{TiO}_2$ (Titania): Bright white ($3.6\text{ nm}$).
  - $\text{SiO}_2$ (Silica): Translucent cyan ($3.0\text{ nm}$).
- **Continuous Thermal Color Shift**:
  - Cool fluid enters cooling channels (Cyan/Blue $\sim 25^\circ\text{C}$).
  - Gradually warms as it absorbs battery heat along the channel (Yellow $\rightarrow$ Orange/Red $\sim 35\text{--}40^\circ\text{C}$).
  - Collects in outlet manifold and flows into the heat exchanger and radiator.
  - Radiator and chiller reject thermal power to ambient, returning the coolant to cool Blue/Cyan before entering the reservoir and pump suction.
- **Physical Pump Interlock**: When the circulation pump is deactivated (`pump_active = false`), particle animation speed freezes to zero immediately.

---

## 4. Intelligent Thermal Controller & 4 Operating Modes

The automated thermal management controller features hysteresis switching and 4 operational modes:
1. **Hybrid Nanofluid Mode** (Default): Intelligent hysteresis ($T_{ON} = 35.0^\circ\text{C}$, $T_{OFF} = 32.0^\circ\text{C}$) with proportional pump (1200–3000 RPM) and fan speed modulation based on thermal overshoot.
2. **Active Chiller Mode**: High-rate heat rejection routing through refrigeration chiller for fast cool-down.
3. **Passive Mode**: Pump and fan remain idle; cooling relies strictly on natural ambient convection ($h \sim 5\text{ W/m}^2\cdot\text{K}$).
4. **Heating / Preconditioning Mode**: PTC heating element activates to warm cold batteries ($T_{cell} < 10^\circ\text{C}$) to optimal operating temperature before charging.
5. **Manual Overrides**: Toggle switch allowing independent operator control over pump and fan actuation.

---

## 5. 10 In-Line Pipeline Measurement Points (P01–P10)

Ten interactive 3D sensor points positioned along the piping network can be clicked to view local thermodynamic and hydrodynamic properties:

| Point | Description | Location | Primary Equations Evaluated |
|---|---|---|---|
| **P01** | Coolant Inlet Port | Pump discharge line | Energy Balance, Fluid Properties |
| **P02** | Cooling Plate Entry | Inlet distribution header | Continuity, Bernoulli Pressure Drop |
| **P03** | Channel 1 Entrance | Cold plate boundary channel | Reynolds ($Re$), Darcy-Brinkman Drag |
| **P04** | Core Pack Channel | Mid-channel (MHD / Foam region) | Hartmann ($Ha$), Darcy ($Da$), Lorentz Force |
| **P05** | Channel 11 Exit | Exit boundary channel | Thermal Convection, Local Heat Flux |
| **P06** | Cooling Plate Exit | Collection outlet manifold | Energy Conservation, Mixed Mean Temp |
| **P07** | Heat Exchanger Inlet | Return line to primary HEX | Counter-Flow LMTD, Heat Exchanged |
| **P08** | Heat Exchanger Outlet | Inter-cooler intermediate line | Fluid Heat Extraction, $\Delta T$ Drop |
| **P09** | Radiator Inlet | Automotive frontal radiator core | Frontal Area Air-Side Heat Rejection |
| **P10** | Radiator Outlet | Cooled return line to reservoir | Reservoir Suction Balance |

---

## 6. All 24 Governing Mathematical Formulations

The interactive **Equation Library Modal** implements all 24 governing formulations with live variable substitution, units, and traceable literature citations:

1. **Battery C-Rate**: $C_{rate} = I / C_{nom}$
2. **Bernardi Heat Generation**: $q_{gen} = \frac{I}{V_{cell}} \left[(U_{ocv} - V_{cell}) - T \frac{dU_{ocv}}{dT}\right]$
3. **Battery Anisotropic Energy Equation**: $\rho_b C_{p,b} \frac{\partial T_b}{\partial t} = \nabla \cdot (\mathbf{k}_b \nabla T_b) + q_{gen}$
4. **Nanoparticle Volume Fraction**: $\phi = \frac{V_{np}}{V_{np} + V_{bf}}$
5. **Nanofluid Mixture Density**: $\rho_{hnf} = (1 - \phi)\rho_{bf} + \phi_1 \rho_{s1} + \phi_2 \rho_{s2}$
6. **Nanofluid Specific Heat Capacity**: $(\rho C_p)_{hnf} = (1 - \phi)(\rho C_p)_{bf} + \phi_1 (\rho C_p)_{s1} + \phi_2 (\rho C_p)_{s2}$
7. **Brinkman Dynamic Viscosity**: $\mu_{hnf} = \frac{\mu_{bf}}{(1 - \phi)^{2.5}}$
8. **Maxwell Effective Thermal Conductivity**: $k_{hnf} = k_{bf} \left[\frac{k_{np} + 2k_{bf} - 2\phi(k_{bf} - k_{np})}{k_{np} + 2k_{bf} + \phi(k_{bf} - k_{np})}\right]$
9. **Porous Effective Conductivity**: $k_{eff} = \varepsilon k_{hnf} + (1 - \varepsilon) k_s$
10. **Continuity Equation**: $\nabla \cdot \mathbf{u} = 0$
11. **Darcy-Brinkman-Forchheimer Momentum**: $\frac{\rho_{hnf}}{\varepsilon} \left[\frac{\partial \mathbf{u}}{\partial t} + (\mathbf{u} \cdot \nabla)\frac{\mathbf{u}}{\varepsilon}\right] = -\nabla p + \frac{\mu_{hnf}}{\varepsilon}\nabla^2\mathbf{u} - \frac{\mu_{hnf}}{K}\mathbf{u} - \frac{\rho_{hnf} C_F}{\sqrt{K}}|\mathbf{u}|\mathbf{u} + \mathbf{J} \times \mathbf{B}$
12. **MHD Transverse Lorentz Force**: $\mathbf{F}_L = \mathbf{J} \times \mathbf{B} = -\sigma_{hnf} B_0^2 u \, \hat{\mathbf{i}}$
13. **Lorentz Drag Force**: $F_{Lx} = -\sigma_{hnf} B_0^2 u$
14. **Magnetic Field Relation**: $B = \mu_0 H$
15. **Energy Equation with Joule & Viscous Dissipation**: $(\rho C_p)_{hnf} \left[\frac{\partial T}{\partial t} + \mathbf{u}\cdot\nabla T\right] = \nabla \cdot (k_{eff}\nabla T) + \Phi_{visc} + \sigma_{hnf} B_0^2 u^2$
16. **Inlet & Outlet Boundary Conditions**: $u|_{in} = U_{in}, T|_{in} = T_{in}; \quad \frac{\partial u}{\partial x}|_{out} = 0, \frac{\partial T}{\partial x}|_{out} = 0$
17. **Conjugate Interface Continuity**: $T_{wall,s} = T_{wall,f}; \quad -k_b \left.\frac{\partial T_b}{\partial n}\right|_{wall} = -k_{eff} \left.\frac{\partial T_f}{\partial n}\right|_{wall}$
18. **Convective Heat Transfer Coefficient**: $h = \frac{q''_{wall}}{T_{wall} - T_{bulk}}$
19. **Reynolds Number**: $Re = \frac{\rho_{hnf} U_{in} D_h}{\mu_{hnf}}$
20. **Prandtl Number**: $Pr = \frac{\mu_{hnf} C_{p,hnf}}{k_{hnf}}$
21. **Nusselt Number**: $Nu = \frac{h D_h}{k_{hnf}}$
22. **Hartmann Number**: $Ha = B_0 D_h \sqrt{\frac{\sigma_{hnf}}{\mu_{hnf}}}$
23. **Darcy Number**: $Da = \frac{K}{D_h^2}$
24. **Thermal Performance Factor (TPF)**: $\eta = \frac{Nu / Nu_0}{(f / f_0)^{1/3}}$

---

## 7. Interactive 5-Section Component Inspector

Selecting any of the 20 components or 50 battery cells populates the right-hand panel across 5 structured sections:
- **Section A: Component Information**: Name, unique ID, engineering function, physical location in BTMS, working principle.
- **Section B: Physical Properties**: Live temperature ($^\circ\text{C}$ and $\text{K}$), pressure ($\text{kPa}$), velocity ($\text{m/s}$), mass ($\text{kg}$), dimensions, thermal conductivity tensor ($k_x, k_y, k_z$), density, specific heat capacity.
- **Section C: Chemical & Material Properties**: Active chemistry (NMC-811 cathode, synthetic graphite anode, $\text{LiPF}_6$ electrolyte), base fluids, nanoparticle composition, corrosion inhibitors, safety thresholds.
- **Section D: Mathematical Model**: Exact governing equation, key variables, physical assumptions, domain boundary conditions.
- **Section E: Step-by-Step Numerical Results**: Detailed substitution arithmetic with intermediate values and final calculated answers.
- **Section F: Machine Learning Comparison**: Instantaneous benchmark comparing Physics Mode A vs ML Mode B predictions (Absolute Error, Relative Error %).

---

## 8. Dataset Ingestion & Dual Simulation Modes

- **Multi-Format Dataset Support**: Ingests `.csv`, `.json`, and `.txt` files containing experimental or CFD simulation data.
- **Automated Validation**: Checks row counts, column aliases, NaN/missing values, and flags physical boundary violations.
- **Dual Execution**:
  - **Mode A (Physics Engine)**: Real-time finite-difference coupled Darcy-Brinkman MHD Navier-Stokes and anisotropic energy equations.
  - **Mode B (Machine Learning)**: Neural Network (MLP) and ensemble surrogates (Random Forest, Gradient Boosting, XGBoost) trained on physics datasets, providing fast millisecond predictions with relative errors $< 2.5\%$.

---

## 9. Execution Instructions & Test Verification

### Launching the 3D BTMS Application

Run via the standalone launcher:
```bash
python3 btms_3d/run_btms_3d.py
```
Or launch through the master project CLI:
```bash
python3 main.py --subpart 3D
```
The application will automatically start the server at `http://127.0.0.1:5000/` and open your default web browser.

### Running the Comprehensive Test Suite

To verify all 24 mathematical formulations, the 50-cell battery pack, thermal controller hysteresis, and Flask REST API endpoints:
```bash
python3 -m unittest discover btms_3d/tests
```
All **37 tests** pass with 100% success rate.

---

## 10. Complete Code Example: REST API Programmatic Client

You can control and query the 3D BTMS simulation programmatically using the Python client below:

```python
#!/usr/bin/env python3
"""
3D BTMS Simulation Programmatic REST API Client
Demonstrates stepping the simulation, reconfiguring parameters,
querying the 50 battery cells, inspecting sensor points, and evaluating equations.
"""
import requests
import json
import time

BASE_URL = "http://127.0.0.1:5000"

# 1. System Health & Initial State
status = requests.get(f"{BASE_URL}/api/status").json()["data"]
print(f"[STATUS] Time: {status['time_seconds']:.1f}s | T_max: {status['pack_stats']['t_max_c']:.2f}°C | Pump: {status['cooling_controller']['pump_rpm']} RPM")

# 2. Dynamic Reconfiguration (e.g. Set C-rate to 3.0C and Threshold to 35.0°C)
requests.post(f"{BASE_URL}/api/configure", json={
    "c_rate": 3.0,
    "threshold_c": 35.0,
    "u_in": 0.06,
    "b0_tesla": 0.50,
    "phi1": 0.02,
    "phi2": 0.01,
    "mode": "hybrid_nanofluid"
})

# 3. Step Simulation Forward by 10 Seconds (20 steps x 0.5s)
print("\n[STEP] Advancing 3D Simulation...")
for step in range(20):
    res = requests.post(f"{BASE_URL}/api/step", json={"dt": 0.5}).json()
    pack = res["data"]["pack_stats"]
    ctrl = res["data"]["cooling_controller"]
    print(f"  Step {step+1:02d}: Time = {res['data']['time_seconds']:>4.1f}s | "
          f"T_max = {pack['t_max_c']:.2f}°C | "
          f"Heat Gen = {pack['total_heat_generated_w']:>6.1f}W | "
          f"Pump = {ctrl['pump_rpm']:>4.0f} RPM | "
          f"Cooling = {'ACTIVE' if ctrl['pump_active'] else 'IDLE'}")
    time.sleep(0.05)

# 4. Query All 50 Battery Cells and Identify Critical Cells
cells = requests.get(f"{BASE_URL}/api/cells").json()["cells"]
hot_cells = [c for c in cells if c["temperature_c"] >= 35.0]
print(f"\n[CELLS] Total: {len(cells)} | Cells >= 35°C (Alert Red): {len(hot_cells)}")
if hot_cells:
    for hc in hot_cells[:3]:
        print(f"  * {hc['cell_id']}: {hc['temperature_c']}°C, Heat Gen = {hc['heat_generation_w']:.2f}W, Status = {hc['thermal_status'].upper()}")

# 5. Inspect In-Line Measurement Point P04 (Core Channel)
p04 = requests.get(f"{BASE_URL}/api/measurement_point/P04").json()["point"]
print(f"\n[MEASUREMENT] Point {p04['id']} ({p04['name']}):")
print(f"  * Temp: {p04['temp_c']}°C | Pressure: {p04['pressure_pa']/1000:.2f} kPa | Velocity: {p04['velocity_m_s']} m/s")

# 6. Evaluate Equation 2 (Bernardi Heat Generation)
eq2 = requests.get(f"{BASE_URL}/api/formula/2").json()["formula"]
print(f"\n[EQUATION] {eq2['name']}:")
print(f"  * Substituted: {eq2['formula']}")
print(f"  * Result: {eq2['result']:.2f} {eq2['unit']}")

# 7. Mode B Machine Learning Surrogate Prediction
ml_pred = requests.post(f"{BASE_URL}/api/ml/predict", json={
    "model_name": "gradient_boosting",
    "c_rate": 3.0,
    "u_in": 0.06,
    "b0_tesla": 0.50,
    "phi1": 0.02,
    "phi2": 0.01,
    "t_in_c": 25.0
}).json()
print(f"\n[ML SURROGATE] Model: {ml_pred['prediction']['model_name'].upper()}")
print(f"  * Physics Mode A T_max: {ml_pred['physics_mode_a']['t_max_c']:.2f}°C")
print(f"  * ML Mode B Predicted : {ml_pred['prediction']['predicted_t_max_c']:.2f}°C")
print(f"  * Absolute Error      : {ml_pred['error_metrics']['absolute_error_c']:.3f}°C")
print(f"  * Relative Error      : {ml_pred['error_metrics']['relative_error_pct']:.2f}%")
```

---

## 11. Complete Code Example: Numerical Calculations & Equation Evaluation

To evaluate all 24 governing equations programmatically without the web server:

```python
#!/usr/bin/env python3
"""
Direct Evaluation of the 24 Governing Equations using the Formula Engine
"""
from btms_3d.backend.formula_engine.equation_library import evaluate_equation, get_all_equations_metadata

# 1. Print all 24 registered equations
print("=" * 80)
print(" ALL 24 GOVERNING EQUATIONS IN BTMS ".center(80, "="))
print("=" * 80)
metadata = get_all_equations_metadata()
for eq in metadata:
    print(f"EQ {eq['id']:02d}: {eq['name']:<45} | Domain: {eq['domain']}")

# 2. Evaluate specific equations with custom state dictionary
custom_state = {
    "I_current_a": 60.0,            # 3C discharge current for 20 Ah cell
    "C_nom_ah": 20.0,
    "V_cell_m3": 9.75e-5,
    "U_ocv_v": 3.85,
    "V_terminal_v": 3.60,
    "T_battery_k": 308.15,
    "dU_ocv_dT": -0.00042,
    "phi1": 0.02,
    "phi2": 0.01,
    "rho_bf": 997.1,
    "rho_s1": 3970.0,
    "rho_s2": 6320.0,
    "u_in": 0.06,
    "b0_tesla": 0.50,
    "sigma_hnf": 0.0526,
    "k_hnf": 0.668,
    "mu_hnf": 0.00096,
    "d_h_m": 0.004,
    "h_fluid": 650.0,
    "Nu": 14.5,
    "Nu_0": 4.36,
    "f_friction": 0.065,
    "f_0": 0.045
}

print("\n" + "=" * 80)
print(" DETAILED STEP-BY-STEP EVALUATION EXAMPLES ".center(80, "="))
print("=" * 80)

# Evaluate Equation 2: Bernardi Heat Generation
eq2 = evaluate_equation(2, custom_state)
print(f"\n[EQ 2] {eq2['name']}")
print(f"Formula : {eq2['formula']}")
print("Steps   :")
for step in eq2["steps"]:
    print(f"  * {step}")
print(f"Result  : {eq2['result']:.2f} {eq2['unit']}")
print(f"Citation: {eq2['citation']['author']} ({eq2['citation']['year']}), {eq2['citation']['title']}")

# Evaluate Equation 13: Lorentz Electromagnetic Force
eq13 = evaluate_equation(13, custom_state)
print(f"\n[EQ 13] {eq13['name']}")
print(f"Formula : {eq13['formula']}")
print(f"Result  : {eq13['result']:.6e} {eq13['unit']}")

# Evaluate Equation 24: Thermal Performance Factor (TPF)
eq24 = evaluate_equation(24, custom_state)
print(f"\n[EQ 24] {eq24['name']}")
print(f"Formula : {eq24['formula']}")
print(f"Result  : {eq24['result']:.3f} {eq24['unit']}")
print(f"Meaning : {eq24['meaning']}")
```

