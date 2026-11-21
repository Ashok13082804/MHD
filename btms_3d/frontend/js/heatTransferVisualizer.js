/**
 * Heat Transfer Visualizer Module
 * Renders dynamic thermal heat flux vectors and arrows flowing from
 * the 50 battery cells into the cooling plate channels.
 */

class HeatTransferVisualizer {
  constructor(scene) {
    this.scene = scene;
    this.group = new THREE.Group();
    this.scene.add(this.group);
    this.arrows = [];
    this.visible = true;

    this.initArrows();
  }

  initArrows() {
    // 50 arrows, one below each of the 50 battery cells pointing toward the cooling plate
    const origin = new THREE.Vector3();
    const dir = new THREE.Vector3(0, -1, 0); // Downward into cooling plate
    const length = 0.25;
    const color = 0x00f0ff;

    // 5x10 grid positions matching the battery layout
    const rows = 5;
    const cols = 10;
    const spacingX = 0.42;
    const spacingZ = 0.28;
    const startX = -((cols - 1) * spacingX) / 2;
    const startZ = -((rows - 1) * spacingZ) / 2;

    for (let r = 0; r < rows; r++) {
      for (let c = 0; c < cols; c++) {
        const x = startX + c * spacingX;
        const z = startZ + r * spacingZ;
        const arrowOrigin = new THREE.Vector3(x, 0.15, z);

        const arrowHelper = new THREE.ArrowHelper(dir, arrowOrigin, length, color, 0.08, 0.05);
        this.group.add(arrowHelper);

        this.arrows.push({
          helper: arrowHelper,
          origin: arrowOrigin,
          row: r,
          col: c,
          cellId: `B${String(r * cols + c + 1).padStart(2, "0")}`
        });
      }
    }
  }

  update(cellsData, coolingActive, simTime) {
    if (!this.visible || !cellsData) return;

    const cellMap = new Map();
    cellsData.forEach(c => cellMap.set(c.cell_id, c));

    this.arrows.forEach(item => {
      const cell = cellMap.get(item.cellId);
      if (!cell) return;

      const qGen = cell.heat_generation_w || 0.0;
      const qCool = cell.cooling_rate_w || 0.0;
      const tempC = cell.temperature_c || 25.0;

      // Color based on temperature and cooling rate
      let col = new THREE.Color(0x00a8ff);
      if (tempC >= 40.0) col.setHex(0xff0044);
      else if (tempC >= 35.0) col.setHex(0xff3366);
      else if (tempC >= 30.0) col.setHex(0xffaa00);
      else if (tempC >= 25.0) col.setHex(0x00ff88);

      item.helper.setColor(col);

      // Arrow length dynamic with heat flux & cooling active
      const baseLen = coolingActive ? 0.15 + Math.min(0.25, qCool * 0.08) : 0.08;
      const pulse = 1.0 + 0.15 * Math.sin(simTime * 5.0 + item.row + item.col);
      const effLen = Math.max(0.08, baseLen * pulse);

      item.helper.setLength(effLen, effLen * 0.35, effLen * 0.25);

      // Slightly oscillate the arrow origin up and down to indicate continuous thermal flow
      const yOffset = coolingActive ? 0.02 * Math.sin(simTime * 6.0 + item.col) : 0;
      item.helper.position.set(item.origin.x, item.origin.y + yOffset, item.origin.z);
    });
  }

  setVisible(visible) {
    this.visible = visible;
    this.group.visible = visible;
  }

  toggle() {
    this.setVisible(!this.visible);
    return this.visible;
  }
}

window.HeatTransferVisualizer = HeatTransferVisualizer;
