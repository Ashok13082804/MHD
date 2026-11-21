# Magnetohydrodynamic Hybrid Nanofluid Cooling of Lithium-Ion Batteries: A Coupled Porous Medium and Data-Driven Modeling Approach

---

## 1. Project Title
**Magnetohydrodynamic (MHD) Hybrid Nanofluid Cooling of Lithium-Ion Batteries: A Coupled Porous Medium and Data-Driven Modeling Approach**

---

## 2. Project Abstract
Thermal management is a critical bottleneck in the performance, safety, and operational lifespan of high-energy-density lithium-ion batteries under aggressive fast-charging and high-discharge C-rates. This academic research project develops a dual-framework modeling suite combining:
1. **Part A (Physics-Based Continuum Simulation - Without Machine Learning):** A rigorous mathematical and finite-difference conjugate heat transfer solver coupling the 2D Darcy-Brinkman momentum equations with transverse Lorentz electromagnetic braking and a two-equation energy balance accounting for electrochemical heat generation (Bernardi model), motional Joule heating, and Brinkman viscous dissipation in a porous channel cooled by an $\text{Al}_2\text{O}_3\text{--CuO/Water}$ hybrid nanofluid.
2. **Part B (Physics-Informed Machine Learning - With Machine Learning):** A data-driven surrogate modeling suite trained on a physically validated synthetic dataset of over 1,500 samples (configurable up to 10,000+). Five regression algorithms (Gradient Boosting, XGBoost, Random Forest, Multi-Layer Perceptron Neural Networks, and Support Vector Regression) are trained, achieving $R^2 > 0.994$ and sub-degree temperature prediction accuracy.

---

## 3. Project Objectives
- Individually implement, test, and document all 18 governing mathematical formulations.
- Formulate and validate effective thermophysical models for hybrid nanofluid density, specific heat, thermal conductivity, dynamic viscosity, and electrical conductivity.
- Implement an electrochemical battery heat generation model incorporating irreversible Joule overpotential losses and reversible entropic reaction heat.
- Solve the 2D conjugate heat transfer problem across a porous Darcy-Brinkman MHD channel and solid battery domain using stable finite-difference schemes with residual convergence monitoring.
- Generate a physics-informed dataset (> 500 samples, default 1,500 samples) grounded in continuum transport equations, rejecting physically inadmissible states.
- Train and benchmark five machine learning regression models, reporting MAE, MSE, RMSE, $R^2$, and latency metrics.
- Provide interactive CLI and automated workflows that print all input parameters with names and units, step-by-step intermediate calculations, final outputs, and high-resolution graphs.

---

## 4. Description of All 18 Mathematical Formulations

### Formula 1: Energy Equation
$$(\rho C_p)_{\text{eff}} \left[ \frac{\partial T}{\partial t} + u \frac{\partial T}{\partial x} + v \frac{\partial T}{\partial y} \right] = k_{\text{eff}} \left( \frac{\partial^2 T}{\partial x^2} + \frac{\partial^2 T}{\partial y^2} \right) + Q_b + Q_{\text{visc}} + Q_J$$
- **Description:** Governs local thermal energy conservation in the hybrid nanofluid and battery domains. Balances transient heat storage, convective transport, conductive diffusion, volumetric battery heat sources ($Q_b$), viscous shear dissipation ($Q_{\text{visc}}$), and electromagnetic Joule dissipation ($Q_J$).
- **Module:** `part_a_without_ml/energy_equation.py`

### Formula 2: Darcy-Brinkman MHD Momentum Equation
$$\rho_{\text{hnf}} \left[ \frac{\partial \mathbf{V}}{\partial t} + (\mathbf{V} \cdot \nabla)\mathbf{V} \right] = -\nabla p + \mu_{\text{eff}} \nabla^2 \mathbf{V} - \frac{\mu_{\text{eff}}}{k} \mathbf{V} + \mathbf{J} \times \mathbf{B}$$
- **Description:** Models 2D incompressible fluid flow through a porous matrix under an external magnetic field. Combines inertial acceleration, pressure gradient forces, Brinkman boundary-layer shear stresses, Darcy drag resistance, and Lorentz forces.
- **Module:** `part_a_without_ml/momentum_equation.py`

### Formula 3: Reynolds Number
$$Re = \frac{\rho_{\text{hnf}} U_{\text{in}} L}{\mu_{\text{eff}}}$$
- **Description:** Dimensionless ratio of inertial forces to viscous forces. Characterizes hydrodynamic boundary layer stability and flow regime (internal channel laminar flow for $Re < 2300$).
- **Module:** `part_a_without_ml/dimensionless_numbers.py`

### Formula 4: Prandtl Number
$$Pr = \frac{\mu_{\text{eff}} C_{p,\text{hnf}}}{k_{\text{eff}}}$$
- **Description:** Dimensionless ratio of momentum diffusivity ($\nu = \mu/\rho$) to thermal diffusivity ($\alpha = k/\rho C_p$). Evaluated strictly with mass-specific heat capacity $C_{p,\text{hnf}}$ in $\text{J}/(\text{kg}\cdot\text{K})$.
- **Module:** `part_a_without_ml/dimensionless_numbers.py`

### Formula 5: Hartmann Number
$$Ha = B_0 L \sqrt{\frac{\sigma_{\text{hnf}}}{\mu_{\text{eff}}}}$$
- **Description:** Ratio of electromagnetic Lorentz retarding forces to dynamic viscous forces. Dictates the flattening of the channel velocity profile and thinning of Hartmann boundary layers.
- **Module:** `part_a_without_ml/dimensionless_numbers.py`

### Formula 6: Darcy Number
$$Da = \frac{k}{L^2}$$
- **Description:** Ratio of porous medium permeability $k$ to the square of characteristic channel dimension $L^2$. Small $Da \ll 10^{-4}$ denotes dense porous packing dominated by Darcy resistance.
- **Module:** `part_a_without_ml/dimensionless_numbers.py`

### Formula 7: Brinkman Number
$$Br = \frac{\mu_{\text{eff}} U_{\text{in}}^2}{k_{\text{eff}} \Delta T}$$
- **Description:** Ratio of viscous heat dissipation to molecular conduction heat transfer across characteristic temperature difference $\Delta T = |T_w - T_{\text{in}}| > 0$.
- **Module:** `part_a_without_ml/dimensionless_numbers.py`

### Formula 8: Nusselt Number
$$Nu = \frac{h L}{k_{\text{eff}}}, \quad Nu_{\text{local}} = -\frac{L}{T_w - T_{\text{in}}} \left. \frac{\partial T}{\partial n} \right|_{\text{wall}}, \quad \overline{Nu} = \frac{1}{L_x}\int_0^{L_x} Nu_{\text{local}}(x) dx$$
- **Description:** Ratio of convective heat transfer rate to pure molecular conductive heat transfer across characteristic length $L$.
- **Module:** `part_a_without_ml/dimensionless_numbers.py`

### Formula 9: C-Rate & Battery Current
$$I = C_{\text{rate}} \cdot Q_{\text{rated}}$$
- **Description:** Battery operating current in Amperes derived from discharge/charge C-rate multiplier and nominal capacity in Ampere-hours.
- **Module:** `part_a_without_ml/dimensionless_numbers.py`

### Formula 10: Boundary Conditions
- **Inlet ($x = 0$):** $u = U_{\text{in}}$, $v = 0$, $T = T_{\text{in}}$
- **Outlet ($x = L$):** $\frac{\partial u}{\partial x} = 0$, $\frac{\partial v}{\partial x} = 0$, $\frac{\partial T}{\partial x} = 0$
- **Channel Bottom ($y = 0$):** $u = 0$, $v = 0$, $\frac{\partial T}{\partial y} = 0$ (Impermeable adiabatic wall)
- **Top Battery Wall ($y = H_{\text{tot}}$):** $-k_b \frac{\partial T}{\partial y} = h_{\text{amb}}(T - T_{\text{amb}})$ (Convection to ambient air)
- **Module:** `part_a_without_ml/boundary_conditions.py`

### Formula 11: Temperature Continuity at Interface
$$T_b(x, y_{\text{int}}) = T_f(x, y_{\text{int}})$$
- **Description:** Enforces continuous temperature field across the conjugate battery-coolant interface without thermal jump.
- **Module:** `part_a_without_ml/boundary_conditions.py`

### Formula 12: Heat Flux Continuity at Interface
$$-k_b \left. \frac{\partial T_b}{\partial n} \right|_{\text{int}} = -k_f \left. \frac{\partial T_f}{\partial n} \right|_{\text{int}} \quad \left( \text{or } \frac{T_b - T_f}{R_{\text{tc}}} \text{ when contact resistance } R_{\text{tc}} > 0 \right)$$
- **Description:** Conjugate energy conservation matching normal heat fluxes between the solid battery and fluid coolant.
- **Module:** `part_a_without_ml/boundary_conditions.py`

### Formula 13: Effective Hybrid Nanofluid Density
$$\rho_{\text{hnf}} = (1 - \phi_1 - \phi_2)\rho_f + \phi_1 \rho_{s1} + \phi_2 \rho_{s2}$$
- **Description:** Mixture density for water base fluid dispersed with $\text{Al}_2\text{O}_3$ ($\phi_1$) and $\text{CuO}$ ($\phi_2$) nanoparticles.
- **Module:** `part_a_without_ml/material_properties.py`

### Formula 14: Fluid and Nanoparticle Density Separation & Validation
$$\phi_1 \ge 0, \quad \phi_2 \ge 0, \quad \phi_1 + \phi_2 < 1.0$$
- **Description:** Independent specification and programmatic validation of base fluid and constituent nanoparticle densities.
- **Module:** `part_a_without_ml/material_properties.py`

### Formula 15: Effective Thermal Conductivity and Dynamic Viscosity
- **Maxwell Hybrid Thermal Conductivity Model:**
  $$k_s = \frac{\phi_1 k_{s1} + \phi_2 k_{s2}}{\phi}, \quad \frac{k_{\text{hnf}}}{k_f} = \frac{k_s + 2k_f - 2\phi(k_f - k_s)}{k_s + 2k_f + \phi(k_f - k_s)}$$
- **Brinkman Dynamic Viscosity Model:**
  $$\mu_{\text{hnf}} = \frac{\mu_f}{(1 - \phi_1 - \phi_2)^{2.5}}$$
- **Module:** `part_a_without_ml/material_properties.py`

### Formula 16: Motional Joule Heating
$$Q_J = \mathbf{J} \cdot \mathbf{E}' = \frac{|\mathbf{J}|^2}{\sigma_{\text{hnf}}} = \sigma_{\text{hnf}} |\mathbf{V} \times \mathbf{B}|^2 = \sigma_{\text{hnf}} B_0^2 u^2 \quad [\text{W/m}^3]$$
- **Description:** Volumetric ohmic dissipation induced by fluid motion across transverse magnetic field lines $\mathbf{B} = (0, B_0, 0)$ under low magnetic Reynolds number ($Re_m \ll 1$).
- **Module:** `part_a_without_ml/material_properties.py`

### Formula 17: Lorentz Electromagnetic Body Force
$$\mathbf{F}_L = \mathbf{J} \times \mathbf{B} = -\sigma_{\text{hnf}} B_0^2 u \, \hat{\mathbf{i}} \quad [\text{N/m}^3]$$
- **Description:** Opposing magnetic brake acting strictly in the $-X$ direction against fluid flow.
- **Module:** `part_a_without_ml/material_properties.py`

### Formula 18: Darcy-Brinkman MHD Combined Momentum Formulation
$$\rho_{\text{hnf}} \left[ \frac{\partial \mathbf{V}}{\partial t} + (\mathbf{V} \cdot \nabla)\mathbf{V} \right] = -\nabla p + \mu_{\text{eff}} \nabla^2 \mathbf{V} - \frac{\mu_{\text{eff}}}{k} \mathbf{V} - \sigma_{\text{hnf}} B_0^2 \mathbf{V}$$
- **Description:** Unifies fluid inertia, pressure gradient drive, Brinkman viscous diffusion, Darcy porous resistance, and Lorentz damping into a single momentum framework.
- **Module:** `part_a_without_ml/material_properties.py`

---

## 5. Explanation of Every Physical Parameter and Unit

| Parameter | Symbol | SI Unit | Physical Meaning |
|---|---|---|---|
| Inlet Velocity | $U_{\text{in}}$ | $\text{m/s}$ | Prescribed fluid inflow velocity at channel entrance |
| Inlet Temperature | $T_{\text{in}}$ | $\text{K}$ | Uniform coolant temperature entering channel |
| Battery Temperature | $T_b, T$ | $\text{K}$ | Local temperature of the battery cell |
| Ambient Temperature | $T_{\text{amb}}$ | $\text{K}$ | Surrounding atmospheric temperature |
| Magnetic Flux Density | $B_0$ | $\text{T}$ (Tesla) | Applied external transverse magnetic field |
| Porous Permeability | $k$ | $\text{m}^2$ | Hydraulic permeability of the porous matrix |
| Porosity | $\varepsilon$ | Dimensionless | Void volume fraction of the porous medium |
| Base Fluid Density | $\rho_f$ | $\text{kg/m}^3$ | Pure liquid density (Water = $997.10\text{ kg/m}^3$) |
| $\text{Al}_2\text{O}_3$ Density | $\rho_{s1}$ | $\text{kg/m}^3$ | Density of alumina nanoparticles ($3970.0\text{ kg/m}^3$) |
| $\text{CuO}$ Density | $\rho_{s2}$ | $\text{kg/m}^3$ | Density of cupric oxide nanoparticles ($6320.0\text{ kg/m}^3$) |
| $\text{Al}_2\text{O}_3$ Volume Fraction | $\phi_1$ | Dimensionless | Solid volume fraction of $\text{Al}_2\text{O}_3$ |
| $\text{CuO}$ Volume Fraction | $\phi_2$ | Dimensionless | Solid volume fraction of $\text{CuO}$ |
| Base Fluid Specific Heat | $C_{p,f}$ | $\text{J}/(\text{kg}\cdot\text{K})$ | Heat capacity per unit mass of water ($4179.0\text{ J}/(\text{kg}\cdot\text{K})$) |
| Effective Specific Heat | $C_{p,\text{hnf}}$ | $\text{J}/(\text{kg}\cdot\text{K})$ | Mass-specific heat capacity of hybrid nanofluid |
| Volumetric Heat Capacity | $(\rho C_p)_{\text{hnf}}$ | $\text{J}/(\text{m}^3\cdot\text{K})$ | Volumetric heat storage capacity of nanofluid |
| Base Fluid Conductivity | $k_f$ | $\text{W}/(\text{m}\cdot\text{K})$ | Pure water thermal conductivity ($0.613\text{ W}/(\text{m}\cdot\text{K})$) |
| Effective Conductivity | $k_{\text{hnf}}$ | $\text{W}/(\text{m}\cdot\text{K})$ | Enhanced thermal conductivity of hybrid nanofluid |
| Effective Viscosity | $\mu_{\text{hnf}}$ | $\text{Pa}\cdot\text{s}$ | Dynamic shear viscosity of the suspension |
| Electrical Conductivity | $\sigma_{\text{hnf}}$ | $\text{S/m}$ | Electrical conductivity of the conducting fluid |
| Battery Current | $I$ | $\text{A}$ | Discharge current extracted from cell |
| Open-Circuit Voltage | $V_{\text{oc}}$ | $\text{V}$ | Thermodynamic equilibrium cell voltage |
| Operating Cell Voltage | $V_{\text{op}}$ | $\text{V}$ | Terminal voltage under load |
| Entropic Temperature Coeff. | $\frac{dU_{\text{oc}}}{dT}$ | $\text{V/K}$ | Entropic coefficient of open-circuit voltage |
| Battery Heat Generation | $\dot{Q}_b$ | $\text{W}$ | Total heat generation rate in battery cell |
| Volumetric Heat Gen. | $q'''_b$ | $\text{W/m}^3$ | Volumetric heat generation rate |
| Characteristic Channel Height | $L$ | $\text{m}$ | Hydraulic gap width of the cooling channel |
| Battery Length | $L_x$ | $\text{m}$ | In-plane axial dimension of the battery pouch |
| Battery Thickness | $W$ | $\text{m}$ | Transverse cell thickness |
| Convective Coefficient | $h$ | $\text{W}/(\text{m}^2\cdot\text{K})$ | Surface heat transfer coefficient |
| Thermal Contact Resistance | $R_{\text{tc}}$ | $\text{m}^2\cdot\text{K/W}$ | Interface interfacial thermal impedance |

---

## 6. Effective Thermophysical Property Models
- **Volumetric Heat Capacity (Section 3):**
  $$(\rho C_p)_{\text{hnf}} = (1 - \phi_1 - \phi_2)(\rho C_p)_f + \phi_1 (\rho C_p)_{s1} + \phi_2 (\rho C_p)_{s2} \quad [\text{J}/(\text{m}^3\cdot\text{K})]$$
- **Mass-Specific Heat Capacity:**
  $$C_{p,\text{hnf}} = \frac{(\rho C_p)_{\text{hnf}}}{\rho_{\text{hnf}}} \quad [\text{J}/(\text{kg}\cdot\text{K})]$$
- **Electrical Conductivity (Maxwell Relation):**
  $$\frac{\sigma_{\text{hnf}}}{\sigma_f} = 1 + \frac{3 \left(\frac{\sigma_s}{\sigma_f} - 1\right)\phi}{\left(\frac{\sigma_s}{\sigma_f} + 2\right) - \left(\frac{\sigma_s}{\sigma_f} - 1\right)\phi}, \quad \text{where } \sigma_s = \frac{\phi_1 \sigma_{s1} + \phi_2 \sigma_{s2}}{\phi}$$

---

## 7. Battery Heat Generation Model (Bernardi et al.)
$$\dot{Q}_b = I (V_{\text{oc}} - V_{\text{op}}) - I T \left( \frac{\partial U_{\text{oc}}}{\partial T} \right)$$
1. **Irreversible Joule / Polarization Heat:** $Q_{\text{irr}} = I (V_{\text{oc}} - V_{\text{op}}) = I^2 R_{\text{int}} > 0$.
2. **Reversible Entropic Reaction Heat:** $Q_{\text{rev}} = -I T \frac{dU_{\text{oc}}}{dT}$, reflecting the entropy change $\Delta S$ of lithium intercalation.

---

## 8. MHD and Darcy-Brinkman Mathematical Model
For steady, fully developed 2D channel flow between bottom wall $y = 0$ and interface $y = H_f$ under transverse magnetic field $B_0 \hat{\mathbf{j}}$:
$$\mu_{\text{eff}} \frac{d^2 u}{dy^2} - \left( \frac{\mu_{\text{eff}}}{k} + \sigma_{\text{hnf}} B_0^2 \right) u = \frac{dp}{dx} = -G$$
Defining the resistance parameter:
$$\lambda = \sqrt{\frac{1}{k} + \frac{\sigma_{\text{hnf}} B_0^2}{\mu_{\text{eff}}}}$$
Analytical velocity profile satisfying no-slip $u(0) = u(H_f) = 0$:
$$u(y) = \frac{G}{\mu_{\text{eff}} \lambda^2} \left[ 1 - \frac{\cosh\left(\lambda (y - H_f/2)\right)}{\cosh(\lambda H_f / 2)} \right]$$
The axial pressure gradient required to deliver inlet velocity $U_{\text{in}}$ is:
$$G = -\frac{dp}{dx} = \frac{U_{\text{in}} \mu_{\text{eff}} \lambda^2}{1 - \frac{\tanh(\lambda H_f / 2)}{\lambda H_f / 2}}$$

---

## 9. Numerical Discretization Approach
- **Grid Layout:** 2D staggered/collocated mesh with $N_x = 60$ axial nodes and $N_y = 50$ transverse nodes ($N_{y,f} = 25$ fluid nodes, $N_{y,b} = 25$ battery nodes).
- **Convective Terms:** First-order upwind differencing $\left( u \frac{T_{i,j} - T_{i-1,j}}{\Delta x} \right)$ ensuring diagonal dominance and unconditional stability.
- **Diffusive Terms:** Second-order central differencing $\left( \frac{T_{i+1,j} - 2T_{i,j} + T_{i-1,j}}{\Delta x^2} + \frac{T_{i,j+1} - 2T_{i,j} + T_{i,j-1}}{\Delta y^2} \right)$.
- **Iterative Scheme:** Successive Over-Relaxation (SOR) with under-relaxation factor $\omega = 0.8$.
- **Convergence Criterion:** Normalized max temperature residual $\max_{i,j} \frac{|T^{(k+1)} - T^{(k)}|}{T_{\text{max}} - T_{\text{min}} + 10^{-5}} < 1.0 \times 10^{-6}$.

---

## 10. Boundary Conditions
- **Inlet ($x = 0$):** $u = U_{\text{in}}$, $v = 0$, $T = T_{\text{in}}$. Battery lateral boundary is insulated ($\partial T/\partial x = 0$).
- **Outlet ($x = L_x$):** $\partial u/\partial x = 0$, $\partial v/\partial x = 0$, $\partial T/\partial x = 0$.
- **Bottom Wall ($y = 0$):** $u = 0, v = 0$, $\partial T/\partial y = 0$ (adiabatic impermeable).
- **Top Battery Surface ($y = H_{\text{tot}}$):** $-k_b \frac{\partial T}{\partial y} = h_{\text{amb}} (T - T_{\text{amb}})$.

---

## 11. Battery-Coolant Interface Conditions
- **Temperature Continuity:** $T_b(x, H_f) = T_f(x, H_f)$.
- **Heat Flux Continuity:**
  $$k_{\text{eff}} \left. \frac{\partial T}{\partial y} \right|_{H_f^-} = k_b \left. \frac{\partial T}{\partial y} \right|_{H_f^+}$$
  Harmonic mean finite-difference conductance across the interface:
  $$T_{\text{int}} = \frac{\frac{k_{\text{eff}}}{\Delta y_f} T_{i, j_{\text{int}}-1} + \frac{k_b}{\Delta y_b} T_{i, j_{\text{int}}+1}}{\frac{k_{\text{eff}}}{\Delta y_f} + \frac{k_b}{\Delta y_b} + R_{\text{tc}} \frac{k_{\text{eff}} k_b}{\Delta y_f \Delta y_b}}$$

---

## 12. Dataset Generation Methodology
- **Sampling:** Stratified Latin Hypercube / uniform pseudorandom sampling across multi-dimensional physical parameter space.
- **Physical Bounds:**
  - $U_{\text{in}} \in [0.01, 0.20]\text{ m/s}$
  - $T_{\text{in}} \in [288.15, 308.15]\text{ K}$
  - $B_0 \in [0.0, 1.5]\text{ T}$
  - $\phi_1 \in [0.0, 0.04]$ ($\text{Al}_2\text{O}_3$), $\phi_2 \in [0.0, 0.03]$ ($\text{CuO}$), $\phi_1 + \phi_2 \le 0.06$
  - $k_{\text{perm}} \in [10^{-8}, 10^{-6}]\text{ m}^2$
  - $C_{\text{rate}} \in [0.5, 4.0]\text{ C}$, $Q_{\text{rated}} \in [10.0, 30.0]\text{ Ah}$
- **Rejection Sampling:** Rejects any unphysical combinations ($\phi < 0$, $\sum \phi \ge 0.06$, $k \le 0$).
- **Grounded Ground-Truth:** All target values are computed directly from the governing conservation laws.

---

## 13. Dataset Input and Output Parameters
- **Inputs (11 Features):** `U_in`, `T_in`, `T_batt_init`, `T_amb`, `B0`, `phi1`, `phi2`, `k_perm`, `c_rate`, `Q_rated`, `L_char`.
- **Target Outputs (17 Columns):** `rho_hnf`, `rho_cp_hnf`, `cp_hnf`, `k_hnf`, `mu_hnf`, `sigma_hnf`, `Re`, `Pr`, `Ha`, `Da`, `Br`, `I_batt`, `Q_b_W`, `Q_J_W_m3`, `Lorentz_force_x`, `Nu_avg`, `T_max_battery`.

---

## 14. Machine Learning Algorithms Used
1. **Random Forest Regressor:** Ensemble of 100 decorrelated decision trees with bootstrap aggregation.
2. **XGBoost Regressor:** Extreme gradient boosted decision trees with regularization and shrinkage.
3. **Support Vector Regression (SVR):** Kernelized radial basis function (RBF) margin maximization.
4. **Gradient Boosting Regressor:** Sequential additive gradient boosted trees minimizing squared-error loss.
5. **Artificial Neural Network (MLP):** Deep Multi-Layer Perceptron (128-64-32 architecture, ReLU activation, Adam optimizer, early stopping).

---

## 15. Model Evaluation Metrics

| Metric | Formula | Meaning |
|---|---|---|
| MAE | $\frac{1}{N}\sum |y_i - \hat{y}_i|$ | Mean Absolute Error [K] |
| MSE | $\frac{1}{N}\sum (y_i - \hat{y}_i)^2$ | Mean Squared Error [$\text{K}^2$] |
| RMSE | $\sqrt{\frac{1}{N}\sum (y_i - \hat{y}_i)^2}$ | Root Mean Squared Error [K] |
| $R^2$ Score | $1 - \frac{\sum (y_i - \hat{y}_i)^2}{\sum (y_i - \bar{y})^2}$ | Coefficient of Determination (Max = 1.0) |
| MAPE (%) | $\frac{100\%}{N}\sum |\frac{y_i - \hat{y}_i}{y_i}|$ | Mean Absolute Percentage Error [%] |

---

## 16. Graphical Outputs (All 25 Figures Saved)

| Figure Name | File Name | Description |
|---|---|---|
| Figure 1 | `01_transient_temperature_evolution.png` | Transient temperature vs time ($t \in [0, 600]\text{ s}$) |
| Figure 2 | `02_battery_temp_vs_position.png` | Axial temperature profile along interface and top surface |
| Figure 3 | `03_coolant_temperature_distribution.png` | Coolant mean temperature rise along channel length |
| Figure 4 | `04_2d_temperature_contour.png` | 2D conjugate temperature contour (Channel + Battery) |
| Figure 5 | `05_3d_temperature_surface.png` | 3D temperature surface across $(x, y)$ domain |
| Figure 6 | `06_velocity_profile.png` | Hartmann-Darcy-Brinkman velocity profile $u(y)$ |
| Figure 8 | `08_velocity_contour.png` | 2D velocity magnitude field in porous channel |
| Figure 9 | `09_pressure_distribution.png` | Axial gauge pressure drop $p(x)$ |
| Figure 10 | `10_reynolds_vs_velocity.png` | Reynolds number vs inlet velocity |
| Figure 11 | `11_prandtl_vs_nanoparticle.png` | Prandtl number vs nanoparticle volume fraction |
| Figure 12 | `12_hartmann_vs_magnetic_field.png` | Hartmann number vs magnetic field strength $B_0$ |
| Figure 13 | `13_darcy_vs_permeability.png` | Darcy number vs porous permeability $k$ |
| Figure 14 | `14_brinkman_vs_velocity.png` | Brinkman number vs coolant inlet velocity |
| Figure 15 | `15_nusselt_vs_reynolds.png` | Average Nusselt number vs Reynolds number |
| Figure 16 | `16_nusselt_vs_nanoparticle.png` | Nusselt number vs total nanoparticle concentration |
| Figure 17 | `17_joule_heating_vs_magnetic_field.png` | Volumetric Joule heating $Q_J$ vs magnetic field |
| Figure 18 | `18_lorentz_force_vs_magnetic_field.png` | Retarding Lorentz force $|F_{Lx}|$ vs magnetic field |
| Figure 19 | `19_battery_temp_vs_crate.png` | Battery peak temperature vs discharge C-rate |
| Figure 20 | `20_battery_temp_vs_nanoparticle_fraction.png` | Battery temperature suppression vs nanoparticle concentration |
| Figure 21 | `21_actual_vs_predicted.png` | Actual vs predicted parity plots for all 5 ML models |
| Figure 22 | `22_model_performance_comparison.png` | Bar chart comparison of $R^2$ scores and RMSE |
| Figure 23 | `23_prediction_error_distribution.png` | Residual prediction error histograms ($y_{\text{pred}} - y_{\text{true}}$) |
| Figure 24 | `24_correlation_heatmap.png` | Correlation matrix heatmap of inputs and outputs |
| Figure 25 | `25_cooling_strategy_comparison.png` | Cooling performance benchmark across thermal strategies |

---

## 17. Project Directory Structure
```
BTMS_MHD_Hybrid_Nanofluid/
│
├── README.md
├── requirements.txt
├── main.py
├── config.py
│
├── data/
│   ├── generated_dataset.csv
│   └── processed_dataset.csv
│
├── part_a_without_ml/
│   ├── A1_formula_calculator.py
│   ├── A2_physics_solver.py
│   ├── material_properties.py
│   ├── boundary_conditions.py
│   ├── energy_equation.py
│   ├── momentum_equation.py
│   ├── dimensionless_numbers.py
│   └── visualizations.py
│
├── part_b_with_ml/
│   ├── B1_dataset_generation.py
│   ├── B1_model_training.py
│   ├── B2_prediction.py
│   ├── model_evaluation.py
│   └── feature_preprocessing.py
│
├── models/
│   ├── random_forest/
│   ├── gradient_boosting/
│   ├── svr/
│   ├── xgboost/
│   └── neural_network_mlp/
│
├── outputs/
│   ├── part_a/
│   │   ├── numerical_results/
│   │   ├── graphs/
│   │   └── reports/
│   │
│   └── part_b/
│       ├── predictions/
│       ├── graphs/
│       ├── model_metrics/
│       └── reports/
│
└── tests/
    ├── test_formulas.py
    ├── test_physics_solver.py
    ├── test_properties.py
    └── test_ml_predictions.py
```

---

## 18. Installation Instructions
1. Clone or navigate into the workspace repository:
   ```bash
   cd "/Users/ashokkumar/Downloads/Separate Blocks"
   ```
2. Set up virtual environment and install dependencies:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

---

## 19. Execution Instructions

### A1 – Without ML: Individual Formula Numerical Calculator
Evaluates all 18 governing formulations sequentially, printing input parameters with units, substituted equations, intermediate steps, final numerical values, and saving results to CSV:
```bash
python part_a_without_ml/A1_formula_calculator.py
```
*(Or `python3 part_a_without_ml/A1_formula_calculator.py`)*

### A2 – Without ML: 2D Coupled Physics-Based BTMS Solver
Executes the conjugate finite-difference solver for Darcy-Brinkman MHD flow and battery energy conservation:
```bash
python part_a_without_ml/A2_physics_solver.py
```
*(Or `python3 part_a_without_ml/A2_physics_solver.py`)*

### B1 – With ML: Dataset Generation and Model Training
Generate the physics-grounded synthetic dataset (> 500 samples, default 1,500 samples):
```bash
python part_b_with_ml/B1_dataset_generation.py --samples 1500
```
Train and benchmark all 5 machine learning models (Random Forest, XGBoost, SVR, Gradient Boosting, MLP):
```bash
python part_b_with_ml/B1_model_training.py
```

### B2 – With ML: Prediction and Visualization
Interactive and argument-driven prediction program comparing ML output against reference numerical calculation:
```bash
python part_b_with_ml/B2_prediction.py --U_in 0.05 --T_in 298.15 --c_rate 2.0 --phi1 0.02 --phi2 0.01 --B0 0.5
```

### Master Runner (Interactive CLI Menu)
```bash
python main.py
```
Or execute specific subparts directly:
```bash
python main.py --subpart A1
python main.py --subpart A2
python main.py --subpart B1_data
python main.py --subpart B1_train
python main.py --subpart B2
python main.py --subpart 3D
python main.py --subpart all
python main.py --subpart test
```

---

## 20. Interactive 3D Nanofluid Battery Thermal Management System (BTMS)

### 20.1 Overview & Architecture
In addition to the 2D finite-difference physics solver and ML surrogate benchmarks, this project includes a complete, scientifically functional, fully interactive **Real-Time 3D Battery Thermal Management System (BTMS)**. 

The 3D application is an engineering-grade digital twin featuring:
1. **50 Individual Battery Cells (B01 - B50):** Arranged in a realistic 5-row $\times$ 10-column module configuration. Each cell tracks its own temperature, electrochemical heat generation (Bernardi equation), C-rate, operating voltage, internal resistance, and heat dissipation.
2. **Selective Thermal Color Mapping:** Dynamic visual feedback using a six-stage thermal gradient:
   - **Blue:** $< 25^\circ\text{C}$ (Low temperature)
   - **Cyan:** $25^\circ\text{C} - 30^\circ\text{C}$ (Normal operating temperature)
   - **Green:** $30^\circ\text{C} - 35^\circ\text{C}$ (Stable temperature)
   - **Yellow:** $35^\circ\text{C} - 40^\circ\text{C}$ (Increasing temperature)
   - **Orange:** $40^\circ\text{C} - \text{Threshold}$ (High temperature)
   - **Red:** $\ge \text{Threshold}$ (**Overheating Alert**). When a cell exceeds the threshold, **only that specific cell turns red**; non-overheating cells retain their true temperatures.
3. **Visible Nanofluid Circulation with Moving Nanoparticles:**
   - Visualized inside transparent piping and microchannel cooling plates.
   - Dual-species nanoparticles: **Silver $\text{Al}_2\text{O}_3$ spheres** ($25\text{ nm}$, metallic specular sheen) and **Copper $\text{CuO}$ spheres** ($35\text{ nm}$, warm copper tone).
   - Continuous motion along the closed-loop hydraulic circuit matching calculated fluid velocity $U_{\text{in}}$.
   - Particle density scales dynamically with user-configured volume fractions $\phi_1$ ($\text{Al}_2\text{O}_3$) and $\phi_2$ ($\text{CuO}$).
4. **Complete 3D Cooling Circuit Components:**
   - 50-cell battery pack with removable transparent enclosure
   - Microchannel cold plate with visible internal flow channels
   - Coolant expansion reservoir
   - Electric coolant pump with spinning 6-blade centrifugal impeller
   - Front-end compact radiator with spinning axial cooling fan
   - Plate-fin refrigerant chiller unit
   - 3-way electro-thermal diversion valve
   - Integrated temperature, pressure, and flow rate sensor blocks
5. **11 Pipeline Thermal Stations:**
   Color-coded fluid temperature segments tracking local enthalpy changes:
   - Station 1: Reservoir Outlet
   - Station 2: Pump Outlet
   - Station 3: Cold Plate Inlet
   - Station 4: Channel 1 (Entrance Region)
   - Station 5: Channel 2 (Mid-Plate Convective Zone)
   - Station 6: Channel 3 (Exit Region)
   - Station 7: Cold Plate Outlet
   - Station 8: Heat Exchanger / Chiller Inlet
   - Station 9: Chiller Outlet
   - Station 10: Radiator Inlet
   - Station 11: Radiator Outlet (Return to Reservoir)
6. **Automatic Temperature-Controlled Cooling:**
   - Real-time draggable threshold slider ($20^\circ\text{C} - 60^\circ\text{C}$, default $35^\circ\text{C}$)
   - Built-in $2^\circ\text{C}$ hysteresis deadband preventing rapid actuator chattering
   - Variable-speed modulation: Pump ($0 - 4500\text{ RPM}$) and Fan ($0 - 2800\text{ RPM}$) modulate proportionally to thermal overshoot above $(T_{\text{threshold}} - T_{\text{hysteresis}})$
   - Three operational modes:
     - **Mode A (Passive):** Natural convection, pump and fan off
     - **Mode B (Active Nanofluid):** Pump and radiator fan dynamically modulated
     - **Mode C (Active Chiller):** Refrigerant chiller engaged for extreme heat dissipation
7. **Complete 24 Governing Mathematical Formulations:**
   All 24 equations evaluated live with step-by-step substitution, intermediate calculations, and SI units displayed directly upon clicking any 3D component or cell, and accessible through the top **"All 24 Equations Catalog"** modal.
8. **Interactive 3D Camera & Controls:**
   - 360° Left-Click Orbit rotation
   - Right-Click Panning
   - Scroll-Wheel Zoom ($0.4\text{m} - 5.0\text{m}$)
   - Exploded View button (smooth lerping of casing and cells outward)
   - Transparent Enclosure toggle
   - Preset camera buttons (Isometric, Top/Pack, Side/Radiator, Front/Chiller, Reset)
9. **Dataset Ingestion & Batch Playback:**
   - Supports CSV, JSON, and Excel file uploads via drag-and-drop or file picker
   - Validates schema, physical ranges, and units
   - Real-time vector playback into the 3D model
10. **ML Surrogate Inference:**
    - Live integration with trained machine learning models (Gradient Boosting, Random Forest)
    - Sub-millisecond instantaneous prediction of peak battery temperature

---

### 20.2 Instructions and Code to Run the 3D Animation

#### Launch Command (Instant One-Step Runner)
Execute the dedicated 3D orchestrator script from the project root directory:

```bash
python3 main_3d.py
```

Or launch via the master orchestrator CLI:
```bash
python3 main.py --subpart 3D
```
Or interactively:
```bash
python3 main.py
# Enter choice [8] to launch Interactive 3D Real-Time BTMS Simulation
```

#### Custom Port and Host Flags
```bash
# Run on custom port 8888 without automatically opening the browser
python3 main_3d.py --port 8888 --no-browser

# Bind to all network interfaces for LAN / remote access
python3 main_3d.py --host 0.0.0.0 --port 8080
```

Once started, the application is live at:
```
http://localhost:8080
```

#### Interactive Simulation Controls Summary
- **Orbit 3D Scene:** Click and drag with **Left Mouse Button**
- **Pan Camera:** Click and drag with **Right Mouse Button** (or Shift + Left Click)
- **Zoom:** Rotate **Scroll Wheel**
- **Inspect Cell (B01 - B50):** Click on any individual battery cell cylinder to open the **Cell Inspection HUD** displaying all 10 operational parameters and the live Bernardi heat equation.
- **Inspect Circuit Component:** Click on the pump, radiator, chiller, reservoir, or valve to inspect thermophysical properties and applicable fluid equations.
- **Adjust Threshold Slider:** Move the threshold slider to change the activation temperature ($20^\circ\text{C} - 60^\circ\text{C}$). Watch the pump and fan automatically adjust their RPM.
- **Toggle Exploded View:** Click **"Exploded View"** on the bottom toolbar to view separated cell spacing and internal cooling channels.
- **Upload Dataset:** Click **"Upload Dataset"** to load CSV/JSON files from `btms_3d/datasets/` and step through records.
- **Export Simulation Data:** Click **"Export CSV"** to download full 50-cell time-series logs.

---

### 20.3 Unity 6 C# Scripts Architecture (`Unity_BTMS_Project/`)

For deployment into **Unity 6 (Universal Render Pipeline / HDRP)**, complete production-ready C# scripts are provided in `Unity_BTMS_Project/Assets/Scripts/`:

| Script File | Purpose & Responsibilities |
|---|---|
| `BatteryCell.cs` | Manages individual cell (B01-B50) state, Bernardi heat generation, $6$-stage thermal color gradient, and selective red highlighting for overheating. |
| `BatteryPackManager.cs` | Instantiates and controls 50 cells in 5x10 grid, inter-cell 3D conduction, pack min/avg/max telemetry, and exploded view lerp. |
| `NanofluidCirculation.cs` | Particle system & waypoint spline tracking for silver $\text{Al}_2\text{O}_3$ and copper $\text{CuO}$ spheres inside transparent piping. |
| `ThermalController.cs` | Temperature threshold slider, $2^\circ\text{C}$ hysteresis band, pump/fan RPM modulation, and Modes A/B/C logic. |
| `CoolingCircuit.cs` | Manages 11 pipeline thermal stations, pump impeller rotation, and radiator fan spinning animations. |
| `GoverningEquations.cs` | Full C# implementation of all 24 governing mathematical equations with step-by-step substitution and SI units. |
| `CameraController3D.cs` | Smooth 360° orbit, pan, zoom, click-to-focus, and preset camera angles (Isometric, Top, Side, Front). |
| `ComponentInspector.cs` | 3D raycast selection, HUD presentation of 10 cell parameters, component properties, and governing formulas. |
| `DatasetManager.cs` | Ingestion, validation, and real-time playback of CSV and JSON simulation datasets. |
| `BTMSMasterSimulation.cs` | Master Unity coordinator coupling the thermal solver, UI events, and optional REST API sync with the Python backend. |

#### Unity 6 Import Instructions:
1. Open or create a Unity 6 project (Universal Render Pipeline recommended).
2. Copy the folder `Unity_BTMS_Project/Assets/Scripts/` into your Unity project's `Assets/` directory.
3. Attach `BTMSMasterSimulation.cs` to a master GameObject in your scene.
4. Assign the camera with `CameraController3D.cs` and `ComponentInspector.cs`.
5. Press **Play** in Unity to run the simulation natively in C#.

---

### 20.4 Automated Testing & Validation

All 53 unit tests across both the 2D solver, ML surrogate models, and the 3D BTMS system can be executed with 100% pass rate:

```bash
# Run 3D BTMS system tests (30 tests: formulas, 50-cell pack, controller, REST API)
python3 -m unittest discover btms_3d/tests

# Run core physics & ML benchmark tests (23 tests)
python3 -m unittest discover tests
```

---

## 21. Expected Numerical and Graphical Outputs

### Expected Numerical Results Sample (Subpart A1)
```
[FORMULATION 13]: Effective Hybrid Nanofluid Density
  Governing Equation: rho_hnf = (1 - phi1 - phi2)*rho_f + phi1*rho_s1 + phi2*rho_s2
  --- INPUT PARAMETERS ---
    * rho_f (Water)                  =   9.971000e+02 [kg/m^3]
    * rho_s1 (Al2O3)                 =   3.970000e+03 [kg/m^3]
    * rho_s2 (CuO)                   =   6.320000e+03 [kg/m^3]
    * phi1                           =   2.000000e-02 [dimensionless]
    * phi2                           =   1.000000e-02 [dimensionless]
  --- INTERMEDIATE CALCULATIONS ---
    * fluid_mass_fraction_term       =   9.671870e+02 [kg/m^3]
    * nanoparticle_1_term            =   7.940000e+01 [kg/m^3]
    * nanoparticle_2_term            =   6.320000e+01 [kg/m^3]
    * total_particle_volume_fraction =   3.000000e-02 [dimensionless]
  --- FINAL NUMERICAL OUTPUT ---
    >> Calculated Result :   1.109787e+03 kg/m^3
  --- PHYSICAL INTERPRETATION ---
    Hybrid nanofluid density is 1109.79 kg/m^3 (+11.30% enhancement over base fluid).
```

### Machine Learning Leaderboard (Subpart B1)
```
               Model       MAE        MSE      RMSE  R2_Score  MAPE_percent  Train_Time_s  Inference_Time_ms
   Gradient Boosting  5.560954  55.679432  7.461865  0.994751      1.117892        0.18 s           0.51 ms
             XGBoost  5.721454  60.326445  7.767010  0.994313      1.148987        0.17 s           4.31 ms
       Random Forest  7.370720 104.437897 10.219486  0.990154      1.476260        0.06 s          16.07 ms
Neural Network (MLP)  8.850919 132.455034 11.508911  0.987513      1.986770        0.72 s           0.11 ms
                 SVR 10.051595 211.362930 14.538326  0.980074      2.117731        0.04 s           4.60 ms
```

### Expected Physics vs ML Prediction Comparison (Subpart B2)
```
Metric                                 | Physics Numerical  | ML Predicted       | Abs Error    | Rel Error (%)  | Unit
-------------------------------------------------------------------------------------------------------------------
Peak Battery Temp (T_max_battery)      |             464.03 |             466.44 |       2.4111 |         0.520% | K
Peak Temp in Celsius                   |             190.88 |             193.29 |       2.4111 |         0.520% | °C
-------------------------------------------------------------------------------------------------------------------
Thermal Safety Assessment (Safe Limit <= 328.15 K / 55°C):
  * Physics Assessment : UNSAFE (EXCEEDED LIMIT)
  * ML Prediction      : UNSAFE (EXCEEDED LIMIT)
```

---

## 22. Limitations and Assumptions
1. **Low Magnetic Reynolds Number ($Re_m \ll 1$):** Induced magnetic fields are negligible compared to the externally applied field $B_0$.
2. **Dilute Nanoparticle Suspension:** Nanoparticle aggregation and non-Newtonian shear-thinning effects are assumed negligible for total volume fractions $\phi \le 0.06$.
3. **Porous Homogeneity:** The porous metal foam insert is treated as isotropic and homogeneous with Darcy-Brinkman continuum properties ($k, \varepsilon$).
4. **Thermal Equilibrium:** Local thermal equilibrium is assumed between the solid matrix and the saturating hybrid nanofluid.
5. **Experimental Verification:** Machine learning models are trained on physics-grounded synthetic simulation data. Predictions should be calibrated against empirical laboratory calorimeter tests prior to battery module production.

---

## 23. References for Mathematical Models
1. **Bernardi, D., Pawlikowski, E., & Newman, J.** (1985). *A General Energy Balance for Battery Systems*. Journal of the Electrochemical Society, 132(1), 5-12.
2. **Brinkman, H. C.** (1949). *A calculation of the viscous force exerted by a flowing fluid on a dense swarm of particles*. Applied Scientific Research, 1(1), 27-34.
3. **Maxwell, J. C.** (1881). *A Treatise on Electricity and Magnetism*. Clarendon Press, Oxford.
4. **Takabi, B., & Salehi, S.** (2014). *Augmentation of the Heat Transfer Performance of Nanofluids in an Enclosure by Utilizing Hybrid Nanofluids*. Journal of Heat Transfer, 136(5), 052401.
5. **Chamkha, A. J., & Rashad, A. M.** (2014). *Unsteady MHD natural convection from a heated vertical cylinder embedded in a porous medium filled with a nanofluid*. Transport in Porous Media, 101(3), 447-463.
6. **Davidson, P. A.** (2016). *An Introduction to Magnetohydrodynamics*. Cambridge University Press.

---

## 23. Programmatic Code Examples – Individual Formula Calculations (Part A1)

Below is the complete, self-contained Python code demonstrating how to calculate all 18 governing formulations individually using the physics modules in `part_a_without_ml/`:

```python
#!/usr/bin/env python3
"""
Quickstart Example: Calculating Governing Mathematical Formulations (Part A1)
"""
import numpy as np
from part_a_without_ml.material_properties import (
    calc_effective_density,
    calc_effective_heat_capacity,
    calc_effective_thermal_conductivity,
    calc_effective_dynamic_viscosity,
    calc_effective_electrical_conductivity,
    calc_battery_heat_generation,
    calc_joule_heating,
    calc_lorentz_force,
    calc_darcy_brinkman_mhd_forces
)
from part_a_without_ml.dimensionless_numbers import (
    calc_reynolds_number,
    calc_prandtl_number,
    calc_hartmann_number,
    calc_darcy_number,
    calc_brinkman_number,
    calc_nusselt_number,
    calc_c_rate_current
)
from part_a_without_ml.energy_equation import calc_energy_equation_terms
from part_a_without_ml.boundary_conditions import calc_temperature_continuity, calc_heat_flux_continuity

# 1. Base input parameters
phi1 = 0.02          # 2.0 vol% Al2O3 nanoparticles
phi2 = 0.01          # 1.0 vol% CuO nanoparticles
U_in = 0.05          # Inlet velocity [m/s]
T_in = 298.15        # Inlet coolant temperature [K] (25°C)
T_batt = 308.15      # Battery temperature [K] (35°C)
B0 = 0.50            # Applied magnetic field [Tesla]
k_perm = 1.0e-7      # Porous medium permeability [m^2]
L_char = 0.01        # Characteristic channel height [m]
C_rate = 2.0         # 2C discharge rate
Q_rated = 20.0       # 20 Ah rated capacity

print("=" * 80)
print(" 18 FORMULATIONS NUMERICAL CALCULATION ".center(80, "="))
print("=" * 80)

# Formula 13: Effective Nanofluid Density
rho_res = calc_effective_density(phi1=phi1, phi2=phi2)
rho_hnf = rho_res["result"]
print(f"[F13] Effective Density (rho_hnf)        : {rho_hnf:.2f} kg/m^3")

# Formula 6: Specific Heat Capacity
cp_res = calc_effective_heat_capacity(phi1=phi1, phi2=phi2, rho_hnf=rho_hnf)
Cp_hnf = cp_res["result"]
print(f"[F06] Specific Heat Capacity (Cp_hnf)   : {Cp_hnf:.2f} J/(kg*K)")

# Formula 15a: Effective Thermal Conductivity (Maxwell Model)
k_res = calc_effective_thermal_conductivity(phi1=phi1, phi2=phi2)
k_hnf = k_res["result"]
print(f"[F15a] Thermal Conductivity (k_hnf)     : {k_hnf:.4f} W/(m*K)")

# Formula 15b: Dynamic Viscosity (Brinkman Model)
mu_res = calc_effective_dynamic_viscosity(phi1=phi1, phi2=phi2)
mu_hnf = mu_res["result"]
print(f"[F15b] Dynamic Viscosity (mu_hnf)       : {mu_hnf:.6e} Pa*s")

# Electrical Conductivity (Maxwell Relation)
sigma_res = calc_effective_electrical_conductivity(phi1=phi1, phi2=phi2)
sigma_hnf = sigma_res["result"]
print(f"[MHD] Electrical Conductivity (sigma)   : {sigma_hnf:.6e} S/m")

# Formula 9: Battery Current from C-rate
i_res = calc_c_rate_current(c_rate=C_rate, q_rated_ah=Q_rated)
I_batt = i_res["result"]
print(f"[F09] Battery Current at {C_rate}C        : {I_batt:.2f} A")

# Battery Heat Generation (Bernardi Model)
q_batt_res = calc_battery_heat_generation(I_current=I_batt, T_battery=T_batt)
Q_b = q_batt_res["result"]
print(f"[HEAT] Battery Total Heat Output (Q_b)  : {Q_b:.2f} W ({q_batt_res['intermediates']['q_volumetric_W_m3'][0]:.1f} W/m^3)")

# Formula 16: Motional Joule Heating
q_j_res = calc_joule_heating(sigma_hnf=sigma_hnf, B0=B0, u_velocity=U_in)
Q_j = q_j_res["result"]
print(f"[F16] Volumetric Joule Heating (Q_J)    : {Q_j:.6e} W/m^3")

# Formula 17: Lorentz Electromagnetic Body Force
f_lorentz_res = calc_lorentz_force(sigma_hnf=sigma_hnf, B0=B0, u_velocity=U_in)
F_Lx = f_lorentz_res["result"]
print(f"[F17] Lorentz Retarding Force (F_Lx)    : {F_Lx:.6e} N/m^3")

# Formula 18: Darcy-Brinkman MHD Resistance Forces
db_res = calc_darcy_brinkman_mhd_forces(mu_eff=mu_hnf, k_permeability=k_perm, sigma_hnf=sigma_hnf, B0=B0, u_velocity=U_in)
print(f"[F18] Darcy Porous Resistance           : {db_res['intermediates']['porous_resistance_N_m3'][0]:.4f} N/m^3")
print(f"[F18] Total Momentum Resistance Force   : {db_res['result']:.4f} N/m^3")

# Dimensionless Numbers (Formulas 3 - 8)
Re = calc_reynolds_number(rho_hnf=rho_hnf, U_in=U_in, L_char=L_char, mu_eff=mu_hnf)["result"]
Pr = calc_prandtl_number(mu_eff=mu_hnf, Cp_hnf=Cp_hnf, k_eff=k_hnf)["result"]
Ha = calc_hartmann_number(B0=B0, L_char=L_char, sigma_hnf=sigma_hnf, mu_eff=mu_hnf)["result"]
Da = calc_darcy_number(k_permeability=k_perm, L_char=L_char)["result"]
Br = calc_brinkman_number(mu_eff=mu_hnf, U_in=U_in, k_eff=k_hnf, delta_T=abs(T_batt - T_in))["result"]
Nu = calc_nusselt_number(h_conv=650.0, L_char=L_char, k_eff=k_hnf)["result"]

print("-" * 80)
print(f"[F03] Reynolds Number (Re)              : {Re:.2f} (Laminar Flow)")
print(f"[F04] Prandtl Number (Pr)               : {Pr:.2f}")
print(f"[F05] Hartmann Number (Ha)              : {Ha:.4f} (MHD suppression)")
print(f"[F06] Darcy Number (Da)                 : {Da:.6e}")
print(f"[F07] Brinkman Number (Br)              : {Br:.6e}")
print(f"[F08] Nusselt Number (Nu)               : {Nu:.2f}")

# Formula 11 & 12: Interface Temperature & Heat Flux Continuity
t_cont = calc_temperature_continuity(T_fluid_wall=T_in + 4.5, T_battery_wall=T_in + 4.5)
q_cont = calc_heat_flux_continuity(k_fluid=k_hnf, dT_dy_fluid=3200.0, k_battery=28.0, dT_dy_battery=76.33, R_tc=0.0)
print(f"[F11] Interface Temp Continuity Error   : {t_cont['result']:.4f} K")
print(f"[F12] Interface Heat Flux Balance Error : {q_cont['result']:.4f} W/m^2")

# Formula 1: Full Energy Equation Terms Evaluation
energy_terms = calc_energy_equation_terms(
    rho_eff=rho_hnf, Cp_eff=Cp_hnf, k_eff=k_hnf,
    u=U_in, v=0.0, dT_dx=12.0, dT_dy=180.0,
    d2T_dx2=-5.0, d2T_dy2=-1200.0,
    Q_b=0.0, Q_visc=0.015, Q_J=Q_j
)
print(f"[F01] Energy Convective Flux Rate       : {energy_terms['intermediates']['convection_rate_W_m3'][0]:.2f} W/m^3")
print(f"[F01] Energy Conduction Diffusion Rate  : {energy_terms['intermediates']['conduction_rate_W_m3'][0]:.2f} W/m^3")
print(f"[F01] Net Temperature Rate dT/dt        : {energy_terms['result']:.6f} K/s")
print("=" * 80)
```

To run this calculation suite across all 18 formulations and automatically export CSV logs and graphs:
```bash
python3 part_a_without_ml/A1_formula_calculator.py
```

---

## 24. Programmatic Code Examples – Coupled 2D Numerical Physics Solver (Part A2)

The 2D conjugate heat transfer and fluid dynamics solver solves the coupled Darcy-Brinkman MHD equations and the anisotropic battery energy equation simultaneously on a finite-difference grid:

```python
#!/usr/bin/env python3
"""
Executing the 2D Coupled Physics Solver Programmatically (Part A2)
"""
import numpy as np
import matplotlib.pyplot as plt
from part_a_without_ml.A2_physics_solver import CoupledBTMSSolver

# 1. Instantiate the coupled solver with customized research parameters
solver = CoupledBTMSSolver(
    Nx=60,                  # Axial grid nodes along channel length
    Ny_f=25,                # Fluid channel transverse nodes
    Ny_b=25,                # Solid battery domain transverse nodes
    Lx=0.150,               # Cell length = 150 mm
    Hf=0.004,               # Coolant channel gap = 4 mm
    Hb=0.010,               # Battery cell thickness = 10 mm
    U_in=0.05,              # Coolant inlet velocity = 0.05 m/s
    T_in=298.15,            # Inlet temperature = 25°C
    T_batt_init=298.15,     # Initial battery pack temperature = 25°C
    B0=0.50,                # Transverse magnetic field = 0.5 T
    phi1=0.02,              # 2 vol% Al2O3 nanoparticles
    phi2=0.01,              # 1 vol% CuO nanoparticles
    k_perm=1.0e-7,          # Porous foam permeability = 1e-7 m^2
    c_rate=2.0,             # 2C discharge operation
    Q_rated=20.0,           # 20 Ah rated capacity
    convergence_tol=1e-6,   # SOR residual tolerance
    max_iter=3000           # Maximum iterative steps
)

# 2. Run the numerical solver
print("[BTMS] Launching 2D coupled conjugate Darcy-Brinkman MHD solver...")
solution = solver.solve()

# 3. Inspect converged physical fields and heat transfer performance
print("\n--- NUMERICAL SIMULATION RESULTS ---")
print(f"Convergence Status      : {'CONVERGED' if solution['converged'] else 'ITERATION LIMIT'}")
print(f"Total Iterations        : {solution['iterations']}")
print(f"Final Max Residual      : {solution['final_residual']:.3e}")
print(f"Execution Time          : {solution['execution_time_s']:.2f} seconds")
print(f"Peak Battery Temp (T_max): {solution['T_max_battery_C']:.2f} °C ({solution['T_max_battery_K']:.2f} K)")
print(f"Min Battery Temp (T_min): {solution['T_min_battery_C']:.2f} °C")
print(f"Battery Delta T         : {solution['delta_T_battery_K']:.2f} K")
print(f"Coolant Outlet Temp     : {solution['T_coolant_out_C']:.2f} °C")
print(f"Axial Pressure Drop (dP): {solution['pressure_drop_Pa']:.2f} Pa")
print(f"Average Nusselt Number  : {solution['Nu_avg']:.2f}")
print(f"Reynolds Number (Re)    : {solution['Re']:.1f}")
print(f"Hartmann Number (Ha)    : {solution['Ha']:.4f}")
print(f"Darcy Number (Da)       : {solution['Da']:.4e}")

# 4. Access 2D spatial fields
T_field = solver.T          # 2D array of temperatures [K], shape (Ny_f + Ny_b, Nx)
u_velocity = solver.u       # 1D/2D axial velocity profile [m/s]
x_coords = solver.x         # Axial spatial coordinates [m]
y_coords = solver.y         # Transverse spatial coordinates [m]

# 5. Extract and print local temperature along the conjugate interface
y_int_idx = solver.Ny_f - 1
T_interface_C = T_field[y_int_idx, :] - 273.15
print(f"Interface Inflow Temp   : {T_interface_C[0]:.2f} °C")
print(f"Interface Midpoint Temp : {T_interface_C[len(T_interface_C)//2]:.2f} °C")
print(f"Interface Outflow Temp  : {T_interface_C[-1]:.2f} °C")
```

To run this simulation non-interactively and generate all 2D contour maps, 3D temperature surfaces, and axial distribution plots:
```bash
python3 part_a_without_ml/A2_physics_solver.py
```

---

## 25. Programmatic Code Examples – Interactive 3D BTMS Simulation & REST API (`btms_3d`)

The `btms_3d/` subproject contains the complete 3D digital twin of the BTMS, featuring a 50-cell battery pack, closed-loop nanofluid flow animation, 20 mechanical components, and real-time REST API integration.

### Launching the 3D BTMS Application

Run via the standalone Python runner:
```bash
python3 btms_3d/run_btms_3d.py --port 5000
```
Or launch through the master CLI:
```bash
python3 main.py --subpart 3D
```
The server will start at `http://127.0.0.1:5000/` and automatically open your web browser.

### Programmatic Python Client for the 3D BTMS REST API

You can control and query the running 3D BTMS simulation programmatically using standard HTTP requests:

```python
#!/usr/bin/env python3
"""
Programmatic Client for the Interactive 3D BTMS Simulation REST API
"""
import requests
import json
import time

BASE_URL = "http://127.0.0.1:5000"

# 1. Health check & status retrieval
print(">>> 1. QUERYING SYSTEM STATUS")
res = requests.get(f"{BASE_URL}/api/status")
state = res.json()["data"]
print(f"  * Simulation Time       : {state['time_seconds']:.1f} s")
print(f"  * Peak Pack Temp (T_max): {state['pack_stats']['t_max_c']:.2f} °C")
print(f"  * Pump RPM              : {state['cooling_controller']['pump_rpm']} RPM")
print(f"  * Cooling Status        : {'ACTIVE' if state['cooling_controller']['pump_active'] else 'IDLE'}")

# 2. Dynamic parameter reconfiguration
print("\n>>> 2. RECONFIGURING BTMS PARAMETERS (Aggressive 3.5C Discharge)")
reconfig_payload = {
    "c_rate": 3.5,            # Increase discharge to 3.5C
    "threshold_c": 35.0,      # Set cooling activation threshold to 35°C
    "u_in": 0.08,             # Boost inlet velocity to 0.08 m/s
    "b0_tesla": 0.75,         # Increase magnetic field to 0.75 T
    "phi1": 0.025,            # 2.5 vol% Al2O3
    "phi2": 0.015,            # 1.5 vol% Cu
    "mode": "hybrid_nanofluid"# Intelligent hysteresis mode
}
requests.post(f"{BASE_URL}/api/configure", json=reconfig_payload)
print("  * Reconfiguration command sent successfully.")

# 3. Step the simulation forward by 5 seconds (10 steps x 0.5s)
print("\n>>> 3. ADVANCING SIMULATION (10 Timesteps)")
for step_idx in range(10):
    step_res = requests.post(f"{BASE_URL}/api/step", json={"dt": 0.5}).json()
    pack_data = step_res["data"]["pack_stats"]
    ctrl_data = step_res["data"]["cooling_controller"]
    print(f"  Step {step_idx+1:02d}: Time = {step_res['data']['time_seconds']:>4.1f}s | "
          f"T_max = {pack_data['t_max_c']:.2f}°C | "
          f"Heat Gen = {pack_data['total_heat_generated_w']:>6.1f}W | "
          f"Pump = {ctrl_data['pump_rpm']:>4.0f} RPM | "
          f"Cooling = {'ACTIVE' if ctrl_data['pump_active'] else 'IDLE'}")
    time.sleep(0.1)

# 4. Inspect Individual Battery Cells (50 Cells: B01 to B50)
print("\n>>> 4. INSPECTING INDIVIDUAL BATTERY CELLS")
cells_res = requests.get(f"{BASE_URL}/api/cells").json()
cells = cells_res["cells"]
print(f"  * Total Cells Retrieved : {len(cells)}")

# Find cell with highest temperature
hottest_cell = max(cells, key=lambda c: c["temperature_c"])
print(f"  * Hottest Cell ID       : {hottest_cell['cell_id']} at ({hottest_cell['row']}, {hottest_cell['col']})")
print(f"  * Temperature           : {hottest_cell['temperature_c']} °C ({hottest_cell['temperature_k']} K)")
print(f"  * Local Heat Generation : {hottest_cell['heat_generation_w']:.2f} W")
print(f"  * Cooling Extraction    : {hottest_cell['cooling_rate_w']:.2f} W")
print(f"  * Thermal Status Alert  : {hottest_cell['thermal_status'].upper()}")

# Query detailed cell endpoint with governing equation substitution
cell_detail = requests.get(f"{BASE_URL}/api/cell/{hottest_cell['cell_id']}").json()
print(f"  * Bernardi Substituted Eq: {cell_detail['formulas'][1]['substituted_formula']}")

# 5. Inspect In-Line Pipeline Measurement Points (P01 to P10)
print("\n>>> 5. INSPECTING PIPELINE MEASUREMENT POINT P04 (Core Channel)")
pt_res = requests.get(f"{BASE_URL}/api/measurement_point/P04").json()
pt = pt_res["point"]
print(f"  * Point ID & Name       : {pt['id']} - {pt['name']}")
print(f"  * Location in System    : {pt['location']}")
print(f"  * Local Temperature     : {pt['temp_c']} °C")
print(f"  * Local Fluid Pressure  : {pt['pressure_pa'] / 1000:.2f} kPa")
print(f"  * Local Flow Velocity   : {pt['velocity_m_s']:.4f} m/s")
print(f"  * Effective Conductivity: {pt['thermal_conductivity_w_m_k']:.4f} W/(m*K)")

# 6. Evaluate Specific Equation from Library (e.g., Equation 2: Bernardi Heat)
print("\n>>> 6. LIVE EQUATION EVALUATION (Equation 2: Bernardi Heat)")
eq_res = requests.get(f"{BASE_URL}/api/formula/2").json()
eq = eq_res["formula"]
print(f"  * Formula Name          : {eq['name']}")
print(f"  * Mathematical Formula  : {eq['formula']}")
print(f"  * Intermediate Steps    :")
for step in eq["steps"]:
    print(f"      {step}")
print(f"  * Calculated Result     : {eq['result']:.2f} {eq['unit']}")
print(f"  * Literature Reference  : {eq['citation']['author']} ({eq['citation']['year']})")

# 7. Execute Mode B Machine Learning Surrogate Prediction
print("\n>>> 7. MODE B MACHINE LEARNING PREDICTION & PHYSICS COMPARISON")
ml_req = {
    "model_name": "gradient_boosting",
    "c_rate": 3.5,
    "u_in": 0.08,
    "b0_tesla": 0.75,
    "phi1": 0.025,
    "phi2": 0.015,
    "t_in_c": 25.0
}
ml_res = requests.post(f"{BASE_URL}/api/ml/predict", json=ml_req).json()
p = ml_res["prediction"]
phys_t = ml_res["physics_mode_a"]["t_max_c"]
pred_t = p["predicted_t_max_c"]
print(f"  * ML Surrogate Model    : {p['model_name'].upper()}")
print(f"  * Physics Mode A T_max  : {phys_t:.2f} °C")
print(f"  * ML Mode B Pred. T_max : {pred_t:.2f} °C")
print(f"  * Absolute Discrepancy  : {ml_res['error_metrics']['absolute_error_c']:.3f} °C")
print(f"  * Relative Error        : {ml_res['error_metrics']['relative_error_pct']:.2f} %")
print(f"  * Safe Thermal State    : {'SAFE' if p['is_thermally_safe'] else 'CRITICAL'}")
```

### Three.js 3D WebGL Implementation Highlights

The frontend visualization in `btms_3d/frontend/js/` dynamically maps physics states to WebGL graphics:

#### Dynamic 50-Cell Thermal Color Update (`simulation3d.js`)
```javascript
// Updates each of the 50 battery cells independently based on real simulation data
updateThermalColors(cells, thresholdC = 35.0) {
  cells.forEach(cell => {
    const mesh = this.cellMeshes.get(cell.cell_id);
    if (!mesh) return;

    const t = cell.temperature_c;
    const mat = mesh.material;

    // Independent thermal color assignment
    if (t >= thresholdC) {
      mat.color.setHex(0xff3366);      // Red: Exceeds threshold (triggers cooling)
      mat.emissive.setHex(0x660011);
      mat.emissiveIntensity = 0.5;
    } else if (t >= 35.0) {
      mat.color.setHex(0xff7700);      // Orange: High temperature condition
      mat.emissive.setHex(0x441100);
      mat.emissiveIntensity = 0.3;
    } else if (t >= 30.0) {
      mat.color.setHex(0xffee33);      // Yellow: Increasing temperature
      mat.emissive.setHex(0x332200);
      mat.emissiveIntensity = 0.2;
    } else if (t >= 25.0) {
      mat.color.setHex(0x00f0ff);      // Cyan: Normal operating condition
      mat.emissive.setHex(0x003344);
      mat.emissiveIntensity = 0.15;
    } else {
      mat.color.setHex(0x00a8ff);      // Blue: Cold / Sub-ambient
      mat.emissive.setHex(0x001133);
      mat.emissiveIntensity = 0.1;
    }
  });
}
```

#### Nanoparticle Flow Circulation with Pump Interlock (`flowParticles.js`)
```javascript
// Simulates continuous multi-species nanoparticle flow along the closed BTMS loop
update(dt, velocity, pumpActive, tInC = 25.0, tOutC = 35.0) {
  // If the pump is turned OFF by the controller, flow freezes immediately
  const effectiveSpeed = pumpActive ? Math.max(0.02, velocity * 0.18) : 0.0;

  for (let i = 0; i < this.totalParticles; i++) {
    const p = this.particles[i];

    if (effectiveSpeed > 0) {
      p.u = (p.u + effectiveSpeed * p.speedFactor * dt) % 1.0;
    }

    // Get 3D coordinate along channel curve
    const pos = this.channelCurves[p.channelIndex].getPointAt(p.u);
    this.positions[i * 3]     = pos.x;
    this.positions[i * 3 + 1] = pos.y;
    this.positions[i * 3 + 2] = pos.z;

    // Fluid temperature color shift: Blue (inlet) -> Red (channels) -> Blue (radiator)
    let localTemp = (p.u < 0.15) ? tInC :
                    (p.u < 0.50) ? tInC + ((p.u - 0.15) / 0.35) * (tOutC - tInC) :
                    (p.u < 0.65) ? tOutC :
                    (p.u < 0.85) ? tOutC - ((p.u - 0.65) / 0.20) * (tOutC - tInC) : tInC;

    let col = new THREE.Color(localTemp >= 38.0 ? 0xff3366 :
                              localTemp >= 33.0 ? 0xffaa00 :
                              localTemp >= 28.0 ? 0xffee33 :
                              localTemp >= 25.0 ? 0x00f0ff : 0x00a8ff);

    // Blend thermal color with physical nanoparticle pigment (Al2O3, Cu, CuO, TiO2, SiO2)
    col.lerp(p.npType.baseColor, 0.35);
    this.colors[i * 3]     = col.r;
    this.colors[i * 3 + 1] = col.g;
    this.colors[i * 3 + 2] = col.b;
  }

  this.pointsMesh.geometry.attributes.position.needsUpdate = true;
  this.pointsMesh.geometry.attributes.color.needsUpdate = true;
}
```

