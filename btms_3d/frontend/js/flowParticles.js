/**
 * Nanofluid & Nanoparticle Flow Animation
 * Simulates continuous circulation of hybrid nanoparticles (Al2O3, Cu, CuO, TiO2)
 * through the complete BTMS loop: Pump -> Manifold -> 11 Channels -> Radiator -> Reservoir.
 */

class FlowParticlesManager {
  constructor(scene) {
    this.scene = scene;
    this.numChannels = 11;
    this.particlesPerChannel = 40;
    this.totalParticles = this.numChannels * this.particlesPerChannel;
    this.channelCurves = [];
    this.particles = [];

    // Nanoparticle optical properties
    this.npPalette = [
      { name: "Al2O3", baseColor: new THREE.Color(0xf0f8ff), size: 0.035 }, // Pale ivory/white
      { name: "Cu", baseColor: new THREE.Color(0xee6622), size: 0.040 },    // Metallic copper
      { name: "CuO", baseColor: new THREE.Color(0x3a3028), size: 0.032 },   // Dark bronze
      { name: "TiO2", baseColor: new THREE.Color(0xffffff), size: 0.036 },  // Bright white
      { name: "SiO2", baseColor: new THREE.Color(0x77ddff), size: 0.030 }   // Translucent silica
    ];

    this.initPaths();
    this.initParticleGeometry();
  }

  initPaths() {
    // Pack dimensions and channel positions
    const rows = 5;
    const cols = 10;
    const spacingX = 0.42;
    const spacingZ = 0.28;
    const startX = -((cols - 1) * spacingX) / 2;
    const endX = ((cols - 1) * spacingX) / 2;
    const startZ = -((rows - 1) * spacingZ) / 2;
    const endZ = ((rows - 1) * spacingZ) / 2;

    // Fixed BTMS external loop points
    const pPump = new THREE.Vector3(-3.2, 0.4, 2.0);
    const pInletManifold = new THREE.Vector3(-2.3, 0.35, 1.3);
    const pOutletManifold = new THREE.Vector3(2.3, 0.35, -1.3);
    const pHexIn = new THREE.Vector3(3.0, 0.5, -2.0);
    const pHexOut = new THREE.Vector3(3.2, 0.6, -0.6);
    const pRadIn = new THREE.Vector3(1.6, 0.8, 2.4);
    const pRadOut = new THREE.Vector3(-0.6, 0.7, 2.7);
    const pReservoir = new THREE.Vector3(-2.2, 0.6, 2.5);

    // Build 11 distinct channel paths through the cooling plate
    for (let i = 0; i < this.numChannels; i++) {
      // 11 channels spaced across the Z-axis
      const zChannel = startZ - 0.14 + i * (spacingZ * 0.95);
      const chIn = new THREE.Vector3(startX - 0.3, 0.15, zChannel);
      const chMid = new THREE.Vector3(0.0, 0.15, zChannel);
      const chOut = new THREE.Vector3(endX + 0.3, 0.15, zChannel);

      const pathPoints = [
        pPump.clone(),
        pInletManifold.clone(),
        chIn,
        chMid,
        chOut,
        pOutletManifold.clone(),
        pHexIn.clone(),
        pHexOut.clone(),
        pRadIn.clone(),
        pRadOut.clone(),
        pReservoir.clone(),
        pPump.clone()
      ];

      const curve = new THREE.CatmullRomCurve3(pathPoints, true, "centripetal", 0.4);
      this.channelCurves.push(curve);
    }
  }

  initParticleGeometry() {
    const geometry = new THREE.BufferGeometry();
    const positions = new Float32Array(this.totalParticles * 3);
    const colors = new Float32Array(this.totalParticles * 3);
    const sizes = new Float32Array(this.totalParticles);

    let idx = 0;
    for (let c = 0; c < this.numChannels; c++) {
      for (let p = 0; p < this.particlesPerChannel; p++) {
        const u = (p / this.particlesPerChannel) + (Math.random() * 0.02);
        const npType = this.npPalette[idx % this.npPalette.length];

        this.particles.push({
          channelIndex: c,
          u: u % 1.0,
          npType: npType,
          speedFactor: 0.85 + Math.random() * 0.3
        });

        // Initial default colors (Cool cyan)
        colors[idx * 3] = 0.0;
        colors[idx * 3 + 1] = 0.94;
        colors[idx * 3 + 2] = 1.0;
        sizes[idx] = npType.size;

        idx++;
      }
    }

    geometry.setAttribute("position", new THREE.BufferAttribute(positions, 3));
    geometry.setAttribute("color", new THREE.BufferAttribute(colors, 3));
    geometry.setAttribute("size", new THREE.BufferAttribute(sizes, 1));

    // Custom point material with soft radial falloff texture
    const canvas = document.createElement("canvas");
    canvas.width = 64;
    canvas.height = 64;
    const ctx = canvas.getContext("2d");
    const gradient = ctx.createRadialGradient(32, 32, 0, 32, 32, 32);
    gradient.addColorStop(0, "rgba(255, 255, 255, 1.0)");
    gradient.addColorStop(0.3, "rgba(200, 240, 255, 0.8)");
    gradient.addColorStop(0.8, "rgba(100, 180, 255, 0.2)");
    gradient.addColorStop(1, "rgba(0, 0, 0, 0)");
    ctx.fillStyle = gradient;
    ctx.fillRect(0, 0, 64, 64);
    const pTexture = new THREE.CanvasTexture(canvas);

    const material = new THREE.PointsMaterial({
      size: 0.12,
      vertexColors: true,
      map: pTexture,
      transparent: true,
      opacity: 0.88,
      blending: THREE.AdditiveBlending,
      depthWrite: false
    });

    this.pointsMesh = new THREE.Points(geometry, material);
    this.scene.add(this.pointsMesh);
  }

  update(dt, velocity, pumpActive, tInC = 25.0, tOutC = 35.0) {
    if (!this.pointsMesh) return;

    const positions = this.pointsMesh.geometry.attributes.position.array;
    const colors = this.pointsMesh.geometry.attributes.color.array;

    // If pump is OFF, flow stops completely (speed = 0)
    const effectiveSpeed = pumpActive ? Math.max(0.02, velocity * 0.18) : 0.0;

    for (let i = 0; i < this.totalParticles; i++) {
      const p = this.particles[i];

      // Advance along path
      if (effectiveSpeed > 0) {
        p.u = (p.u + effectiveSpeed * p.speedFactor * dt) % 1.0;
      }

      // Calculate 3D coordinate along channel curve
      const curve = this.channelCurves[p.channelIndex];
      const pos = curve.getPointAt(p.u);

      positions[i * 3] = pos.x;
      positions[i * 3 + 1] = pos.y;
      positions[i * 3 + 2] = pos.z;

      // Dynamic color shift based on position along loop (temperature evolution)
      // u: 0.0 - 0.15: Inlet (Cool ~25°C) -> Blue/Cyan
      // u: 0.15 - 0.50: Channels (Heating up ~25 to 38°C) -> Yellow -> Orange -> Red
      // u: 0.50 - 0.65: Outlet manifold & HEX (Warm ~35-38°C) -> Red/Orange
      // u: 0.65 - 0.85: Radiator core (Cooling rejection) -> Orange -> Cyan
      // u: 0.85 - 1.00: Return to pump (Cooled ~25°C) -> Blue
      let localTempC = tInC;
      if (p.u < 0.15) {
        localTempC = tInC;
      } else if (p.u < 0.50) {
        const prog = (p.u - 0.15) / 0.35;
        localTempC = tInC + prog * (tOutC - tInC);
      } else if (p.u < 0.65) {
        localTempC = tOutC;
      } else if (p.u < 0.85) {
        const prog = (p.u - 0.65) / 0.20;
        localTempC = tOutC - prog * (tOutC - tInC);
      } else {
        localTempC = tInC;
      }

      // Blend nanoparticle inherent color with thermal state
      let thermalCol = new THREE.Color(0x00f0ff);
      if (localTempC >= 38.0) thermalCol.setHex(0xff3366);
      else if (localTempC >= 33.0) thermalCol.setHex(0xffaa00);
      else if (localTempC >= 28.0) thermalCol.setHex(0xffee33);
      else if (localTempC >= 25.0) thermalCol.setHex(0x00ff88);
      else thermalCol.setHex(0x00a8ff);

      // Lerp with nanoparticle base color for physical distinction
      const finalCol = thermalCol.clone().lerp(p.npType.baseColor, 0.35);

      colors[i * 3] = finalCol.r;
      colors[i * 3 + 1] = finalCol.g;
      colors[i * 3 + 2] = finalCol.b;
    }

    this.pointsMesh.geometry.attributes.position.needsUpdate = true;
    this.pointsMesh.geometry.attributes.color.needsUpdate = true;
  }
}

window.FlowParticlesManager = FlowParticlesManager;
