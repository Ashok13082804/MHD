using System;
using UnityEngine;

namespace BTMS3D.Simulation
{
    public enum BTMSMode
    {
        Passive,
        ActiveNanofluid,
        ActiveChiller
    }

    /// <summary>
    /// Automatic temperature-controlled BTMS regulator.
    /// Features dynamic threshold slider, hysteresis deadband, variable pump RPM and fan modulation,
    /// and multi-mode switching (Passive, Active Radiator, Active Chiller).
    /// </summary>
    public class ThermalController : MonoBehaviour
    {
        [Header("Controller Settings")]
        [Range(20.0f, 60.0f)] public float thresholdC = 35.0f;
        [Range(0.5f, 5.0f)] public float hysteresisC = 2.0f;
        public BTMSMode activeMode = BTMSMode.ActiveNanofluid;

        [Header("Actuator Telemetry")]
        public bool isCoolingActive = false;
        public float pumpRPM = 0.0f;
        public float fanRPM = 0.0f;
        public float fluidVelocity_m_s = 0.005f; // Baseline natural circulation
        public bool isChillerEngaged = false;
        public float powerConsumptionWatts = 0.0f;
        public float totalEnergyConsumedWh = 0.0f;

        [Header("Hardware Limits")]
        public float maxPumpRPM = 4500.0f;
        public float maxFanRPM = 2800.0f;
        public float maxVelocity_m_s = 0.20f;
        public float pumpRatedPowerWatts = 65.0f;
        public float fanRatedPowerWatts = 120.0f;
        public float chillerRatedPowerWatts = 1800.0f;

        public float LowerThresholdC => thresholdC - hysteresisC;

        public void SetThreshold(float newThreshold)
        {
            thresholdC = Mathf.Clamp(newThreshold, 20.0f, 60.0f);
        }

        public void SetMode(BTMSMode mode)
        {
            activeMode = mode;
        }

        /// <summary>
        /// Updates the controller state given the current peak cell temperature.
        /// </summary>
        public void EvaluateControlStep(float maxCellTempC, float ambientTempC, float dt)
        {
            float lowerThresh = LowerThresholdC;

            switch (activeMode)
            {
                case BTMSMode.Passive:
                    isCoolingActive = false;
                    pumpRPM = 0.0f;
                    fanRPM = 0.0f;
                    fluidVelocity_m_s = 0.005f;
                    isChillerEngaged = false;
                    powerConsumptionWatts = 0.0f;
                    break;

                case BTMSMode.ActiveNanofluid:
                    if (maxCellTempC >= thresholdC)
                    {
                        isCoolingActive = true;
                    }
                    else if (maxCellTempC <= lowerThresh)
                    {
                        isCoolingActive = false;
                    }

                    if (isCoolingActive)
                    {
                        // Modulate pump RPM and fan speed proportional to thermal overshoot
                        float overshoot = Mathf.Max(maxCellTempC - lowerThresh, 0.1f);
                        float demand = Mathf.Clamp(overshoot / 8.0f, 0.35f, 1.0f);

                        pumpRPM = demand * maxPumpRPM;
                        fanRPM = demand * maxFanRPM;
                        fluidVelocity_m_s = demand * maxVelocity_m_s;
                        isChillerEngaged = false;

                        float pPump = pumpRatedPowerWatts * Mathf.Pow(demand, 2.0f);
                        float pFan = fanRatedPowerWatts * Mathf.Pow(demand, 2.0f);
                        powerConsumptionWatts = pPump + pFan;
                    }
                    else
                    {
                        pumpRPM = 0.0f;
                        fanRPM = 0.0f;
                        fluidVelocity_m_s = 0.005f;
                        isChillerEngaged = false;
                        powerConsumptionWatts = 0.0f;
                    }
                    break;

                case BTMSMode.ActiveChiller:
                    if (maxCellTempC >= (thresholdC - 2.0f))
                    {
                        isCoolingActive = true;
                        isChillerEngaged = true;
                    }
                    else if (maxCellTempC <= (lowerThresh - 3.0f))
                    {
                        isCoolingActive = false;
                        isChillerEngaged = false;
                    }

                    if (isCoolingActive)
                    {
                        pumpRPM = maxPumpRPM * 0.90f;
                        fanRPM = maxFanRPM * 0.50f;
                        fluidVelocity_m_s = maxVelocity_m_s * 0.90f;
                        powerConsumptionWatts = (pumpRatedPowerWatts * 0.8f) + (fanRatedPowerWatts * 0.4f) + (chillerRatedPowerWatts * 0.75f);
                    }
                    else
                    {
                        pumpRPM = 0.0f;
                        fanRPM = 0.0f;
                        fluidVelocity_m_s = 0.005f;
                        isChillerEngaged = false;
                        powerConsumptionWatts = 0.0f;
                    }
                    break;
            }

            // Energy accumulation
            totalEnergyConsumedWh += (powerConsumptionWatts * dt) / 3600.0f;
        }
    }
}
