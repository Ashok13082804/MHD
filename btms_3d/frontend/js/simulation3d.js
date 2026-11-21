/**
 * 3D BTMS Simulation Engine (Three.js WebGL)
 * Implements all 20 mechanical/thermal components, 50 individual battery cells,
 * raycasting interaction, view modes, and rotating mechanisms.
 */

class BTMS3DSimulation {
  constructor() {
    this.container = document.getElementById("viewport3d");
    this.tooltip = document.getElementById("floatingTooltip");
    this.selectedObject = null;
    this.hoveredObject = null;

    // View mode flags
    this.isExploded = false;
    this.isCutaway = false;
    this.explodeFactor = 0.0;
    this.targetExplodeFactor = 0.0;

    // Component meshes registry
    this.cellMeshes = new Map(); // "B01" -> Mesh
    this.componentMeshes = new Map(); // "pump" -> Group/Mesh
    this.interactiveObjects = [];

    // Animated rotating parts
    this.fanBlades = null;
    this.pumpImpeller = null;
    this.magneticFluxGroup = null;
    this.porousFoamGroup = null;

    this.initScene();
    this.initLighting();
    this.buildGeometry();
    this.initInteraction();
    this.bindViewButtons();
  }

  initScene() {
    const width = this.container.clientWidth;
    const height = this.container.clientHeight;

    this.scene = new THREE.Scene();
    this.scene.background = new THREE.Color(0x070d19);
    this.scene.fog = new THREE.FogExp2(0x070d19, 0.035);

    this.camera = new THREE.PerspectiveCamera(45, width / height, 0.1, 100);
    this.defaultCamPos = new THREE.Vector3(0, 5.0, 7.5);
    this.defaultCamTarget = new THREE.Vector3(0, 0.2, 0);
    this.camera.position.copy(this.defaultCamPos);

    this.renderer = new THREE.WebGLRenderer({ antialias: true, alpha: false });
    this.renderer.setSize(width, height);
    this.renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    this.renderer.shadowMap.enabled = true;
    this.renderer.shadowMap.type = THREE.PCFSoftShadowMap;
    this.container.appendChild(this.renderer.domElement);

    this.controls = new THREE.OrbitControls(this.camera, this.renderer.domElement);
    this.controls.enableDamping = true;
    this.controls.dampingFactor = 0.05;
    this.controls.target.copy(this.defaultCamTarget);
    this.controls.maxPolarAngle = Math.PI / 2 + 0.1; // Don't go below floor
    this.controls.minDistance = 1.5;
    this.controls.maxDistance = 25.0;

    // Grid Floor
    const grid = new THREE.GridHelper(20, 40, 0x00f0ff, 0x152238);
    grid.position.y = -0.6;
    this.scene.add(grid);

    window.addEventListener("resize", () => this.onWindowResize());
  }

  initLighting() {
    const ambientLight = new THREE.AmbientLight(0xffffff, 0.45);
    this.scene.add(ambientLight);

    const dirLight = new THREE.DirectionalLight(0xffffff, 0.9);
    dirLight.position.set(6, 12, 8);
    dirLight.castShadow = true;
    dirLight.shadow.mapSize.width = 2048;
    dirLight.shadow.mapSize.height = 2048;
    dirLight.shadow.bias = -0.0001;
    this.scene.add(dirLight);

    const fillLight = new THREE.DirectionalLight(0x00a8ff, 0.35);
    fillLight.position.set(-8, 5, -6);
    this.scene.add(fillLight);

    const rimLight = new THREE.PointLight(0x00f0ff, 0.8, 10);
    rimLight.position.set(0, 3, -4);
    this.scene.add(rimLight);
  }

  buildGeometry() {
    this.build50BatteryCells();
    this.buildCoolingPlatesAndChannels();
    this.buildManifoldsAndPipelines();
    this.buildCirculationPump();
    this.buildCoolantReservoir();
    this.buildRadiatorAndFan();
    this.buildHeatExchangerAndChiller();
    this.buildThermalSensorsAndValves();
    this.buildMHDMagneticField();
    this.buildBMSController();
  }

  // 1. Exactly 50 Battery Cells (5x10 Array)
  build50BatteryCells() {
    this.cellsGroup = new THREE.Group();
    this.scene.add(this.cellsGroup);

    const rows = 5;
    const cols = 10;
    const spacingX = 0.42;
    const spacingZ = 0.28;
    const startX = -((cols - 1) * spacingX) / 2;
    const startZ = -((rows - 1) * spacingZ) / 2;

    const cellWidth = 0.34;
    const cellHeight = 0.65;
    const cellDepth = 0.18;

    const cellGeo = new THREE.BoxGeometry(cellWidth, cellHeight, cellDepth);

    // Terminal geometries (+ and - tabs on top of cell)
    const tabGeo = new THREE.BoxGeometry(0.06, 0.08, 0.04);
    const posTabMat = new THREE.MeshStandardMaterial({ color: 0xcc2222, metalness: 0.9, roughness: 0.2 });
    const negTabMat = new THREE.MeshStandardMaterial({ color: 0x222222, metalness: 0.9, roughness: 0.2 });

    let cellNum = 1;
    for (let r = 0; r < rows; r++) {
      for (let c = 0; c < cols; c++) {
        const cellId = `B${String(cellNum).padStart(2, "0")}`;
        const posX = startX + c * spacingX;
        const posY = 0.35 + cellHeight / 2;
        const posZ = startZ + r * spacingZ;

        // Individual cell material to allow independent coloring
        const cellMat = new THREE.MeshStandardMaterial({
          color: 0x00f0ff,
          roughness: 0.3,
          metalness: 0.6,
          emissive: 0x003344,
          emissiveIntensity: 0.2
        });

        const cellMesh = new THREE.Mesh(cellGeo, cellMat);
        cellMesh.position.set(posX, posY, posZ);
        cellMesh.castShadow = true;
        cellMesh.receiveShadow = true;

        cellMesh.userData = {
          type: "battery_cell",
          cellId: cellId,
          row: r,
          col: c,
          originalPos: new THREE.Vector3(posX, posY, posZ),
          explodePos: new THREE.Vector3(posX * 1.35, posY + 0.5, posZ * 1.35)
        };

        // Terminals
        const posTab = new THREE.Mesh(tabGeo, posTabMat);
        posTab.position.set(-0.08, cellHeight / 2 + 0.04, 0);
        cellMesh.add(posTab);

        const negTab = new THREE.Mesh(tabGeo, negTabMat);
        negTab.position.set(0.08, cellHeight / 2 + 0.04, 0);
        cellMesh.add(negTab);

        this.cellsGroup.add(cellMesh);
        this.cellMeshes.set(cellId, cellMesh);
        this.interactiveObjects.push(cellMesh);

        cellNum++;
      }
    }
  }

  // 2. Battery Cooling Plates and Internal Channels
  buildCoolingPlatesAndChannels() {
    this.coolingPlatesGroup = new THREE.Group();
    this.scene.add(this.coolingPlatesGroup);

    // Main aluminum cooling cold plate (located directly beneath the 50 cells)
    const plateWidth = 4.4;
    const plateHeight = 0.12;
    const plateDepth = 1.6;

    const plateGeo = new THREE.BoxGeometry(plateWidth, plateHeight, plateDepth);
    this.plateMat = new THREE.MeshStandardMaterial({
      color: 0x8899aa,
      metalness: 0.85,
      roughness: 0.25,
      transparent: false,
      opacity: 1.0
    });

    this.coldPlateMesh = new THREE.Mesh(plateGeo, this.plateMat);
    this.coldPlateMesh.position.set(0, 0.25, 0);
    this.coldPlateMesh.castShadow = true;
    this.coldPlateMesh.receiveShadow = true;
    this.coldPlateMesh.userData = {
      type: "component",
      id: "cooling_plate",
      name: "Cold Plate",
      originalPos: new THREE.Vector3(0, 0.25, 0),
      explodePos: new THREE.Vector3(0, -0.4, 0)
    };
    this.coolingPlatesGroup.add(this.coldPlateMesh);
    this.componentMeshes.set("cooling_plate", this.coldPlateMesh);
    this.interactiveObjects.push(this.coldPlateMesh);

    // 11 Internal Cooling Channels (visible in cutaway/exploded view)
    this.channelGroup = new THREE.Group();
    const rows = 5;
    const spacingZ = 0.28;
    const startZ = -((rows - 1) * spacingZ) / 2;

    const chGeo = new THREE.BoxGeometry(4.2, 0.06, 0.08);
    const chMat = new THREE.MeshStandardMaterial({
      color: 0x00f0ff,
      roughness: 0.2,
      metalness: 0.3,
      transparent: true,
      opacity: 0.75
    });

    for (let i = 0; i < 11; i++) {
      const zPos = startZ - 0.14 + i * (spacingZ * 0.95);
      const chMesh = new THREE.Mesh(chGeo, chMat);
      chMesh.position.set(0, 0.25, zPos);
      chMesh.userData = { type: "component", id: "cooling_channel", name: `Cooling Channel ${i+1}` };
      this.channelGroup.add(chMesh);
    }
    this.coolingPlatesGroup.add(this.channelGroup);

    // Porous Metal Foam Inserts (textured/wireframe inserts within channels)
    this.porousFoamGroup = new THREE.Group();
    const foamMat = new THREE.MeshStandardMaterial({
      color: 0xb87333, // Copper foam color
      wireframe: true,
      transparent: true,
      opacity: 0.5
    });
    for (let i = 0; i < 11; i++) {
      const zPos = startZ - 0.14 + i * (spacingZ * 0.95);
      const foamMesh = new THREE.Mesh(chGeo, foamMat);
      foamMesh.position.set(0, 0.25, zPos);
      foamMesh.scale.set(0.98, 0.9, 0.9);
      this.porousFoamGroup.add(foamMesh);
    }
    this.scene.add(this.porousFoamGroup);
  }

  // 3. Manifolds and Tubular Pipelines
  buildManifoldsAndPipelines() {
    this.pipelineGroup = new THREE.Group();
    this.scene.add(this.pipelineGroup);

    const pipeMat = new THREE.MeshStandardMaterial({
      color: 0x4a6572,
      metalness: 0.8,
      roughness: 0.3,
      transparent: false,
      opacity: 1.0
    });
    this.pipeMat = pipeMat;

    // Inlet Manifold Cylinder (distribution plenum)
    const manifoldGeo = new THREE.CylinderGeometry(0.12, 0.12, 1.6, 24);
    const inManifold = new THREE.Mesh(manifoldGeo, pipeMat);
    inManifold.rotation.x = Math.PI / 2;
    inManifold.position.set(-2.2, 0.25, 0);
    inManifold.userData = { type: "component", id: "inlet_manifold", name: "Inlet Distribution Manifold" };
    this.pipelineGroup.add(inManifold);
    this.interactiveObjects.push(inManifold);

    // Outlet Manifold Cylinder (collection plenum)
    const outManifold = new THREE.Mesh(manifoldGeo, pipeMat);
    outManifold.rotation.x = Math.PI / 2;
    outManifold.position.set(2.2, 0.25, 0);
    outManifold.userData = { type: "component", id: "outlet_manifold", name: "Outlet Collection Manifold" };
    this.pipelineGroup.add(outManifold);
    this.interactiveObjects.push(outManifold);

    // Curved Connection Pipelines using TubeGeometry
    const createTube = (pts, name, id) => {
      const curve = new THREE.CatmullRomCurve3(pts);
      const tubeGeo = new THREE.TubeGeometry(curve, 32, 0.07, 16, false);
      const tube = new THREE.Mesh(tubeGeo, pipeMat);
      tube.userData = { type: "component", id: id, name: name };
      this.pipelineGroup.add(tube);
      this.interactiveObjects.push(tube);
      return tube;
    };

    // Pump to Inlet Manifold line
    createTube([
      new THREE.Vector3(-3.2, 0.4, 2.0),
      new THREE.Vector3(-2.8, 0.4, 1.8),
      new THREE.Vector3(-2.2, 0.25, 1.0),
      new THREE.Vector3(-2.2, 0.25, 0.6)
    ], "Inlet Pipeline", "inlet_pipeline");

    // Outlet Manifold to Heat Exchanger line
    createTube([
      new THREE.Vector3(2.2, 0.25, -0.6),
      new THREE.Vector3(2.2, 0.35, -1.5),
      new THREE.Vector3(2.8, 0.45, -2.0),
      new THREE.Vector3(3.0, 0.5, -2.0)
    ], "Outlet Pipeline", "outlet_pipeline");

    // Heat Exchanger to Radiator line
    createTube([
      new THREE.Vector3(3.2, 0.6, -0.6),
      new THREE.Vector3(2.8, 0.7, 1.0),
      new THREE.Vector3(1.8, 0.8, 2.2),
      new THREE.Vector3(1.6, 0.8, 2.4)
    ], "Inter-Cooler Return Line", "return_pipeline");

    // Radiator to Reservoir line
    createTube([
      new THREE.Vector3(-0.6, 0.7, 2.7),
      new THREE.Vector3(-1.4, 0.65, 2.7),
      new THREE.Vector3(-2.0, 0.6, 2.5)
    ], "Reservoir Suction Line", "suction_pipeline");
  }

  // 4. Nanofluid Circulation Pump
  buildCirculationPump() {
    this.pumpGroup = new THREE.Group();
    this.pumpGroup.position.set(-3.2, 0.4, 2.0);
    this.scene.add(this.pumpGroup);

    // Pump motor casing (cylindrical motor)
    const motorGeo = new THREE.CylinderGeometry(0.24, 0.24, 0.55, 24);
    const motorMat = new THREE.MeshStandardMaterial({ color: 0x1e3d59, metalness: 0.8, roughness: 0.3 });
    const motorMesh = new THREE.Mesh(motorGeo, motorMat);
    motorMesh.position.y = 0.28;
    this.pumpGroup.add(motorMesh);

    // Volute casing
    const voluteGeo = new THREE.TorusGeometry(0.26, 0.12, 16, 32);
    const voluteMat = new THREE.MeshStandardMaterial({ color: 0x17b978, metalness: 0.6, roughness: 0.4 });
    const voluteMesh = new THREE.Mesh(voluteGeo, voluteMat);
    voluteMesh.rotation.x = Math.PI / 2;
    this.pumpGroup.add(voluteMesh);

    // Internal rotating impeller (visible inside pump)
    this.pumpImpeller = new THREE.Group();
    const bladeGeo = new THREE.BoxGeometry(0.04, 0.08, 0.24);
    const bladeMat = new THREE.MeshStandardMaterial({ color: 0xffaa00, metalness: 0.9, roughness: 0.2 });
    for (let i = 0; i < 6; i++) {
      const blade = new THREE.Mesh(bladeGeo, bladeMat);
      blade.rotation.y = (i * Math.PI) / 3;
      this.pumpImpeller.add(blade);
    }
    this.pumpGroup.add(this.pumpImpeller);

    this.pumpGroup.userData = {
      type: "component",
      id: "pump",
      name: "Nanofluid Circulation Pump",
      originalPos: new THREE.Vector3(-3.2, 0.4, 2.0),
      explodePos: new THREE.Vector3(-4.2, 0.4, 2.8)
    };
    this.componentMeshes.set("pump", this.pumpGroup);
    this.interactiveObjects.push(motorMesh);
  }

  // 5. Coolant Reservoir
  buildCoolantReservoir() {
    this.resGroup = new THREE.Group();
    this.resGroup.position.set(-2.2, 0.6, 2.5);
    this.scene.add(this.resGroup);

    // Translucent acrylic reservoir tank
    const tankGeo = new THREE.CylinderGeometry(0.3, 0.3, 0.8, 24);
    const tankMat = new THREE.MeshStandardMaterial({
      color: 0x88ccff,
      roughness: 0.1,
      metalness: 0.1,
      transparent: true,
      opacity: 0.4
    });
    const tankMesh = new THREE.Mesh(tankGeo, tankMat);
    this.resGroup.add(tankMesh);

    // Fluid mesh inside reservoir
    const fluidGeo = new THREE.CylinderGeometry(0.28, 0.28, 0.6, 24);
    const fluidMat = new THREE.MeshStandardMaterial({
      color: 0x00e5ff,
      roughness: 0.2,
      metalness: 0.2,
      transparent: true,
      opacity: 0.75
    });
    const fluidMesh = new THREE.Mesh(fluidGeo, fluidMat);
    fluidMesh.position.y = -0.08;
    this.resGroup.add(fluidMesh);

    this.resGroup.userData = {
      type: "component",
      id: "reservoir",
      name: "Hybrid Nanofluid Reservoir",
      originalPos: new THREE.Vector3(-2.2, 0.6, 2.5),
      explodePos: new THREE.Vector3(-3.0, 0.8, 3.5)
    };
    this.componentMeshes.set("reservoir", this.resGroup);
    this.interactiveObjects.push(tankMesh);
  }

  // 6. Radiator & Rotating Fan
  buildRadiatorAndFan() {
    this.radiatorGroup = new THREE.Group();
    this.radiatorGroup.position.set(0.5, 0.8, 2.6);
    this.scene.add(this.radiatorGroup);

    // Radiator Core Frame
    const frameGeo = new THREE.BoxGeometry(1.8, 1.1, 0.18);
    const frameMat = new THREE.MeshStandardMaterial({ color: 0x222831, metalness: 0.7, roughness: 0.4 });
    const frameMesh = new THREE.Mesh(frameGeo, frameMat);
    this.radiatorGroup.add(frameMesh);

    // Radiator Fin Grid (corrugated texture representation)
    const finGeo = new THREE.BoxGeometry(1.6, 0.9, 0.14);
    const finMat = new THREE.MeshStandardMaterial({ color: 0x718096, metalness: 0.9, roughness: 0.3, wireframe: false });
    const finMesh = new THREE.Mesh(finGeo, finMat);
    this.radiatorGroup.add(finMesh);

    // Fan Shroud & Rotating Axial Fan
    const shroudGeo = new THREE.CylinderGeometry(0.42, 0.42, 0.12, 32);
    const shroudMat = new THREE.MeshStandardMaterial({ color: 0x1a202c, roughness: 0.5 });
    const shroudMesh = new THREE.Mesh(shroudGeo, shroudMat);
    shroudMesh.rotation.x = Math.PI / 2;
    shroudMesh.position.set(0, 0, 0.14);
    this.radiatorGroup.add(shroudMesh);

    // 7-Blade Axial Fan
    this.fanBlades = new THREE.Group();
    this.fanBlades.position.set(0, 0, 0.14);
    const bladeGeo = new THREE.BoxGeometry(0.08, 0.38, 0.02);
    const bladeMat = new THREE.MeshStandardMaterial({ color: 0x00f0ff, roughness: 0.2, metalness: 0.5 });

    for (let b = 0; b < 7; b++) {
      const blade = new THREE.Mesh(bladeGeo, bladeMat);
      blade.rotation.z = (b * Math.PI * 2) / 7;
      blade.position.y = 0.18 * Math.cos((b * Math.PI * 2) / 7);
      blade.position.x = -0.18 * Math.sin((b * Math.PI * 2) / 7);
      this.fanBlades.add(blade);
    }
    this.radiatorGroup.add(this.fanBlades);

    this.radiatorGroup.userData = {
      type: "component",
      id: "radiator",
      name: "Front Radiator & Axial Fan",
      originalPos: new THREE.Vector3(0.5, 0.8, 2.6),
      explodePos: new THREE.Vector3(0.5, 1.2, 4.0)
    };
    this.componentMeshes.set("radiator", this.radiatorGroup);
    this.interactiveObjects.push(frameMesh);
  }

  // 7. Heat Exchanger & Chiller
  buildHeatExchangerAndChiller() {
    // Heat Exchanger Unit (Shell & Tube HEX)
    this.hexGroup = new THREE.Group();
    this.hexGroup.position.set(3.1, 0.5, -1.3);
    this.scene.add(this.hexGroup);

    const hexGeo = new THREE.CylinderGeometry(0.26, 0.26, 1.1, 24);
    const hexMat = new THREE.MeshStandardMaterial({ color: 0xd4af37, metalness: 0.85, roughness: 0.2 }); // Brass/copper shell
    const hexMesh = new THREE.Mesh(hexGeo, hexMat);
    hexMesh.rotation.z = Math.PI / 2;
    this.hexGroup.add(hexMesh);

    this.hexGroup.userData = {
      type: "component",
      id: "heat_exchanger",
      name: "Counter-Flow Heat Exchanger",
      originalPos: new THREE.Vector3(3.1, 0.5, -1.3),
      explodePos: new THREE.Vector3(4.3, 0.5, -1.8)
    };
    this.componentMeshes.set("heat_exchanger", this.hexGroup);
    this.interactiveObjects.push(hexMesh);

    // Refrigeration Chiller Unit
    this.chillerGroup = new THREE.Group();
    this.chillerGroup.position.set(3.0, 0.4, 0.5);
    this.scene.add(this.chillerGroup);

    const chillerGeo = new THREE.BoxGeometry(0.7, 0.6, 0.7);
    const chillerMat = new THREE.MeshStandardMaterial({ color: 0x334e68, metalness: 0.7, roughness: 0.4 });
    const chillerMesh = new THREE.Mesh(chillerGeo, chillerMat);
    this.chillerGroup.add(chillerMesh);

    this.chillerGroup.userData = {
      type: "component",
      id: "chiller",
      name: "Vapor-Compression Chiller",
      originalPos: new THREE.Vector3(3.0, 0.4, 0.5),
      explodePos: new THREE.Vector3(4.2, 0.4, 0.8)
    };
    this.componentMeshes.set("chiller", this.chillerGroup);
    this.interactiveObjects.push(chillerMesh);
  }

  // 8. Sensors and 3-Way Thermal Valve
  buildThermalSensorsAndValves() {
    this.sensorsGroup = new THREE.Group();
    this.scene.add(this.sensorsGroup);

    // 3-Way Thermal Control Valve
    const valveGeo = new THREE.BoxGeometry(0.24, 0.24, 0.24);
    const valveMat = new THREE.MeshStandardMaterial({ color: 0xff5722, metalness: 0.8, roughness: 0.3 });
    const valveMesh = new THREE.Mesh(valveGeo, valveMat);
    valveMesh.position.set(2.6, 0.35, -1.5);
    valveMesh.userData = { type: "component", id: "thermal_valve", name: "3-Way Thermal Proportional Valve" };
    this.sensorsGroup.add(valveMesh);
    this.interactiveObjects.push(valveMesh);
  }

  // 9. Magnetohydrodynamic (MHD) Field Visualization
  buildMHDMagneticField() {
    this.mhdGroup = new THREE.Group();
    this.scene.add(this.mhdGroup);

    // North Pole Magnet Block (Top)
    const poleGeo = new THREE.BoxGeometry(1.2, 0.15, 1.8);
    const northMat = new THREE.MeshStandardMaterial({ color: 0xd32f2f, metalness: 0.8, roughness: 0.3 });
    const northPole = new THREE.Mesh(poleGeo, northMat);
    northPole.position.set(0, 1.2, 0);
    this.mhdGroup.add(northPole);

    // South Pole Magnet Block (Bottom)
    const southMat = new THREE.MeshStandardMaterial({ color: 0x1976d2, metalness: 0.8, roughness: 0.3 });
    const southPole = new THREE.Mesh(poleGeo, southMat);
    southPole.position.set(0, -0.4, 0);
    this.mhdGroup.add(southPole);

    // Translucent Magnetic Flux Lines passing between poles
    this.magneticFluxGroup = new THREE.Group();
    const lineMat = new THREE.LineDashedMaterial({
      color: 0x00f0ff,
      dashSize: 0.1,
      gapSize: 0.05,
      transparent: true,
      opacity: 0.65
    });

    for (let x = -0.5; x <= 0.5; x += 0.25) {
      for (let z = -0.7; z <= 0.7; z += 0.35) {
        const points = [
          new THREE.Vector3(x, 1.1, z),
          new THREE.Vector3(x, -0.3, z)
        ];
        const lineGeo = new THREE.BufferGeometry().setFromPoints(points);
        const line = new THREE.Line(lineGeo, lineMat);
        line.computeLineDistances();
        this.magneticFluxGroup.add(line);
      }
    }
    this.mhdGroup.add(this.magneticFluxGroup);

    this.mhdGroup.userData = { type: "component", id: "mhd_region", name: "MHD Transverse Magnetic Pole Core" };
  }

  // 10. BMS Controller Module
  buildBMSController() {
    this.bmsGroup = new THREE.Group();
    this.bmsGroup.position.set(-2.8, 0.4, -1.8);
    this.scene.add(this.bmsGroup);

    const bmsGeo = new THREE.BoxGeometry(0.8, 0.4, 0.5);
    const bmsMat = new THREE.MeshStandardMaterial({ color: 0x1f2937, metalness: 0.6, roughness: 0.3 });
    const bmsMesh = new THREE.Mesh(bmsGeo, bmsMat);
    this.bmsGroup.add(bmsMesh);

    // Status LED
    const ledGeo = new THREE.SphereGeometry(0.04, 16, 16);
    this.bmsLedMat = new THREE.MeshBasicMaterial({ color: 0x00ff88 });
    const ledMesh = new THREE.Mesh(ledGeo, this.bmsLedMat);
    ledMesh.position.set(0.3, 0.21, 0.15);
    this.bmsGroup.add(ledMesh);

    this.bmsGroup.userData = {
      type: "component",
      id: "bms_controller",
      name: "Battery Management System Controller",
      originalPos: new THREE.Vector3(-2.8, 0.4, -1.8),
      explodePos: new THREE.Vector3(-3.8, 0.6, -2.6)
    };
    this.componentMeshes.set("bms_controller", this.bmsGroup);
    this.interactiveObjects.push(bmsMesh);
  }

  initInteraction() {
    this.raycaster = new THREE.Raycaster();
    this.mouse = new THREE.Vector2();

    this.container.addEventListener("mousemove", (e) => this.onMouseMove(e));
    this.container.addEventListener("click", (e) => this.onClick(e));
  }

  onMouseMove(e) {
    const rect = this.container.getBoundingClientRect();
    this.mouse.x = ((e.clientX - rect.left) / rect.width) * 2 - 1;
    this.mouse.y = -((e.clientY - rect.top) / rect.height) * 2 + 1;

    // Check measurement points first
    let hitFound = false;
    let clickables = [...this.interactiveObjects];
    if (window.measManager) {
      clickables = clickables.concat(window.measManager.getClickableObjects());
    }

    this.raycaster.setFromCamera(this.mouse, this.camera);
    const intersects = this.raycaster.intersectObjects(clickables, true);

    if (intersects.length > 0) {
      const hit = intersects[0].object;
      const data = hit.userData || (hit.parent && hit.parent.userData);

      if (data) {
        hitFound = true;
        this.hoveredObject = hit;
        this.showTooltip(e.clientX, e.clientY, data);
      }
    }

    if (!hitFound) {
      this.hoveredObject = null;
      this.hideTooltip();
    }
  }

  onClick(e) {
    const rect = this.container.getBoundingClientRect();
    this.mouse.x = ((e.clientX - rect.left) / rect.width) * 2 - 1;
    this.mouse.y = -((e.clientY - rect.top) / rect.height) * 2 + 1;

    let clickables = [...this.interactiveObjects];
    if (window.measManager) {
      clickables = clickables.concat(window.measManager.getClickableObjects());
    }

    this.raycaster.setFromCamera(this.mouse, this.camera);
    const intersects = this.raycaster.intersectObjects(clickables, true);

    if (intersects.length > 0) {
      const hit = intersects[0].object;
      const data = hit.userData || (hit.parent && hit.parent.userData);

      if (data) {
        this.selectObject(data);
      }
    }
  }

  selectObject(data) {
    if (data.type === "battery_cell") {
      if (window.ComponentInspector) {
        window.ComponentInspector.inspectCell(data.cellId);
      }
    } else if (data.type === "measurement_point") {
      if (window.measManager) {
        window.measManager.inspectPoint(data.id);
      }
    } else if (data.type === "component") {
      if (window.ComponentInspector) {
        window.ComponentInspector.inspectComponent(data.id);
      }
    }
  }

  showTooltip(clientX, clientY, data) {
    if (!this.tooltip) return;

    const rect = this.container.getBoundingClientRect();
    const x = clientX - rect.left + 15;
    const y = clientY - rect.top + 15;

    this.tooltip.style.left = `${x}px`;
    this.tooltip.style.top = `${y}px`;
    this.tooltip.classList.remove("hidden");

    if (data.type === "battery_cell") {
      document.getElementById("ttTitle").textContent = `CELL ${data.cellId}`;
      const cellData = (window.latestSimState && window.latestSimState.cells && window.latestSimState.cells.find(c => c.cell_id === data.cellId));
      if (cellData) {
        document.getElementById("ttTemp").textContent = `${cellData.temperature_c.toFixed(2)} °C`;
        document.getElementById("ttQgen").textContent = `${cellData.heat_generation_w.toFixed(2)} W`;
        document.getElementById("ttQcool").textContent = `${cellData.cooling_rate_w.toFixed(2)} W`;
        const statusEl = document.getElementById("ttStatus");
        statusEl.textContent = cellData.thermal_status.toUpperCase();
        statusEl.className = `status-pill ${cellData.thermal_status}`;
      }
    } else if (data.type === "measurement_point") {
      document.getElementById("ttTitle").textContent = `POINT ${data.id}`;
      const ptData = (window.latestSimState && window.latestSimState.measurement_points && window.latestSimState.measurement_points[data.id]);
      if (ptData) {
        document.getElementById("ttTemp").textContent = `${ptData.temp_c.toFixed(2)} °C`;
        document.getElementById("ttQgen").textContent = `${(ptData.pressure_pa / 1000).toFixed(1)} kPa`;
        document.getElementById("ttQcool").textContent = `${ptData.velocity_m_s.toFixed(3)} m/s`;
        document.getElementById("ttStatus").textContent = "MEASURING";
      }
    } else {
      document.getElementById("ttTitle").textContent = (data.name || data.id || "COMPONENT").toUpperCase();
      document.getElementById("ttTemp").textContent = "--";
      document.getElementById("ttQgen").textContent = "--";
      document.getElementById("ttQcool").textContent = "--";
      document.getElementById("ttStatus").textContent = "ACTIVE";
    }
  }

  hideTooltip() {
    if (this.tooltip) this.tooltip.classList.add("hidden");
  }

  bindViewButtons() {
    const btnDefault = document.getElementById("btnViewDefault");
    const btnTop = document.getElementById("btnViewTop");
    const btnSide = document.getElementById("btnViewSide");
    const btnFront = document.getElementById("btnViewFront");
    const btnExplode = document.getElementById("btnViewExplode");
    const btnCutaway = document.getElementById("btnViewCutaway");
    const btnReset = document.getElementById("btnResetCamera");

    if (btnDefault) btnDefault.addEventListener("click", () => this.setView("default"));
    if (btnTop) btnTop.addEventListener("click", () => this.setView("top"));
    if (btnSide) btnSide.addEventListener("click", () => this.setView("side"));
    if (btnFront) btnFront.addEventListener("click", () => this.setView("front"));
    if (btnExplode) btnExplode.addEventListener("click", () => this.toggleExplode(btnExplode));
    if (btnCutaway) btnCutaway.addEventListener("click", () => this.toggleCutaway(btnCutaway));
    if (btnReset) btnReset.addEventListener("click", () => this.resetCamera());
  }

  setView(mode) {
    if (mode === "default") {
      this.animateCameraTo(new THREE.Vector3(0, 5.0, 7.5), new THREE.Vector3(0, 0.2, 0));
    } else if (mode === "top") {
      this.animateCameraTo(new THREE.Vector3(0, 8.5, 0.01), new THREE.Vector3(0, 0, 0));
    } else if (mode === "side") {
      this.animateCameraTo(new THREE.Vector3(7.5, 1.5, 0), new THREE.Vector3(0, 0.5, 0));
    } else if (mode === "front") {
      this.animateCameraTo(new THREE.Vector3(0, 1.5, 7.5), new THREE.Vector3(0, 0.5, 0));
    }
  }

  animateCameraTo(targetPos, targetLookAt) {
    this.camera.position.copy(targetPos);
    this.controls.target.copy(targetLookAt);
    this.controls.update();
  }

  resetCamera() {
    this.animateCameraTo(this.defaultCamPos, this.defaultCamTarget);
  }

  toggleExplode(btn) {
    this.isExploded = !this.isExploded;
    this.targetExplodeFactor = this.isExploded ? 1.0 : 0.0;
    if (btn) btn.classList.toggle("active", this.isExploded);
  }

  toggleCutaway(btn) {
    this.isCutaway = !this.isCutaway;
    if (btn) btn.classList.toggle("active", this.isCutaway);

    // Toggle transparency of cold plate and pipes
    if (this.plateMat) {
      this.plateMat.transparent = this.isCutaway;
      this.plateMat.opacity = this.isCutaway ? 0.35 : 1.0;
      this.plateMat.needsUpdate = true;
    }
    if (this.pipeMat) {
      this.pipeMat.transparent = this.isCutaway;
      this.pipeMat.opacity = this.isCutaway ? 0.45 : 1.0;
      this.pipeMat.needsUpdate = true;
    }
  }

  updateExplodeAnimation() {
    if (Math.abs(this.explodeFactor - this.targetExplodeFactor) > 0.01) {
      this.explodeFactor += (this.targetExplodeFactor - this.explodeFactor) * 0.1;

      // Animate battery cells outward/upward
      this.cellMeshes.forEach(mesh => {
        const orig = mesh.userData.originalPos;
        const expl = mesh.userData.explodePos;
        mesh.position.lerpVectors(orig, expl, this.explodeFactor);
      });

      // Animate external components
      this.componentMeshes.forEach(comp => {
        if (comp.userData && comp.userData.originalPos && comp.userData.explodePos) {
          comp.position.lerpVectors(comp.userData.originalPos, comp.userData.explodePos, this.explodeFactor);
        }
      });
    }
  }

  // Update battery cells thermal colors from live simulation state
  updateThermalColors(cells, thresholdC = 35.0) {
    if (!cells) return;

    cells.forEach(cell => {
      const mesh = this.cellMeshes.get(cell.cell_id);
      if (!mesh) return;

      const t = cell.temperature_c;
      const mat = mesh.material;

      // Temperature color spectrum:
      // Blue: < 25°C
      // Cyan: 25 - 30°C
      // Yellow: 30 - 35°C
      // Orange: 35 - 40°C
      // Red: >= Threshold (default 35°C, or user slider)
      if (t >= thresholdC) {
        mat.color.setHex(0xff3366); // Alert Red
        mat.emissive.setHex(0x660011);
        mat.emissiveIntensity = 0.5;
      } else if (t >= 35.0) {
        mat.color.setHex(0xff7700); // Warm Orange
        mat.emissive.setHex(0x441100);
        mat.emissiveIntensity = 0.3;
      } else if (t >= 30.0) {
        mat.color.setHex(0xffee33); // Increasing Yellow
        mat.emissive.setHex(0x332200);
        mat.emissiveIntensity = 0.2;
      } else if (t >= 25.0) {
        mat.color.setHex(0x00f0ff); // Normal Cyan
        mat.emissive.setHex(0x003344);
        mat.emissiveIntensity = 0.15;
      } else {
        mat.color.setHex(0x00a8ff); // Cool Blue
        mat.emissive.setHex(0x001133);
        mat.emissiveIntensity = 0.1;
      }
    });
  }

  updateRotatingParts(dt, pumpActive, fanActive, pumpRpm = 2400, fanRpm = 1800) {
    // Spin pump impeller when pump is active
    if (this.pumpImpeller && pumpActive) {
      const radPerSec = (pumpRpm / 60) * Math.PI * 2;
      this.pumpImpeller.rotation.y += radPerSec * dt * 0.05;
    }

    // Spin radiator fan blades when fan is active
    if (this.fanBlades && fanActive) {
      const radPerSec = (fanRpm / 60) * Math.PI * 2;
      this.fanBlades.rotation.z += radPerSec * dt * 0.05;
    }

    // Pulsing magnetic field flux lines
    if (this.magneticFluxGroup) {
      this.magneticFluxGroup.rotation.y += dt * 0.5;
    }

    // BMS status LED blink
    if (this.bmsLedMat) {
      const blink = (Math.sin(Date.now() * 0.005) > 0);
      this.bmsLedMat.color.setHex(blink ? 0x00ff88 : 0x003311);
    }
  }

  setPorousFoamVisible(visible) {
    if (this.porousFoamGroup) {
      this.porousFoamGroup.visible = visible;
    }
  }

  onWindowResize() {
    const width = this.container.clientWidth;
    const height = this.container.clientHeight;
    this.camera.aspect = width / height;
    this.camera.updateProjectionMatrix();
    this.renderer.setSize(width, height);
  }

  render() {
    this.controls.update();
    this.updateExplodeAnimation();
    this.renderer.render(this.scene, this.camera);
  }
}

window.BTMS3DSimulation = BTMS3DSimulation;
