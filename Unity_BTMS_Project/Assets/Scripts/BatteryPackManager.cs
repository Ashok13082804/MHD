using System.Collections.Generic;
using UnityEngine;

namespace BTMS3D.Simulation
{
    /// <summary>
    /// Manages the 50-cell battery pack module (5 rows x 10 columns).
    /// Orchestrates inter-cell conduction, pack-level thermal metrics,
    /// exploded view transformations, and enclosure transparency.
    /// </summary>
    public class BatteryPackManager : MonoBehaviour
    {
        [Header("Cell Configuration")]
        public GameObject cellPrefab;
        public Transform cellsParent;
        public int rows = 5;
        public int cols = 10;
        public float spacingX = 0.055f; // 55mm pitch
        public float spacingZ = 0.045f; // 45mm pitch
        public float cellHeightY = 0.065f;

        [Header("Live Cell Registry")]
        public List<BatteryCell> cells = new List<BatteryCell>();

        [Header("Enclosure & Plates")]
        public GameObject topEnclosure;
        public GameObject bottomColdPlate;
        public GameObject sideCasings;

        [Header("Pack Thermal Telemetry")]
        public float maxTemperatureC = 25.0f;
        public float avgTemperatureC = 25.0f;
        public float minTemperatureC = 25.0f;
        public float deltaTC = 0.0f;
        public int overheatingCount = 0;
        public float totalHeatGenWatts = 0.0f;
        public float totalHeatExtractedWatts = 0.0f;

        [Header("Exploded View")]
        public bool isExploded = false;
        public float explodedFactor = 0.0f;
        private Vector3[] initialCellLocalPositions;
        private Vector3[] explodedCellLocalPositions;

        private void Awake()
        {
            if (cells.Count == 0)
            {
                SpawnPackGrid();
            }
            CacheExplodedPositions();
        }

        public void SpawnPackGrid()
        {
            cells.Clear();
            int cellId = 1;

            for (int r = 0; r < rows; r++)
            {
                for (int c = 0; c < cols; c++)
                {
                    float xPos = (c - (cols - 1) * 0.5f) * spacingX;
                    float zPos = (r - (rows - 1) * 0.5f) * spacingZ;
                    Vector3 localPos = new Vector3(xPos, cellHeightY * 0.5f, zPos);

                    GameObject cellObj;
                    if (cellPrefab != null)
                    {
                        cellObj = Instantiate(cellPrefab, cellsParent != null ? cellsParent : transform);
                    }
                    else
                    {
                        // Fallback procedural cylinder
                        cellObj = GameObject.CreatePrimitive(PrimitiveType.Cylinder);
                        cellObj.transform.localScale = new Vector3(0.04f, cellHeightY * 0.5f, 0.04f);
                        if (cellsParent != null) cellObj.transform.SetParent(cellsParent);
                    }

                    cellObj.name = $"Cell_B{cellId:D2}";
                    cellObj.transform.localPosition = localPos;

                    BatteryCell cellComp = cellObj.GetComponent<BatteryCell>();
                    if (cellComp == null)
                    {
                        cellComp = cellObj.AddComponent<BatteryCell>();
                    }

                    cellComp.Initialize(cellId, r, c, 25.0f);
                    cells.Add(cellComp);
                    cellId++;
                }
            }
        }

        private void CacheExplodedPositions()
        {
            initialCellLocalPositions = new Vector3[cells.Count];
            explodedCellLocalPositions = new Vector3[cells.Count];

            for (int i = 0; i < cells.Count; i++)
            {
                Vector3 initPos = cells[i].transform.localPosition;
                initialCellLocalPositions[i] = initPos;

                // Expand outward from center along X, Z, and slightly upward in Y
                Vector3 offset = new Vector3(initPos.x * 1.8f, initPos.y + 0.08f, initPos.z * 1.8f);
                explodedCellLocalPositions[i] = offset;
            }
        }

        public void SetExplodedView(bool explode)
        {
            isExploded = explode;
        }

        private void Update()
        {
            // Smoothly animate exploded view
            float targetFactor = isExploded ? 1.0f : 0.0f;
            explodedFactor = Mathf.MoveTowards(explodedFactor, targetFactor, Time.deltaTime * 2.5f);

            if (initialCellLocalPositions != null && initialCellLocalPositions.Length == cells.Count)
            {
                for (int i = 0; i < cells.Count; i++)
                {
                    cells[i].transform.localPosition = Vector3.Lerp(
                        initialCellLocalPositions[i],
                        explodedCellLocalPositions[i],
                        explodedFactor
                    );
                }
            }

            if (topEnclosure != null)
            {
                topEnclosure.transform.localPosition = Vector3.Lerp(
                    Vector3.zero,
                    new Vector3(0, 0.25f, 0),
                    explodedFactor
                );
            }
        }

        /// <summary>
        /// Solves coupled thermal physics across all 50 cells for time step dt.
        /// </summary>
        public void StepThermalConduction(float dt, float cRate, float hCoolant, float coolantTempC, float thresholdC, bool coolingActive)
        {
            float sumTemp = 0.0f;
            maxTemperatureC = -999.0f;
            minTemperatureC = 999.0f;
            overheatingCount = 0;
            totalHeatGenWatts = 0.0f;
            totalHeatExtractedWatts = 0.0f;

            // Step 1: Compute heat generation
            for (int i = 0; i < cells.Count; i++)
            {
                float qGen = cells[i].ComputeHeatGeneration(cRate);
                totalHeatGenWatts += qGen;
            }

            // Step 2: Compute inter-cell conduction and cold plate cooling
            float kInterCell = 2.5f; // Effective conduction conductance between adjacent cells (W/K)
            float plateAreaPerCell = 0.0042f; // m^2

            for (int i = 0; i < cells.Count; i++)
            {
                BatteryCell cell = cells[i];

                // Cold plate convective heat transfer
                float qCooling = 0.0f;
                if (coolingActive)
                {
                    qCooling = hCoolant * plateAreaPerCell * Mathf.Max(cell.currentTemperatureC - coolantTempC, 0.0f);
                }
                else
                {
                    // Natural passive dissipation
                    qCooling = 12.0f * plateAreaPerCell * Mathf.Max(cell.currentTemperatureC - coolantTempC, 0.0f);
                }
                totalHeatExtractedWatts += qCooling;

                // Inter-cell conduction from 4 orthogonal neighbors
                float qInterCell = 0.0f;
                int r = cell.row;
                int c = cell.col;

                if (r > 0) qInterCell += kInterCell * (cells[(r - 1) * cols + c].currentTemperatureC - cell.currentTemperatureC);
                if (r < rows - 1) qInterCell += kInterCell * (cells[(r + 1) * cols + c].currentTemperatureC - cell.currentTemperatureC);
                if (c > 0) qInterCell += kInterCell * (cells[r * cols + (c - 1)].currentTemperatureC - cell.currentTemperatureC);
                if (c < cols - 1) qInterCell += kInterCell * (cells[r * cols + (c + 1)].currentTemperatureC - cell.currentTemperatureC);

                float qAmbient = 5.0f * 0.015f * Mathf.Max(cell.currentTemperatureC - 25.0f, 0.0f);

                cell.UpdateThermalStep(dt, qCooling, qInterCell, qAmbient, thresholdC);

                // Statistics
                sumTemp += cell.currentTemperatureC;
                if (cell.currentTemperatureC > maxTemperatureC) maxTemperatureC = cell.currentTemperatureC;
                if (cell.currentTemperatureC < minTemperatureC) minTemperatureC = cell.currentTemperatureC;
                if (cell.isOverheating) overheatingCount++;
            }

            avgTemperatureC = sumTemp / cells.Count;
            deltaTC = maxTemperatureC - minTemperatureC;
        }

        public BatteryCell GetCellById(int id)
        {
            if (id >= 1 && id <= cells.Count) return cells[id - 1];
            return null;
        }

        public BatteryCell GetCellByName(string name)
        {
            return cells.Find(c => c.cellName.Equals(name, System.StringComparison.OrdinalIgnoreCase));
        }
    }
}
