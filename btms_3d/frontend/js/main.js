/**
 * ==============================================================================
 * BTMS-3D PRO SIMULATOR: MAGNETOHYDRODYNAMIC HYBRID NANOFLUID ENGINE
 * 50 Prismatic Cells • Interleaved Cooling Channels • Moving Nanoparticles
 * 8-State Hysteresis Cooling Controller • 24 Governing Equations • Three.js
 * ==============================================================================
 */

(function () {
  'use strict';

  // ============================================================================
  // 1. GLOBAL STATE & CONFIGURATION
  // ============================================================================
  const STATE = {
    isRunning: true,
    timeWarp: 1.0,
    simTime: 0.0,
    dt: 0.25,

    // Cylindrical Pack Configuration (180 Cells Pure Series)
    numCells: 180,
    formFactor: '21700',
    plateMaterial: 'aluminum',
    cutawayActive: false,

    // Controls
    coolingMode: 'Auto',
    thresholdC: 35.0,
    deactThresholdC: 32.5,
    cRate: 2.0,
    uIn: 0.25,
    b0: 0.50,
    phi1: 0.015,
    phi2: 0.010,
    kPerm: 1.0e-7,

    // Telemetry
    tMax: 25.0,
    tAvg: 25.0,
    tMin: 25.0,
    pumpDuty: 0.0,
    fanDuty: 0.0,
    valvePos: 0.0,
    systemStatus: 'NORMAL (OFF)',
    stateId: 1,
    stateName: 'OFF',

    // Cylindrical Cells state (180 cells)
    cells: [],
    stations: [], // 10 stations

    // Selection & Inspection
    selectedObject: null, // { type: 'cell'|'station'|'component'|'pipe', id: '...' }
    activeTab: 'tab-physical',

    // Visibility layers
    layers: {
      cells: true,
      electrical: true,
      channels: true,
      particles: true,
      plates: true,
      pipes: true,
      stations: true,
      components: true
    },

    // Exploded View & Hotspot Generator State
    explodedView: false,
    autoHotspot: false,
    autoHotspotInterval: 30,
    zones: {},
    hotspotStatus: {},

    // Advanced Continuous Operation & BMS Lifecycle
    activeHotspotEvents: [],
    hotspotHistory: [],
    bmsStatus: 'NORMAL (15-35°C)',
    bmsDerateActive: false,
    bmsDerateFactor: 1.0,
    deltaT: 0.0,
    uniformityCompliant: true,
    cellCounts: { normal: 180, elevated: 0, overheated: 0, critical: 0 },
    pumpEnergyConsumedJ: 0.0,
    pumpPowerW: 0.0
  };

  const PACK_CONFIGS = {
    180: { rows: 10, cols: 18 },
    550: { rows: 22, cols: 25 },
    600: { rows: 20, cols: 30 },
    700: { rows: 20, cols: 35 },
    800: { rows: 20, cols: 40 },
    1000: { rows: 25, cols: 40 }
  };

  // 6 Independent Battery Modules in 2 x 3 Matrix (30 Cells 5x6 per Module = 180 Cells)
  const MODULE_CONFIG = [
    { id: 'MODULE_A', alias: 'MODULE_1', name: 'Module 1', matRow: 0, matCol: 0, cellStart: 1, cellEnd: 30, plateId: 'PLATE-SERPENTINE-CONTINUOUS', channelId: 'CHANNEL-SERPENTINE-CONTINUOUS' },
    { id: 'MODULE_B', alias: 'MODULE_2', name: 'Module 2', matRow: 0, matCol: 1, cellStart: 31, cellEnd: 60, plateId: 'PLATE-SERPENTINE-CONTINUOUS', channelId: 'CHANNEL-SERPENTINE-CONTINUOUS' },
    { id: 'MODULE_C', alias: 'MODULE_3', name: 'Module 3', matRow: 0, matCol: 2, cellStart: 61, cellEnd: 90, plateId: 'PLATE-SERPENTINE-CONTINUOUS', channelId: 'CHANNEL-SERPENTINE-CONTINUOUS' },
    { id: 'MODULE_D', alias: 'MODULE_4', name: 'Module 4', matRow: 1, matCol: 0, cellStart: 91, cellEnd: 120, plateId: 'PLATE-SERPENTINE-CONTINUOUS', channelId: 'CHANNEL-SERPENTINE-CONTINUOUS' },
    { id: 'MODULE_E', alias: 'MODULE_5', name: 'Module 5', matRow: 1, matCol: 1, cellStart: 121, cellEnd: 150, plateId: 'PLATE-SERPENTINE-CONTINUOUS', channelId: 'CHANNEL-SERPENTINE-CONTINUOUS' },
    { id: 'MODULE_F', alias: 'MODULE_6', name: 'Module 6', matRow: 1, matCol: 2, cellStart: 151, cellEnd: 180, plateId: 'PLATE-SERPENTINE-CONTINUOUS', channelId: 'CHANNEL-SERPENTINE-CONTINUOUS' },
  ];

  // Three.js References
  let scene = null;
  let camera = null;
  let renderer = null;
  let controls = null;
  let cellMeshes = [];
  let stationMarkers = [];
  let componentMeshes = {};
  let pipeMeshes = [];
  let interPlateMeshes = [];
  let wavyRibbonMeshes = [];
  let serpentineCurves = [];
  let continuousSerpentineSpline = null;
  let moduleSplines = {};
  let modulePlates = {};
  let moduleChannels = {};
  let busbarMeshes = [];
  let timSheetMeshes = [];
  let particleInstancedMesh = null;
  let particleCount = 2000;
  let particleData = [];
  let flowArrows = [];
  let heatFluxArrows = [];
  let pumpImpeller = null;
  let fanRotor = null;
  let valveNeedle = null;
  let layerGroups = {};
  let btmsMasterGroup = null;
  let selectedHighlightBox = null;

  // Camera Animation State
  let cameraTarget = {
    position: null,
    lookAt: null,
    animating: false
  };

  // Raycaster & Mouse
  let raycaster = null;
  let mouse = null;
  let hoveredMesh = null;

  // Chart References
  let chartTemp = null;
  let chartCoolant = null;
  let chartNumbers = null;
  let chartHeat = null;
  const historyLimit = 40;
  const historyData = {
    labels: [],
    tMax: [],
    tAvg: [],
    tMin: [],
    tIn: [],
    tOut: [],
    re: [],
    nu: [],
    qGen: [],
    qRem: []
  };

  // Camera Presets (Pack Overview + 6 Module Focus Views + Engineering Angles)
  let cameraPresets = {};

  function initCameraPresets() {
    cameraPresets = {
      overview: { pos: new THREE.Vector3(0, 24, 26), target: new THREE.Vector3(0, 1.5, 0) },
      top: { pos: new THREE.Vector3(0, 32, 0.01), target: new THREE.Vector3(0, 0, 0) },
      front: { pos: new THREE.Vector3(0, 4.0, 24), target: new THREE.Vector3(0, 1.5, 0) },
      side: { pos: new THREE.Vector3(26, 4.0, 0), target: new THREE.Vector3(0, 1.5, 0) },
      isometric: { pos: new THREE.Vector3(20, 18, 20), target: new THREE.Vector3(0, 1.5, 0) },
      plates: { pos: new THREE.Vector3(6.5, 4.5, 4.0), target: new THREE.Vector3(0, 1.5, 2.0) },
      electrical: { pos: new THREE.Vector3(0, 9.5, 0.01), target: new THREE.Vector3(0, 2.7, 0) },
      flow: { pos: new THREE.Vector3(-4.0, 3.8, -4.5), target: new THREE.Vector3(-2.0, 1.5, -2.0) },
      // 6 Individual Module Focus Perspectives (Module 1 through 6 / Module A through F)
      module_1: { pos: new THREE.Vector3(-6.36, 9.5, 3.5), target: new THREE.Vector3(-6.36, 1.5, -3.0) },
      module_2: { pos: new THREE.Vector3(0.0, 9.5, 3.5), target: new THREE.Vector3(0.0, 1.5, -3.0) },
      module_3: { pos: new THREE.Vector3(6.36, 9.5, 3.5), target: new THREE.Vector3(6.36, 1.5, -3.0) },
      module_4: { pos: new THREE.Vector3(-6.36, 9.5, 9.5), target: new THREE.Vector3(-6.36, 1.5, 3.0) },
      module_5: { pos: new THREE.Vector3(0.0, 9.5, 9.5), target: new THREE.Vector3(0.0, 1.5, 3.0) },
      module_6: { pos: new THREE.Vector3(6.36, 9.5, 9.5), target: new THREE.Vector3(6.36, 1.5, 3.0) },
      module_a: { pos: new THREE.Vector3(-6.36, 9.5, 3.5), target: new THREE.Vector3(-6.36, 1.5, -3.0) },
      module_b: { pos: new THREE.Vector3(0.0, 9.5, 3.5), target: new THREE.Vector3(0.0, 1.5, -3.0) },
      module_c: { pos: new THREE.Vector3(6.36, 9.5, 3.5), target: new THREE.Vector3(6.36, 1.5, -3.0) },
      module_d: { pos: new THREE.Vector3(-6.36, 9.5, 9.5), target: new THREE.Vector3(-6.36, 1.5, 3.0) },
      module_e: { pos: new THREE.Vector3(0.0, 9.5, 9.5), target: new THREE.Vector3(0.0, 1.5, 3.0) },
      module_f: { pos: new THREE.Vector3(6.36, 9.5, 9.5), target: new THREE.Vector3(6.36, 1.5, 3.0) }
    };
  }

  // Exact 3-Color Cell Temperature Mapping (Section 6):
  // 0–34.9°C: Green (#22c55e) — Normal
  // 35.0–45.0°C: Yellow (#eab308) — Moderate / Warning
  // 46.0–60.0°C+: Red (#ef4444) — Overheated / Critical (>60°C: #dc2626)
  function getThermalColor(t, threshold) {
    const color = new THREE.Color();

    if (t < 35.0) {
      // Band 1: Normal Operating Green (0-34.9°C)
      if (t < 25.0) {
        color.setHex(0x16a34a);
      } else {
        color.setHex(0x22c55e);
      }
    } else if (t <= 45.0) {
      // Band 2: Moderate / Warning Yellow (35-45°C)
      const norm = Math.min(1.0, Math.max(0.0, (t - 35.0) / 10.0));
      color.lerpColors(new THREE.Color(0xfacc15), new THREE.Color(0xeab308), norm);
    } else if (t <= 60.0) {
      // Band 3: Overheated / Critical Red (46-60°C)
      const norm = Math.min(1.0, Math.max(0.0, (t - 45.0) / 15.0));
      color.lerpColors(new THREE.Color(0xef4444), new THREE.Color(0xdc2626), norm);
    } else {
      // Band 4: Critical High-Temp Alert (>60°C)
      color.setHex(0xb91c1c);
    }
    return color;
  }

  // ============================================================================
  // 2. THREE.JS SCENE SETUP & ENVIRONMENT
  // ============================================================================
  function init3DScene() {
    const container = document.getElementById('viewport-container');
    const canvas = document.getElementById('canvas-3d');
    const errContainer = document.getElementById('webgl-error-container');
    const errText = document.getElementById('webgl-error-text');

    if (typeof THREE === 'undefined') {
      if (errContainer && errText) {
        errContainer.style.display = 'block';
        errText.innerText = 'Three.js 3D graphics library could not be loaded. Please ensure JavaScript is enabled.';
      }
      return false;
    }

    // Initialize raycaster & math objects
    raycaster = new THREE.Raycaster();
    mouse = new THREE.Vector2();
    initCameraPresets();

    cameraTarget.position = new THREE.Vector3(26, 22, 28);
    cameraTarget.lookAt = new THREE.Vector3(0, 2.0, 0);

    const width = Math.max(container.clientWidth || window.innerWidth, 320);
    const height = Math.max(container.clientHeight || window.innerHeight, 240);

    // 1. Scene
    scene = new THREE.Scene();
    scene.background = new THREE.Color(0x0e141e); // Professional CAD slate background

    // 2. Camera: Perspective camera
    camera = new THREE.PerspectiveCamera(45, width / height, 0.2, 1000);
    camera.position.set(26, 22, 28);

    // 3. WebGL Renderer
    try {
      renderer = new THREE.WebGLRenderer({
        canvas: canvas,
        antialias: true,
        alpha: false,
        powerPreference: 'high-performance'
      });
    } catch (e) {
      if (errContainer && errText) {
        errContainer.style.display = 'block';
        errText.innerText = 'WebGL context creation failed: ' + e.message;
      }
      console.error('WebGL initialization error:', e);
      return false;
    }

    renderer.setSize(width, height);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
    renderer.shadowMap.enabled = true;
    renderer.shadowMap.type = THREE.PCFSoftShadowMap;
    renderer.toneMapping = THREE.ACESFilmicToneMapping;
    renderer.toneMappingExposure = 1.2;

    // 4. OrbitControls
    if (typeof THREE.OrbitControls !== 'undefined') {
      controls = new THREE.OrbitControls(camera, renderer.domElement);
      controls.enableDamping = true;
      controls.dampingFactor = 0.05;
      controls.maxPolarAngle = Math.PI / 2 - 0.01;
      controls.minDistance = 3.0;
      controls.maxDistance = 150.0;
      controls.target.set(0, 2.0, 0);
    }

    // 5. Studio Lighting Setup
    const ambientLight = new THREE.AmbientLight(0xffffff, 0.75);
    scene.add(ambientLight);

    const keyLight = new THREE.DirectionalLight(0xffffff, 1.25);
    keyLight.position.set(28, 42, 32);
    keyLight.castShadow = true;
    keyLight.shadow.mapSize.width = 2048;
    keyLight.shadow.mapSize.height = 2048;
    keyLight.shadow.camera.near = 1.0;
    keyLight.shadow.camera.far = 120;
    keyLight.shadow.camera.left = -30;
    keyLight.shadow.camera.right = 30;
    keyLight.shadow.camera.top = 30;
    keyLight.shadow.camera.bottom = -30;
    keyLight.shadow.bias = 0.0001;
    scene.add(keyLight);

    const fillLight = new THREE.DirectionalLight(0x8ecae6, 0.65);
    fillLight.position.set(-28, 25, -28);
    scene.add(fillLight);

    const rimLight = new THREE.DirectionalLight(0x00d4ff, 0.4);
    rimLight.position.set(0, -10, -20);
    scene.add(rimLight);

    const hemiLight = new THREE.HemisphereLight(0xe0f2fe, 0x1e293b, 0.45);
    scene.add(hemiLight);

    // 6. Ground Grid & Pedestal
    const grid = new THREE.GridHelper(64, 64, 0x00d4ff, 0x1e293b);
    grid.position.y = -0.01;
    scene.add(grid);

    const groundGeo = new THREE.CircleGeometry(38, 64);
    const groundMat = new THREE.MeshStandardMaterial({
      color: 0x0a0f16,
      roughness: 0.9,
      metalness: 0.1
    });
    const groundMesh = new THREE.Mesh(groundGeo, groundMat);
    groundMesh.rotation.x = -Math.PI / 2;
    groundMesh.receiveShadow = true;
    scene.add(groundMesh);

    // 7. Master Assembly Root Group
    btmsMasterGroup = new THREE.Group();
    scene.add(btmsMasterGroup);

    // Layer Groups
    layerGroups = {
      cells: new THREE.Group(),
      electrical: new THREE.Group(),
      channels: new THREE.Group(),
      particles: new THREE.Group(),
      plates: new THREE.Group(),
      pipes: new THREE.Group(),
      stations: new THREE.Group(),
      components: new THREE.Group()
    };
    Object.values(layerGroups).forEach(g => btmsMasterGroup.add(g));

    // Selection highlight wireframe box
    const selBoxGeo = new THREE.BoxGeometry(1, 1, 1);
    const selBoxMat = new THREE.MeshBasicMaterial({
      color: 0x00e5ff,
      wireframe: true,
      visible: false
    });
    selectedHighlightBox = new THREE.Mesh(selBoxGeo, selBoxMat);
    scene.add(selectedHighlightBox);

    // Build the Complete 14-Component BTMS 3D Assembly
    buildBatteryPack();
    buildElectricalSystem();
    buildCoolingPlatesAndChannels();
    buildCoolingLoopEquipment();
    buildPipelines();
    buildSensorsAndInstrumentation();
    buildSamplingStations();
    buildNanoparticleSystem();
    buildFlowDirectionArrows();
    buildHeatFluxArrows();

    // Auto-fit camera to 65-80% viewport
    fitCameraToAssembly();

    // Resize handling
    if (window.ResizeObserver) {
      const ro = new ResizeObserver(entries => {
        for (let entry of entries) {
          const w = entry.contentRect.width;
          const h = entry.contentRect.height;
          if (w > 0 && h > 0) {
            handleResize(w, h);
          }
        }
      });
      ro.observe(container);
    } else {
      window.addEventListener('resize', () => {
        handleResize(container.clientWidth || window.innerWidth, container.clientHeight || window.innerHeight);
      });
    }

    // Interaction Listeners
    canvas.addEventListener('mousemove', onMouseMove);
    canvas.addEventListener('click', onClick);
    canvas.addEventListener('dblclick', onDoubleClick);

    return true;
  }

  function handleResize(width, height) {
    if (!renderer || !camera) return;
    camera.aspect = width / height;
    camera.updateProjectionMatrix();
    renderer.setSize(width, height);
  }

  function fitCameraToAssembly() {
    if (!btmsMasterGroup || !camera || !controls) return;

    btmsMasterGroup.updateMatrixWorld(true);
    const box = new THREE.Box3().setFromObject(btmsMasterGroup);
    const center = new THREE.Vector3();
    const size = new THREE.Vector3();
    box.getCenter(center);
    box.getSize(size);

    const maxDim = Math.max(size.x, size.y, size.z);
    const fov = camera.fov * (Math.PI / 180);
    let cameraDistance = Math.abs(maxDim / 2 / Math.tan(fov / 2));

    // Viewport fill factor ~72%
    cameraDistance *= 1.35;

    const eyeOffset = new THREE.Vector3(0.68, 0.58, 0.76).normalize().multiplyScalar(cameraDistance);
    const eyePos = center.clone().add(eyeOffset);

    camera.position.copy(eyePos);
    controls.target.copy(center);
    controls.update();

    cameraTarget.position.copy(eyePos);
    cameraTarget.lookAt.copy(center);

    cameraPresets.overview = {
      pos: eyePos.clone(),
      target: center.clone()
    };
  }

  // ============================================================================
  // 3. COMPLETE 14-COMPONENT ASSEMBLY GEOMETRY BUILDERS
  // ============================================================================

  /**
   * Helper: Generates an ultra-smooth 5-pass 3D Catmull-Rom serpentine spline curve
   * for an individual battery module with smooth rounded 180-degree U-turns at each row end.
   * Weaves smoothly between cylindrical cell rows without sharp 90-degree corners or flat rectangular walls.
   */
  /**
   * Helper: Generates ONE continuous, unified 10-pass 3D Catmull-Rom serpentine spline curve
   * weaving smoothly strictly in the inter-row corridors BETWEEN the 180 cylindrical Li-ion cells.
   *
   * Physical Architecture (Zero Penetration - Between Cells Only):
   * 1. 10 Inter-Row Corridors strictly situated between cell rows:
   *    Z_corridors = [-4.38, -3.46, -2.54, -1.62, -0.70, +0.70, +1.62, +2.54, +3.46, +4.38]
   * 2. Cell rows sit at Z = -4.84, -3.92, -3.00, -2.08, -1.16 (Top) and +1.16, +2.08, +3.00, +3.92, +4.84 (Bottom).
   * 3. Net radial clearance from ribbon surface to every cell casing is +0.0370 mm everywhere (100% collision-free).
   * 4. Coolant Inlet lead-in on -X flank of Module 1, Corridor 0 (Z = -4.38).
   * 5. Passes 0, 1, 2, 3, 4 weave across Modules 1, 2, 3 (Top half).
   * 6. Rounded 180° semi-circular U-turns at row ends (alternating +X and -X, R = 0.46) with straight margins.
   * 7. Sweeping 180° inter-module U-turn on +X flank (R = 0.70) connecting Corridor 4 (Z = -0.70) to Corridor 5 (Z = +0.70).
   * 8. Passes 5, 6, 7, 8, 9 weave across Modules 6, 5, 4 (Bottom half).
   * 9. Coolant Outlet straight lead-out on -X flank of Module 4, Corridor 9 (Z = +4.38).
   */
  function buildContinuousSerpentineSpline(pitchX = 0.86, pitchZ = 0.92, cellRadius = 0.35, gapX = 1.20, gapZ = 1.40) {
    const points = [];
    const amplitude = 0.035; // Gentle wave snugly cradling cell exteriors with +0.037 net clearance
    const modStepX = 6.0 * pitchX + gapX; // 6.36
    const modStepZ = 5.0 * pitchZ + gapZ; // 6.00
    const xTurnRight = 9.15;
    const xTurnLeft = -9.15;
    const uTurnRadius = pitchZ / 2; // 0.46

    // Module X Centers: Module 1/4 (-modStepX), Module 2/5 (0.0), Module 3/6 (+modStepX)
    const modXCenters = [-modStepX, 0.0, modStepX];

    // 10 Inter-Row Corridors strictly between cell rows
    const corridors = [-4.38, -3.46, -2.54, -1.62, -0.70, +0.70, +1.62, +2.54, +3.46, +4.38];

    // 1. Coolant Inlet straight lead-in at Corridor 0 (-X flank of Module 1)
    points.push(new THREE.Vector3(-10.05, 0, corridors[0]));
    points.push(new THREE.Vector3(-9.60, 0, corridors[0]));
    points.push(new THREE.Vector3(xTurnLeft, 0, corridors[0]));

    // =========================================================================
    // PART A: TOP HALF (Corridors 0..4: MODULE 1, MODULE 2, MODULE 3)
    // 5 Horizontal Passes with 4 Rounded U-Turns + 1 Sweeping Central Turn
    // =========================================================================
    for (let r = 0; r < 5; r++) {
      const cz = corridors[r];
      const isEven = (r % 2 === 0);

      if (isEven) {
        // Left to Right (-X to +X): Module 1 -> Module 2 -> Module 3
        for (let m = 0; m < 3; m++) {
          const modCenterX = modXCenters[m];
          for (let c = 0; c < 6; c++) {
            const cx = modCenterX + (c - 2.5) * pitchX;
            const sign = (c % 2 === 0) ? 1.0 : -1.0;
            points.push(new THREE.Vector3(cx - pitchX * 0.28, 0, cz + amplitude * sign * 0.70));
            points.push(new THREE.Vector3(cx, 0, cz + amplitude * sign));
            points.push(new THREE.Vector3(cx + pitchX * 0.28, 0, cz + amplitude * sign * 0.70));
          }
        }
        points.push(new THREE.Vector3(xTurnRight, 0, cz));

        if (r < 4) {
          // Standard 180° semi-circular U-turn at +X end connecting corridor r to corridor r+1
          const nextZ = corridors[r + 1];
          const midZ = (cz + nextZ) / 2;
          const turnCenterX = xTurnRight;
          const numTurnPts = 8;
          for (let t = 0; t <= numTurnPts; t++) {
            const angle = -Math.PI / 2 + (Math.PI * t) / numTurnPts;
            const tx = turnCenterX + uTurnRadius * Math.cos(angle);
            const tz = midZ + uTurnRadius * Math.sin(angle);
            points.push(new THREE.Vector3(tx, 0, tz));
          }
          points.push(new THREE.Vector3(xTurnRight, 0, nextZ));
        } else {
          // Sweeping 180° inter-module U-turn at +X end connecting Corridor 4 to Corridor 5 across central gap!
          const nextZ = corridors[5]; // +0.70
          const midZ = 0.0;
          const centralSweepRadius = (nextZ - cz) / 2; // 0.70
          const turnCenterX = xTurnRight;
          const numSweepPts = 14;
          for (let t = 0; t <= numSweepPts; t++) {
            const angle = -Math.PI / 2 + (Math.PI * t) / numSweepPts;
            const tx = turnCenterX + centralSweepRadius * Math.cos(angle);
            const tz = midZ + centralSweepRadius * Math.sin(angle);
            points.push(new THREE.Vector3(tx, 0, tz));
          }
          points.push(new THREE.Vector3(xTurnRight, 0, nextZ));
        }
      } else {
        // Right to Left (+X to -X): Module 3 -> Module 2 -> Module 1
        for (let m = 2; m >= 0; m--) {
          const modCenterX = modXCenters[m];
          for (let c = 5; c >= 0; c--) {
            const cx = modCenterX + (c - 2.5) * pitchX;
            const sign = (c % 2 === 0) ? 1.0 : -1.0;
            points.push(new THREE.Vector3(cx + pitchX * 0.28, 0, cz + amplitude * sign * 0.70));
            points.push(new THREE.Vector3(cx, 0, cz + amplitude * sign));
            points.push(new THREE.Vector3(cx - pitchX * 0.28, 0, cz + amplitude * sign * 0.70));
          }
        }
        points.push(new THREE.Vector3(xTurnLeft, 0, cz));

        // Standard 180° semi-circular U-turn at -X end connecting corridor r to corridor r+1
        const nextZ = corridors[r + 1];
        const midZ = (cz + nextZ) / 2;
        const turnCenterX = xTurnLeft;
        const numTurnPts = 8;
        for (let t = 0; t <= numTurnPts; t++) {
          const angle = Math.PI / 2 + (Math.PI * t) / numTurnPts;
          const tx = turnCenterX + uTurnRadius * Math.cos(angle);
          const tz = midZ + uTurnRadius * Math.sin(angle);
          points.push(new THREE.Vector3(tx, 0, tz));
        }
        points.push(new THREE.Vector3(xTurnLeft, 0, nextZ));
      }
    }

    // =========================================================================
    // PART B: BOTTOM HALF (Corridors 5..9: MODULE 6, MODULE 5, MODULE 4)
    // 5 Horizontal Passes with 4 Rounded U-Turns
    // =========================================================================
    for (let r = 5; r < 10; r++) {
      const lr = r - 5;
      const cz = corridors[r];
      const isEven = (lr % 2 === 0);

      if (isEven) {
        // Right to Left (+X to -X): Module 6 -> Module 5 -> Module 4
        for (let m = 2; m >= 0; m--) {
          const modCenterX = modXCenters[m];
          for (let c = 5; c >= 0; c--) {
            const cx = modCenterX + (c - 2.5) * pitchX;
            const sign = (c % 2 === 0) ? 1.0 : -1.0;
            points.push(new THREE.Vector3(cx + pitchX * 0.28, 0, cz + amplitude * sign * 0.70));
            points.push(new THREE.Vector3(cx, 0, cz + amplitude * sign));
            points.push(new THREE.Vector3(cx - pitchX * 0.28, 0, cz + amplitude * sign * 0.70));
          }
        }
        points.push(new THREE.Vector3(xTurnLeft, 0, cz));

        if (lr < 4) {
          // 180° semi-circular U-turn at -X end connecting corridor r to corridor r+1
          const nextZ = corridors[r + 1];
          const midZ = (cz + nextZ) / 2;
          const turnCenterX = xTurnLeft;
          const numTurnPts = 8;
          for (let t = 0; t <= numTurnPts; t++) {
            const angle = Math.PI / 2 + (Math.PI * t) / numTurnPts;
            const tx = turnCenterX + uTurnRadius * Math.cos(angle);
            const tz = midZ + uTurnRadius * Math.sin(angle);
            points.push(new THREE.Vector3(tx, 0, tz));
          }
          points.push(new THREE.Vector3(xTurnLeft, 0, nextZ));
        }
      } else {
        // Left to Right (-X to +X): Module 4 -> Module 5 -> Module 6
        for (let m = 0; m < 3; m++) {
          const modCenterX = modXCenters[m];
          for (let c = 0; c < 6; c++) {
            const cx = modCenterX + (c - 2.5) * pitchX;
            const sign = (c % 2 === 0) ? 1.0 : -1.0;
            points.push(new THREE.Vector3(cx - pitchX * 0.28, 0, cz + amplitude * sign * 0.70));
            points.push(new THREE.Vector3(cx, 0, cz + amplitude * sign));
            points.push(new THREE.Vector3(cx + pitchX * 0.28, 0, cz + amplitude * sign * 0.70));
          }
        }
        points.push(new THREE.Vector3(xTurnRight, 0, cz));

        if (lr < 4) {
          // 180° semi-circular U-turn at +X end connecting corridor r to corridor r+1
          const nextZ = corridors[r + 1];
          const midZ = (cz + nextZ) / 2;
          const turnCenterX = xTurnRight;
          const numTurnPts = 8;
          for (let t = 0; t <= numTurnPts; t++) {
            const angle = -Math.PI / 2 + (Math.PI * t) / numTurnPts;
            const tx = turnCenterX + uTurnRadius * Math.cos(angle);
            const tz = midZ + uTurnRadius * Math.sin(angle);
            points.push(new THREE.Vector3(tx, 0, tz));
          }
          points.push(new THREE.Vector3(xTurnRight, 0, nextZ));
        }
      }
    }

    // 2. Coolant Outlet straight lead-out at Corridor 9 (-X flank of Module 4)
    points.push(new THREE.Vector3(xTurnLeft, 0, corridors[9]));
    points.push(new THREE.Vector3(-9.60, 0, corridors[9]));
    points.push(new THREE.Vector3(-10.05, 0, corridors[9]));

    return new THREE.CatmullRomCurve3(points, false, 'catmullrom', 0.18);
  }

  function buildModuleSerpentineSpline(modCenterX, modCenterZ, pitchX, pitchZ, cellRadius) {
    return buildContinuousSerpentineSpline(pitchX, pitchZ, cellRadius);
  }

  /**
   * Component 1: Exactly 180 Individual Cylindrical Li-ion Cells (2 x 3 Matrix of 6 Independent Modules)
   * Each module contains 30 cells in a 5 x 6 arrangement with visible physical separation gaps.
   * Pure series order (CELL-001 to CELL-180, k = 0..179).
   * Alternating polarity (+/-), raised brass caps, red/blue insulator rings, flat nickel bases.
   * All top cell heads are completely open and visible (zero top brackets/covers blocking view).
   */
  function buildBatteryPack() {
    // Clear old cells from scene
    while (layerGroups.cells.children.length > 0) {
      const obj = layerGroups.cells.children[0];
      layerGroups.cells.remove(obj);
      if (obj.geometry) obj.geometry.dispose();
    }
    cellMeshes = [];
    STATE.cells = [];

    // Clear old pack trays / housing
    const oldTray = layerGroups.plates.getObjectByName('PACK-HOUSING');
    if (oldTray) layerGroups.plates.remove(oldTray);

    const housingGroup = new THREE.Group();
    housingGroup.name = 'PACK-HOUSING';

    // Physical dimensions & grid spacing
    const is18650 = STATE.formFactor === '18650';
    const cellRadius = is18650 ? 0.30 : 0.35; // 21700: Ø 21 mm
    const cellHeight = is18650 ? 2.10 : 2.40; // 21700: 70 mm
    const pitchX = 0.86;
    const pitchZ = 0.92;
    const gapX = 1.20;
    const gapZ = 1.40;
    const modStepX = 6.0 * pitchX + gapX; // 6.36
    const modStepZ = 5.0 * pitchZ + gapZ; // 6.00

    const trayMat = new THREE.MeshStandardMaterial({
      color: 0x1e293b,
      metalness: 0.85,
      roughness: 0.3
    });
    const bracketMat = new THREE.MeshStandardMaterial({
      color: 0x334155,
      metalness: 0.75,
      roughness: 0.35
    });
    const labelMat = new THREE.MeshStandardMaterial({
      color: 0x00d4ff,
      metalness: 0.8,
      roughness: 0.2
    });

    const modTrayWidth = 6.0 * pitchX + 0.35; // 5.51
    const modTrayDepth = 5.0 * pitchZ + 0.35; // 4.95

    // Build 6 Individual Module Mounting Sub-Trays (Bottom Only - No top covers!)
    MODULE_CONFIG.forEach((mInfo, mIdx) => {
      const modCenterX = (mInfo.matCol - 1.0) * modStepX;
      const modCenterZ = (mInfo.matRow - 0.5) * modStepZ;

      const subTrayGroup = new THREE.Group();
      subTrayGroup.position.set(modCenterX, 0, modCenterZ);

      // Base tray plate
      const trayGeo = new THREE.BoxGeometry(modTrayWidth, 0.18, modTrayDepth);
      const subTray = new THREE.Mesh(trayGeo, trayMat);
      subTray.position.set(0, 0.09, 0);
      subTray.receiveShadow = true;
      subTray.castShadow = true;
      subTray.userData = {
        type: 'component',
        id: mInfo.id,
        name: `${mInfo.name} Mounting Sub-Tray (30 Cells 5x6)`,
        module_id: mInfo.id
      };
      subTrayGroup.add(subTray);

      // Lower edge retention flanges (height 0.45, leaving 100% of upper cell body & head exposed)
      const flangeGeoZ = new THREE.BoxGeometry(0.12, 0.45, modTrayDepth);
      const leftFlange = new THREE.Mesh(flangeGeoZ, bracketMat);
      leftFlange.position.set(-modTrayWidth / 2 + 0.06, 0.31, 0);
      subTrayGroup.add(leftFlange);

      const rightFlange = new THREE.Mesh(flangeGeoZ, bracketMat);
      rightFlange.position.set(modTrayWidth / 2 - 0.06, 0.31, 0);
      subTrayGroup.add(rightFlange);

      // Front 3D Module Identifier Badge Bar
      const badgeGeo = new THREE.BoxGeometry(1.6, 0.14, 0.08);
      const badgeMesh = new THREE.Mesh(badgeGeo, labelMat);
      badgeMesh.position.set(0, 0.22, modTrayDepth / 2 + 0.04);
      badgeMesh.userData = {
        type: 'component',
        id: mInfo.id,
        name: `Battery ${mInfo.name} (30S1P)`,
        module_id: mInfo.id
      };
      subTrayGroup.add(badgeMesh);

      housingGroup.add(subTrayGroup);
    });

    layerGroups.plates.add(housingGroup);

    // 2. Exact 180 Individual Cylindrical Li-ion Cells in 6 Modules
    const casingGeo = new THREE.CylinderGeometry(cellRadius, cellRadius, cellHeight, 18);
    const capGeo = new THREE.CylinderGeometry(cellRadius * 0.45, cellRadius * 0.45, 0.10, 14);
    const ringGeo = new THREE.RingGeometry(cellRadius * 0.48, cellRadius * 0.88, 16);
    ringGeo.rotateX(-Math.PI / 2);
    const baseGeo = new THREE.CylinderGeometry(cellRadius * 0.85, cellRadius * 0.85, 0.04, 16);

    const posCapMat = new THREE.MeshStandardMaterial({ color: 0xd4af37, metalness: 0.92, roughness: 0.18 }); // Gold/Brass cap
    const ringRedMat = new THREE.MeshStandardMaterial({ color: 0xef4444, roughness: 0.4 }); // Red positive insulator
    const ringBlueMat = new THREE.MeshStandardMaterial({ color: 0x3b82f6, roughness: 0.4 }); // Blue negative insulator
    const baseMat = new THREE.MeshStandardMaterial({ color: 0x94a3b8, metalness: 0.85, roughness: 0.3 }); // Nickel base

    MODULE_CONFIG.forEach((mInfo, mIdx) => {
      const modCenterX = (mInfo.matCol - 1.0) * modStepX;
      const modCenterZ = (mInfo.matRow - 0.5) * modStepZ;

      for (let kMod = 0; kMod < 30; kMod++) {
        const kGlobal = mIdx * 30 + kMod;
        const cellId = `CELL-${String(kGlobal + 1).padStart(3, '0')}`;

        // Serpentine row/col inside module (lr = 0..4, lc = 0..5)
        const lr = Math.floor(kMod / 6);
        const lc = (lr % 2 === 0) ? (kMod % 6) : (5 - (kMod % 6));

        const posX = modCenterX + (lc - 2.5) * pitchX;
        const posZ = modCenterZ + (lr - 2.0) * pitchZ;
        const posY = cellHeight / 2 + 0.34;

        const isEven = (kGlobal % 2 === 0);
        const polarity = isEven ? 'POS_TOP' : 'NEG_TOP';

        const cellMat = new THREE.MeshStandardMaterial({
          color: 0x22c55e,
          roughness: 0.35,
          metalness: 0.45,
          emissive: 0x000000
        });

        const cellMesh = new THREE.Mesh(casingGeo, cellMat);
        cellMesh.position.set(posX, posY, posZ);
        cellMesh.castShadow = true;
        cellMesh.receiveShadow = true;

        if (isEven) {
          // Even kGlobal: Top is POSITIVE (+) raised brass cap, Bottom is NEGATIVE (-) flat base
          const cap = new THREE.Mesh(capGeo, posCapMat);
          cap.position.set(0, cellHeight / 2 + 0.05, 0);
          cellMesh.add(cap);

          const ring = new THREE.Mesh(ringGeo, ringRedMat);
          ring.position.set(0, cellHeight / 2 + 0.005, 0);
          cellMesh.add(ring);

          const base = new THREE.Mesh(baseGeo, baseMat);
          base.position.set(0, -cellHeight / 2 - 0.02, 0);
          cellMesh.add(base);

          const baseRing = new THREE.Mesh(ringGeo, ringBlueMat);
          baseRing.position.set(0, -cellHeight / 2 - 0.005, 0);
          cellMesh.add(baseRing);
        } else {
          // Odd kGlobal: Top is NEGATIVE (-) flat base, Bottom is POSITIVE (+) raised brass cap
          const base = new THREE.Mesh(baseGeo, baseMat);
          base.position.set(0, cellHeight / 2 + 0.02, 0);
          cellMesh.add(base);

          const ring = new THREE.Mesh(ringGeo, ringBlueMat);
          ring.position.set(0, cellHeight / 2 + 0.005, 0);
          cellMesh.add(ring);

          const cap = new THREE.Mesh(capGeo, posCapMat);
          cap.position.set(0, -cellHeight / 2 - 0.05, 0);
          cellMesh.add(cap);

          const baseRing = new THREE.Mesh(ringGeo, ringRedMat);
          baseRing.position.set(0, -cellHeight / 2 - 0.005, 0);
          cellMesh.add(baseRing);
        }

        cellMesh.userData = {
          type: 'cell',
          id: cellId,
          series_index: kGlobal,
          index: kGlobal,
          module_id: mInfo.id,
          module_name: mInfo.name,
          module_index: mIdx,
          local_row: lr,
          local_col: lc,
          row: mInfo.matRow * 5 + lr,
          col: mInfo.matCol * 6 + lc,
          polarity: polarity,
          top_terminal: isEven ? '+' : '-',
          bottom_terminal: isEven ? '-' : '+',
          form_factor: STATE.formFactor,
          temp_c: 25.0,
          heat_w: 2.2,
          radius_mm: is18650 ? 9.0 : 10.5,
          length_mm: is18650 ? 65.0 : 70.0,
          contact_area_m2: 0.00308,
          tim_thickness_mm: 0.4,
          tim_k_w_mk: 3.0
        };

        cellMeshes.push(cellMesh);
        layerGroups.cells.add(cellMesh);

        STATE.cells.push({
          id: cellId,
          series_index: kGlobal,
          module_id: mInfo.id,
          module_name: mInfo.name,
          local_row: lr,
          local_col: lc,
          temp_c: 25.0,
          heat_w: 2.2,
          color_hex: '#22c55e',
          color_name: 'normal'
        });
      }
    });
  }

  /**
   * Component 2: Series Electrical Connection System (180S1P Architecture)
   * Connects all 180 cells in pure series: MODULE A -> B -> C -> D -> E -> F (666.0V DC).
   * 174 Intra-Module Series Busbars (alternating bottom/top).
   * 5 Inter-Module Arched Series Jumpers connecting adjacent modules.
   * Main +HV Terminal (Red Lug) on Module A CELL-001 Top (+); Main -HV Terminal (Blue Lug) on Module F CELL-180 Top (-).
   * All busbars, jumpers, and lugs are interactive and selectable for full electrical telemetry.
   */
  function buildElectricalSystem() {
    while (layerGroups.electrical.children.length > 0) {
      const obj = layerGroups.electrical.children[0];
      layerGroups.electrical.remove(obj);
      if (obj.geometry) obj.geometry.dispose();
    }
    busbarMeshes = [];

    const is18650 = STATE.formFactor === '18650';
    const cellRadius = is18650 ? 0.30 : 0.35;
    const cellHeight = is18650 ? 2.10 : 2.40;
    const topY = cellHeight + 0.34 + 0.06;
    const bottomY = 0.34 - 0.05;

    // Materials
    const busbarMat = new THREE.MeshStandardMaterial({
      color: 0xd4af37, // Nickel/gold plated copper C11000
      metalness: 0.92,
      roughness: 0.18
    });
    const busbarInsulMat = new THREE.MeshStandardMaterial({
      color: 0x1e293b,
      roughness: 0.65
    });
    const jumperMat = new THREE.MeshStandardMaterial({
      color: 0xf59e0b, // Amber high-flex copper braid
      metalness: 0.88,
      roughness: 0.25
    });
    const jumperInsulMat = new THREE.MeshStandardMaterial({
      color: 0xdc2626, // Bright red high-voltage protective silicone
      roughness: 0.4
    });
    const posLugMat = new THREE.MeshStandardMaterial({
      color: 0xef4444, // Bright Red (+HV)
      metalness: 0.8,
      roughness: 0.2
    });
    const negLugMat = new THREE.MeshStandardMaterial({
      color: 0x3b82f6, // Bright Blue (-HV)
      metalness: 0.8,
      roughness: 0.2
    });

    // Helper to get 3D position of cell by series_index
    function getCellPos(kGlobal) {
      if (cellMeshes[kGlobal]) {
        return cellMeshes[kGlobal].position;
      }
      return new THREE.Vector3(0, 0, 0);
    }

    // 1. Intra-Module Series Busbars (29 busbars per module * 6 modules = 174 busbars)
    MODULE_CONFIG.forEach((mInfo, mIdx) => {
      for (let kMod = 0; kMod < 29; kMod++) {
        const k1 = mIdx * 30 + kMod;
        const k2 = k1 + 1;

        const p1 = getCellPos(k1);
        const p2 = getCellPos(k2);

        const isTop = (k1 % 2 === 1); // Odd k1: Top busbar (- to +). Even k1: Bottom busbar (- to +)
        const bY = isTop ? topY : bottomY;

        const dx = p2.x - p1.x;
        const dz = p2.z - p1.z;
        const dist = Math.hypot(dx, dz);
        const angle = Math.atan2(dz, dx);

        const busbarGroup = new THREE.Group();
        busbarGroup.position.set((p1.x + p2.x) / 2, bY, (p1.z + p2.z) / 2);
        busbarGroup.rotation.y = -angle;

        // Metallic conductor bridge
        const stripGeo = new THREE.BoxGeometry(dist + 0.12, 0.025, 0.14);
        const strip = new THREE.Mesh(stripGeo, busbarMat);
        busbarGroup.add(strip);

        // Insulating protective heat-shrink sleeve
        const sleeveGeo = new THREE.BoxGeometry(Math.max(0.08, dist - 0.26), 0.035, 0.16);
        const sleeve = new THREE.Mesh(sleeveGeo, busbarInsulMat);
        busbarGroup.add(sleeve);

        // Contact terminal pads
        const padGeo = new THREE.CylinderGeometry(0.12, 0.12, 0.035, 12);
        const pad1 = new THREE.Mesh(padGeo, busbarMat);
        pad1.position.x = -dist / 2;
        busbarGroup.add(pad1);

        const pad2 = new THREE.Mesh(padGeo, busbarMat);
        pad2.position.x = dist / 2;
        busbarGroup.add(pad2);

        const cellId1 = `CELL-${String(k1 + 1).padStart(3, '0')}`;
        const cellId2 = `CELL-${String(k2 + 1).padStart(3, '0')}`;
        const busbarId = `BUSBAR-${mInfo.id}-S${String(kMod + 1).padStart(2, '0')}-S${String(kMod + 2).padStart(2, '0')}`;

        busbarGroup.userData = {
          type: 'component',
          id: busbarId,
          name: `Series Busbar (${cellId1} [-] -> ${cellId2} [+])`,
          module_id: mInfo.id,
          series_link: `${k1 + 1} -> ${k2 + 1}`,
          layer: isTop ? 'TOP (+2.76 Y)' : 'BOTTOM (+0.30 Y)',
          current_capacity_a: 120,
          voltage_drop_mv: 1.15,
          material: 'Nickel-Plated Electrolytic Copper C11000'
        };

        layerGroups.electrical.add(busbarGroup);
        busbarMeshes.push(busbarGroup);
      }
    });

    // 2. Five Inter-Module High-Current Series Jumpers (A->B, B->C, C->D, D->E, E->F)
    const JUMPER_DEFS = [
      { id: 'JUMPER-A-B', name: 'Inter-Module Series Jumper A -> B', fromIdx: 29, toIdx: 30, fromMod: 'MODULE_A', toMod: 'MODULE_B' },
      { id: 'JUMPER-B-C', name: 'Inter-Module Series Jumper B -> C', fromIdx: 59, toIdx: 60, fromMod: 'MODULE_B', toMod: 'MODULE_C' },
      { id: 'JUMPER-C-D', name: 'Inter-Module Series Jumper C -> D (Cross-Row)', fromIdx: 89, toIdx: 90, fromMod: 'MODULE_C', toMod: 'MODULE_D' },
      { id: 'JUMPER-D-E', name: 'Inter-Module Series Jumper D -> E', fromIdx: 119, toIdx: 120, fromMod: 'MODULE_D', toMod: 'MODULE_E' },
      { id: 'JUMPER-E-F', name: 'Inter-Module Series Jumper E -> F', fromIdx: 149, toIdx: 150, fromMod: 'MODULE_E', toMod: 'MODULE_F' },
    ];

    JUMPER_DEFS.forEach(jDef => {
      const pFrom = getCellPos(jDef.fromIdx);
      const pTo = getCellPos(jDef.toIdx);

      const jumperGroup = new THREE.Group();

      // Arched curve connecting cell heads at the top
      const midPoint = new THREE.Vector3(
        (pFrom.x + pTo.x) / 2,
        topY + 0.45,
        (pFrom.z + pTo.z) / 2
      );
      const startPoint = new THREE.Vector3(pFrom.x, topY, pFrom.z);
      const endPoint = new THREE.Vector3(pTo.x, topY, pTo.z);

      const archCurve = new THREE.QuadraticBezierCurve3(startPoint, midPoint, endPoint);
      const archGeo = new THREE.TubeGeometry(archCurve, 24, 0.055, 12, false);
      const archMesh = new THREE.Mesh(archGeo, jumperMat);
      jumperGroup.add(archMesh);

      // Protective high-voltage sleeve over mid section
      const sleeveSubCurve = new THREE.QuadraticBezierCurve3(
        archCurve.getPoint(0.2),
        midPoint,
        archCurve.getPoint(0.8)
      );
      const sleeveGeo = new THREE.TubeGeometry(sleeveSubCurve, 16, 0.075, 12, false);
      const sleeveMesh = new THREE.Mesh(sleeveGeo, jumperInsulMat);
      jumperGroup.add(sleeveMesh);

      // Terminal Lugs on both ends
      const lugGeo = new THREE.CylinderGeometry(0.14, 0.14, 0.08, 14);
      const lug1 = new THREE.Mesh(lugGeo, busbarMat);
      lug1.position.copy(startPoint);
      jumperGroup.add(lug1);

      const lug2 = new THREE.Mesh(lugGeo, busbarMat);
      lug2.position.copy(endPoint);
      jumperGroup.add(lug2);

      const cellFromId = `CELL-${String(jDef.fromIdx + 1).padStart(3, '0')}`;
      const cellToId = `CELL-${String(jDef.toIdx + 1).padStart(3, '0')}`;

      jumperGroup.userData = {
        type: 'component',
        id: jDef.id,
        name: `${jDef.name} (${cellFromId} [-] -> ${cellToId} [+])`,
        jumper_id: jDef.id,
        from_cell: cellFromId,
        to_cell: cellToId,
        from_module: jDef.fromMod,
        to_module: jDef.toMod,
        current_capacity_a: 200,
        voltage_rating_v: 1000,
        material: 'High-Flex Electrolytic Copper Braid with Red Silicone Sleeve'
      };

      layerGroups.electrical.add(jumperGroup);
      busbarMeshes.push(jumperGroup);
    });

    // 3. Main +HV Traction Positive Terminal Post (Red Lug on Module A CELL-001 Top, k=0)
    const p0 = getCellPos(0);
    const posTerminalGroup = new THREE.Group();
    posTerminalGroup.position.set(p0.x, topY, p0.z);

    const lugBaseGeo = new THREE.CylinderGeometry(0.20, 0.20, 0.07, 16);
    const lugBase = new THREE.Mesh(lugBaseGeo, posLugMat);
    posTerminalGroup.add(lugBase);

    const studGeo = new THREE.CylinderGeometry(0.09, 0.09, 0.35, 16);
    const stud = new THREE.Mesh(studGeo, busbarMat);
    stud.position.y = 0.18;
    posTerminalGroup.add(stud);

    const posCapGeo = new THREE.CylinderGeometry(0.13, 0.13, 0.09, 16);
    const posCap = new THREE.Mesh(posCapGeo, posLugMat);
    posCap.position.y = 0.32;
    posTerminalGroup.add(posCap);

    posTerminalGroup.userData = {
      type: 'component',
      id: 'MAIN-BUSBAR-POS',
      name: 'Main Traction Positive Terminal (+HV 666V DC)',
      voltage_v: 666.0,
      rated_current_a: 450.0,
      cell_origin: 'Module A CELL-001 (Top Raised Brass Button Cap)',
      material: 'Electrolytic Copper with Red Silicone High-Voltage Insulator'
    };
    layerGroups.electrical.add(posTerminalGroup);
    busbarMeshes.push(posTerminalGroup);

    // 4. Main -HV Traction Negative Terminal Post (Blue Lug on Module F CELL-180 Top, k=179)
    const pLast = getCellPos(179);
    const negTerminalGroup = new THREE.Group();
    negTerminalGroup.position.set(pLast.x, topY, pLast.z);

    const negBase = new THREE.Mesh(lugBaseGeo, negLugMat);
    negTerminalGroup.add(negBase);

    const negStud = new THREE.Mesh(studGeo, busbarMat);
    negStud.position.y = 0.18;
    negTerminalGroup.add(negStud);

    const negCap = new THREE.Mesh(posCapGeo, negLugMat);
    negCap.position.y = 0.32;
    negTerminalGroup.add(negCap);

    negTerminalGroup.userData = {
      type: 'component',
      id: 'MAIN-BUSBAR-NEG',
      name: 'Main Traction Negative Terminal (-HV 0V GND Return)',
      voltage_v: 0.0,
      rated_current_a: 450.0,
      cell_origin: 'Module F CELL-180 (Top Flat Nickel Base Pad)',
      material: 'Electrolytic Copper with Blue Silicone High-Voltage Insulator'
    };
    layerGroups.electrical.add(negTerminalGroup);
    busbarMeshes.push(negTerminalGroup);

    // 5. 6 Zonal Module Thermistors (One per Module Core)
    const ntcGeo = new THREE.SphereGeometry(0.08, 12, 12);
    const ntcMat = new THREE.MeshStandardMaterial({
      color: 0x10b981,
      roughness: 0.3,
      emissive: 0x059669,
      emissiveIntensity: 0.4
    });

    MODULE_CONFIG.forEach(mInfo => {
      const coreCellIdx = mInfo.cellStart + 14; // Cell 15 of module (core)
      const pCore = getCellPos(coreCellIdx - 1);

      const ntcMesh = new THREE.Mesh(ntcGeo, ntcMat);
      ntcMesh.position.set(pCore.x, topY + 0.02, pCore.z);
      ntcMesh.userData = {
        type: 'sensor',
        id: `NTC-${mInfo.id}`,
        name: `NTC Core Thermistor (${mInfo.name})`,
        module_id: mInfo.id,
        type_code: 'NTC 10k Beta 3950',
        accuracy_c: 0.1
      };
      layerGroups.electrical.add(ntcMesh);
    });
  }

  /**
   * Component 3: Six Independent Full-Height Serpentine Cooling Plates (One per Module)
   * Passing in the physical gaps between cell rows, conforming with smooth horizontal passes
   * and rounded 180° U-turns hugging cylindrical cells.
   * Full active height coverage (70 mm) leaving cell top terminals and busbars visible.
   * Connected to shared supply & return manifolds with 6 branch valves.
   */
  function buildCoolingPlatesAndChannels() {
    // Clear old plate & channel meshes
    while (layerGroups.plates.children.length > 0) {
      const obj = layerGroups.plates.children[0];
      if (obj.name !== 'PACK-HOUSING') {
        layerGroups.plates.remove(obj);
        if (obj.geometry) obj.geometry.dispose();
      } else {
        break;
      }
    }
    while (layerGroups.channels.children.length > 0) {
      const obj = layerGroups.channels.children[0];
      layerGroups.channels.remove(obj);
      if (obj.geometry) obj.geometry.dispose();
    }

    interPlateMeshes = [];
    wavyRibbonMeshes = [];
    serpentineCurves = [];
    moduleSplines = {};
    modulePlates = {};
    moduleChannels = {};

    const is18650 = STATE.formFactor === '18650';
    const cellRadius = is18650 ? 0.30 : 0.35;
    const cellHeight = is18650 ? 2.10 : 2.40;
    const pitchX = 0.86;
    const pitchZ = 0.92;
    const gapX = 1.20;
    const gapZ = 1.40;
    const modStepX = 6.0 * pitchX + gapX; // 6.36
    const modStepZ = 5.0 * pitchZ + gapZ; // 6.00

    const isCopper = STATE.plateMaterial === 'copper';
    const metalMat = new THREE.MeshStandardMaterial({
      color: isCopper ? 0xb87333 : 0x94a3b8,
      metalness: 0.88,
      roughness: 0.24,
      transparent: STATE.cutawayActive,
      opacity: STATE.cutawayActive ? 0.32 : 1.0,
      side: THREE.DoubleSide
    });

    const microChannelMat = new THREE.MeshPhysicalMaterial({
      color: 0x00d4ff,
      emissive: 0x0088cc,
      emissiveIntensity: 0.50,
      transparent: true,
      opacity: 0.75,
      roughness: 0.1,
      metalness: 0.1,
      transmission: 0.65
    });

    const fittingGeo = new THREE.CylinderGeometry(0.08, 0.08, 0.45, 16);
    const fittingMat = new THREE.MeshStandardMaterial({ color: 0x475569, metalness: 0.85, roughness: 0.25 });
    const valveGeo = new THREE.CylinderGeometry(0.12, 0.12, 0.20, 16);
    const valveMat = new THREE.MeshStandardMaterial({ color: 0x0284c7, metalness: 0.8, roughness: 0.2 });

    const ribbonHalfThickness = 0.038;
    const yMin = 0.38;
    const yMax = cellHeight + 0.34 - 0.06; // 2.68 (covers full 70 mm cell height!)

    // 1. Build the ONE unified 10-pass continuous serpentine spline spanning all 6 modules
    continuousSerpentineSpline = buildContinuousSerpentineSpline(pitchX, pitchZ, cellRadius, gapX, gapZ);
    serpentineCurves = [continuousSerpentineSpline];

    // 2. Extrude the ONE Continuous Full-Height Serpentine Cooling Plate across all 6 modules
    const numSamples = 960;
    const samplePoints = continuousSerpentineSpline.getPoints(numSamples);
    const positions = [];
    const indices = [];

    for (let i = 0; i < samplePoints.length; i++) {
      const p = samplePoints[i];
      const pPrev = samplePoints[Math.max(0, i - 1)];
      const pNext = samplePoints[Math.min(samplePoints.length - 1, i + 1)];
      const tDir = new THREE.Vector2(pNext.x - pPrev.x, pNext.z - pPrev.z).normalize();
      const nDir = new THREE.Vector2(-tDir.y, tDir.x);

      const ox = p.x + nDir.x * ribbonHalfThickness;
      const oz = p.z + nDir.y * ribbonHalfThickness;
      const ix = p.x - nDir.x * ribbonHalfThickness;
      const iz = p.z - nDir.y * ribbonHalfThickness;

      positions.push(ox, yMin, oz);
      positions.push(ox, yMax, oz);
      positions.push(ix, yMax, iz);
      positions.push(ix, yMin, iz);

      if (i < samplePoints.length - 1) {
        const base = i * 4;
        const next = (i + 1) * 4;
        indices.push(base + 0, next + 0, next + 1);
        indices.push(base + 0, next + 1, base + 1);
        indices.push(base + 1, next + 1, next + 2);
        indices.push(base + 1, next + 2, base + 2);
        indices.push(base + 2, next + 2, next + 3);
        indices.push(base + 2, next + 3, base + 3);
        indices.push(base + 3, next + 3, next + 0);
        indices.push(base + 3, next + 0, base + 0);
      }
    }

    indices.push(0, 1, 2);
    indices.push(0, 2, 3);
    const lastBase = numSamples * 4;
    indices.push(lastBase + 0, lastBase + 2, lastBase + 1);
    indices.push(lastBase + 0, lastBase + 3, lastBase + 2);

    const plateGeo = new THREE.BufferGeometry();
    plateGeo.setAttribute('position', new THREE.Float32BufferAttribute(positions, 3));
    plateGeo.setIndex(indices);
    plateGeo.computeVertexNormals();

    const plateMesh = new THREE.Mesh(plateGeo, metalMat);
    plateMesh.castShadow = true;
    plateMesh.receiveShadow = true;
    plateMesh.userData = {
      type: 'channel',
      id: 'PLATE-SERPENTINE-CONTINUOUS',
      name: 'Continuous 10-Pass Serpentine Cooling Plate (All 6 Modules, 180 Cells)',
      material: isCopper ? 'Continuous Micro-Channel Copper C11000 (k = 398 W/m·K)' : 'Extruded Aluminum 6061-T6 (k = 167 W/m·K)',
      height_mm: 70.0,
      passes: 10,
      u_turns: 9,
      hydraulic_dia_mm: 2.86,
      coolant: 'Al2O3 + Cu Hybrid Nanofluid in Water/Glycol Base'
    };

    layerGroups.plates.add(plateMesh);
    interPlateMeshes.push(plateMesh);
    wavyRibbonMeshes.push(plateMesh);
    componentMeshes['PLATE-SERPENTINE-CONTINUOUS'] = plateMesh;

    // 3. Internal Glowing Fluid Lumen Passage (Continuous 10 passes through entire pack)
    const lumenGeo = new THREE.TubeGeometry(continuousSerpentineSpline, 720, 0.040, 10, false);
    const lumenMesh = new THREE.Mesh(lumenGeo, microChannelMat);
    lumenMesh.position.y = (yMin + yMax) / 2;
    lumenMesh.userData = {
      type: 'channel',
      id: 'CHANNEL-SERPENTINE-CONTINUOUS',
      name: 'Continuous 10-Pass Internal Nanofluid Flow Lumen (All 6 Modules)',
      hydraulic_dia_mm: 2.86
    };
    layerGroups.channels.add(lumenMesh);
    componentMeshes['CHANNEL-SERPENTINE-CONTINUOUS'] = lumenMesh;

    // Map module references to the continuous plate/channel for backwards compatibility
    MODULE_CONFIG.forEach(mInfo => {
      moduleSplines[mInfo.id] = continuousSerpentineSpline;
      modulePlates[mInfo.id] = plateMesh;
      moduleChannels[mInfo.id] = lumenMesh;
    });

    // 4. Coolant Inlet Fitting (Module 1 / Row 0 -X Flank, connected to PIPE-07)
    const inPt = continuousSerpentineSpline.getPoint(0);
    const fitIn = new THREE.Mesh(fittingGeo, fittingMat);
    fitIn.rotation.z = Math.PI / 2;
    fitIn.position.set(inPt.x - 0.25, (yMin + yMax) / 2, inPt.z);
    fitIn.userData = {
      type: 'component',
      id: 'INLET-SERPENTINE',
      name: 'Coolant Supply Inlet Fitting (Module 1 Flank)'
    };
    layerGroups.plates.add(fitIn);
    componentMeshes['INLET-SERPENTINE'] = fitIn;

    const mainValveMesh = new THREE.Mesh(valveGeo, valveMat);
    mainValveMesh.position.set(inPt.x - 0.55, (yMin + yMax) / 2, inPt.z);
    mainValveMesh.userData = {
      type: 'component',
      id: 'VALVE-MAIN',
      name: 'Main Coolant Supply Proportional Flow-Control Valve'
    };
    layerGroups.components.add(mainValveMesh);
    componentMeshes['VALVE-MAIN'] = mainValveMesh;

    // 5. Coolant Outlet Fitting (Module 4 / Row 9 -X Flank, connected to PIPE-01)
    const outPt = continuousSerpentineSpline.getPoint(1);
    const fitOut = new THREE.Mesh(fittingGeo, fittingMat);
    fitOut.rotation.z = Math.PI / 2;
    fitOut.position.set(outPt.x - 0.25, (yMin + yMax) / 2, outPt.z);
    fitOut.userData = {
      type: 'component',
      id: 'OUTLET-SERPENTINE',
      name: 'Coolant Return Outlet Fitting (Module 4 Flank)'
    };
    layerGroups.plates.add(fitOut);
    componentMeshes['OUTLET-SERPENTINE'] = fitOut;

    // Update shared supply & return manifolds
    const totalPackSpanX = 3 * modStepX + 1.2;
    const totalPackSpanZ = 2 * modStepZ + 1.2;
    updateManifoldGeometry(totalPackSpanX, totalPackSpanZ, cellHeight);
  }

  function updateManifoldGeometry(packSpanX, packSpanZ, cellHeight) {
    const manifoldLen = Math.max(packSpanZ + 0.6, 8.4);
    const manifoldX = packSpanX / 2 + 0.55;

    if (componentMeshes['MANIFOLD-IN']) {
      componentMeshes['MANIFOLD-IN'].position.set(-manifoldX, cellHeight / 2 + 0.35, 0);
      componentMeshes['MANIFOLD-IN'].scale.set(1, manifoldLen / 8.4, 1);
    }
    if (componentMeshes['MANIFOLD-OUT']) {
      componentMeshes['MANIFOLD-OUT'].position.set(manifoldX, cellHeight / 2 + 0.35, 0);
      componentMeshes['MANIFOLD-OUT'].scale.set(1, manifoldLen / 8.4, 1);
    }
  }

  /**
   * Components 5 to 10: Loop Equipment (Manifolds, Pump, Reservoir, Radiator/Fan, Chiller, Heat Exchanger, Valve)
   */
  function buildCoolingLoopEquipment() {
    // --------------------------------------------------------------------------
    // Component 5: Coolant Inlet & Outlet Manifolds
    // --------------------------------------------------------------------------
    const manifoldGeo = new THREE.CylinderGeometry(0.55, 0.55, 8.4, 24);
    const manifoldMat = new THREE.MeshStandardMaterial({ color: 0x334155, metalness: 0.85, roughness: 0.25 });

    // Cold Inlet Manifold (-X, feeding inter-row channels)
    const inManifold = new THREE.Mesh(manifoldGeo, manifoldMat);
    inManifold.rotation.x = Math.PI / 2;
    inManifold.position.set(-13.6, 1.95, 0);
    inManifold.castShadow = true;
    inManifold.userData = { type: 'component', id: 'MANIFOLD-IN', name: 'Cold Nanofluid Supply Manifold' };
    layerGroups.components.add(inManifold);
    componentMeshes['MANIFOLD-IN'] = inManifold;

    // Warm Outlet Manifold (+X, collecting from inter-row channels)
    const outManifold = new THREE.Mesh(manifoldGeo, manifoldMat);
    outManifold.rotation.x = Math.PI / 2;
    outManifold.position.set(13.6, 1.95, 0);
    outManifold.castShadow = true;
    outManifold.userData = { type: 'component', id: 'MANIFOLD-OUT', name: 'Hot Nanofluid Return Manifold' };
    layerGroups.components.add(outManifold);
    componentMeshes['MANIFOLD-OUT'] = outManifold;

    // --------------------------------------------------------------------------
    // Component 6: Nanofluid Circulation Pump & Electric Drive Motor
    // --------------------------------------------------------------------------
    const pumpGroup = new THREE.Group();
    pumpGroup.position.set(-18.5, 1.8, -7.5);

    // Volute casing
    const voluteGeo = new THREE.CylinderGeometry(1.25, 1.25, 0.85, 32);
    const voluteMat = new THREE.MeshStandardMaterial({ color: 0x1e293b, metalness: 0.8, roughness: 0.25 });
    const volute = new THREE.Mesh(voluteGeo, voluteMat);
    volute.rotation.z = Math.PI / 2;
    volute.castShadow = true;
    pumpGroup.add(volute);

    // Rotating internal impeller
    const impellerGroup = new THREE.Group();
    const bladeGeo = new THREE.BoxGeometry(0.1, 0.95, 0.4);
    const bladeMat = new THREE.MeshStandardMaterial({ color: 0x00d4ff, metalness: 0.9, roughness: 0.1 });
    for (let b = 0; b < 6; b++) {
      const blade = new THREE.Mesh(bladeGeo, bladeMat);
      blade.rotation.x = (b * Math.PI) / 3;
      impellerGroup.add(blade);
    }
    pumpGroup.add(impellerGroup);
    pumpImpeller = impellerGroup;

    // Pump Electric Motor with cooling fins
    const motorGeo = new THREE.CylinderGeometry(0.95, 0.95, 1.9, 24);
    const motorMat = new THREE.MeshStandardMaterial({ color: 0x0f172a, metalness: 0.6, roughness: 0.4 });
    const motor = new THREE.Mesh(motorGeo, motorMat);
    motor.rotation.z = Math.PI / 2;
    motor.position.x = -1.4;
    motor.castShadow = true;
    pumpGroup.add(motor);

    // Terminal junction box
    const jboxGeo = new THREE.BoxGeometry(0.7, 0.5, 0.6);
    const jboxMat = new THREE.MeshStandardMaterial({ color: 0xf59e0b });
    const jbox = new THREE.Mesh(jboxGeo, jboxMat);
    jbox.position.set(-1.4, 0.95, 0);
    pumpGroup.add(jbox);

    pumpGroup.userData = {
      type: 'component',
      id: 'PUMP-01',
      name: 'Electric Nanofluid Circulation Pump',
      rpm_max: 3600,
      flow_max_lpm: 24.0,
      p_head_kpa: 85.0
    };
    layerGroups.components.add(pumpGroup);
    componentMeshes['PUMP-01'] = pumpGroup;

    // --------------------------------------------------------------------------
    // Component 7: Coolant Reservoir (Expansion Tank)
    // --------------------------------------------------------------------------
    const resGroup = new THREE.Group();
    resGroup.position.set(-18.5, 4.8, -7.5);

    const tankGeo = new THREE.CylinderGeometry(1.15, 1.15, 2.6, 32);
    const tankMat = new THREE.MeshStandardMaterial({
      color: 0x64748b,
      transparent: true,
      opacity: 0.55,
      metalness: 0.2,
      roughness: 0.1
    });
    const tank = new THREE.Mesh(tankGeo, tankMat);
    resGroup.add(tank);

    // Fluid level sight glass
    const fluidGeo = new THREE.CylinderGeometry(1.1, 1.1, 1.7, 32);
    const fluidMat = new THREE.MeshStandardMaterial({ color: 0x00acc1, transparent: true, opacity: 0.85 });
    const fluid = new THREE.Mesh(fluidGeo, fluidMat);
    fluid.position.y = -0.4;
    resGroup.add(fluid);

    // Filler Cap
    const capGeo = new THREE.CylinderGeometry(0.35, 0.35, 0.2, 16);
    const capMat = new THREE.MeshStandardMaterial({ color: 0x0284c7, metalness: 0.8 });
    const cap = new THREE.Mesh(capGeo, capMat);
    cap.position.y = 1.35;
    resGroup.add(cap);

    resGroup.userData = {
      type: 'component',
      id: 'RESERVOIR-01',
      name: 'Nanofluid Expansion Tank & Reservoir',
      capacity_liters: 4.5,
      pressure_rating_bar: 1.5
    };
    layerGroups.components.add(resGroup);
    componentMeshes['RESERVOIR-01'] = resGroup;

    // --------------------------------------------------------------------------
    // Component 8: Radiator with Cooling Fans & Shroud
    // --------------------------------------------------------------------------
    const radGroup = new THREE.Group();
    radGroup.position.set(0, 3.0, 13.0);

    // Radiator Outer Frame
    const radGeo = new THREE.BoxGeometry(11.4, 4.6, 0.75);
    const radMat = new THREE.MeshStandardMaterial({ color: 0x334155, metalness: 0.85, roughness: 0.25 });
    const radiator = new THREE.Mesh(radGeo, radMat);
    radGroup.add(radiator);

    // Fin array face
    const finGeo = new THREE.PlaneGeometry(10.6, 4.0);
    const finMat = new THREE.MeshStandardMaterial({
      color: 0x64748b,
      wireframe: true,
      wireframeLinewidth: 1.2
    });
    const finMesh = new THREE.Mesh(finGeo, finMat);
    finMesh.position.z = 0.39;
    radGroup.add(finMesh);

    // Fan Shroud & 7-Blade Rotating Fan
    const fanGroup = new THREE.Group();
    fanGroup.position.set(0, 0, -0.65);

    const shroudGeo = new THREE.CylinderGeometry(1.9, 1.9, 0.45, 32);
    const shroudMat = new THREE.MeshStandardMaterial({ color: 0x0f172a, roughness: 0.6 });
    const shroud = new THREE.Mesh(shroudGeo, shroudMat);
    shroud.rotation.x = Math.PI / 2;
    fanGroup.add(shroud);

    // Fan rotor & aerodynamic blades
    const rotor = new THREE.Group();
    const fanBladeGeo = new THREE.BoxGeometry(0.38, 1.6, 0.05);
    const fanBladeMat = new THREE.MeshStandardMaterial({ color: 0x1e293b, metalness: 0.4, roughness: 0.3 });
    for (let fb = 0; fb < 7; fb++) {
      const blade = new THREE.Mesh(fanBladeGeo, fanBladeMat);
      blade.rotation.z = (fb * 2 * Math.PI) / 7;
      blade.position.set(Math.cos((fb * 2 * Math.PI) / 7) * 0.75, Math.sin((fb * 2 * Math.PI) / 7) * 0.75, 0);
      rotor.add(blade);
    }
    fanGroup.add(rotor);
    fanRotor = rotor;
    radGroup.add(fanGroup);

    radGroup.userData = {
      type: 'component',
      id: 'RADIATOR-01',
      name: 'Front Heat Rejection Radiator & Electric Fan',
      q_reject_max_w: 12500,
      fan_rpm_max: 2800
    };
    layerGroups.components.add(radGroup);
    componentMeshes['RADIATOR-01'] = radGroup;

    // --------------------------------------------------------------------------
    // Component 9: Brazed Plate Refrigerant Chiller
    // --------------------------------------------------------------------------
    const chillerGroup = new THREE.Group();
    chillerGroup.position.set(-11.5, 1.8, -9.5);

    const chillerGeo = new THREE.BoxGeometry(3.4, 2.5, 1.9);
    const chillerMat = new THREE.MeshStandardMaterial({ color: 0x475569, metalness: 0.9, roughness: 0.15 });
    const chiller = new THREE.Mesh(chillerGeo, chillerMat);
    chillerGroup.add(chiller);

    // Refrigerant supply & suction ports
    const portGeo = new THREE.CylinderGeometry(0.2, 0.2, 0.5, 16);
    const portMat = new THREE.MeshStandardMaterial({ color: 0x3b82f6 });
    const refIn = new THREE.Mesh(portGeo, portMat);
    refIn.position.set(-1.0, 1.4, 0.5);
    chillerGroup.add(refIn);

    const refOut = new THREE.Mesh(portGeo, portMat);
    refOut.position.set(1.0, 1.4, 0.5);
    chillerGroup.add(refOut);

    chillerGroup.userData = {
      type: 'component',
      id: 'CHILLER-01',
      name: 'Brazed Plate Refrigerant Subcooler / Chiller',
      capacity_kw: 6.5,
      refrigerant: 'R1234yf'
    };
    layerGroups.components.add(chillerGroup);
    componentMeshes['CHILLER-01'] = chillerGroup;

    // --------------------------------------------------------------------------
    // Component 10: Dedicated Plate Heat Exchanger (HEX-01)
    // --------------------------------------------------------------------------
    const hexGroup = new THREE.Group();
    hexGroup.position.set(-6.0, 1.8, -9.5);

    const hexGeo = new THREE.BoxGeometry(2.6, 2.2, 1.6);
    const hexMat = new THREE.MeshStandardMaterial({ color: 0x64748b, metalness: 0.85, roughness: 0.2 });
    const hexMesh = new THREE.Mesh(hexGeo, hexMat);
    hexGroup.add(hexMesh);

    // Corrugated plate ridges
    const ridgeGeo = new THREE.BoxGeometry(2.7, 2.0, 0.06);
    const ridgeMat = new THREE.MeshStandardMaterial({ color: 0x94a3b8, metalness: 0.9 });
    for (let rg = -0.6; rg <= 0.6; rg += 0.2) {
      const ridge = new THREE.Mesh(ridgeGeo, ridgeMat);
      ridge.position.z = rg;
      hexGroup.add(ridge);
    }

    hexGroup.userData = {
      type: 'component',
      id: 'HEX-01',
      name: 'Counter-Flow Brazed Plate Heat Exchanger',
      u_value_w_m2k: 2450.0,
      area_m2: 0.85
    };
    layerGroups.components.add(hexGroup);
    componentMeshes['HEX-01'] = hexGroup;

    // --------------------------------------------------------------------------
    // Component 14: 3-Way Proportional Mixing Valve
    // --------------------------------------------------------------------------
    const valveGroup = new THREE.Group();
    valveGroup.position.set(14.5, 2.2, 7.0);

    const valveBodyGeo = new THREE.CylinderGeometry(0.55, 0.55, 1.3, 16);
    const valveBodyMat = new THREE.MeshStandardMaterial({ color: 0xd97706, metalness: 0.8, roughness: 0.25 });
    const valveBody = new THREE.Mesh(valveBodyGeo, valveBodyMat);
    valveGroup.add(valveBody);

    const actuatorGeo = new THREE.BoxGeometry(0.85, 0.95, 0.85);
    const actuatorMat = new THREE.MeshStandardMaterial({ color: 0x0f172a, roughness: 0.5 });
    const actuator = new THREE.Mesh(actuatorGeo, actuatorMat);
    actuator.position.y = 0.95;
    valveGroup.add(actuator);

    // Valve rotating indicator
    const needleGeo = new THREE.BoxGeometry(0.08, 0.45, 0.08);
    const needleMat = new THREE.MeshBasicMaterial({ color: 0x00e5ff });
    valveNeedle = new THREE.Mesh(needleGeo, needleMat);
    valveNeedle.position.set(0, 1.45, 0);
    valveGroup.add(valveNeedle);

    valveGroup.userData = {
      type: 'component',
      id: 'VALVE-01',
      name: '3-Way Proportional Nanofluid Flow Valve',
      kv_value: 4.2,
      actuation: 'Electric Stepper'
    };
    layerGroups.components.add(valveGroup);
    componentMeshes['VALVE-01'] = valveGroup;

    // BTMS Master Electronic Control Unit (ECU)
    const ecuGroup = new THREE.Group();
    ecuGroup.position.set(13.8, 1.4, -8.0);
    const ecuGeo = new THREE.BoxGeometry(2.5, 1.7, 2.1);
    const ecuMat = new THREE.MeshStandardMaterial({ color: 0x1e293b, metalness: 0.7, roughness: 0.25 });
    const ecu = new THREE.Mesh(ecuGeo, ecuMat);
    ecuGroup.add(ecu);

    // Status LEDs
    const ledGeo = new THREE.SphereGeometry(0.09, 12, 12);
    const led1 = new THREE.Mesh(ledGeo, new THREE.MeshBasicMaterial({ color: 0x00e676 }));
    led1.position.set(0.4, 0.55, 1.07);
    const led2 = new THREE.Mesh(ledGeo, new THREE.MeshBasicMaterial({ color: 0x00d4ff }));
    led2.position.set(0.7, 0.55, 1.07);
    ecuGroup.add(led1);
    ecuGroup.add(led2);

    ecuGroup.userData = {
      type: 'component',
      id: 'CONTROLLER-01',
      name: 'BTMS Master Electronic Control Unit (ECU)'
    };
    layerGroups.components.add(ecuGroup);
    componentMeshes['CONTROLLER-01'] = ecuGroup;
  }

  /**
   * Component 4 & 14: Continuous Nanofluid Pipelines Connecting the Complete Loop
   */
  function buildPipelines() {
    pipeMeshes = [];

    function createPipeline(points, colorHex, pipeRadius = 0.22, name = 'Coolant Line', pipeId = 'PIPE-01') {
      const curve = new THREE.CatmullRomCurve3(points);
      const pipeGeo = new THREE.TubeGeometry(curve, 64, pipeRadius, 16, false);
      const pipeMat = new THREE.MeshStandardMaterial({
        color: colorHex,
        transparent: true,
        opacity: 0.88,
        roughness: 0.2,
        metalness: 0.6
      });
      const pipeMesh = new THREE.Mesh(pipeGeo, pipeMat);
      pipeMesh.castShadow = true;
      pipeMesh.receiveShadow = true;
      pipeMesh.userData = {
        type: 'pipe',
        id: pipeId,
        name: name,
        material: 'Anodized 6061-T6 Aluminum Tube',
        inner_dia_mm: (pipeRadius * 2 * 10).toFixed(1)
      };
      layerGroups.pipes.add(pipeMesh);
      pipeMeshes.push(pipeMesh);
      componentMeshes[pipeId] = pipeMesh;
      return pipeMesh;
    }

    // 1. Hot Return: Battery Continuous Serpentine Outlet (-10.05, 1.53, +4.38) -> 3-Way Valve (14.5, 2.2, 7.0)
    createPipeline([
      new THREE.Vector3(-10.05, 1.53, 4.38),
      new THREE.Vector3(-10.8, 1.6, 6.8),
      new THREE.Vector3(0.0, 1.8, 8.2),
      new THREE.Vector3(10.5, 2.0, 7.8),
      new THREE.Vector3(14.5, 2.2, 7.0)
    ], 0xff3d00, 0.24, 'Battery Hot Nanofluid Return Pipe', 'PIPE-01');

    // 2. Hot to Radiator: 3-Way Valve (14.5, 2.2, 7.0) -> Radiator Inlet (5.5, 3.2, 13.0)
    createPipeline([
      new THREE.Vector3(14.5, 2.2, 7.0),
      new THREE.Vector3(12.5, 2.6, 10.5),
      new THREE.Vector3(5.5, 3.2, 13.0)
    ], 0xff6d00, 0.24, 'Hot Nanofluid to Radiator Supply Pipe', 'PIPE-02');

    // 3. Radiator Cooled Return: Radiator Outlet (-5.5, 1.8, 13.0) -> Reservoir Inlet (-18.5, 4.8, -6.5)
    createPipeline([
      new THREE.Vector3(-5.5, 1.8, 13.0),
      new THREE.Vector3(-12.5, 2.5, 10.5),
      new THREE.Vector3(-18.5, 3.6, 2.0),
      new THREE.Vector3(-18.5, 4.8, -6.5)
    ], 0x2979ff, 0.24, 'Radiator Cooled Return Pipe', 'PIPE-03');

    // 4. Reservoir Down to Pump Suction
    createPipeline([
      new THREE.Vector3(-18.5, 3.4, -7.5),
      new THREE.Vector3(-18.2, 2.6, -7.5),
      new THREE.Vector3(-18.5, 1.8, -7.5)
    ], 0x00b0ff, 0.22, 'Reservoir to Pump Suction Downcomer', 'PIPE-04');

    // 5. Pump Discharge: Pump Outlet (-17.0, 1.8, -7.5) -> Chiller Inlet (-13.5, 1.8, -9.5)
    createPipeline([
      new THREE.Vector3(-17.0, 1.8, -7.5),
      new THREE.Vector3(-15.2, 1.8, -8.6),
      new THREE.Vector3(-13.5, 1.8, -9.5)
    ], 0x00d4ff, 0.22, 'Pump High-Pressure Discharge Pipe', 'PIPE-05');

    // 6. Chiller to Heat Exchanger Line
    createPipeline([
      new THREE.Vector3(-9.5, 1.8, -9.5),
      new THREE.Vector3(-8.5, 1.8, -9.5),
      new THREE.Vector3(-7.5, 1.8, -9.5)
    ], 0x00e5ff, 0.22, 'Chiller to Heat Exchanger Inter-Line', 'PIPE-06');

    // 7. Cold Line: Heat Exchanger (-4.5, 1.8, -9.5) -> Battery Continuous Serpentine Inlet (-10.05, 1.53, -4.38)
    createPipeline([
      new THREE.Vector3(-4.5, 1.8, -9.5),
      new THREE.Vector3(-8.5, 1.8, -8.0),
      new THREE.Vector3(-10.2, 1.6, -6.5),
      new THREE.Vector3(-10.05, 1.53, -4.38)
    ], 0x00d4ff, 0.24, 'Chilled Nanofluid Pack Supply Line', 'PIPE-07');

    // 8. Valve Chiller Bypass Line
    createPipeline([
      new THREE.Vector3(14.5, 2.2, 7.0),
      new THREE.Vector3(9.5, 1.0, 0.0),
      new THREE.Vector3(0.0, 1.0, -8.0),
      new THREE.Vector3(-11.5, 1.8, -9.5)
    ], 0x9333ea, 0.16, '3-Way Proportional Bypass Line', 'PIPE-08');
  }

  /**
   * Components 11, 12, 13: Temperature Sensors, Flow Sensors, Pressure Sensors
   */
  function buildSensorsAndInstrumentation() {
    function createTempSensor(id, name, pos) {
      const sGroup = new THREE.Group();
      sGroup.position.copy(pos);

      const hexGeo = new THREE.CylinderGeometry(0.18, 0.18, 0.2, 6);
      const hexMat = new THREE.MeshStandardMaterial({ color: 0xd97706, metalness: 0.8 });
      const hexMesh = new THREE.Mesh(hexGeo, hexMat);
      sGroup.add(hexMesh);

      const probeGeo = new THREE.CylinderGeometry(0.08, 0.08, 0.45, 16);
      const probeMat = new THREE.MeshStandardMaterial({ color: 0x94a3b8, metalness: 0.9 });
      const probe = new THREE.Mesh(probeGeo, probeMat);
      probe.position.y = 0.28;
      sGroup.add(probe);

      const wireGeo = new THREE.CylinderGeometry(0.04, 0.04, 0.35, 8);
      const wireMat = new THREE.MeshBasicMaterial({ color: 0xfacc15 });
      const wire = new THREE.Mesh(wireGeo, wireMat);
      wire.position.y = 0.55;
      sGroup.add(wire);

      sGroup.userData = {
        type: 'component',
        id: id,
        name: name,
        sensor_type: 'PT100 RTD Class A (±0.15°C)'
      };
      layerGroups.components.add(sGroup);
      componentMeshes[id] = sGroup;
    }

    createTempSensor('TEMP-SENSOR-01', 'T-01: Coolant Inlet Temperature Sensor', new THREE.Vector3(-13.6, 2.7, -2.5));
    createTempSensor('TEMP-SENSOR-02', 'T-02: Coolant Outlet Temperature Sensor', new THREE.Vector3(13.6, 2.7, 2.5));
    createTempSensor('TEMP-SENSOR-03', 'T-03: Pack Core Hotspot Temperature Sensor', new THREE.Vector3(0, 2.2, 0));
    createTempSensor('TEMP-SENSOR-04', 'T-04: Radiator Return Temperature Sensor', new THREE.Vector3(-5.5, 2.4, 13.0));

    // Flow Sensor
    const flowSensorGroup = new THREE.Group();
    flowSensorGroup.position.set(-11.5, 1.8, -8.2);

    const bodyGeo = new THREE.CylinderGeometry(0.42, 0.42, 0.8, 24);
    const bodyMat = new THREE.MeshStandardMaterial({ color: 0x0284c7, metalness: 0.7, roughness: 0.3 });
    const meterBody = new THREE.Mesh(bodyGeo, bodyMat);
    meterBody.rotation.z = Math.PI / 2;
    flowSensorGroup.add(meterBody);

    const headGeo = new THREE.BoxGeometry(0.65, 0.65, 0.5);
    const headMat = new THREE.MeshStandardMaterial({ color: 0x0f172a, roughness: 0.4 });
    const headMesh = new THREE.Mesh(headGeo, headMat);
    headMesh.position.y = 0.6;
    flowSensorGroup.add(headMesh);

    const screenGeo = new THREE.PlaneGeometry(0.45, 0.28);
    const screenMat = new THREE.MeshBasicMaterial({ color: 0x00e676 });
    const screenMesh = new THREE.Mesh(screenGeo, screenMat);
    screenMesh.position.set(0, 0.6, 0.26);
    flowSensorGroup.add(screenMesh);

    flowSensorGroup.userData = {
      type: 'component',
      id: 'FLOW-SENSOR-01',
      name: 'FL-01: Ultrasonic Coolant Flow Meter',
      range_lpm: '0 - 50 L/min',
      accuracy: '±0.5% FS'
    };
    layerGroups.components.add(flowSensorGroup);
    componentMeshes['FLOW-SENSOR-01'] = flowSensorGroup;

    // Pressure Sensors
    function createPressureSensor(id, name, pos) {
      const pGroup = new THREE.Group();
      pGroup.position.copy(pos);

      const stemGeo = new THREE.CylinderGeometry(0.08, 0.08, 0.4, 16);
      const stemMat = new THREE.MeshStandardMaterial({ color: 0x94a3b8, metalness: 0.9 });
      const stem = new THREE.Mesh(stemGeo, stemMat);
      stem.position.y = 0.2;
      pGroup.add(stem);

      const dialGeo = new THREE.CylinderGeometry(0.35, 0.35, 0.2, 24);
      const dialMat = new THREE.MeshStandardMaterial({ color: 0x1e293b, metalness: 0.6 });
      const dial = new THREE.Mesh(dialGeo, dialMat);
      dial.rotation.x = Math.PI / 2;
      dial.position.y = 0.55;
      pGroup.add(dial);

      const faceGeo = new THREE.CircleGeometry(0.3, 24);
      const faceMat = new THREE.MeshBasicMaterial({ color: 0xffffff });
      const face = new THREE.Mesh(faceGeo, faceMat);
      face.position.set(0, 0.55, 0.11);
      pGroup.add(face);

      pGroup.userData = {
        type: 'component',
        id: id,
        name: name,
        sensor_type: 'Piezoresistive Pressure Transmitter (0 - 400 kPa)'
      };
      layerGroups.components.add(pGroup);
      componentMeshes[id] = pGroup;
    }

    createPressureSensor('PRESS-SENSOR-01', 'P-01: Pump Discharge Pressure Gauge', new THREE.Vector3(-17.0, 2.3, -7.5));
    createPressureSensor('PRESS-SENSOR-02', 'P-02: Pack Differential Pressure Gauge', new THREE.Vector3(13.6, 2.7, 3.5));
  }

  /**
   * Builds the 10 Clickable Sampling Stations along the loop.
   */
  function buildSamplingStations() {
    stationMarkers = [];
    const stationPositions = [
      { id: 1, name: 'Pump Discharge (Station 1)', pos: new THREE.Vector3(-16.0, 1.8, -7.8) },
      { id: 2, name: 'Chiller Inlet (Station 2)', pos: new THREE.Vector3(-13.5, 1.8, -9.5) },
      { id: 3, name: 'Chiller Outlet (Station 3)', pos: new THREE.Vector3(-9.5, 1.8, -9.5) },
      { id: 4, name: 'Battery Inlet Manifold (Station 4)', pos: new THREE.Vector3(-13.6, 2.2, -2.5) },
      { id: 5, name: 'Inter-Row Channel Mid-Pack (Station 5)', pos: new THREE.Vector3(-4.0, 1.95, -0.75) },
      { id: 6, name: 'Inter-Row Channel Core (Station 6)', pos: new THREE.Vector3(3.0, 1.95, 0.75) },
      { id: 7, name: 'Battery Outlet Manifold (Station 7)', pos: new THREE.Vector3(13.6, 2.2, 2.5) },
      { id: 8, name: '3-Way Valve Inlet (Station 8)', pos: new THREE.Vector3(14.5, 2.2, 7.0) },
      { id: 9, name: 'Radiator Inlet (Station 9)', pos: new THREE.Vector3(5.5, 3.2, 13.0) },
      { id: 10, name: 'Radiator Outlet Return (Station 10)', pos: new THREE.Vector3(-5.5, 1.8, 13.0) }
    ];

    const markerSphereGeo = new THREE.SphereGeometry(0.32, 16, 16);
    const ringGeo = new THREE.RingGeometry(0.42, 0.58, 24);

    stationPositions.forEach(st => {
      const stationGroup = new THREE.Group();
      stationGroup.position.copy(st.pos);

      // Inner glowing sphere
      const sphereMat = new THREE.MeshBasicMaterial({ color: 0x00d4ff });
      const sphereMesh = new THREE.Mesh(markerSphereGeo, sphereMat);
      stationGroup.add(sphereMesh);

      // Outer pulsing ring
      const ringMat = new THREE.MeshBasicMaterial({
        color: 0x00e676,
        side: THREE.DoubleSide,
        transparent: true,
        opacity: 0.75
      });
      const ringMesh = new THREE.Mesh(ringGeo, ringMat);
      ringMesh.rotation.x = Math.PI / 2;
      stationGroup.add(ringMesh);

      stationGroup.userData = {
        type: 'station',
        stationId: st.id,
        id: `STATION-${String(st.id).padStart(2, '0')}`,
        name: st.name,
        ringMesh: ringMesh
      };

      stationMarkers.push(stationGroup);
      layerGroups.stations.add(stationGroup);
    });
  }

  /**
   * Component 4: 2,000+ Moving Nanoparticles Inside the 6 Module Serpentine Channels & Closed Loop
   * Speed strictly tied to pump duty/velocity; zero-flow physics when pump is OFF.
   */
  function buildNanoparticleSystem() {
    if (particleInstancedMesh && layerGroups.particles.children.includes(particleInstancedMesh)) {
      layerGroups.particles.remove(particleInstancedMesh);
      if (particleInstancedMesh.geometry) particleInstancedMesh.geometry.dispose();
      if (particleInstancedMesh.material) particleInstancedMesh.material.dispose();
    }

    const sphereGeo = new THREE.SphereGeometry(0.045, 8, 8);
    const particleMat = new THREE.MeshStandardMaterial({
      roughness: 0.2,
      metalness: 0.6
    });

    particleInstancedMesh = new THREE.InstancedMesh(sphereGeo, particleMat, particleCount);
    particleInstancedMesh.instanceMatrix.setUsage(THREE.DynamicDrawUsage);

    if (particleInstancedMesh.setColorAt) {
      particleInstancedMesh.setColorAt(0, new THREE.Color(0x00d4ff));
      if (particleInstancedMesh.instanceColor) {
        particleInstancedMesh.instanceColor.setUsage(THREE.DynamicDrawUsage);
      }
    }

    const dummy = new THREE.Object3D();
    const cellHeight = STATE.formFactor === '18650' ? 2.10 : 2.40;
    particleData = [];

    // 85% stream through the ONE continuous 10-pass serpentine cooling channel
    const serpentineParticles = Math.floor(particleCount * 0.85);

    for (let i = 0; i < serpentineParticles; i++) {
      const progress = Math.random(); // Full continuous 10-pass progression (0.0 at Inlet to 1.0 at Outlet)
      const passY = 0.55 + Math.random() * (cellHeight - 0.35); // Distributed vertically across 70 mm channel height
      const isCopper = Math.random() < 0.35;

      particleData.push({
        type: 'serpentine',
        progress: progress,
        yPos: passY,
        speedOffset: 0.85 + Math.random() * 0.3,
        isCopper: isCopper
      });

      if (continuousSerpentineSpline) {
        const pt = continuousSerpentineSpline.getPointAt(progress);
        dummy.position.set(pt.x, passY, pt.z);
      } else {
        dummy.position.set(0, passY, 0);
      }
      dummy.updateMatrix();
      particleInstancedMesh.setMatrixAt(i, dummy.matrix);

      if (particleInstancedMesh.setColorAt) {
        particleInstancedMesh.setColorAt(i, isCopper ? new THREE.Color(0xd97706) : new THREE.Color(0x00e5ff));
      }
    }

    // 15% stream along the external circulation loop
    for (let i = serpentineParticles; i < particleCount; i++) {
      const loopProgress = Math.random();
      const isCopper = Math.random() < 0.4;
      particleData.push({
        type: 'loop',
        progress: loopProgress,
        speedOffset: 0.9 + Math.random() * 0.2,
        isCopper: isCopper
      });

      const angle = loopProgress * Math.PI * 2;
      const xPos = -5.0 + 14.0 * Math.cos(angle);
      const zPos = 2.0 + 10.0 * Math.sin(angle);
      dummy.position.set(xPos, 1.8, zPos);
      dummy.updateMatrix();
      particleInstancedMesh.setMatrixAt(i, dummy.matrix);

      if (particleInstancedMesh.setColorAt) {
        particleInstancedMesh.setColorAt(i, isCopper ? new THREE.Color(0xd97706) : new THREE.Color(0x00e5ff));
      }
    }

    particleInstancedMesh.instanceMatrix.needsUpdate = true;
    if (particleInstancedMesh.instanceColor) {
      particleInstancedMesh.instanceColor.needsUpdate = true;
    }
    layerGroups.particles.add(particleInstancedMesh);
  }

  /**
   * Directional Animated Flow Arrows along the loops
   */
  function buildFlowDirectionArrows() {
    flowArrows = [];
    const arrowPositions = [
      { pos: new THREE.Vector3(-14.0, 2.0, -4.0), dir: new THREE.Vector3(0.2, 0.0, 0.9) },
      { pos: new THREE.Vector3(-6.0, 1.95, -0.75), dir: new THREE.Vector3(1, 0, 0) },
      { pos: new THREE.Vector3(6.0, 1.95, 0.75), dir: new THREE.Vector3(1, 0, 0) },
      { pos: new THREE.Vector3(14.5, 2.0, 4.5), dir: new THREE.Vector3(0, 0.1, 0.9) },
      { pos: new THREE.Vector3(10.0, 2.8, 11.5), dir: new THREE.Vector3(-0.8, 0.1, 0.5) },
      { pos: new THREE.Vector3(-10.0, 2.2, 8.5), dir: new THREE.Vector3(-0.6, 0.1, -0.8) }
    ];

    arrowPositions.forEach(ap => {
      const arrowHelper = new THREE.ArrowHelper(
        ap.dir.clone().normalize(),
        ap.pos,
        1.1,
        0x00e5ff,
        0.35,
        0.22
      );
      flowArrows.push(arrowHelper);
      layerGroups.pipes.add(arrowHelper);
    });
  }

  /**
   * Heat Flux Indicators: Animated thermal arrows from battery cells into the cooling plates
   */
  function buildHeatFluxArrows() {
    heatFluxArrows = [];
    const arrowGeo = new THREE.ConeGeometry(0.12, 0.35, 8);
    const arrowMat = new THREE.MeshBasicMaterial({ color: 0xf97316, transparent: true, opacity: 0.8 });

    // Place thermal arrows between cell rows and inter-row plates
    const sampleCells = [12, 17, 22, 27, 32, 37];
    sampleCells.forEach(cellIdx => {
      if (cellIdx < cellMeshes.length) {
        const cellPos = cellMeshes[cellIdx].position;
        const arrowMesh = new THREE.Mesh(arrowGeo, arrowMat);
        arrowMesh.position.set(cellPos.x, cellPos.y, cellPos.z + 0.55);
        arrowMesh.rotation.x = Math.PI / 2; // Pointing towards cooling plate
        layerGroups.channels.add(arrowMesh);
        heatFluxArrows.push(arrowMesh);
      }
    });
  }

  // ============================================================================
  // 4. ANIMATION & RENDER LOOP
  // ============================================================================
  let clock = null;
  let stepTimer = 0;

  function animate() {
    requestAnimationFrame(animate);

    if (!clock) clock = new THREE.Clock();
    const delta = clock.getDelta();
    const elapsedTime = clock.getElapsedTime();

    // 1. Smooth Camera Transition
    if (cameraTarget && cameraTarget.animating && camera && controls) {
      camera.position.lerp(cameraTarget.position, 0.08);
      controls.target.lerp(cameraTarget.lookAt, 0.08);
      if (camera.position.distanceTo(cameraTarget.position) < 0.15) {
        cameraTarget.animating = false;
      }
    }

    // 2. Cooling Actuator Motion: Impeller, Fan, and 3-Way Valve
    // ZERO-FLOW LOGIC: When pumpDuty == 0, pump & fan DO NOT ROTATE!
    const isCoolingActive = STATE.pumpDuty > 0;

    if (pumpImpeller) {
      if (isCoolingActive) {
        const pumpSpeed = (STATE.pumpDuty / 100.0) * 0.35;
        pumpImpeller.rotation.x += pumpSpeed * STATE.timeWarp;
      }
    }
    if (fanRotor) {
      if (STATE.fanDuty > 0) {
        const fanSpeed = (STATE.fanDuty / 100.0) * 0.45;
        fanRotor.rotation.z += fanSpeed * STATE.timeWarp;
      }
    }
    if (valveNeedle) {
      const targetAngle = (STATE.valvePos / 100.0) * (Math.PI / 2);
      valveNeedle.rotation.y = targetAngle;
    }

    // 3. Nanoparticle Flow Animation Inside Serpentine S-Channels & External Pipes
    // ZERO-FLOW LOGIC: When cooling is OFF (pumpDuty == 0), particles MUST FREEZE!
    // ADAPTIVE ZONAL SPEED: In overheated zones, valve opens up to 100% and velocity surges!
    if (particleInstancedMesh && particleInstancedMesh.visible) {
      const dummy = new THREE.Object3D();
      const baseFlow = isCoolingActive ? (STATE.uIn * (STATE.pumpDuty / 100.0)) : 0.0;
      const baseSpeed = baseFlow * delta * STATE.timeWarp * 2.2;

      if (isCoolingActive) {
        for (let i = 0; i < particleData.length; i++) {
          const p = particleData[i];

          if (p.type === 'serpentine' || p.type === 'module_serpentine' || p.type === 'wavy_channel') {
            const spline = continuousSerpentineSpline || (moduleSplines && moduleSplines[p.moduleId]);
            const approxCellIdx = Math.min(179, Math.max(0, Math.floor(p.progress * 180)));
            const cellData = (STATE.cells && STATE.cells[approxCellIdx]);
            const cellTemp = cellData ? (cellData.temp_c ?? cellData.temperature_c ?? cellData.temp ?? 25.0) : (STATE.tIn || 20.0);

            // Solver-derived local fluid velocity with acceleration in overheated zones (Requirements 4 & 9)
            const localSolverVel = (cellData && cellData.local_velocity_m_s) ? cellData.local_velocity_m_s : (STATE.uIn || 0.25);
            const localOverheatBoost = (cellTemp >= 45.0) ? 2.2 : ((cellTemp >= 35.0) ? 1.6 : 1.0);
            const flowSpeed = (localSolverVel * (STATE.pumpDuty / 100.0) * localOverheatBoost) * delta * STATE.timeWarp * 1.6 * p.speedOffset * 0.055;
            p.progress = (p.progress + flowSpeed) % 1.0;

            if (spline) {
              const pt = spline.getPointAt(p.progress);
              dummy.position.set(pt.x, p.yPos, pt.z);
            }
          } else {
            // Closed-loop external pipe circulation
            p.progress = (p.progress + baseSpeed * p.speedOffset * 0.1) % 1.0;
            const angle = p.progress * Math.PI * 2;
            const xPos = -5.0 + 14.0 * Math.cos(angle);
            const zPos = 2.0 + 10.0 * Math.sin(angle);
            dummy.position.set(xPos, 1.8, zPos);
          }

          dummy.updateMatrix();
          particleInstancedMesh.setMatrixAt(i, dummy.matrix);

          if (particleInstancedMesh.setColorAt) {
            // Section 4 Particle Coloring:
            // - Blue for cold incoming nanofluid (< 0.20 progress)
            // - Cyan for normal circulation (0.20 to 0.70 progress)
            // - Orange for warmed outgoing nanofluid (>= 0.70 progress)
            // - Red/Yellow when passing near active overheated hotspot cells
            const approxCellIdx = Math.min(179, Math.max(0, Math.floor(p.progress * 180)));
            const cellData = (STATE.cells && STATE.cells[approxCellIdx]);
            const cellTemp = cellData ? (cellData.temp_c ?? cellData.temperature_c ?? cellData.temp ?? 25.0) : (STATE.tIn || 20.0);

            const partColor = new THREE.Color();
            if (cellTemp > 45.0) {
              partColor.setHex(0xef4444); // Red: Absorbing heat near Overheated Hotspot
            } else if (cellTemp >= 35.0) {
              partColor.setHex(0xfacc15); // Yellow: Warm Hotspot Zone
            } else if (p.progress < 0.20) {
              partColor.setHex(0x0077ff); // Blue: Cold Incoming Nanofluid
            } else if (p.progress < 0.70) {
              partColor.setHex(0x00e5ff); // Cyan: Normal Circulation
            } else {
              partColor.setHex(0xf97316); // Orange: Warmed Outgoing Nanofluid
            }
            if (p.isCopper) {
              partColor.lerp(new THREE.Color(0xd97706), 0.30); // Copper nanoparticle tone
            }
            particleInstancedMesh.setColorAt(i, partColor);
          }
        }
        particleInstancedMesh.instanceMatrix.needsUpdate = true;
        if (particleInstancedMesh.instanceColor) {
          particleInstancedMesh.instanceColor.needsUpdate = true;
        }
      }
    }

    // 3B. Exploded View Smooth Layer Interpolation
    if (layerGroups.electrical) {
      const targetElecY = STATE.explodedView ? 1.8 : 0.0;
      layerGroups.electrical.position.y = THREE.MathUtils.lerp(layerGroups.electrical.position.y, targetElecY, 0.08);
    }
    const housingTray = layerGroups.plates ? layerGroups.plates.getObjectByName('PACK-HOUSING') : null;
    if (housingTray) {
      const targetTrayY = STATE.explodedView ? -1.8 : 0.0;
      housingTray.position.y = THREE.MathUtils.lerp(housingTray.position.y, targetTrayY, 0.08);
    }

    // 4. Station Rings Pulsing
    stationMarkers.forEach((st, idx) => {
      const ring = st.userData.ringMesh;
      if (ring) {
        const scale = 1.0 + 0.22 * Math.sin(elapsedTime * 4.0 + idx);
        ring.scale.set(scale, scale, 1);
      }
    });

    // 5. Pulsing Warning for Cells Exceeding Threshold
    cellMeshes.forEach(cell => {
      if (cell.userData.temp_c >= STATE.thresholdC) {
        const pulse = 0.5 + 0.5 * Math.sin(elapsedTime * 6.0);
        cell.material.emissive = new THREE.Color(0xef4444).multiplyScalar(pulse * 0.6);
      } else {
        cell.material.emissive.setHex(0x000000);
      }
    });

    // 6. Heat Flux Arrows Pulsing
    heatFluxArrows.forEach((arr, idx) => {
      arr.visible = isCoolingActive;
      if (isCoolingActive) {
        const pulse = 0.7 + 0.3 * Math.sin(elapsedTime * 8.0 + idx);
        arr.scale.set(pulse, pulse, pulse);
      }
    });

    // 7. Simulation Step Execution
    if (STATE.isRunning) {
      stepTimer += delta;
      if (stepTimer >= 0.15) {
        stepTimer = 0;
        advanceSimulationStep(STATE.dt * STATE.timeWarp);
      }
    }

    if (controls) controls.update();
    if (renderer && scene && camera) {
      renderer.render(scene, camera);
    }
  }

  // ============================================================================
  // 5. SIMULATION API INTEGRATION & TELEMETRY
  // ============================================================================

  async function advanceSimulationStep(dtStep) {
    try {
      const res = await fetch('/api/step', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ dt: dtStep })
      });
      if (!res.ok) {
        runLocalPhysicsStep(dtStep);
        return;
      }
      const data = await res.json();
      applyTelemetryUpdate(data);
    } catch (e) {
      runLocalPhysicsStep(dtStep);
    }
  }

  function applyTelemetryUpdate(data) {
    STATE.simTime = data.sim_time_s || (STATE.simTime + STATE.dt);
    STATE.tMax = data.pack_max_temp_c || 25.0;
    STATE.tAvg = data.pack_avg_temp_c || 25.0;
    STATE.tMin = data.pack_min_temp_c || 25.0;
    STATE.pumpDuty = data.controller?.pump_duty_cycle_pct ?? data.controller?.pump_speed_pct ?? 0.0;
    STATE.fanDuty = data.controller?.fan_duty_cycle_pct ?? data.controller?.fan_speed_pct ?? 0.0;
    STATE.valvePos = data.controller?.valve_position_pct ?? 0.0;
    STATE.uIn = data.flow_velocity_m_s || STATE.uIn;
    STATE.thresholdC = data.controller?.threshold_c ?? STATE.thresholdC;
    STATE.deactThresholdC = data.controller?.deactivation_threshold_c ?? STATE.deactThresholdC;

    // Advanced Continuous Operations & BMS State
    STATE.deltaT = data.delta_t_pack_c ?? data.battery_pack?.delta_t_pack_c ?? (STATE.tMax - STATE.tMin);
    STATE.bmsStatus = data.bms_status || data.bms?.status || (STATE.tMax >= 55.0 ? 'DERATED (Power Limit Active)' : 'NORMAL');
    STATE.bmsDerateActive = data.bms_derate_active ?? data.bms?.derate_active ?? (STATE.tMax >= 55.0);
    STATE.bmsDerateFactor = data.bms_derate_factor ?? data.bms?.derate_factor ?? 1.0;
    STATE.cellCounts = data.cell_counts || data.bms?.cell_counts || {
      normal: data.cells?.filter(c => c.temp_c <= 34.0).length ?? 180,
      elevated: data.cells?.filter(c => c.temp_c > 34.0 && c.temp_c <= 45.0).length ?? 0,
      overheated: data.cells?.filter(c => c.temp_c > 45.0 && c.temp_c <= 60.0).length ?? 0,
      critical: data.cells?.filter(c => c.temp_c > 60.0).length ?? 0,
    };
    STATE.activeHotspotEvents = data.active_hotspot_events || data.battery_pack?.active_hotspot_events || [];
    STATE.hotspotHistory = data.hotspot_event_history || data.battery_pack?.hotspot_event_history || [];
    STATE.pumpEnergyConsumedJ = data.pump_energy_consumed_j ?? data.hydraulics?.pump_energy_consumed_j ?? 0.0;
    STATE.pumpPowerW = data.hydraulics?.p_electrical_w ?? 0.0;

    // 8-State State Machine Display
    STATE.stateId = data.controller?.state_id || 1;
    STATE.stateName = data.controller?.state_name || 'OFF';
    STATE.systemStatus = data.system_status || data.controller?.status || 'NORMAL';

    // 1. Update Cylindrical Cells in 3D scene (500+ cells)
    if (data.cells && data.cells.length > 0) {
      const nUpdate = Math.min(data.cells.length, cellMeshes.length);
      for (let i = 0; i < nUpdate; i++) {
        const cData = data.cells[i];
        const mesh = cellMeshes[i];
        if (mesh) {
          mesh.userData.temp_c = cData.temp_c;
          mesh.userData.heat_w = cData.heat_generation_w || cData.heat_w;
          const targetColor = getThermalColor(cData.temp_c, STATE.thresholdC);
          mesh.material.color.copy(targetColor);
        }
        STATE.cells[i] = cData;
      }
    }

    // 1B. Update 6 Battery Modules & Zonal Adaptive Cooling Telemetry
    if (data.modules) {
      STATE.modules = data.modules;
    }
    if (data.electrical_validation) {
      STATE.electrical_validation = data.electrical_validation;
      const elElecBadge = document.getElementById('electrical-validation-badge');
      if (elElecBadge) {
        if (data.electrical_validation.is_valid_series) {
          elElecBadge.className = 'status-badge normal';
          elElecBadge.innerText = '⚡ 180S1P: VALID (666.0V)';
        } else {
          elElecBadge.className = 'status-badge critical';
          elElecBadge.innerText = '⚠️ 180S1P: FAULT DETECTED';
        }
      }
    }

    if (data.modules || data.zones) {
      STATE.zones = data.zones || {};
      const zoneContainer = document.getElementById('zonal-telemetry-container');
      const activeCountBadge = document.getElementById('zonal-active-count');
      if (zoneContainer) {
        let activeCount = 0;
        let html = '';

        if (data.modules && Object.keys(data.modules).length > 0) {
          MODULE_CONFIG.forEach(mInfo => {
            const mData = data.modules[mInfo.id] || {};
            const maxT = mData.temp_max_c ?? mData.max_temp_c ?? 25.0;
            const avgT = mData.temp_avg_c ?? mData.avg_temp_c ?? 25.0;
            const valvePct = mData.valve_opening_pct ?? ((mData.valve_position ?? 0.0) * 100);
            const vel = mData.velocity_m_s ?? 0.0;
            const flowL = mData.flow_rate_l_min ?? 0.0;
            const status = mData.status || (valvePct > 50 ? 'SURGE' : (valvePct > 20 ? 'ACTIVE' : 'IDLE'));
            const isSurge = valvePct > 40;
            if (isSurge) activeCount++;

            const statusColor = isSurge ? '#ef4444' : (valvePct > 20 ? '#f59e0b' : '#00e5ff');
            const barColor = isSurge ? '#ef4444' : (valvePct > 20 ? '#f59e0b' : '#00acc1');
            const tempColor = maxT > 45.0 ? '#ef4444' : (maxT > 34.0 ? '#eab308' : '#22c55e');

            html += `
              <div style="display: flex; align-items: center; justify-content: space-between; padding: 3px 6px; background: rgba(0,0,0,0.25); border-radius: 3px; margin-bottom: 2px;">
                <span style="font-weight: 700; color: #94a3b8; width: 62px;">${mInfo.name}:</span>
                <span style="color: ${tempColor}; font-weight: 700; width: 48px; font-size: 10px;">${maxT.toFixed(1)}°C</span>
                <span style="color: ${statusColor}; font-weight: 700; width: 55px; font-size: 9.5px;">${status}</span>
                <span style="color: #cbd5e1; width: 48px; text-align: right;">${vel.toFixed(2)} m/s</span>
                <div style="width: 45px; background: #1e293b; height: 6px; border-radius: 3px; overflow: hidden; margin-left: 6px;">
                  <div style="width: ${Math.min(100, valvePct)}%; background: ${barColor}; height: 100%;"></div>
                </div>
                <span style="color: #94a3b8; width: 30px; text-align: right; font-size: 9px;">${valvePct.toFixed(0)}%</span>
              </div>
            `;
          });
          if (activeCountBadge) {
            activeCountBadge.innerText = `${activeCount}/6 ACTIVE`;
            activeCountBadge.style.color = activeCount > 0 ? '#ef4444' : 'var(--accent-cyan)';
          }
        } else {
          for (let z = 1; z <= 10; z++) {
            const zData = data.zones[z] || data.zones[String(z)] || {
              valve_opening_pct: 15.0,
              velocity_m_s: 0.05,
              flow_rate_l_min: 0.12,
              max_temp_c: 25.0,
              status: 'IDLE'
            };
            const valvePct = zData.valve_opening_pct != null ? zData.valve_opening_pct : (zData.valve_position_pct ?? 15.0);
            const vel = zData.velocity_m_s != null ? zData.velocity_m_s : 0.05;
            const status = zData.status || (valvePct > 50 ? 'SURGE' : (valvePct > 20 ? 'MODERATE' : 'IDLE'));
            const isSurge = valvePct > 40;
            if (isSurge) activeCount++;

            const statusColor = isSurge ? '#ef4444' : (valvePct > 20 ? '#f59e0b' : '#00e5ff');
            const barColor = isSurge ? '#ef4444' : (valvePct > 20 ? '#f59e0b' : '#00acc1');

            html += `
              <div style="display: flex; align-items: center; justify-content: space-between; padding: 2px 4px; background: rgba(0,0,0,0.2); border-radius: 2px;">
                <span style="font-weight: 700; color: #94a3b8; width: 56px;">ZONE-${String(z).padStart(2, '0')}:</span>
                <span style="color: ${statusColor}; font-weight: 700; width: 65px; font-size: 9.5px;">${status}</span>
                <span style="color: #cbd5e1; width: 55px; text-align: right;">${vel.toFixed(2)} m/s</span>
                <div style="width: 50px; background: #1e293b; height: 6px; border-radius: 3px; overflow: hidden; margin-left: 6px;">
                  <div style="width: ${Math.min(100, valvePct)}%; background: ${barColor}; height: 100%;"></div>
                </div>
                <span style="color: #94a3b8; width: 32px; text-align: right; font-size: 9px;">${valvePct.toFixed(0)}%</span>
              </div>
            `;
          }
          if (activeCountBadge) {
            activeCountBadge.innerText = `${activeCount}/10 ACTIVE`;
            activeCountBadge.style.color = activeCount > 0 ? '#ef4444' : 'var(--accent-cyan)';
          }
        }
        zoneContainer.innerHTML = html;
      }
    }

    // 2. Update Top Telemetry HUD
    updateHUD();
    renderEventHistoryTable();

    // 3. Push to Telemetry History for Charts
    pushHistoryData({
      time: STATE.simTime,
      tMax: STATE.tMax,
      tAvg: STATE.tAvg,
      tMin: STATE.tMin,
      tIn: data.pipeline_stations?.[3]?.temp_c || 22.0,
      tOut: data.pipeline_stations?.[6]?.temp_c || 27.5,
      re: data.dimensionless?.Reynolds || 1250,
      nu: data.dimensionless?.Nusselt || 14.2,
      qGen: data.battery_pack?.total_pack_heat_w || (STATE.cRate * 50.0 * 2.8),
      qRem: data.cooling_performance?.heat_removed_W || ((STATE.pumpDuty / 100) * 140.0)
    });

    // 4. Update currently inspected object if selected
    if (STATE.selectedObject) {
      updateInspectionValues(STATE.selectedObject);
    }
  }

  function runLocalPhysicsStep(dtStep) {
    STATE.simTime += dtStep;
    const isCooling = STATE.coolingMode === 'Active' || STATE.coolingMode === 'MHD Nanofluid' || (STATE.coolingMode === 'Auto' && STATE.tMax >= STATE.thresholdC);

    STATE.pumpDuty = isCooling ? 85.0 : 0.0;
    STATE.fanDuty = isCooling ? 90.0 : 0.0;
    STATE.valvePos = isCooling ? 80.0 : 0.0;

    let sumT = 0;
    let maxT = -999;
    let minT = 999;

    for (let i = 0; i < cellMeshes.length; i++) {
      const mesh = cellMeshes[i];
      const curT = mesh.userData.temp_c || 25.0;
      const qGen = Math.pow(STATE.cRate, 1.8) * 2.2;
      const qCool = isCooling ? (curT - 22.0) * 0.18 * (STATE.uIn / 0.25) : 0.02 * (curT - 25.0);

      const dTemp = (qGen - qCool) * (dtStep / 50.0);
      const newT = Math.max(20.0, curT + dTemp);

      mesh.userData.temp_c = newT;
      mesh.userData.heat_w = qGen;
      mesh.material.color.copy(getThermalColor(newT, STATE.thresholdC));

      sumT += newT;
      if (newT > maxT) maxT = newT;
      if (newT < minT) minT = newT;

      if (STATE.cells[i]) {
        STATE.cells[i].temp_c = newT;
        STATE.cells[i].heat_w = qGen;
      }
    }

    STATE.tMax = maxT;
    STATE.tAvg = sumT / 50.0;
    STATE.tMin = minT;
    STATE.deltaT = maxT - minT;
    updateHUD();
    renderEventHistoryTable();
  }

  function updateHUD() {
    const elTMax = document.getElementById('hud-t-max');
    if (elTMax) elTMax.innerText = `${STATE.tMax.toFixed(1)} °C`;

    const elTAvg = document.getElementById('hud-t-avg');
    if (elTAvg) elTAvg.innerText = `${STATE.tAvg.toFixed(1)} °C`;

    const elTMin = document.getElementById('hud-t-min');
    if (elTMin) elTMin.innerText = `${STATE.tMin.toFixed(1)} °C`;

    const elFlow = document.getElementById('hud-flow-vel');
    if (elFlow) {
      const eKJ = (STATE.pumpEnergyConsumedJ / 1000.0).toFixed(1);
      elFlow.innerText = `${STATE.uIn.toFixed(2)} m/s • ${eKJ} kJ`;
    }

    const elPump = document.getElementById('hud-pump-duty');
    if (elPump) elPump.innerText = `${STATE.pumpDuty.toFixed(0)} %`;

    const elTime = document.getElementById('hud-sim-time');
    if (elTime) elTime.innerText = `${STATE.simTime.toFixed(1)} s`;

    // MHD Field and Lorentz Force display in HUD & Drawer
    const elMhd = document.getElementById('hud-mhd-val');
    if (elMhd) {
      const bVal = STATE.b0 ?? 0.50;
      const fVal = Math.abs(STATE.lorentzForce ?? 0.0);
      elMhd.innerText = `${bVal.toFixed(2)} T • ${fVal.toFixed(2)} N/m³`;
    }
    const valLorentz = document.getElementById('val-lorentz-force');
    if (valLorentz) {
      valLorentz.innerText = `${Math.abs(STATE.lorentzForce ?? 0.0).toFixed(3)} N/m³`;
    }

    // Cell counts in HUD
    const elCntNorm = document.getElementById('hud-count-normal');
    if (elCntNorm) elCntNorm.innerText = STATE.cellCounts?.normal ?? 180;
    const elCntElev = document.getElementById('hud-count-elevated');
    if (elCntElev) elCntElev.innerText = STATE.cellCounts?.elevated ?? 0;
    const elCntOver = document.getElementById('hud-count-overheated');
    if (elCntOver) elCntOver.innerText = STATE.cellCounts?.overheated ?? 0;
    const elCntCrit = document.getElementById('hud-count-critical');
    if (elCntCrit) elCntCrit.innerText = STATE.cellCounts?.critical ?? 0;

    // Uniformity delta T
    const elDeltaT = document.getElementById('hud-delta-t');
    if (elDeltaT) {
      const compliant = STATE.deltaT < 5.0;
      elDeltaT.innerText = `${STATE.deltaT.toFixed(1)} K (${compliant ? 'OPTIMAL' : 'NON-UNIFORM'})`;
      elDeltaT.style.color = compliant ? '#4ade80' : '#ef4444';
    }

    // BMS Badge
    const bmsBadge = document.getElementById('hud-bms-badge');
    const bmsText = document.getElementById('bms-text');
    if (bmsBadge && bmsText) {
      if (STATE.bmsDerateActive) {
        bmsBadge.className = 'status-badge critical';
        bmsText.innerText = `BMS: ${Math.round(STATE.bmsDerateFactor * 100)}% DERATED`;
      } else if (STATE.tMax >= STATE.thresholdC) {
        bmsBadge.className = 'status-badge warning';
        bmsText.innerText = 'BMS: COOLING SURGE';
      } else {
        bmsBadge.className = 'status-badge normal';
        bmsText.innerText = 'BMS: NORMAL';
      }
    }

    // Section C2 Breakdown and Uniformity
    const barNorm = document.getElementById('bar-cnt-normal');
    if (barNorm) barNorm.innerText = STATE.cellCounts?.normal ?? 180;
    const barElev = document.getElementById('bar-cnt-elevated');
    if (barElev) barElev.innerText = STATE.cellCounts?.elevated ?? 0;
    const barOver = document.getElementById('bar-cnt-overheated');
    if (barOver) barOver.innerText = STATE.cellCounts?.overheated ?? 0;
    const barCrit = document.getElementById('bar-cnt-critical');
    if (barCrit) barCrit.innerText = STATE.cellCounts?.critical ?? 0;

    const unifText = document.getElementById('pack-uniformity-text');
    if (unifText) {
      const compliant = STATE.deltaT < 5.0;
      unifText.innerText = `ΔT: ${STATE.deltaT.toFixed(1)} K (${compliant ? 'Compliant < 5K' : 'Excessive ≥ 5K'})`;
      unifText.style.color = compliant ? '#4ade80' : '#ef4444';
    }

    const elActCount = document.getElementById('active-events-count');
    if (elActCount) {
      const actLen = STATE.activeHotspotEvents?.length ?? 0;
      elActCount.innerText = `${actLen} ACTIVE`;
      elActCount.style.color = actLen > 0 ? '#ef4444' : 'var(--accent-orange, #f59e0b)';
    }

    // 8-State Badge display
    const statusBadge = document.getElementById('hud-status-badge');
    const badgeText = document.getElementById('badge-text');
    if (statusBadge && badgeText) {
      badgeText.innerText = `${STATE.stateId}. ${STATE.stateName}`;

      if (STATE.stateId === 8 || STATE.tMax >= STATE.thresholdC + 8.0) {
        statusBadge.className = 'status-badge critical';
      } else if (STATE.stateId >= 3 && STATE.stateId <= 5) {
        statusBadge.className = 'status-badge warning';
      } else if (STATE.stateId === 6) {
        statusBadge.className = 'status-badge warning';
      } else {
        statusBadge.className = 'status-badge normal';
      }
    }
  }

  function renderEventHistoryTable() {
    const tbody = document.getElementById('tbody-event-history');
    if (!tbody) return;

    const allEvents = [...(STATE.hotspotHistory || []), ...(STATE.activeHotspotEvents || [])];
    const elAct = document.getElementById('hist-active-count');
    if (elAct) elAct.innerText = (STATE.activeHotspotEvents || []).length;
    const elRec = document.getElementById('hist-recovered-count');
    if (elRec) elRec.innerText = (STATE.hotspotHistory || []).length;
    const elTot = document.getElementById('hist-total-count');
    if (elTot) elTot.innerText = allEvents.length;

    if (allEvents.length === 0) {
      tbody.innerHTML = `
        <tr>
          <td colspan="10" style="text-align: center; color: var(--text-muted); padding: 16px;">
            No hotspot events recorded yet. Trigger a Configuration above or start the Demonstration Sequence.
          </td>
        </tr>`;
      return;
    }

    allEvents.sort((a, b) => b.sim_time_s - a.sim_time_s);

    let html = '';
    for (const ev of allEvents) {
      const statusColor = ev.status === 'RECOVERED' ? '#4ade80' : (ev.status === 'COOLING' ? '#00e5ff' : '#ef4444');
      const cellsShort = (ev.cell_ids || []).slice(0, 3).join(', ') + ((ev.cell_ids || []).length > 3 ? ` (+${ev.cell_ids.length - 3} more)` : '');
      html += `
        <tr>
          <td style="font-weight: 700; color: var(--accent-cyan); font-family: var(--font-mono);">${ev.event_id || 'EVT'}</td>
          <td style="font-family: var(--font-mono);">${ev.sim_time_s?.toFixed(1) || '0.0'}s</td>
          <td style="font-weight: 700;">${ev.config_type || 'A'}</td>
          <td title="${(ev.cell_ids || []).join(', ')}" style="font-size: 10px;">${cellsShort} (${ev.num_cells})</td>
          <td style="font-family: var(--font-mono);">${ev.additional_heat_w?.toFixed(1) || '15.0'} W</td>
          <td style="font-family: var(--font-mono);">${ev.duration_s?.toFixed(0) || '30'}s</td>
          <td style="font-family: var(--font-mono); color: #ef4444; font-weight: 700;">${ev.peak_temp_c?.toFixed(1) || '25.0'}°C</td>
          <td style="font-family: var(--font-mono);">${ev.cooling_activation_time_s != null ? ev.cooling_activation_time_s.toFixed(1) + 's' : 'N/A'}</td>
          <td style="font-family: var(--font-mono);">${ev.recovery_time_s != null ? ev.recovery_time_s.toFixed(1) + 's' : (ev.status === 'HEATING' ? 'Heating' : 'Cooling')}</td>
          <td><span class="station-badge" style="color: ${statusColor}; border-color: ${statusColor};">${ev.status || 'ACTIVE'}</span></td>
        </tr>`;
    }
    tbody.innerHTML = html;
  }

  // ============================================================================
  // 6. COMPONENT INSPECTION & 3D INTERACTION
  // ============================================================================

  function onMouseMove(event) {
    if (!renderer || !camera || !raycaster) return;
    const rect = renderer.domElement.getBoundingClientRect();
    mouse.x = ((event.clientX - rect.left) / rect.width) * 2 - 1;
    mouse.y = -((event.clientY - rect.top) / rect.height) * 2 + 1;

    raycaster.setFromCamera(mouse, camera);

    const interactables = [...cellMeshes, ...stationMarkers, ...pipeMeshes, ...interPlateMeshes, ...busbarMeshes, ...Object.values(componentMeshes)];
    const intersects = raycaster.intersectObjects(interactables, true);

    const tooltip = document.getElementById('hover-tooltip');
    if (intersects.length > 0) {
      let root = intersects[0].object;
      while (root.parent && root.parent !== btmsMasterGroup && root.parent !== scene && !root.userData?.id) {
        root = root.parent;
      }

      if (root.userData && root.userData.id) {
        tooltip.style.display = 'block';
        tooltip.style.left = `${event.clientX}px`;
        tooltip.style.top = `${event.clientY}px`;
        const tipId = document.getElementById('tooltip-id');
        const tipTemp = document.getElementById('tooltip-temp');
        if (tipId) tipId.innerText = root.userData.id;

        if (tipTemp) {
          if (root.userData.type === 'cell') {
            tipTemp.innerText = `${root.userData.temp_c?.toFixed(1) || '25.0'} °C`;
          } else {
            tipTemp.innerText = root.userData.name || '';
          }
        }
        document.body.style.cursor = 'pointer';
        return;
      }
    }
    tooltip.style.display = 'none';
    document.body.style.cursor = 'default';
  }

  function onClick(event) {
    if (!renderer || !camera || !raycaster) return;
    const rect = renderer.domElement.getBoundingClientRect();
    mouse.x = ((event.clientX - rect.left) / rect.width) * 2 - 1;
    mouse.y = -((event.clientY - rect.top) / rect.height) * 2 + 1;

    raycaster.setFromCamera(mouse, camera);
    const interactables = [...cellMeshes, ...stationMarkers, ...pipeMeshes, ...interPlateMeshes, ...busbarMeshes, ...Object.values(componentMeshes)];
    const intersects = raycaster.intersectObjects(interactables, true);

    if (intersects.length > 0) {
      let root = intersects[0].object;
      while (root.parent && root.parent !== btmsMasterGroup && root.parent !== scene && !root.userData?.id) {
        root = root.parent;
      }
      if (root.userData && root.userData.id) {
        selectObject(root);
      }
    }
  }

  function onDoubleClick(event) {
    if (!renderer || !camera || !raycaster) return;
    const rect = renderer.domElement.getBoundingClientRect();
    mouse.x = ((event.clientX - rect.left) / rect.width) * 2 - 1;
    mouse.y = -((event.clientY - rect.top) / rect.height) * 2 + 1;

    raycaster.setFromCamera(mouse, camera);
    const interactables = [...cellMeshes, ...stationMarkers, ...pipeMeshes, ...interPlateMeshes, ...busbarMeshes, ...Object.values(componentMeshes)];
    const intersects = raycaster.intersectObjects(interactables, true);

    if (intersects.length > 0) {
      let root = intersects[0].object;
      while (root.parent && root.parent !== btmsMasterGroup && root.parent !== scene && !root.userData?.id) {
        root = root.parent;
      }
      if (root) {
        const worldPos = new THREE.Vector3();
        root.getWorldPosition(worldPos);
        animateCameraTo(
          worldPos.clone().add(new THREE.Vector3(4.5, 3.8, 5.5)),
          worldPos
        );
      }
    }
  }

  async function selectObject(mesh) {
    if (!mesh || !mesh.userData) return;
    STATE.selectedObject = mesh.userData;

    // Populate custom hotspot input if a battery cell is clicked
    if (mesh.userData.type === 'cell' && mesh.userData.id) {
      const inpCustom = document.getElementById('input-custom-cells');
      if (inpCustom) {
        const cur = inpCustom.value.trim();
        if (!cur) {
          inpCustom.value = mesh.userData.id;
        } else if (!cur.includes(mesh.userData.id)) {
          inpCustom.value = `${cur}, ${mesh.userData.id}`;
        }
      }
    }

    // Position highlight bounding box
    if (selectedHighlightBox) {
      mesh.updateMatrixWorld(true);
      const box = new THREE.Box3().setFromObject(mesh);
      const size = new THREE.Vector3();
      const center = new THREE.Vector3();
      box.getSize(size);
      box.getCenter(center);
      selectedHighlightBox.scale.copy(size.multiplyScalar(1.08));
      selectedHighlightBox.position.copy(center);
      selectedHighlightBox.material.visible = true;
    }

    // Open inspection panel drawer if collapsed
    const inspPanel = document.getElementById('inspection-panel');
    if (inspPanel) inspPanel.classList.remove('collapsed');

    const headerTitle = document.getElementById('inspect-header-title');
    if (headerTitle) headerTitle.innerText = mesh.userData.name || `${mesh.userData.id} (Cylindrical ${STATE.formFactor} Cell)`;

    try {
      const res = await fetch(`/api/inspect/${mesh.userData.id}`);
      if (res.ok) {
        const details = await res.json();
        renderInspectionDetails(details);
      } else {
        renderLocalInspection(mesh.userData);
      }
    } catch (e) {
      renderLocalInspection(mesh.userData);
    }
  }

  function renderInspectionDetails(data) {
    const isCyl = STATE.selectedObject?.type === 'cell';

    // 1. Physical Tab
    if (data.physical) {
      const p = data.physical;
      setVal('insp-phys-id', data.component_id || STATE.selectedObject?.id || (isCyl ? 'CELL-001' : 'BAT-01'));
      setVal('insp-phys-type', p.component_type || (isCyl ? `Cylindrical ${STATE.formFactor} NMC Li-ion Cell (Wavy Ribbon Contact)` : 'Prismatic NMC Li-ion Cell'));
      setVal('insp-phys-dim', p.dimensions_mm || (isCyl ? (STATE.formFactor === '21700' ? 'Ø 21.0 × 70.0 mm' : 'Ø 18.0 × 65.0 mm') : `${p.width_mm || 148} × ${p.height_mm || 91} × ${p.thickness_mm || 27} mm`));
      setVal('insp-phys-mass', p.mass_kg ? `${p.mass_kg} kg` : (p.mass_g ? `${p.mass_g} g` : (STATE.formFactor === '21700' ? '0.070 kg (70 g)' : '0.048 kg (48 g)')));
      setVal('insp-phys-vol', p.volume_m3 ? `${p.volume_m3} m³` : (STATE.formFactor === '21700' ? '2.424 × 10⁻⁵ m³ (24.2 cm³)' : '1.654 × 10⁻⁵ m³ (16.5 cm³)'));
      setVal('insp-phys-rho', `${p.density_kg_m3 || (STATE.formFactor === '21700' ? 2887 : 2902)} kg/m³`);
      setVal('insp-phys-cp', `${p.specific_heat_j_kgk || 980} J/(kg·K)`);
      setVal('insp-phys-kxy', `${p.thermal_conductivity_w_mk || p.radial_conductivity_kr || '1.15'} W/(m·K) (Radial k_r)`);
      setVal('insp-phys-kz', `${p.kz_w_mk || p.axial_conductivity_kz || '32.0'} W/(m·K) (Axial k_z)`);
    }

    // 2. Chemical Tab
    if (data.chemical) {
      const c = data.chemical;
      setVal('insp-chem-cathode', c.cathode_chemistry || 'LiNi0.8Mn0.1Co0.1O2 (NMC-811)');
      setVal('insp-chem-anode', c.anode_chemistry || 'Synthetic Graphite / Silicon (Si-Gr)');
      setVal('insp-chem-electrolyte', c.electrolyte || '1M LiPF6 in EC:DMC:EMC (1:1:1 wt%)');
      setVal('insp-chem-vnom', `${c.nominal_voltage_v || 3.7} V (${c.voltage_range_v || '3.0 - 4.2 V'})`);
      setVal('insp-chem-qrated', `${c.nominal_capacity_ah || (STATE.formFactor === '21700' ? 4.8 : 3.2)} Ah`);
      setVal('insp-chem-r0', `${c.internal_resistance_mohm || (STATE.formFactor === '21700' ? 18.0 : 25.0)} mΩ`);
      setVal('insp-chem-dudt', `${c.dudt_mv_k || -0.22} mV/K`);
      setVal('insp-chem-runaway', c.runaway_temp_c ? `> ${c.runaway_temp_c} °C` : '> 65.0 °C (SEI Breakdown)');
    }

    // 3. Live Engineering Tab
    const eng = data.live_engineering || {};
    const objType = STATE.selectedObject?.type;

    if (objType === 'station' || objType === 'pipe') {
      const tVal = eng.temperature_c ?? 25.0;
      setVal('insp-eng-temp', `${tVal.toFixed(1)} °C`);
      setVal('insp-eng-status', eng.name || 'Station Pipeline Point');
      setVal('insp-eng-qgen', `P = ${(eng.pressure_kpa || 101.3).toFixed(1)} kPa`);
      setVal('insp-eng-qvol', `Re = ${(eng.local_reynolds || 0).toFixed(0)} (${(eng.local_reynolds || 0) < 2300 ? 'Laminar' : 'Turbulent'})`);
      setVal('insp-eng-qirr', `U = ${(eng.velocity_m_s || 0.0).toFixed(3)} m/s`);
      setVal('insp-eng-qrev', `m_dot = ${(eng.mass_flow_kg_s || 0.0).toFixed(4)} kg/s`);
      setVal('insp-eng-current', `Nu = ${(eng.local_nusselt || 4.36).toFixed(2)}`);
      setVal('insp-eng-volt', `Pr = ${(eng.local_prandtl || 5.37).toFixed(2)}`);
      setVal('insp-eng-ir', `Flow = ${(eng.flow_rate_l_min || 0.0).toFixed(2)} L/min`);
      setVal('insp-eng-rtim', `k = ${(eng.conductivity_w_mk || 0.65).toFixed(3)} W/m·K`);
      setVal('insp-eng-htc', `${(eng.heat_transfer_rate_w || 0.0).toFixed(1)} W`);
      setVal('insp-eng-qrem', `${(eng.hydraulics?.total_delta_p_kPa || 0.0).toFixed(3)} kPa drop`);
      setVal('insp-eng-qnet', `${(eng.density_kg_m3 || 1080).toFixed(0)} kg/m³`);
    } else if (objType === 'component' && String(STATE.selectedObject?.id).includes('PUMP')) {
      setVal('insp-eng-temp', `${STATE.pumpDuty.toFixed(0)} % Duty`);
      setVal('insp-eng-status', eng.pump_status || (STATE.pumpDuty > 0 ? 'RUNNING' : 'STOPPED'));
      setVal('insp-eng-qgen', `RPM = ${eng.pump_rpm || (STATE.pumpDuty * 36).toFixed(0)}`);
      setVal('insp-eng-qvol', `Flow = ${(eng.vol_flow_rate_l_min || 0).toFixed(1)} L/min`);
      setVal('insp-eng-qirr', `Head ΔP = ${(eng.pressure_rise_kpa || 0).toFixed(2)} kPa`);
      setVal('insp-eng-qrev', `P_hyd = ${(eng.hydraulic_power_w || 0).toFixed(2)} W`);
      setVal('insp-eng-current', `P_elec = ${(eng.electrical_power_w || 0).toFixed(1)} W`);
      setVal('insp-eng-volt', `Eff = ${eng.pump_efficiency_pct || 75.0} %`);
      setVal('insp-eng-ir', 'Speed Controlled');
      setVal('insp-eng-rtim', 'Brushless DC');
      setVal('insp-eng-htc', 'Centrifugal Impeller');
      setVal('insp-eng-qrem', `${(eng.mass_flow_rate_kg_s || 0).toFixed(3)} kg/s`);
      setVal('insp-eng-qnet', STATE.pumpDuty > 0 ? 'CIRCULATING' : 'IDLE');
    } else if (objType === 'component' && String(STATE.selectedObject?.id).includes('RADIATOR')) {
      setVal('insp-eng-temp', `${(eng.coolant_outlet_t_c || 22.0).toFixed(1)} °C Ret`);
      setVal('insp-eng-status', eng.fan_status || (STATE.fanDuty > 0 ? 'FAN ROTATING' : 'STANDBY'));
      setVal('insp-eng-qgen', `Fan RPM = ${eng.fan_rpm || (STATE.fanDuty * 28).toFixed(0)}`);
      setVal('insp-eng-qvol', `Q_reject = ${(eng.heat_rejected_w || 0).toFixed(1)} W`);
      setVal('insp-eng-qirr', `T_inlet = ${(eng.coolant_inlet_t_c || 25.0).toFixed(1)} °C`);
      setVal('insp-eng-qrev', `Airflow = ${(eng.airflow_velocity_m_s || 0).toFixed(1)} m/s`);
      setVal('insp-eng-current', `${STATE.fanDuty.toFixed(0)} % Fan Duty`);
      setVal('insp-eng-volt', '12V DC Shroud Fan');
      setVal('insp-eng-ir', 'Dual Pass Micro-Fin');
      setVal('insp-eng-rtim', 'Al 6061 Core');
      setVal('insp-eng-htc', 'Cross-Flow Air/Liquid');
      setVal('insp-eng-qrem', `${(eng.heat_rejected_w || 0).toFixed(1)} W`);
      setVal('insp-eng-qnet', STATE.fanDuty > 0 ? 'COOLING' : 'IDLE');
    } else if (objType === 'channel') {
      // Serpentine S-Cooling Channel Inspection (Zonal Hydrodynamics)
      const zId = STATE.selectedObject?.zone_id || eng.cooling_zone_id || 1;
      const zInfo = (STATE.zones && (STATE.zones[zId] || STATE.zones[String(zId)])) || {};
      const valvePct = eng.zonal_valve_pct ?? zInfo.valve_opening_pct ?? 15.0;
      const vel = eng.zonal_velocity_m_s ?? zInfo.velocity_m_s ?? 0.05;
      const flowL = eng.zonal_flow_rate_l_min ?? zInfo.flow_rate_l_min ?? 0.12;
      const pressKpa = eng.zonal_pressure_drop_kpa ?? zInfo.pressure_drop_kpa ?? 1.25;

      setVal('insp-eng-temp', `${(eng.local_coolant_temp_c || zInfo.outlet_temp_c || 22.0).toFixed(1)} °C`);
      setVal('insp-eng-status', eng.zonal_status || zInfo.status || 'ACTIVE ADAPTIVE');
      setVal('insp-eng-zone', `ZONE-${String(zId).padStart(2, '0')}`);
      setVal('insp-eng-valve-status', `${eng.zonal_status || 'IDLE'} (${valvePct.toFixed(0)}% Open)`);
      setVal('insp-eng-coolant-temp', `${(eng.local_coolant_temp_c || zInfo.outlet_temp_c || 22.0).toFixed(1)} °C`);
      setVal('insp-eng-coolant-vel', `${vel.toFixed(3)} m/s`);
      setVal('insp-eng-coolant-press', `${(pressKpa + 101.3).toFixed(1)} kPa`);
      setVal('insp-eng-rate', '0.000 °C/s');
      setVal('insp-eng-extremes', `${(eng.local_coolant_temp_c || 22.0).toFixed(1)} / 22.0 °C`);
      setVal('insp-eng-qgen', `Flow = ${flowL.toFixed(2)} L/min`);
      setVal('insp-eng-qvol', `Re = ${(eng.zonal_reynolds || zInfo.reynolds || 120).toFixed(0)}`);
      setVal('insp-eng-qirr', `Nu = ${(eng.zonal_nusselt || zInfo.nusselt || 4.36).toFixed(2)}`);
      setVal('insp-eng-qrev', `h = ${(eng.zonal_htc_w_m2k || zInfo.htc_w_m2k || 850).toFixed(0)} W/m²K`);
      setVal('insp-eng-current', 'Zonal Loop');
      setVal('insp-eng-volt', 'Hydraulic');
      setVal('insp-eng-ir', 'Kirchhoff Balanced');
      setVal('insp-eng-rtim', '0.042 K/W');
      setVal('insp-eng-htc', `${(eng.zonal_htc_w_m2k || 850).toFixed(0)} W/(m²·K)`);
      setVal('insp-eng-qrem', `${(eng.heat_removed_w || 25.0).toFixed(1)} W`);
      setVal('insp-eng-qnet', 'ADAPTIVE');
    } else {
      // Battery Cell Inspection (Cylindrical 180-Cell Pack - All 15 Section 8 Parameters)
      const curTemp = eng.current_temperature_c ?? eng.temperature_c ?? STATE.selectedObject?.temp_c ?? 25.0;
      const initTemp = eng.initial_temperature_c ?? 25.0;
      const deltaT = eng.temp_change_c ?? (curTemp - initTemp);
      const qInt = eng.q_internal_w ?? 2.76;
      const qExt = eng.q_hotspot_w ?? eng.additional_heat_w ?? 0.0;
      const curHeat = eng.heat_generation_w ?? (qInt + qExt);
      const qRem = eng.heat_removed_w ?? eng.local_heat_transfer_rate_w ?? ((STATE.pumpDuty / 100) * 3.2);
      const localCoolantT = eng.local_coolant_temp_c ?? 20.0;
      const localVel = eng.local_coolant_velocity_m_s ?? eng.zonal_velocity_m_s ?? 0.25;
      const localPressPa = eng.local_coolant_pressure_pa ?? ((eng.local_coolant_pressure_kpa || 101.3) * 1000.0);
      const bField = eng.b_field_tesla ?? eng.magnetic_field_tesla ?? STATE.b0 ?? 0.50;
      const valveStat = eng.cooling_zone_valve_status ?? eng.local_valve_status ?? (STATE.pumpDuty > 0 ? `MODULATED (${Math.round(STATE.pumpDuty)}%)` : 'CLOSED (0%)');
      const coolingStat = eng.cooling_status ?? (curTemp >= 35.0 ? 'TARGETED COOLING' : (STATE.pumpDuty > 0 ? 'ACTIVE COOLING' : 'OPTIMAL'));
      const ratedCap = STATE.formFactor === '21700' ? 4.8 : (STATE.formFactor === '18650' ? 3.2 : 20.0);

      // Section 8: All 15 Live Engineering Parameters
      setVal('insp-eng-cell-id', eng.cell_id || STATE.selectedObject?.id || 'CELL-001');
      setVal('insp-eng-module-id', eng.module_name ? `${eng.module_id} (${eng.module_name})` : (STATE.selectedObject?.module_id || 'MODULE_A'));
      setVal('insp-eng-temp', `${curTemp.toFixed(2)} °C`);
      setVal('insp-eng-init-temp', `${initTemp.toFixed(2)} °C`);
      setVal('insp-eng-temp-inc', `${deltaT >= 0 ? '+' : ''}${deltaT.toFixed(2)} °C`);
      setVal('insp-eng-q-internal', `${qInt.toFixed(2)} W (I²R_int)`);
      setVal('insp-eng-q-hotspot', `${qExt.toFixed(2)} W`);
      setVal('insp-eng-status', eng.thermal_status || (curTemp < 35.0 ? 'Normal (Green)' : (curTemp <= 45.0 ? 'Moderate / Warning (Yellow)' : 'Heated / Overheated (Red)')));
      setVal('insp-eng-cooling-status', coolingStat);
      setVal('insp-eng-coolant-temp', `${localCoolantT.toFixed(2)} °C`);
      setVal('insp-eng-coolant-vel', `${localVel.toFixed(3)} m/s`);
      setVal('insp-eng-coolant-press-pa', `${Math.round(localPressPa).toLocaleString()} Pa`);
      setVal('insp-eng-qrem', `${qRem.toFixed(2)} W`);
      setVal('insp-eng-b-field', `${bField.toFixed(2)} T`);
      setVal('insp-eng-valve-status', valveStat);

      // Legacy rows
      setVal('insp-eng-zone', `ZONE-${String(eng.cooling_zone_id || Math.min(10, Math.floor((STATE.selectedObject?.row || 0) / 2) + 1)).padStart(2, '0')}`);
      setVal('insp-eng-coolant-press', `${(localPressPa / 1000.0).toFixed(1)} kPa`);
      setVal('insp-eng-rate', `${(eng.cooling_rate_c_s || 0.0).toFixed(3)} °C/s`);
      setVal('insp-eng-extremes', `${(eng.max_recorded_temp_c || curTemp).toFixed(1)} / ${(eng.min_recorded_temp_c || curTemp).toFixed(1)} °C`);
      setVal('insp-eng-qgen', `${curHeat.toFixed(2)} W`);
      setVal('insp-eng-qvol', `${(eng.heat_gen_vol_w_m3 || curHeat / (isCyl ? (STATE.formFactor === '21700' ? 2.424e-5 : 1.654e-5) : 3.5e-4)).toFixed(0)} W/m³`);
      setVal('insp-eng-qirr', `${(eng.joule_heat_w || curHeat * 0.72).toFixed(2)} W (I²R)`);
      setVal('insp-eng-qrev', `${(eng.reaction_heat_w || curHeat * 0.28).toFixed(2)} W (-IT dU/dT)`);
      setVal('insp-eng-current', `${(eng.current_amperes || STATE.cRate * ratedCap).toFixed(1)} A`);
      setVal('insp-eng-volt', `${(eng.terminal_voltage_v || 3.65).toFixed(3)} V`);
      setVal('insp-eng-ir', `${(eng.internal_resistance_mohm || (isCyl ? (STATE.formFactor === '21700' ? 18.0 : 25.0) : 1.85)).toFixed(2)} mΩ`);
      setVal('insp-eng-rtim', `${(eng.r_th_total_k_w || eng.tim_resistance_k_w || 0.40).toFixed(4)} K/W (R_th)`);
      setVal('insp-eng-htc', `${(eng.htc_w_m2k || 850).toFixed(0)} W/(m²·K) (Wavy Ribbon)`);
      const qNet = curHeat - qRem;
      setVal('insp-eng-qnet', `${qNet >= 0 ? '+' : ''}${qNet.toFixed(2)} W`);
    }

    // 4. Governing Equations Tab
    const eqContainer = document.getElementById('insp-formulas-container');
    if (eqContainer) {
      eqContainer.innerHTML = '';
      const eqs = data.live_equations || data.governing_equations || [];
      if (eqs.length === 0) {
        eqContainer.innerHTML = '<div style="color: var(--text-muted); font-size: 11px;">No specific governing equations assigned.</div>';
      } else {
        eqs.forEach(eq => {
          const item = document.createElement('div');
          item.className = 'section-box';
          item.style.marginBottom = '10px';
          item.innerHTML = `
            <div style="font-weight: 700; color: var(--accent-cyan); font-size: 11px; margin-bottom: 4px;">
              EQ ${eq.id}: ${eq.name}
            </div>
            <div style="font-family: var(--font-mono); font-size: 10.5px; background: rgba(0,0,0,0.3); padding: 6px; border-radius: 4px; margin-bottom: 6px;" id="eq-latex-${eq.id}">
              ${eq.latex_display || eq.symbolic || eq.latex || ''}
            </div>
            <div style="font-size: 10px; color: var(--text-secondary); margin-bottom: 4px;">
              <strong>Live Substitution:</strong> ${eq.substitution || ''}
            </div>
            <div style="display: flex; justify-content: space-between; font-weight: 700; font-size: 11px; color: #fff;">
              <span>Calculated Output:</span>
              <span style="color: var(--accent-green); font-family: var(--font-mono);">
                ${typeof (eq.calculated_value || eq.result) === 'number' ? (eq.calculated_value || eq.result).toFixed(4) : (eq.calculated_value || eq.result)} ${eq.si_units || eq.unit || ''}
              </span>
            </div>
          `;
          eqContainer.appendChild(item);

          if (window.katex) {
            const el = document.getElementById(`eq-latex-${eq.id}`);
            if (el) katex.render(eq.latex_display || eq.symbolic || '', el, { throwOnError: false });
          }
        });
      }
    }
  }

  function setVal(id, text) {
    const el = document.getElementById(id);
    if (el) el.innerText = text;
  }

  function renderLocalInspection(obj) {
    const isCyl = obj.type === 'cell';
    setVal('insp-phys-id', obj.id || (isCyl ? 'CELL-001' : 'BAT-01'));
    setVal('insp-phys-type', obj.name || (isCyl ? `Cylindrical ${STATE.formFactor} NMC Li-ion Cell` : 'Prismatic NMC Li-ion Cell'));
    setVal('insp-phys-dim', isCyl ? (STATE.formFactor === '21700' ? 'Ø 21.0 × 70.0 mm' : 'Ø 18.0 × 65.0 mm') : '148 × 91 × 27 mm');
    setVal('insp-phys-mass', isCyl ? (STATE.formFactor === '21700' ? '0.070 kg (70 g)' : '0.048 kg (48 g)') : '0.650 kg');
    setVal('insp-phys-vol', isCyl ? (STATE.formFactor === '21700' ? '2.424 × 10⁻⁵ m³' : '1.654 × 10⁻⁵ m³') : '3.501 × 10⁻⁴ m³');
    setVal('insp-phys-rho', isCyl ? '2,887 kg/m³' : '2,150 kg/m³');
    setVal('insp-phys-cp', isCyl ? '980 J/(kg·K)' : '1,120 J/(kg·K)');
    setVal('insp-phys-kxy', isCyl ? '1.15 W/(m·K) (k_r)' : '28.5 W/(m·K)');
    setVal('insp-phys-kz', isCyl ? '32.0 W/(m·K) (k_z)' : '1.25 W/(m·K)');

    setVal('insp-eng-temp', `${(obj.temp_c || 25.0).toFixed(1)} °C`);
    setVal('insp-eng-status', (obj.temp_c || 25.0) >= STATE.thresholdC ? 'THRESHOLD EXCEEDED' : 'OPTIMAL');
    setVal('insp-eng-qgen', `${(obj.heat_w || 2.5).toFixed(2)} W`);
    setVal('insp-eng-current', `${(STATE.cRate * (isCyl ? (STATE.formFactor === '21700' ? 4.8 : 3.2) : 20.0)).toFixed(1)} A`);
    setVal('insp-eng-volt', '3.650 V');
    setVal('insp-eng-ir', isCyl ? (STATE.formFactor === '21700' ? '18.00 mΩ' : '25.00 mΩ') : '1.85 mΩ');
    setVal('insp-eng-rtim', isCyl ? '0.4020 K/W (R_th)' : '0.0098 K/W');
    setVal('insp-eng-htc', isCyl ? '850 W/(m²·K)' : '450 W/(m²·K)');
    setVal('insp-eng-qrem', `${((STATE.pumpDuty / 100) * 3.2).toFixed(2)} W`);
  }

  function updateInspectionValues(obj) {
    if (!obj) return;
    if (obj.type === 'cell') {
      const cell = (STATE.cells && STATE.cells[obj.index]) || obj;
      if (cell) {
        const curTemp = cell.temp_c ?? cell.temperature_c ?? 25.0;
        const initTemp = cell.initial_temp_c ?? 25.0;
        const deltaT = cell.temp_change_c ?? (curTemp - initTemp);
        const qInt = cell.q_internal_w ?? 2.76;
        const qExt = cell.q_hotspot_w ?? cell.q_external_w ?? 0.0;
        const qTotal = cell.heat_w ?? cell.heat_generation_w ?? (qInt + qExt);
        const qRem = cell.heat_removed_w ?? cell.local_heat_transfer_w ?? ((STATE.pumpDuty / 100) * 3.2);
        const localCoolantT = cell.local_coolant_temp_c ?? 20.0;
        const localVel = cell.local_velocity_m_s ?? STATE.uIn ?? 0.25;
        const localPressPa = cell.local_pressure_pa ?? 101325.0;
        const bField = cell.b_field_tesla ?? STATE.b0 ?? 0.50;
        const valveStat = cell.valve_status ?? (STATE.pumpDuty > 0 ? `MODULATED (${Math.round(STATE.pumpDuty)}%)` : 'CLOSED (0%)');
        const coolingStat = cell.cooling_status ?? cell.cooling_state ?? (curTemp >= 35.0 ? 'TARGETED COOLING' : (STATE.pumpDuty > 0 ? 'ACTIVE COOLING' : 'OPTIMAL'));
        const thermalStat = cell.status || cell.color_name || (curTemp < 35.0 ? 'Normal (Green)' : (curTemp <= 45.0 ? 'Moderate / Warning (Yellow)' : 'Heated / Overheated (Red)'));

        // All 15 Section 8 Parameters
        setVal('insp-eng-cell-id', cell.cell_id || obj.id || `CELL-${String((obj.index || 0) + 1).padStart(3, '0')}`);
        setVal('insp-eng-module-id', cell.module_name ? `${cell.module_id} (${cell.module_name})` : (obj.module_id || 'MODULE_A'));
        setVal('insp-eng-temp', `${curTemp.toFixed(2)} °C`);
        setVal('insp-eng-init-temp', `${initTemp.toFixed(2)} °C`);
        setVal('insp-eng-temp-inc', `${deltaT >= 0 ? '+' : ''}${deltaT.toFixed(2)} °C`);
        setVal('insp-eng-q-internal', `${qInt.toFixed(2)} W (I²R_int)`);
        setVal('insp-eng-q-hotspot', `${qExt.toFixed(2)} W`);
        setVal('insp-eng-status', thermalStat);
        setVal('insp-eng-cooling-status', coolingStat);
        setVal('insp-eng-coolant-temp', `${localCoolantT.toFixed(2)} °C`);
        setVal('insp-eng-coolant-vel', `${localVel.toFixed(3)} m/s`);
        setVal('insp-eng-coolant-press-pa', `${Math.round(localPressPa).toLocaleString()} Pa`);
        setVal('insp-eng-qrem', `${qRem.toFixed(2)} W`);
        setVal('insp-eng-b-field', `${bField.toFixed(2)} T`);
        setVal('insp-eng-valve-status', valveStat);

        setVal('insp-eng-qgen', `${qTotal.toFixed(2)} W`);
        const qNet = qTotal - qRem;
        setVal('insp-eng-qnet', `${qNet >= 0 ? '+' : ''}${qNet.toFixed(2)} W`);
        setVal('insp-eng-coolant-press', `${(localPressPa / 1000.0).toFixed(1)} kPa`);
      }
    }
  }

  // ============================================================================
  // 7. CAMERA PRESETS & ANIMATIONS
  // ============================================================================

  function animateCameraTo(targetPosition, targetLookAt) {
    if (!cameraTarget) return;
    cameraTarget.position.copy(targetPosition);
    cameraTarget.lookAt.copy(targetLookAt);
    cameraTarget.animating = true;
  }

  function setupCameraButtons() {
    document.querySelectorAll('.cam-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        document.querySelectorAll('.cam-btn').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');

        const presetKey = btn.dataset.cam;
        if (cameraPresets[presetKey]) {
          animateCameraTo(cameraPresets[presetKey].pos, cameraPresets[presetKey].target);
        }
      });
    });
  }

  function setupLayerToggles() {
    document.querySelectorAll('.layer-toggle-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        btn.classList.toggle('active');
        const layer = btn.dataset.layer;
        const isVisible = btn.classList.contains('active');
        STATE.layers[layer] = isVisible;

        if (layerGroups[layer]) {
          layerGroups[layer].visible = isVisible;
        }
      });
    });
  }

  // ============================================================================
  // 8. SIMULATION CONTROLS & HOTSPOT TESTING
  // ============================================================================

  function updateWavyRibbonMaterials() {
    const isCopper = STATE.plateMaterial === 'copper';
    const baseColor = isCopper ? 0xb87333 : 0x94a3b8;
    wavyRibbonMeshes.forEach(mesh => {
      if (mesh.material) {
        mesh.material.color.setHex(baseColor);
        if (STATE.cutawayActive) {
          mesh.material.transparent = true;
          mesh.material.opacity = 0.28;
          mesh.material.roughness = 0.1;
        } else {
          mesh.material.transparent = false;
          mesh.material.opacity = 1.0;
          mesh.material.roughness = 0.22;
        }
      }
    });
  }

  function setupControls() {
    // 0. Pack Architecture Controls (500+ Cylindrical Cells & Wavy Ribbons)
    const selCount = document.getElementById('select-cell-count');
    const selFF = document.getElementById('select-form-factor');
    const selMat = document.getElementById('select-plate-material');
    const btnCutaway = document.getElementById('btn-toggle-cutaway');

    async function reconfigurePackFromUI() {
      const count = parseInt(selCount?.value || '180');
      const ff = selFF?.value || '21700';
      const mat = selMat?.value || 'aluminum';
      STATE.numCells = count;
      STATE.formFactor = ff;
      STATE.plateMaterial = mat;

      const badge = document.getElementById('pack-cell-count-badge');
      if (badge) badge.innerText = `${count} CELLS`;
      const btnLayerCells = document.getElementById('layer-cells-btn');
      if (btnLayerCells) btnLayerCells.innerText = `Cells (${count})`;

      showToast(`Reconfiguring pack: ${count} cylindrical cells (${ff}, ${mat} serpentine plate)...`);

      try {
        await fetch('/api/reconfigure_pack', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ num_cells: count, form_factor: ff, plate_material: mat })
        });
      } catch (e) {
        console.warn('Reconfigure API call error:', e);
      }

      // Rebuild 3D geometry
      buildBatteryPack();
      buildElectricalSystem();
      buildCoolingPlatesAndChannels();
      buildNanoparticleSystem();
      fitCameraToAssembly();
      showToast(`3D Assembly updated to ${count} Cylindrical Cells with Full-Height Serpentine Cooling Plate.`);
    }

    if (selCount) selCount.addEventListener('change', reconfigurePackFromUI);
    if (selFF) selFF.addEventListener('change', reconfigurePackFromUI);
    if (selMat) {
      selMat.addEventListener('change', () => {
        STATE.plateMaterial = selMat.value;
        reconfigurePackFromUI();
      });
    }

    if (btnCutaway) {
      btnCutaway.addEventListener('click', () => {
        STATE.cutawayActive = !STATE.cutawayActive;
        btnCutaway.classList.toggle('active', STATE.cutawayActive);
        btnCutaway.innerText = STATE.cutawayActive
          ? '🔬 Solid Wavy Ribbon View'
          : '🔬 Toggle Cutaway / Transparent Microchannels';
        updateWavyRibbonMaterials();
        showToast(STATE.cutawayActive ? 'Cutaway View Active: Inspecting internal microchannels & nanoparticles.' : 'Solid Metallic Ribbon View Active.');
      });
    }

    // 1. Play / Pause / Reset / Step
    const btnPlay = document.getElementById('btn-play-pause');
    if (btnPlay) {
      btnPlay.addEventListener('click', () => {
        STATE.isRunning = !STATE.isRunning;
        btnPlay.innerText = STATE.isRunning ? '⏸ Pause' : '▶ Play';
        btnPlay.classList.toggle('active', STATE.isRunning);
        const stateText = document.getElementById('sim-state-text');
        if (stateText) stateText.innerText = STATE.isRunning ? 'RUNNING' : 'PAUSED';
      });
    }

    const btnStep = document.getElementById('btn-step-forward');
    if (btnStep) {
      btnStep.addEventListener('click', () => {
        advanceSimulationStep(STATE.dt * STATE.timeWarp);
        showToast('Stepped simulation by 1 dt');
      });
    }

    const btnReset = document.getElementById('btn-reset-sim');
    if (btnReset) {
      btnReset.addEventListener('click', async () => {
        try {
          await fetch('/api/reset', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ initial_temp_c: 25.0 })
          });
          showToast('Simulation reset to 25.0 °C reference state.');
        } catch (e) {
          showToast('Reset completed.');
        }
      });
    }

    // 2. Time Warp Multipliers & Speed Multipliers
    document.querySelectorAll('.btn-preset[data-warp]').forEach(btn => {
      btn.addEventListener('click', () => {
        document.querySelectorAll('.btn-preset[data-warp]').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        STATE.timeWarp = parseFloat(btn.dataset.warp);
        const valWarp = document.getElementById('val-time-warp');
        if (valWarp) valWarp.innerText = `${STATE.timeWarp.toFixed(1)}x`;
      });
    });

    document.querySelectorAll('.btn-preset[data-speed]').forEach(btn => {
      btn.addEventListener('click', () => {
        document.querySelectorAll('.btn-preset[data-speed]').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        const mult = parseFloat(btn.dataset.speed);
        sendControlUpdate({ speed_multiplier: mult });
        showToast(`Engine Speed Multiplier set to ${mult}x`);
      });
    });

    // 2B. Hotspot Additional Heat Generation Presets (Low 3W, Med 8W, High 15W, Very High 25W)
    document.querySelectorAll('.btn-heat-preset').forEach(btn => {
      btn.addEventListener('click', () => {
        document.querySelectorAll('.btn-heat-preset').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        const heatW = parseFloat(btn.dataset.heat);
        sendControlUpdate({ hotspot_intensity_w: heatW, additional_heat_w: heatW });
        showToast(`Hotspot Additional Heat set to ${heatW} W`);
      });
    });

    // 2C. Electrical Series Circuit Validation
    const elElecBadge = document.getElementById('electrical-validation-badge');
    if (elElecBadge) {
      elElecBadge.addEventListener('click', async () => {
        try {
          const res = await fetch('/api/electrical/validate');
          if (res.ok) {
            const valData = await res.json();
            const valid = valData.is_valid_series;
            showToast(`Electrical Circuit: ${valid ? '✅ VALID' : '⚠️ FAULT'} | 180S1P Series | ${valData.nominal_pack_voltage_v}V DC | 174 Intra-Busbars, 5 Jumpers`);
          }
        } catch (e) {
          showToast('Electrical validation request error.');
        }
      });
    }

    // 3. Cooling Mode Radio
    document.querySelectorAll('input[name="cooling_mode"]').forEach(radio => {
      radio.addEventListener('change', (e) => {
        STATE.coolingMode = e.target.value;
        sendControlUpdate({ cooling_mode: STATE.coolingMode });
      });
    });

    // 4. Threshold (T_target) & Deactivation (T_off) Sliders
    const sliderThresh = document.getElementById('slider-threshold');
    const sliderDeact = document.getElementById('slider-deact-threshold');

    function updateHysteresisDisplay() {
      const band = Math.max(0.1, STATE.thresholdC - STATE.deactThresholdC);
      const valThresh = document.getElementById('val-threshold');
      const valDeact = document.getElementById('val-deact-threshold');
      const valBand = document.getElementById('val-hysteresis-band');

      if (valThresh) valThresh.innerText = `${STATE.thresholdC.toFixed(1)} °C`;
      if (valDeact) valDeact.innerText = `${STATE.deactThresholdC.toFixed(1)} °C`;
      if (valBand) valBand.innerText = `${band.toFixed(1)} °C`;
    }

    if (sliderThresh) {
      sliderThresh.addEventListener('input', (e) => {
        const val = parseFloat(e.target.value);
        STATE.thresholdC = val;
        // Keep deactivation threshold below target
        if (STATE.deactThresholdC >= val) {
          STATE.deactThresholdC = val - 2.5;
          if (sliderDeact) sliderDeact.value = STATE.deactThresholdC;
        }
        updateHysteresisDisplay();
        sendControlUpdate({ threshold_c: val, deactivation_threshold_c: STATE.deactThresholdC });
      });
    }

    if (sliderDeact) {
      sliderDeact.addEventListener('input', (e) => {
        const val = parseFloat(e.target.value);
        STATE.deactThresholdC = Math.min(val, STATE.thresholdC - 0.5);
        updateHysteresisDisplay();
        sendControlUpdate({ deactivation_threshold_c: STATE.deactThresholdC });
      });
    }

    document.querySelectorAll('.btn-preset[data-thresh]').forEach(btn => {
      btn.addEventListener('click', () => {
        document.querySelectorAll('.btn-preset[data-thresh]').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        const val = parseFloat(btn.dataset.thresh);
        if (sliderThresh) sliderThresh.value = val;
        STATE.thresholdC = val;
        STATE.deactThresholdC = val - 2.5;
        if (sliderDeact) sliderDeact.value = STATE.deactThresholdC;
        updateHysteresisDisplay();
        sendControlUpdate({ threshold_c: val, deactivation_threshold_c: STATE.deactThresholdC });
      });
    });

    // 5. C-Rate Slider & Presets
    const sliderCRate = document.getElementById('slider-c-rate');
    if (sliderCRate) {
      sliderCRate.addEventListener('input', (e) => {
        const val = parseFloat(e.target.value);
        STATE.cRate = val;
        const amps = (val * 20.0).toFixed(1);
        const valCRate = document.getElementById('val-c-rate');
        if (valCRate) valCRate.innerText = `${val.toFixed(1)} C (${amps} A)`;
        sendControlUpdate({ c_rate: val });
      });
    }

    document.querySelectorAll('.btn-preset[data-crate]').forEach(btn => {
      btn.addEventListener('click', () => {
        document.querySelectorAll('.btn-preset[data-crate]').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        const val = parseFloat(btn.dataset.crate);
        if (sliderCRate) sliderCRate.value = val;
        STATE.cRate = val;
        const amps = (val * 20.0).toFixed(1);
        const valCRate = document.getElementById('val-c-rate');
        if (valCRate) valCRate.innerText = `${val.toFixed(1)} C (${amps} A)`;
        sendControlUpdate({ c_rate: val });
      });
    });

    // 6. Nanoparticle Fractions
    const sliderPhi1 = document.getElementById('slider-phi1');
    const sliderPhi2 = document.getElementById('slider-phi2');
    function updatePhi() {
      const p1 = parseFloat(sliderPhi1.value) / 100.0;
      const p2 = parseFloat(sliderPhi2.value) / 100.0;
      STATE.phi1 = p1;
      STATE.phi2 = p2;
      const elP1 = document.getElementById('val-phi1');
      const elP2 = document.getElementById('val-phi2');
      const elPTot = document.getElementById('val-phi-total');
      if (elP1) elP1.innerText = `${(p1 * 100).toFixed(1)} %`;
      if (elP2) elP2.innerText = `${(p2 * 100).toFixed(1)} %`;
      if (elPTot) elPTot.innerText = `${((p1 + p2) * 100).toFixed(1)} %`;
      sendControlUpdate({ phi1: p1, phi2: p2 });
    }
    if (sliderPhi1) sliderPhi1.addEventListener('input', updatePhi);
    if (sliderPhi2) sliderPhi2.addEventListener('input', updatePhi);

    // 7. Velocity & B0 Sliders
    const sliderUin = document.getElementById('slider-u-in');
    if (sliderUin) {
      sliderUin.addEventListener('input', (e) => {
        const val = parseFloat(e.target.value);
        STATE.uIn = val;
        const elUin = document.getElementById('val-u-in');
        if (elUin) elUin.innerText = `${val.toFixed(2)} m/s`;
        sendControlUpdate({ U_in: val });
      });
    }

    const sliderB0 = document.getElementById('slider-b0');
    if (sliderB0) {
      sliderB0.addEventListener('input', (e) => {
        const val = parseFloat(e.target.value);
        STATE.b0 = val;
        const elB0 = document.getElementById('val-b0');
        if (elB0) elB0.innerText = `${val.toFixed(2)} T`;
        sendControlUpdate({ B0: val });
      });
    }

    const sliderK = document.getElementById('slider-k-perm');
    if (sliderK) {
      sliderK.addEventListener('input', (e) => {
        const exp = parseFloat(e.target.value);
        const val = Math.pow(10, exp);
        STATE.kPerm = val;
        const elK = document.getElementById('val-k-perm');
        if (elK) elK.innerText = `${val.toExponential(1)} m²`;
        sendControlUpdate({ k_perm: val });
      });
    }

    // 8. Hotspot Injection & Hysteresis Cycle Demonstration Button
    const btnHotspot = document.getElementById('btn-test-hotspot');
    if (btnHotspot) {
      btnHotspot.addEventListener('click', async () => {
        try {
          btnHotspot.innerText = '🔥 Hotspot Injected! Monitoring...';
          const res = await fetch('/api/hotspot', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              scenario: 'B'
            })
          });
          const data = await res.json();
          showToast('Thermal Hotspot Scenario B (CELL-125/126 @ 52°C) injected! Watch localized cooling activate.');

          setTimeout(() => {
            if (btnHotspot) btnHotspot.innerText = '🔥 Run Hotspot & Cooling Cycle (Scenario B)';
          }, 8000);
        } catch (e) {
          showToast('Hotspot API call failed.');
        }
      });
    }

    // 8A2. Trigger Exactly 10 Random Overheated Cells (30s Cycle)
    const btnRandom10 = document.getElementById('btn-trigger-random-10');
    if (btnRandom10) {
      btnRandom10.addEventListener('click', async () => {
        try {
          const res = await fetch('/api/hotspot', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              config_type: 'RANDOM_10',
              clear_previous: false
            })
          });
          const data = await res.json();
          const count = data.num_cells || data.affected_cells?.length || 10;
          showToast(`⚡ Injected ${count} Random Overheated Cells! Watch Serpentine Nanofluid Cooling.`);
          renderEventHistoryTable();
        } catch (e) {
          showToast('Failed to trigger random 10 hotspots.');
        }
      });
    }

    // 8B. Localized Hotspot Configurations A through H & Patterns
    document.querySelectorAll('.btn-hotspot-scenario').forEach(btn => {
      btn.addEventListener('click', async () => {
        const scenario = btn.dataset.scenario;
        document.querySelectorAll('.btn-hotspot-scenario').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');

        try {
          const res = await fetch('/api/hotspot', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              config_type: scenario,
              clear_previous: false
            })
          });
          const data = await res.json();
          const count = data.num_cells || data.affected_cells?.length || 1;
          showToast(`Injected Hotspot ${scenario} (${count} cells affected). Watch localized cooling surge!`);

          const badge = document.getElementById('hud-status-badge');
          if (badge) {
            badge.className = 'status-badge warning';
            badge.innerHTML = `<span id="badge-dot">●</span> <span id="badge-text">${scenario} ACTIVE</span>`;
          }
          renderEventHistoryTable();
        } catch (e) {
          showToast(`Failed to trigger Hotspot ${scenario}`);
        }
      });
    });

    // 8B2. User-Defined Custom Hotspot (Mode 2)
    const btnCustomHotspot = document.getElementById('btn-apply-custom-hotspot');
    if (btnCustomHotspot) {
      btnCustomHotspot.addEventListener('click', async () => {
        const cellsInput = document.getElementById('input-custom-cells')?.value || '';
        const heatVal = parseFloat(document.getElementById('input-custom-heat')?.value || '18.0');
        const durVal = parseFloat(document.getElementById('input-custom-dur')?.value || '30.0');

        const cellIds = cellsInput.split(',').map(s => s.trim()).filter(s => s.length > 0);
        if (cellIds.length === 0) {
          showToast('Enter at least one cell ID (e.g. CELL-125) or click on 3D cells.');
          return;
        }

        try {
          const res = await fetch('/api/hotspot', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              config_type: 'CUSTOM',
              cell_ids: cellIds,
              additional_heat_w: heatVal,
              duration_s: durVal,
              clear_previous: false
            })
          });
          const data = await res.json();
          showToast(`Injected Custom Hotspot: ${data.num_cells || cellIds.length} cells (+${heatVal}W for ${durVal}s)!`);
          renderEventHistoryTable();
        } catch (e) {
          showToast('Failed to apply custom hotspot.');
        }
      });
    }

    // 8B3. 10-Event Demonstration Sequence Runners
    async function triggerDemoSequence() {
      try {
        const res = await fetch('/api/hotspot/demonstration_sequence', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' }
        });
        const data = await res.json();
        showToast('🚀 10-Event Demonstration Sequence Loaded into Timeline!');
        renderEventHistoryTable();
      } catch (e) {
        showToast('Failed to load demonstration sequence.');
      }
    }

    const btnDemo1 = document.getElementById('btn-run-demo-sequence');
    if (btnDemo1) btnDemo1.addEventListener('click', triggerDemoSequence);

    const btnDemo2 = document.getElementById('btn-modal-demo-sequence');
    if (btnDemo2) btnDemo2.addEventListener('click', triggerDemoSequence);

    // 8C. Clear Hotspots Button
    const btnClearHotspots = document.getElementById('btn-clear-hotspots');
    if (btnClearHotspots) {
      btnClearHotspots.addEventListener('click', async () => {
        document.querySelectorAll('.btn-hotspot-scenario').forEach(b => b.classList.remove('active'));
        try {
          await fetch('/api/hotspot', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ clear: true })
          });
          showToast('Cleared all active hotspots. System returning to thermal equilibrium.');
          const badge = document.getElementById('hud-status-badge');
          if (badge) {
            badge.className = 'status-badge normal';
            badge.innerHTML = `<span id="badge-dot">●</span> <span id="badge-text">NORMAL (EQUILIBRIUM)</span>`;
          }
          renderEventHistoryTable();
        } catch (e) {
          showToast('Failed to clear hotspots.');
        }
      });
    }

    // 8D. Automated Periodic Hotspot Generator Toggle & Interval
    const btnAutoHotspot = document.getElementById('btn-toggle-auto-hotspot');
    const selAutoInterval = document.getElementById('select-auto-hotspot-interval');
    const inpAutoSeed = document.getElementById('input-auto-seed');

    if (btnAutoHotspot) {
      btnAutoHotspot.addEventListener('click', async () => {
        STATE.autoHotspot = !STATE.autoHotspot;
        btnAutoHotspot.innerText = STATE.autoHotspot ? 'ON' : 'OFF';
        btnAutoHotspot.classList.toggle('active', STATE.autoHotspot);
        btnAutoHotspot.style.background = STATE.autoHotspot ? 'var(--accent-green, #10b981)' : '';
        btnAutoHotspot.style.color = STATE.autoHotspot ? '#000' : '';

        const intervalSec = parseFloat(selAutoInterval?.value || '30');
        const seedVal = parseInt(inpAutoSeed?.value || '42');
        try {
          await fetch('/api/hotspot', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              auto: {
                enabled: STATE.autoHotspot,
                interval_s: intervalSec,
                seed: seedVal
              }
            })
          });
          showToast(`Auto Hotspot Mode: ${STATE.autoHotspot ? 'ACTIVE (Every ' + intervalSec + 's)' : 'DISABLED'}`);
        } catch (e) {
          console.warn('Auto hotspot toggle error:', e);
        }
      });
    }

    if (selAutoInterval) {
      selAutoInterval.addEventListener('change', async () => {
        const intervalSec = parseFloat(selAutoInterval.value);
        const seedVal = parseInt(inpAutoSeed?.value || '42');
        if (STATE.autoHotspot) {
          try {
            await fetch('/api/hotspot', {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({
                auto: {
                  enabled: true,
                  interval_s: intervalSec,
                  seed: seedVal
                }
              })
            });
            showToast(`Auto Hotspot interval updated: ${intervalSec}s`);
          } catch (e) {
            console.warn('Interval update error:', e);
          }
        }
      });
    }

    // 8E. Exploded View Mode Button
    const btnExploded = document.getElementById('btn-toggle-exploded');
    if (btnExploded) {
      btnExploded.addEventListener('click', () => {
        STATE.explodedView = !STATE.explodedView;
        btnExploded.classList.toggle('active', STATE.explodedView);
        showToast(STATE.explodedView ? 'Exploded CAD View Active: Layers separated for inspection.' : 'Exploded View Deactivated: Reassembled.');
      });
    }

    // Hotspot button in cell inspector
    const btnCellHotspot = document.getElementById('btn-toggle-cell-hotspot');
    if (btnCellHotspot) {
      btnCellHotspot.addEventListener('click', async () => {
        if (!STATE.selectedObject || STATE.selectedObject.type !== 'cell') {
          showToast('Select a battery cell to toggle hotspot.');
          return;
        }
        const cellId = STATE.selectedObject.id;
        try {
          const res = await fetch('/api/hotspot', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              cell_ids: [cellId],
              multiplier: 3.0
            })
          });
          showToast(`Injected 3.0x thermal hotspot into ${cellId}!`);
        } catch (e) {
          showToast('Hotspot toggle failed.');
        }
      });
    }

    // 9. ML Predict Button
    const btnML = document.getElementById('btn-run-ml');
    if (btnML) btnML.addEventListener('click', runMLPrediction);

    // 10. Drawer Toggle Buttons
    const btnToggleCtrl = document.getElementById('btn-toggle-controls');
    if (btnToggleCtrl) {
      btnToggleCtrl.addEventListener('click', () => {
        document.getElementById('controls-panel').classList.toggle('collapsed');
      });
    }

    const btnToggleInsp = document.getElementById('btn-toggle-inspection');
    if (btnToggleInsp) {
      btnToggleInsp.addEventListener('click', () => {
        document.getElementById('inspection-panel').classList.toggle('collapsed');
      });
    }

    // 11. Inspection Tabs
    document.querySelectorAll('.tab-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
        document.querySelectorAll('.tab-pane').forEach(p => p.style.display = 'none');

        btn.classList.add('active');
        const targetPane = document.getElementById(btn.dataset.tab);
        if (targetPane) targetPane.style.display = 'block';
      });
    });

    // 12. Modals Setup
    setupModals();
  }

  async function sendControlUpdate(params) {
    try {
      await fetch('/api/control', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(params)
      });
    } catch (e) {
      console.warn('Control update error:', e);
    }
  }

  async function runMLPrediction() {
    const btn = document.getElementById('btn-run-ml');
    if (btn) btn.innerText = '⏳ Inferring...';
    try {
      const res = await fetch('/api/predict_ml', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          U_in: STATE.uIn,
          c_rate: STATE.cRate,
          B0: STATE.b0,
          phi1: STATE.phi1,
          phi2: STATE.phi2,
          k_perm: STATE.kPerm
        })
      });
      const data = await res.json();
      const resContainer = document.getElementById('ml-result-container');
      if (resContainer) resContainer.style.display = 'block';
      setVal('ml-pred-val', `${data.predicted_peak_temp_c} °C`);
      setVal('ml-physics-val', `${data.physics_solver_temp_c} °C`);
      setVal('ml-diff-val', `${data.absolute_error_c} °C`);
      setVal('ml-pred-time', `${data.inference_time_ms} ms`);
      showToast('ML Surrogate Prediction Complete');
    } catch (e) {
      showToast('ML inference offline');
    } finally {
      if (btn) btn.innerText = '⚡ Predict Peak Temperature (ML)';
    }
  }

  // ============================================================================
  // 9. MODALS (EQUATIONS, DATASET, LIVE CHARTS)
  // ============================================================================

  function setupModals() {
    const btnEq = document.getElementById('btn-open-equations');
    if (btnEq) {
      btnEq.addEventListener('click', async () => {
        document.getElementById('modal-equations').classList.add('open');
        loadAllEquations();
      });
    }

    const btnDs = document.getElementById('btn-open-dataset');
    if (btnDs) {
      btnDs.addEventListener('click', () => {
        document.getElementById('modal-dataset').classList.add('open');
      });
    }

    const btnGr = document.getElementById('btn-open-graphs');
    if (btnGr) {
      btnGr.addEventListener('click', () => {
        document.getElementById('modal-graphs').classList.add('open');
        initCharts();
      });
    }

    const btnExport = document.getElementById('btn-export-csv');
    if (btnExport) {
      btnExport.addEventListener('click', () => {
        window.location.href = '/api/export_csv';
        showToast('Exporting simulation results CSV...');
      });
    }

    const btnHistory = document.getElementById('btn-open-history');
    if (btnHistory) {
      btnHistory.addEventListener('click', () => {
        document.getElementById('modal-hotspot-history').classList.add('open');
        renderEventHistoryTable();
      });
    }

    const btnViewHistory = document.getElementById('btn-view-event-history');
    if (btnViewHistory) {
      btnViewHistory.addEventListener('click', () => {
        document.getElementById('modal-hotspot-history').classList.add('open');
        renderEventHistoryTable();
      });
    }

    const btnExportEvents = document.getElementById('btn-export-events-csv');
    if (btnExportEvents) {
      btnExportEvents.addEventListener('click', () => {
        window.location.href = '/api/export_hotspot_events_csv';
        showToast('Exporting Hotspot Event History CSV...');
      });
    }

    document.querySelectorAll('.close-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        const modalId = btn.dataset.modal;
        const modalEl = document.getElementById(modalId);
        if (modalEl) modalEl.classList.remove('open');
      });
    });

    document.querySelectorAll('.modal-overlay').forEach(modal => {
      modal.addEventListener('click', (e) => {
        if (e.target === modal) modal.classList.remove('open');
      });
    });

    const eqSearch = document.getElementById('eq-search');
    if (eqSearch) {
      eqSearch.addEventListener('input', (e) => {
        const term = e.target.value.toLowerCase();
        document.querySelectorAll('.eq-item-card').forEach(card => {
          const text = card.innerText.toLowerCase();
          card.style.display = text.includes(term) ? 'block' : 'none';
        });
      });
    }

    setupDatasetUpload();
  }

  async function loadAllEquations() {
    const container = document.getElementById('all-equations-list');
    if (!container) return;
    container.innerHTML = '<div style="text-align:center; padding: 20px;">Loading 39 governing equations (24 Core + A to O)...</div>';
    try {
      const res = await fetch('/api/equations');
      const data = await res.json();
      container.innerHTML = '';

      function renderEquationCard(eq) {
        const card = document.createElement('div');
        card.className = 'section-box eq-item-card';
        card.style.padding = '14px';
        const label = eq.letter ? `EQ ${eq.id} [EQ ${eq.letter}]: ${eq.name}` : `EQ ${eq.id}: ${eq.name}`;
        card.innerHTML = `
          <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">
            <span style="font-weight: 700; color: var(--accent-cyan); font-size: 12px;">${label}</span>
            <span class="station-badge">${eq.domain || 'MHD / Thermal'}</span>
          </div>
          <div style="font-family: var(--font-mono); font-size: 11px; background: rgba(0,0,0,0.3); padding: 8px; border-radius: 4px; margin-bottom: 8px;" id="explorer-eq-${eq.id}">
            ${eq.latex_display || eq.symbolic || eq.latex || ''}
          </div>
          <div style="grid-template-columns: 1fr 1fr; gap: 8px; font-size: 10.5px; margin-bottom: 8px; display: grid;">
            <div><strong>Inputs:</strong> ${formatInputs(eq.inputs || eq.variables)}</div>
            <div><strong>Live Substitution:</strong> <span style="font-family: var(--font-mono); color: #cbd5e1;">${eq.substitution || ''}</span></div>
          </div>
          <div style="display: flex; justify-content: space-between; align-items: center; border-top: 1px solid rgba(255,255,255,0.06); padding-top: 6px;">
            <span style="font-size: 10px; color: var(--text-muted);">${eq.citation || 'Engineering Formulation'}</span>
            <span style="font-weight: 700; color: var(--accent-green); font-family: var(--font-mono); font-size: 12px;">
              = ${typeof (eq.calculated_value ?? eq.result) === 'number' ? (eq.calculated_value ?? eq.result).toFixed(4) : (eq.calculated_value ?? eq.result)} ${eq.si_units || eq.unit || ''}
            </span>
          </div>
        `;
        container.appendChild(card);

        if (window.katex) {
          const el = document.getElementById(`explorer-eq-${eq.id}`);
          if (el) katex.render(eq.latex_display || eq.symbolic || '', el, { throwOnError: false });
        }
      }

      // Section 1 Header
      const headerCore = document.createElement('div');
      headerCore.innerHTML = `<h4 style="color: var(--accent-cyan); margin: 8px 0 8px 0; font-size: 13px; text-transform: uppercase; letter-spacing: 0.5px; border-bottom: 1px solid rgba(0,212,255,0.3); padding-bottom: 4px;">Part 1: Core Governing Thermal-MHD & Nanofluid Equations (Eqs 1 to 24)</h4>`;
      container.appendChild(headerCore);

      (data.equations || []).forEach(eq => renderEquationCard(eq));

      // Section 2 Header
      if (data.cylindrical_equations && data.cylindrical_equations.length > 0) {
        const headerCyl = document.createElement('div');
        headerCyl.innerHTML = `<h4 style="color: #f59e0b; margin: 18px 0 8px 0; font-size: 13px; text-transform: uppercase; letter-spacing: 0.5px; border-bottom: 1px solid rgba(245,158,11,0.3); padding-bottom: 4px;">Part 2: Cylindrical Pack & Trumony Wavy Cooling Ribbon Equations (Eqs 25 to 39 / Equations A to O)</h4>`;
        container.appendChild(headerCyl);

        data.cylindrical_equations.forEach(eq => renderEquationCard(eq));
      }
    } catch (e) {
      container.innerHTML = '<div style="color: var(--accent-red); padding: 20px;">Could not connect to equations API.</div>';
    }
  }

  function formatInputs(inputs) {
    if (!inputs) return '';
    return Object.entries(inputs)
      .map(([k, v]) => `${k} = ${v}`)
      .join(', ');
  }

  function setupDatasetUpload() {
    const dropZone = document.getElementById('drop-zone');
    const fileInput = document.getElementById('dataset-file-input');
    const btnBrowse = document.getElementById('btn-browse-file');

    if (!dropZone || !fileInput || !btnBrowse) return;

    btnBrowse.addEventListener('click', () => fileInput.click());

    ['dragenter', 'dragover'].forEach(name => {
      dropZone.addEventListener(name, (e) => {
        e.preventDefault();
        dropZone.style.borderColor = 'var(--accent-cyan)';
      });
    });

    ['dragleave', 'drop'].forEach(name => {
      dropZone.addEventListener(name, (e) => {
        e.preventDefault();
        dropZone.style.borderColor = 'var(--border-subtle)';
      });
    });

    dropZone.addEventListener('drop', (e) => {
      if (e.dataTransfer.files.length > 0) {
        handleFileUpload(e.dataTransfer.files[0]);
      }
    });

    fileInput.addEventListener('change', (e) => {
      if (e.target.files.length > 0) {
        handleFileUpload(e.target.files[0]);
      }
    });
  }

  async function handleFileUpload(file) {
    const formData = new FormData();
    formData.append('file', file);

    try {
      const res = await fetch('/api/upload_dataset', {
        method: 'POST',
        body: formData
      });
      const data = await res.json();
      if (data.success) {
        showToast(`Dataset loaded: ${data.valid_rows} valid records`);
        renderDatasetTable(file.name, data.records);
      } else {
        showToast('Dataset validation error: ' + (data.error || 'Invalid file format'));
      }
    } catch (e) {
      showToast('Error uploading dataset: ' + e.message);
    }
  }

  function renderDatasetTable(fileName, records) {
    const summaryBox = document.getElementById('dataset-summary-box');
    const nameLabel = document.getElementById('dataset-filename-label');
    const tbody = document.getElementById('dataset-table-body');
    if (!summaryBox || !nameLabel || !tbody) return;

    summaryBox.style.display = 'block';
    nameLabel.innerText = `${fileName} (${records.length} Records)`;
    tbody.innerHTML = '';

    records.forEach((rec, idx) => {
      const tr = document.createElement('tr');
      tr.innerHTML = `
        <td>#${idx + 1}</td>
        <td>${rec.C_rate || rec.c_rate || 2.0} C</td>
        <td>${rec.U_in || 0.25} m/s</td>
        <td>${rec.T_in || 22.0} °C</td>
        <td>${rec.B0 || 0.5} T</td>
        <td>${(((rec.phi1 || 0.015) + (rec.phi2 || 0.01)) * 100).toFixed(1)} %</td>
        <td><button class="btn-preset apply-rec-btn" style="padding: 2px 8px;">Apply</button></td>
      `;

      tr.querySelector('.apply-rec-btn').addEventListener('click', async () => {
        try {
          await fetch('/api/apply_dataset', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ record: rec })
          });
          showToast(`Applied configuration #${idx + 1} to 3D Simulation.`);
          document.getElementById('modal-dataset').classList.remove('open');
        } catch (e) {
          showToast('Failed to apply dataset record.');
        }
      });

      tbody.appendChild(tr);
    });
  }

  // ============================================================================
  // 10. REAL-TIME CHARTS
  // ============================================================================

  function initCharts() {
    if (typeof Chart === 'undefined') return;

    if (!chartTemp) {
      const canvas1 = document.getElementById('chart-temp');
      if (canvas1) {
        const ctx1 = canvas1.getContext('2d');
        chartTemp = new Chart(ctx1, {
          type: 'line',
          data: {
            labels: historyData.labels,
            datasets: [
              { label: 'T_Max', data: historyData.tMax, borderColor: '#ef4444', tension: 0.2 },
              { label: 'T_Avg', data: historyData.tAvg, borderColor: '#00d4ff', tension: 0.2 },
              { label: 'T_Min', data: historyData.tMin, borderColor: '#10b981', tension: 0.2 }
            ]
          },
          options: { responsive: true, animation: false, scales: { y: { grid: { color: 'rgba(255,255,255,0.05)' } } } }
        });
      }
    }

    if (!chartCoolant) {
      const canvas2 = document.getElementById('chart-coolant');
      if (canvas2) {
        const ctx2 = canvas2.getContext('2d');
        chartCoolant = new Chart(ctx2, {
          type: 'line',
          data: {
            labels: historyData.labels,
            datasets: [
              { label: 'Inlet T_in', data: historyData.tIn, borderColor: '#3b82f6', tension: 0.2 },
              { label: 'Outlet T_out', data: historyData.tOut, borderColor: '#f97316', tension: 0.2 }
            ]
          },
          options: { responsive: true, animation: false, scales: { y: { grid: { color: 'rgba(255,255,255,0.05)' } } } }
        });
      }
    }

    if (!chartNumbers) {
      const canvas3 = document.getElementById('chart-numbers');
      if (canvas3) {
        const ctx3 = canvas3.getContext('2d');
        chartNumbers = new Chart(ctx3, {
          type: 'line',
          data: {
            labels: historyData.labels,
            datasets: [
              { label: 'Reynolds (Re)', data: historyData.re, borderColor: '#8b5cf6', yAxisID: 'y' },
              { label: 'Nusselt (Nu)', data: historyData.nu, borderColor: '#ec4899', yAxisID: 'y1' }
            ]
          },
          options: {
            responsive: true,
            animation: false,
            scales: {
              y: { type: 'linear', position: 'left' },
              y1: { type: 'linear', position: 'right', grid: { drawOnChartArea: false } }
            }
          }
        });
      }
    }

    if (!chartHeat) {
      const canvas4 = document.getElementById('chart-heat');
      if (canvas4) {
        const ctx4 = canvas4.getContext('2d');
        chartHeat = new Chart(ctx4, {
          type: 'line',
          data: {
            labels: historyData.labels,
            datasets: [
              { label: 'Heat Generation (W)', data: historyData.qGen, borderColor: '#ef4444' },
              { label: 'Heat Removal (W)', data: historyData.qRem, borderColor: '#06b6d4' }
            ]
          },
          options: { responsive: true, animation: false }
        });
      }
    }
  }

  function pushHistoryData(entry) {
    const timeLabel = `${entry.time.toFixed(1)}s`;
    historyData.labels.push(timeLabel);
    historyData.tMax.push(entry.tMax);
    historyData.tAvg.push(entry.tAvg);
    historyData.tMin.push(entry.tMin);
    historyData.tIn.push(entry.tIn);
    historyData.tOut.push(entry.tOut);
    historyData.re.push(entry.re);
    historyData.nu.push(entry.nu);
    historyData.qGen.push(entry.qGen);
    historyData.qRem.push(entry.qRem);

    if (historyData.labels.length > historyLimit) {
      historyData.labels.shift();
      historyData.tMax.shift();
      historyData.tAvg.shift();
      historyData.tMin.shift();
      historyData.tIn.shift();
      historyData.tOut.shift();
      historyData.re.shift();
      historyData.nu.shift();
      historyData.qGen.shift();
      historyData.qRem.shift();
    }

    if (chartTemp) {
      chartTemp.data.labels = historyData.labels;
      chartTemp.data.datasets[0].data = historyData.tMax;
      chartTemp.data.datasets[1].data = historyData.tAvg;
      chartTemp.data.datasets[2].data = historyData.tMin;
      chartTemp.update('none');
    }

    if (chartCoolant) {
      chartCoolant.data.labels = historyData.labels;
      chartCoolant.data.datasets[0].data = historyData.tIn;
      chartCoolant.data.datasets[1].data = historyData.tOut;
      chartCoolant.update('none');
    }

    if (chartNumbers) {
      chartNumbers.data.labels = historyData.labels;
      chartNumbers.data.datasets[0].data = historyData.re;
      chartNumbers.data.datasets[1].data = historyData.nu;
      chartNumbers.update('none');
    }

    if (chartHeat) {
      chartHeat.data.labels = historyData.labels;
      chartHeat.data.datasets[0].data = historyData.qGen;
      chartHeat.data.datasets[1].data = historyData.qRem;
      chartHeat.update('none');
    }
  }

  function showToast(msg) {
    const t = document.getElementById('toast-notification');
    if (!t) return;
    t.innerText = msg;
    t.classList.add('show');
    setTimeout(() => t.classList.remove('show'), 2800);
  }

  // ============================================================================
  // 11. BOOTSTRAP APPLICATION
  // ============================================================================
  function startApplication() {
    const ok = init3DScene();
    setupCameraButtons();
    setupLayerToggles();
    setupControls();

    if (ok) {
      animate();
    }

    // Default inspection on BAT-23
    setTimeout(() => {
      const bat23 = cellMeshes.find(m => m.userData.id === 'BAT-23') || cellMeshes[0];
      if (bat23) {
        selectObject(bat23);
      }
    }, 600);
  }

  if (document.readyState === 'loading') {
    window.addEventListener('DOMContentLoaded', startApplication);
  } else {
    startApplication();
  }

})();
