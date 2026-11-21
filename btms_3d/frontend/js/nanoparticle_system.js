/**
 * Nanofluid Visible Nanoparticle Circulation System
 * Simulates suspended 3D silver (Al2O3) and copper (CuO) nanoparticles
 * continuously circulating inside transparent cooling channels and pipelines.
 */

class NanoparticleCirculationEngine {
  constructor(scene, pipelinePathPoints) {
    this.scene = scene;
    this.pipelinePathPoints = pipelinePathPoints;
    this.particles = [];
    this.maxParticles = 600; // high visual fidelity
    this.activeCount = 300;
    this.velocity = 0.05; // m/s
    this.phi1 = 0.02; // Al2O3 fraction
    this.phi2 = 0.01; // CuO fraction
    this.flowDirection = 1;

    // Create 3D continuous closed spline curve through the BTMS components
    this.spline = new THREE.CatmullRomCurve3(this.pipelinePathPoints, true, 'catmullrom', 0.15);

    this.initParticleMeshes();
  }

  initParticleMeshes() {
    this.particleGroup = new THREE.Group();
    this.particleGroup.name = "NanoparticleSystem";

    // Silver Al2O3 material
    const al2o3Mat = new THREE.MeshStandardMaterial({
      color: 0xE8ECEF,
      metalness: 0.9,
      roughness: 0.15,
      emissive: 0x334455,
      emissiveIntensity: 0.2
    });

    // Copper/Bronze CuO material
    const cuoMat = new THREE.MeshStandardMaterial({
      color: 0xC86432,
      metalness: 0.85,
      roughness: 0.2,
      emissive: 0x442211,
      emissiveIntensity: 0.25
    });

    const sphereGeo = new THREE.SphereGeometry(0.007, 8, 8); // 7mm visual sphere inside 16mm pipe

    for (let i = 0; i < this.maxParticles; i++) {
      // 67% Al2O3, 33% CuO by default ratio (2:1)
      const isAl2O3 = (i % 3 !== 0);
      const mesh = new THREE.Mesh(sphereGeo, isAl2O3 ? al2o3Mat : cuoMat);

      // Random starting parameter along curve t in [0, 1]
      const t = Math.random();
      // Slight radial offset so particles disperse across pipe diameter
      const radiusOffset = (Math.random() - 0.5) * 0.007;
      const angle = Math.random() * Math.PI * 2;

      mesh.visible = i < this.activeCount;
      this.particleGroup.add(mesh);

      this.particles.push({
        mesh: mesh,
        t: t,
        speed: (0.9 + Math.random() * 0.2), // slight velocity variance
        radOffset: radiusOffset,
        angle: angle,
        isAl2O3: isAl2O3
      });
    }

    this.scene.add(this.particleGroup);
  }

  update(delta, velocity_m_s, phi1, phi2, coolingActive) {
    this.velocity = Math.max(velocity_m_s, 0.005);
    this.phi1 = phi1;
    this.phi2 = phi2;

    // Density scales with total volume fraction
    const totalPhi = phi1 + phi2;
    const targetCount = Math.floor(Math.min(Math.max((totalPhi / 0.05) * 500, 100), this.maxParticles));
    this.activeCount = targetCount;

    // Circulation speed factor (scaled for real-time 3D visibility)
    const baseSpeed = coolingActive ? (this.velocity * 0.35) : 0.02;

    for (let i = 0; i < this.particles.length; i++) {
      const p = this.particles[i];

      if (i >= this.activeCount) {
        p.mesh.visible = false;
        continue;
      }
      p.mesh.visible = true;

      // Advance along spline
      p.t += baseSpeed * p.speed * delta;
      if (p.t > 1.0) p.t -= 1.0;
      if (p.t < 0.0) p.t += 1.0;

      // Get 3D spline tangent and position
      const pos = this.spline.getPointAt(p.t);
      const tangent = this.spline.getTangentAt(p.t).normalize();

      // Normal and binormal vectors for radial dispersion inside pipe
      const up = new THREE.Vector3(0, 1, 0);
      const normal = new THREE.Vector3().crossVectors(tangent, up).normalize();
      const binormal = new THREE.Vector3().crossVectors(tangent, normal).normalize();

      const offsetX = Math.cos(p.angle) * p.radOffset;
      const offsetY = Math.sin(p.angle) * p.radOffset;

      pos.addScaledVector(normal, offsetX);
      pos.addScaledVector(binormal, offsetY);

      p.mesh.position.copy(pos);

      // Thermal glow effect: particles warm up after passing battery (t between 0.3 and 0.6)
      if (p.t > 0.35 && p.t < 0.65) {
        p.mesh.material.emissiveIntensity = 0.55;
      } else {
        p.mesh.material.emissiveIntensity = 0.2;
      }
    }
  }

  setVisible(visible) {
    if (this.particleGroup) {
      this.particleGroup.visible = visible;
    }
  }
}
