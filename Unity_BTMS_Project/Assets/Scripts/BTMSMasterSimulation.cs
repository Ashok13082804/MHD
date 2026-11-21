using System.Collections;
using System.Collections.Generic;
using UnityEngine;
using UnityEngine.Networking;

namespace BTMS3D.Simulation
{
    /// <summary>
    /// Master Coordinator for Unity 6 3D BTMS Simulation:
    /// Couples the 50-cell battery pack, nanofluid circulation, automatic thermal controller,
    /// cooling circuit actuators, and live governing equations.
    /// Also supports synchronization with Python REST API backend (http://localhost:8080).
    /// </summary>
    public class BTMSMasterSimulation : MonoBehaviour
    {
        [Header("Subsystems")]
        public BatteryPackManager packManager;
        public NanofluidCirculation nanofluidCirculation;
        public ThermalController thermalController;
        public CoolingCircuit coolingCircuit;
        public DatasetManager datasetManager;

        [Header("Simulation Timing")]
        public bool isSimulationRunning = true;
        [Range(0.1f, 5.0f)] public float timeScale = 1.0f;
        public float simulationTimeSeconds = 0.0f;

        [Header("Boundary Conditions")]
        [Range(0.5f, 5.0f)] public float batteryCRate = 2.0f;
        public float ambientTemperatureC = 25.0f;
        [Range(0.0f, 2.5f)] public float magneticFieldB0 = 0.5f;

        [Header("Python REST API Synchronization (Optional)")]
        public bool syncWithPythonBackend = false;
        public string apiBaseUrl = "http://localhost:8080/api";
        public float apiSyncInterval = 0.2f;
        private float apiTimer = 0.0f;

        private void Start()
        {
            if (datasetManager != null)
            {
                datasetManager.OnRecordApplied += HandleDatasetRecord;
            }
        }

        private void HandleDatasetRecord(BTMSDatasetRecord rec)
        {
            batteryCRate = rec.discharge_c_rate;
            ambientTemperatureC = rec.ambient_temp;
            magneticFieldB0 = rec.magnetic_field_B0;

            if (nanofluidCirculation != null)
            {
                nanofluidCirculation.UpdateFlowParameters(rec.inlet_velocity, rec.phi1_al2o3, rec.phi2_cuo);
            }
        }

        private void Update()
        {
            if (!isSimulationRunning) return;

            float dt = Time.deltaTime * timeScale;
            simulationTimeSeconds += dt;

            // 1. Evaluate thermal controller
            float maxTemp = packManager != null ? packManager.maxTemperatureC : 25.0f;
            if (thermalController != null)
            {
                thermalController.EvaluateControlStep(maxTemp, ambientTemperatureC, dt);
            }

            // 2. Compute convective heat transfer coefficient
            float fluidVel = thermalController != null ? thermalController.fluidVelocity_m_s : 0.05f;
            float phi1 = nanofluidCirculation != null ? nanofluidCirculation.phi1_Al2O3 : 0.02f;
            float phi2 = nanofluidCirculation != null ? nanofluidCirculation.phi2_CuO : 0.01f;
            float phiTotal = phi1 + phi2;

            // Microchannel laminar Nusselt & h calculation
            float hCoolant = 320.0f + 5500.0f * Mathf.Pow(Mathf.Max(fluidVel, 0.005f), 0.55f) * (1.0f + 2.2f * phiTotal);

            // 3. Step 50 battery cells thermal conduction
            bool coolingActive = thermalController != null && thermalController.isCoolingActive;
            float coolantPlateTemp = coolingCircuit != null ? coolingCircuit.tempPlateInlet : 25.0f;
            float threshold = thermalController != null ? thermalController.thresholdC : 35.0f;

            if (packManager != null)
            {
                packManager.StepThermalConduction(dt, batteryCRate, hCoolant, coolantPlateTemp, threshold, coolingActive);
            }

            // 4. Update cooling circuit animations & temperatures
            if (coolingCircuit != null && thermalController != null)
            {
                coolingCircuit.AnimateActuators(thermalController.pumpRPM, thermalController.fanRPM, dt);

                // Thermal balance across pipeline nodes
                float tInlet = ambientTemperatureC + (thermalController.isCoolingActive ? 0.2f : 1.5f);
                float deltaT = (packManager != null ? packManager.totalHeatExtractedWatts : 50.0f) / Mathf.Max(fluidVel * 2500.0f, 20.0f);
                float tOutlet = tInlet + Mathf.Clamp(deltaT, 0.1f, 15.0f);

                float[] stationTemps = new float[11]
                {
                    tInlet,                    // Reservoir Outlet
                    tInlet + 0.05f,            // Pump Outlet
                    tInlet + 0.10f,            // Plate Inlet
                    tInlet + deltaT * 0.30f,   // Channel 1
                    tInlet + deltaT * 0.65f,   // Channel 2
                    tInlet + deltaT * 0.90f,   // Channel 3
                    tOutlet,                   // Plate Outlet
                    tOutlet,                   // HX Inlet
                    tOutlet - deltaT * 0.40f,  // HX Outlet
                    tOutlet - deltaT * 0.40f,  // Radiator Inlet
                    tInlet                     // Radiator Outlet
                };

                coolingCircuit.UpdatePipelineStationTemperatures(stationTemps);
            }

            // 5. Update nanofluid velocity and particle motion
            if (nanofluidCirculation != null && thermalController != null)
            {
                nanofluidCirculation.fluidVelocity_m_s = thermalController.fluidVelocity_m_s;
            }

            // 6. Optional Python backend sync
            if (syncWithPythonBackend)
            {
                apiTimer += Time.deltaTime;
                if (apiTimer >= apiSyncInterval)
                {
                    apiTimer = 0.0f;
                    StartCoroutine(SyncWithBackendRoutine(dt));
                }
            }
        }

        private IEnumerator SyncWithBackendRoutine(float dt)
        {
            string url = $"{apiBaseUrl}/step";
            string jsonPayload = $"{{\"dt\":{dt:F3}}}";

            using (UnityWebRequest req = UnityWebRequest.Post(url, jsonPayload, "application/json"))
            {
                yield return req.SendWebRequest();
                if (req.result != UnityWebRequest.Result.Success)
                {
                    // Backend unavailable or offline; standalone mode continues seamlessly
                }
            }
        }

        public void ToggleSimulation()
        {
            isSimulationRunning = !isSimulationRunning;
        }

        public void ResetSimulation()
        {
            simulationTimeSeconds = 0.0f;
            if (packManager != null) packManager.SpawnPackGrid();
        }
    }
}
