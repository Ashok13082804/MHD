using System;
using System.Collections.Generic;
using UnityEngine;

namespace BTMS3D.Simulation
{
    /// <summary>
    /// Represents an individual lithium-ion battery cell (B01 - B50).
    /// Tracks electrochemical heat generation (Bernardi equation), transient temperature,
    /// and dynamic color mapping with selective red highlighting when exceeding the thermal threshold.
    /// </summary>
    public class BatteryCell : MonoBehaviour
    {
        [Header("Cell Identification")]
        public int cellId = 1;
        public string cellName = "B01";
        public int row = 0;
        public int col = 0;

        [Header("Thermal State")]
        public float initialTemperatureC = 25.0f;
        public float currentTemperatureC = 25.0f;
        public float temperatureK => currentTemperatureC + 273.15f;
        public bool isOverheating = false;

        [Header("Electrical State")]
        public float nominalCapacityAh = 5.0f;
        public float cRate = 2.0f;
        public float currentA = 10.0f;
        public float openCircuitVoltageVoc = 3.85f;
        public float operatingVoltageVop = 3.65f;
        public float internalResistanceOhm = 0.015f;
        public float stateOfChargeSoc = 0.85f;
        public float entropicCoeff_dU_dT = -0.00045f; // V/K

        [Header("Thermal Properties")]
        public float massKg = 0.382f;
        public float specificHeatJ_kgK = 1050.0f;
        public float heatGenerationWatts = 0.0f;
        public float heatTransferWatts = 0.0f;

        [Header("Rendering & Appearance")]
        public Renderer cellRenderer;
        public MaterialPropertyBlock propBlock;
        private static readonly int ColorPropId = Shader.PropertyToID("_BaseColor");

        // Color definitions matching engineering specifications
        private static readonly Color ColorBlue = new Color(0.16f, 0.50f, 0.73f);   // < 25°C
        private static readonly Color ColorCyan = new Color(0.10f, 0.74f, 0.61f);   // 25 - 30°C
        private static readonly Color ColorGreen = new Color(0.18f, 0.80f, 0.44f);  // 30 - 35°C
        private static readonly Color ColorYellow = new Color(0.95f, 0.77f, 0.06f); // 35 - 40°C
        private static readonly Color ColorOrange = new Color(0.90f, 0.49f, 0.13f); // 40°C - threshold
        private static readonly Color ColorRed = new Color(0.91f, 0.30f, 0.24f);    // >= threshold (OVERHEATING)

        // Telemetry history buffer
        public List<float> temperatureHistory = new List<float>();
        private const int MaxHistorySize = 60;

        private void Awake()
        {
            if (cellRenderer == null)
            {
                cellRenderer = GetComponent<Renderer>();
            }
            propBlock = new MaterialPropertyBlock();
        }

        public void Initialize(int id, int r, int c, float initTempC)
        {
            cellId = id;
            cellName = $"B{id:D2}";
            row = r;
            col = c;
            initialTemperatureC = initTempC;
            currentTemperatureC = initTempC;
            temperatureHistory.Clear();
            temperatureHistory.Add(initTempC);

            UpdateColor(35.0f);
        }

        /// <summary>
        /// Calculates Bernardi electrochemical heat generation:
        /// Q_b = I * (Voc - Vop) - I * T_cell * (dU_oc / dT)
        /// </summary>
        public float ComputeHeatGeneration(float activeCRate)
        {
            cRate = activeCRate;
            currentA = cRate * nominalCapacityAh;

            // Core cells in module center experience higher localized internal resistance
            bool isCore = (row >= 1 && row <= 3) && (col >= 2 && col <= 7);
            float coreFactor = isCore ? 1.08f : 0.96f;
            float effResistance = internalResistanceOhm * coreFactor;

            operatingVoltageVop = Mathf.Max(openCircuitVoltageVoc - (currentA * effResistance), 2.5f);

            float qJouleIrreversible = currentA * (openCircuitVoltageVoc - operatingVoltageVop);
            float qEntropicReversible = -currentA * temperatureK * entropicCoeff_dU_dT;

            heatGenerationWatts = Mathf.Max(qJouleIrreversible + qEntropicReversible, 0.0f);
            return heatGenerationWatts;
        }

        /// <summary>
        /// Updates cell temperature based on heat balance:
        /// m * Cp * (dT / dt) = Q_gen - Q_cooling + Q_intercell - Q_ambient
        /// </summary>
        public void UpdateThermalStep(float dt, float qCooling, float qInterCell, float qAmbient, float thresholdC)
        {
            heatTransferWatts = qCooling;
            float netHeatWatts = heatGenerationWatts - qCooling + qInterCell - qAmbient;
            float deltaT = (netHeatWatts * dt) / (massKg * specificHeatJ_kgK);

            currentTemperatureC += deltaT;

            // Update telemetry buffer
            temperatureHistory.Add(currentTemperatureC);
            if (temperatureHistory.Count > MaxHistorySize)
            {
                temperatureHistory.RemoveAt(0);
            }

            UpdateColor(thresholdC);
        }

        /// <summary>
        /// Color mapping logic:
        /// Only this cell turns red if currentTemperatureC >= thresholdC.
        /// </summary>
        public void UpdateColor(float thresholdC)
        {
            Color targetColor;

            if (currentTemperatureC >= thresholdC)
            {
                isOverheating = true;
                targetColor = ColorRed;
            }
            else
            {
                isOverheating = false;
                if (currentTemperatureC < 25.0f)
                {
                    targetColor = ColorBlue;
                }
                else if (currentTemperatureC < 30.0f)
                {
                    float t = (currentTemperatureC - 25.0f) / 5.0f;
                    targetColor = Color.Lerp(ColorBlue, ColorCyan, t);
                }
                else if (currentTemperatureC < 35.0f)
                {
                    float t = (currentTemperatureC - 30.0f) / 5.0f;
                    targetColor = Color.Lerp(ColorCyan, ColorGreen, t);
                }
                else if (currentTemperatureC < 40.0f)
                {
                    float t = (currentTemperatureC - 35.0f) / 5.0f;
                    targetColor = Color.Lerp(ColorGreen, ColorYellow, t);
                }
                else
                {
                    float t = Mathf.Clamp01((currentTemperatureC - 40.0f) / Mathf.Max(thresholdC - 40.0f, 1.0f));
                    targetColor = Color.Lerp(ColorYellow, ColorOrange, t);
                }
            }

            if (cellRenderer != null)
            {
                cellRenderer.GetPropertyBlock(propBlock);
                propBlock.SetColor(ColorPropId, targetColor);
                cellRenderer.SetPropertyBlock(propBlock);
            }
        }
    }
}
