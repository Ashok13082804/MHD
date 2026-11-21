/**
 * 3D Scene Construction and Component Geometry Engine
 * Renders exactly 50 individual battery cells, micro-channel cold plate,
 * transparent piping network, reservoir, pump, fan, radiator, chiller, and sensors.
 */

class BTMS3DSceneBuilder {
  constructor(scene) {
    this.scene = scene;
    this.clickableObjects = [];
    this.cellMeshes = [];
    this.pipeSegments = [];
    this.fanBlades = null;
    this.pumpImpeller = null;
    this.exploded = false;
    this.casingMesh = null;
    this.transparentCasing = true;

    // Component coordinates
    this.layout = {
      batteryOrigin: new THREE.Vector3(0, 0, 0),
      reservoirPos: new THREE.Vector3(-1.1, 0.15, -0.6),
      pumpPos: new THREE.Vector3(-0.7, 0.05, -0.6),
      valvePos: new THREE.Vector3(0.7, 0.05, 0.5),
      chillerPos: new THREE.Vector3(1.0, 0.10, 0.4),
      radiatorPos: new THREE.Vector3(0.0, 0.25, 0.9),
      bmsPos: new THREE.Vector3(-0.6, 0.12, 0.5)
    };

    this.buildScene();
  }

  buildScene() {
    this.buildLighting();
    this.build50BatteryCells();
    this.buildCoolingPlate();
    this.buildReservoir();
    this.buildPump();
    this.buildRadiatorAndFan();
    this.buildChiller();
    this.buildThermalValve();
    this.buildBMSController();
    this.buildSensors();
    this.buildPipelineNetwork();
  }

  buildLighting() {
    const ambient = new THREE.AmbientLight(0xffffff, 0.65);
    this.scene.add(ambient);

    const dirLight1 = new THREE.DirectionalLight(0xffffff, 0.85);
    dirLight1.position.set(5, 8, 5);
    this.scene.add(dirLight1);

    const dirLight2 = new THREE.DirectionalLight(0x00d2ff, 0.4);
    dirLight2.position.set(-5, 4, -5);
    this.scene.add(dirLight2);

    // Floor grid
    const grid = new THREE.GridHelper(4, 40, 0x00d2ff, 0x1f2937);
    grid.position.y = -0.05;
    this.scene.add(grid);
  }

  build50BatteryCells() {
    this.batteryGroup = new THREE.Group();
    this.batteryGroup.name = "BatteryPack50";

    const cellWidth = 0.042;
    const cellHeight = 0.105;
    const cellDepth = 0.016;
    const cellGeo = new THREE.BoxGeometry(cellWidth, cellHeight, cellDepth);

    // Terminal geometries
    const termGeo = new THREE.CylinderGeometry(0.0035, 0.0035, 0.006, 12);
    const posTermMat = new THREE.MeshStandardMaterial({ color: 0xD4AF37, metalness: 0.9, roughness: 0.2 }); // Gold/copper
    const negTermMat = new THREE.MeshStandardMaterial({ color: 0xC0C0C0, metalness: 0.9, roughness: 0.2 }); // Silver/nickel

    let cellId = 1;
    for (let r = 0; r < 5; r++) {
      for (let c = 0; c < 10; c++) {
        const cellName = `B${cellId < 10 ? '0' + cellId : cellId}`;
        const posX = (c - 4.5) * 0.052;
        const posY = cellHeight / 2 + 0.012; // above cooling plate
        const posZ = (r - 2.0) * 0.038;

        // Individual dynamic temperature material
        const cellMat = new THREE.MeshStandardMaterial({
          color: 0x2980b9, // initial blue
          metalness: 0.35,
          roughness: 0.45,
          emissive: 0x001122,
          emissiveIntensity: 0.15
        });

        const cellMesh = new THREE.Mesh(cellGeo, cellMat);
        cellMesh.position.set(posX, posY, posZ);
        cellMesh.name = cellName;
        cellMesh.userData = {
          component_id: cellName,
          cell_id: cellId,
          type: "battery_cell",
          row: r,
          col: c,
          baseY: posY
        };

        // Add electrical terminals
        const posTerm = new THREE.Mesh(termGeo, posTermMat);
        posTerm.position.set(-0.012, cellHeight / 2 + 0.003, 0);
        cellMesh.add(posTerm);

        const negTerm = new THREE.Mesh(termGeo, negTermMat);
        negTerm.position.set(0.012, cellHeight / 2 + 0.003, 0);
        cellMesh.add(negTerm);

        this.batteryGroup.add(cellMesh);
        this.clickableObjects.push(cellMesh);
        this.cellMeshes.push(cellMesh);

        cellId++;
      }
    }

    // Battery pack casing
    const casingGeo = new THREE.BoxGeometry(0.58, 0.14, 0.24);
    const casingMat = new THREE.MeshPhysicalMaterial({
      color: 0x88bbdd,
      transparent: true,
      opacity: 0.22,
      roughness: 0.1,
      transmission: 0.8,
      thickness: 0.02
    });
    this.casingMesh = new THREE.Mesh(casingGeo, casingMat);
    this.casingMesh.position.set(0, 0.065, 0);
    this.casingMesh.name = "BatteryCasing";
    this.batteryGroup.add(this.casingMesh);

    this.scene.add(this.batteryGroup);
  }

  buildCoolingPlate() {
    const plateGeo = new THREE.BoxGeometry(0.56, 0.012, 0.22);
    const plateMat = new THREE.MeshStandardMaterial({
      color: 0x7f8c8d,
      metalness: 0.8,
      roughness: 0.25
    });
    const plate = new THREE.Mesh(plateGeo, plateMat);
    plate.position.set(0, 0.006, 0);
    plate.name = "CoolingPlate";
    plate.userData = { component_id: "cooling_plate", type: "cooling_plate" };
    this.clickableObjects.push(plate);
    this.scene.add(plate);

    // Internal cooling channel visualization (sub-surface micro-tubes)
    const channelMat = new THREE.MeshBasicMaterial({ color: 0x00d2ff, transparent: true, opacity: 0.6 });
    for (let i = 0; i < 6; i++) {
      const tubeGeo = new THREE.BoxGeometry(0.54, 0.004, 0.008);
      const tube = new THREE.Mesh(tubeGeo, channelMat);
      tube.position.set(0, 0.006, -0.075 + i * 0.030);
      this.scene.add(tube);
    }
  }

  buildReservoir() {
    const group = new THREE.Group();
    group.position.copy(this.layout.reservoirPos);

    // Tank body
    const bodyGeo = new THREE.CylinderGeometry(0.065, 0.065, 0.16, 24);
    const bodyMat = new THREE.MeshPhysicalMaterial({
      color: 0x3498db,
      transparent: true,
      opacity: 0.5,
      roughness: 0.15,
      transmission: 0.7
    });
    const tank = new THREE.Mesh(bodyGeo, bodyMat);
    tank.name = "CoolantReservoir";
    tank.userData = { component_id: "coolant_reservoir", type: "reservoir" };
    group.add(tank);
    this.clickableObjects.push(tank);

    // Tank cap
    const capGeo = new THREE.CylinderGeometry(0.025, 0.025, 0.02, 16);
    const capMat = new THREE.MeshStandardMaterial({ color: 0xf39c12, metalness: 0.5, roughness: 0.4 });
    const cap = new THREE.Mesh(capGeo, capMat);
    cap.position.y = 0.09;
    group.add(cap);

    this.scene.add(group);
  }

  buildPump() {
    const group = new THREE.Group();
    group.position.copy(this.layout.pumpPos);

    // Volute casing
    const casingGeo = new THREE.CylinderGeometry(0.045, 0.045, 0.05, 20);
    const casingMat = new THREE.MeshStandardMaterial({ color: 0x2c3e50, metalness: 0.8, roughness: 0.3 });
    const casing = new THREE.Mesh(casingGeo, casingMat);
    casing.rotation.x = Math.PI / 2;
    casing.name = "CoolantPump";
    casing.userData = { component_id: "coolant_pump", type: "pump" };
    group.add(casing);
    this.clickableObjects.push(casing);

    // Electric motor body
    const motorGeo = new THREE.CylinderGeometry(0.035, 0.035, 0.08, 20);
    const motorMat = new THREE.MeshStandardMaterial({ color: 0x1a252f, metalness: 0.6, roughness: 0.4 });
    const motor = new THREE.Mesh(motorGeo, motorMat);
    motor.position.set(0, 0, -0.06);
    motor.rotation.x = Math.PI / 2;
    group.add(motor);

    // Spinning impeller inside pump
    const impellerGeo = new THREE.BoxGeometry(0.035, 0.006, 0.035);
    const impellerMat = new THREE.MeshBasicMaterial({ color: 0x00d2ff });
    this.pumpImpeller = new THREE.Mesh(impellerGeo, impellerMat);
    group.add(this.pumpImpeller);

    this.scene.add(group);
  }

  buildRadiatorAndFan() {
    const group = new THREE.Group();
    group.position.copy(this.layout.radiatorPos);

    // Radiator core
    const radGeo = new THREE.BoxGeometry(0.50, 0.28, 0.025);
    const radMat = new THREE.MeshStandardMaterial({
      color: 0x4a5568,
      metalness: 0.85,
      roughness: 0.4,
      wireframe: false
    });
    const rad = new THREE.Mesh(radGeo, radMat);
    rad.name = "Radiator";
    rad.userData = { component_id: "radiator", type: "radiator" };
    group.add(rad);
    this.clickableObjects.push(rad);

    // Side tanks
    const tankGeo = new THREE.CylinderGeometry(0.018, 0.018, 0.28, 16);
    const tankMat = new THREE.MeshStandardMaterial({ color: 0x1f2937, metalness: 0.7 });
    const leftTank = new THREE.Mesh(tankGeo, tankMat);
    leftTank.position.x = -0.26;
    group.add(leftTank);

    const rightTank = new THREE.Mesh(tankGeo, tankMat);
    rightTank.position.x = 0.26;
    group.add(rightTank);

    // Axial cooling fan assembly
    const fanShroudGeo = new THREE.CylinderGeometry(0.12, 0.12, 0.02, 24);
    const fanShroudMat = new THREE.MeshStandardMaterial({ color: 0x111827, roughness: 0.5 });
    const fanShroud = new THREE.Mesh(fanShroudGeo, fanShroudMat);
    fanShroud.rotation.x = Math.PI / 2;
    fanShroud.position.set(0, 0, 0.025);
    group.add(fanShroud);

    // Rotating fan blades
    this.fanBlades = new THREE.Group();
    this.fanBlades.position.set(0, 0, 0.025);

    const hubGeo = new THREE.CylinderGeometry(0.03, 0.03, 0.015, 16);
    const hubMat = new THREE.MeshStandardMaterial({ color: 0x222222 });
    const hub = new THREE.Mesh(hubGeo, hubMat);
    hub.rotation.x = Math.PI / 2;
    this.fanBlades.add(hub);

    const bladeGeo = new THREE.BoxGeometry(0.02, 0.08, 0.003);
    const bladeMat = new THREE.MeshStandardMaterial({ color: 0x00d2ff, metalness: 0.5, roughness: 0.2 });
    for (let i = 0; i < 7; i++) {
      const blade = new THREE.Mesh(bladeGeo, bladeMat);
      blade.rotation.z = (i * Math.PI * 2) / 7;
      blade.position.set(
        Math.sin((i * Math.PI * 2) / 7) * 0.055,
        Math.cos((i * Math.PI * 2) / 7) * 0.055,
        0
      );
      this.fanBlades.add(blade);
    }
    this.fanBlades.name = "CoolingFan";
    this.fanBlades.userData = { component_id: "cooling_fan", type: "fan" };
    group.add(this.fanBlades);
    this.clickableObjects.push(this.fanBlades);

    this.scene.add(group);
  }

  buildChiller() {
    const group = new THREE.Group();
    group.position.copy(this.layout.chillerPos);

    const chillerGeo = new THREE.BoxGeometry(0.18, 0.12, 0.08);
    const chillerMat = new THREE.MeshStandardMaterial({
      color: 0x2980b9,
      metalness: 0.9,
      roughness: 0.15
    });
    const chiller = new THREE.Mesh(chillerGeo, chillerMat);
    chiller.name = "PlateChiller";
    chiller.userData = { component_id: "chiller", type: "chiller" };
    group.add(chiller);
    this.clickableObjects.push(chiller);

    this.scene.add(group);
  }

  buildThermalValve() {
    const group = new THREE.Group();
    group.position.copy(this.layout.valvePos);

    const valveGeo = new THREE.CylinderGeometry(0.03, 0.03, 0.06, 16);
    const valveMat = new THREE.MeshStandardMaterial({ color: 0xd35400, metalness: 0.7, roughness: 0.3 });
    const valve = new THREE.Mesh(valveGeo, valveMat);
    valve.name = "ThermalControlValve";
    valve.userData = { component_id: "thermal_valve", type: "valve" };
    group.add(valve);
    this.clickableObjects.push(valve);

    this.scene.add(group);
  }

  buildBMSController() {
    const group = new THREE.Group();
    group.position.copy(this.layout.bmsPos);

    const bmsGeo = new THREE.BoxGeometry(0.14, 0.04, 0.09);
    const bmsMat = new THREE.MeshStandardMaterial({ color: 0x16a085, metalness: 0.4, roughness: 0.5 });
    const bms = new THREE.Mesh(bmsGeo, bmsMat);
    bms.name = "BMSController";
    bms.userData = { component_id: "bms_controller", type: "controller" };
    group.add(bms);
    this.clickableObjects.push(bms);

    this.scene.add(group);
  }

  buildSensors() {
    const sensorGeo = new THREE.CylinderGeometry(0.008, 0.008, 0.016, 12);
    const sensorMat = new THREE.MeshStandardMaterial({ color: 0xf1c40f, emissive: 0x553300 });

    const sensorLocations = [
      { name: "Sensor_T1_Reservoir", pos: new THREE.Vector3(-1.0, 0.12, -0.6) },
      { name: "Sensor_T2_Pump", pos: new THREE.Vector3(-0.6, 0.08, -0.6) },
      { name: "Sensor_T3_PlateInlet", pos: new THREE.Vector3(-0.28, 0.02, 0) },
      { name: "Sensor_T4_PlateOutlet", pos: new THREE.Vector3(0.28, 0.02, 0) },
      { name: "Sensor_T5_Radiator", pos: new THREE.Vector3(0.0, 0.32, 0.9) }
    ];

    sensorLocations.forEach(s => {
      const m = new THREE.Mesh(sensorGeo, sensorMat);
      m.position.copy(s.pos);
      m.name = s.name;
      m.userData = { component_id: "temperature_sensor", type: "sensor" };
      this.clickableObjects.push(m);
      this.scene.add(m);
    });
  }

  buildPipelineNetwork() {
    // 3D Path Waypoints connecting the full loop
    this.pipelinePoints = [
      new THREE.Vector3(-1.1, 0.08, -0.6),  // 0: Reservoir outlet
      new THREE.Vector3(-0.7, 0.05, -0.6),  // 1: Pump inlet
      new THREE.Vector3(-0.5, 0.02, -0.4),  // 2: Pump discharge
      new THREE.Vector3(-0.28, 0.006, 0.0), // 3: Battery cold plate inlet manifold
      new THREE.Vector3(0.0, 0.006, 0.0),   // 4: Battery cooling channels mid
      new THREE.Vector3(0.28, 0.006, 0.0),  // 5: Battery cold plate outlet manifold
      new THREE.Vector3(0.7, 0.05, 0.5),    // 6: 3-Way valve
      new THREE.Vector3(0.9, 0.10, 0.5),    // 7: Chiller branch
      new THREE.Vector3(0.3, 0.18, 0.8),    // 8: Radiator inlet
      new THREE.Vector3(-0.3, 0.18, 0.8),   // 9: Radiator outlet
      new THREE.Vector3(-0.9, 0.12, 0.1),   // 10: Return run
      new THREE.Vector3(-1.1, 0.12, -0.5)   // 11: Reservoir return
    ];

    const spline = new THREE.CatmullRomCurve3(this.pipelinePoints, true, 'catmullrom', 0.15);

    // Segment the tube geometry into clickable, independently color-mapped pipeline sections
    const numSegments = 11;
    this.pipeGroup = new THREE.Group();
    this.pipeGroup.name = "PipingNetwork";

    const segNames = [
      "pipe_reservoir_outlet",
      "pipe_pump_outlet",
      "pipe_plate_inlet",
      "pipe_channel_1",
      "pipe_channel_2",
      "pipe_channel_3",
      "pipe_plate_outlet",
      "pipe_heat_exchanger_inlet",
      "pipe_heat_exchanger_outlet",
      "pipe_radiator_inlet",
      "pipe_radiator_outlet"
    ];

    for (let i = 0; i < numSegments; i++) {
      const t1 = i / numSegments;
      const t2 = (i + 1) / numSegments;

      // Extract sub-curve for segment
      const subPoints = [];
      const subSteps = 12;
      for (let s = 0; s <= subSteps; s++) {
        const t = t1 + (s / subSteps) * (t2 - t1);
        subPoints.push(spline.getPointAt(t));
      }
      const subCurve = new THREE.CatmullRomCurve3(subPoints);
      const tubeGeo = new THREE.TubeGeometry(subCurve, 12, 0.009, 12, false);

      // Glassy transparent material to show particles inside
      const tubeMat = new THREE.MeshPhysicalMaterial({
        color: 0x3498db,
        transparent: true,
        opacity: 0.42,
        roughness: 0.15,
        transmission: 0.75,
        side: THREE.DoubleSide
      });

      const tubeMesh = new THREE.Mesh(tubeGeo, tubeMat);
      tubeMesh.name = segNames[i];
      tubeMesh.userData = {
        component_id: segNames[i],
        type: "pipeline",
        segment_index: i
      };

      this.pipeGroup.add(tubeMesh);
      this.clickableObjects.push(tubeMesh);
      this.pipeSegments.push(tubeMesh);
    }

    this.scene.add(this.pipeGroup);
  }

  updateVisuals(state) {
    if (!state) return;

    // 1. Update 50 battery cell colors
    if (state.cells && state.cells.length === 50) {
      for (let i = 0; i < 50; i++) {
        const cellData = state.cells[i];
        const mesh = this.cellMeshes[i];
        if (mesh && cellData) {
          const targetColor = new THREE.Color(cellData.color_hex);
          mesh.material.color.lerp(targetColor, 0.25);
          if (cellData.is_overheating) {
            mesh.material.emissive.setHex(0x550000);
            mesh.material.emissiveIntensity = 0.6;
          } else {
            mesh.material.emissive.setHex(0x001122);
            mesh.material.emissiveIntensity = 0.1;
          }
        }
      }
    }

    // 2. Update pipeline segment temperature colors
    if (state.pipeline_temperatures) {
      const pTemps = state.pipeline_temperatures;
      const tempArray = [
        pTemps.reservoir_outlet,
        pTemps.pump_outlet,
        pTemps.plate_inlet,
        pTemps.channel_1,
        pTemps.channel_2,
        pTemps.channel_3,
        pTemps.plate_outlet,
        pTemps.heat_exchanger_inlet,
        pTemps.heat_exchanger_outlet,
        pTemps.radiator_inlet,
        pTemps.radiator_outlet
      ];

      for (let i = 0; i < this.pipeSegments.length; i++) {
        const temp = tempArray[i] || 25.0;
        const color = this.getTemperatureColor(temp);
        this.pipeSegments[i].material.color.lerp(color, 0.2);
      }
    }

    // 3. Rotate fan blades and pump impeller
    if (this.fanBlades && state.controller) {
      const fanSpeedRad = (state.controller.fan_rpm / 60.0) * Math.PI * 2 * 0.05;
      this.fanBlades.rotation.z += fanSpeedRad;
    }
    if (this.pumpImpeller && state.controller) {
      const pumpSpeedRad = (state.controller.pump_rpm / 60.0) * Math.PI * 2 * 0.05;
      this.pumpImpeller.rotation.z += pumpSpeedRad;
    }
  }

  getTemperatureColor(tempC) {
    // Blue (<25) -> Cyan (25-30) -> Green (30-35) -> Yellow (35-40) -> Orange (40-45) -> Red (>45)
    if (tempC < 25.0) return new THREE.Color(0x2980b9);
    if (tempC < 30.0) return new THREE.Color(0x1abc9c);
    if (tempC < 35.0) return new THREE.Color(0x2ecc71);
    if (tempC < 40.0) return new THREE.Color(0xf1c40f);
    if (tempC < 45.0) return new THREE.Color(0xe67e22);
    return new THREE.Color(0xe74c3c);
  }

  toggleExplodedView() {
    this.exploded = !this.exploded;
    const factor = this.exploded ? 1.5 : 0.0;

    for (let i = 0; i < this.cellMeshes.length; i++) {
      const mesh = this.cellMeshes[i];
      const targetY = mesh.userData.baseY + factor * 0.08;
      mesh.position.y = targetY;
    }

    if (this.casingMesh) {
      this.casingMesh.position.y = 0.065 + factor * 0.18;
    }
  }

  toggleTransparentCasing() {
    this.transparentCasing = !this.transparentCasing;
    if (this.casingMesh) {
      this.casingMesh.visible = this.transparentCasing;
    }
  }
}
