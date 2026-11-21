using System.Collections.Generic;
using UnityEngine;

namespace BTMS3D.Simulation
{
    /// <summary>
    /// Represents the full 3D cooling circuit:
    /// - 50-cell cooling plate with internal microchannels
    /// - Electric coolant pump with spinning impeller
    /// - Louvered radiator with spinning axial fan
    /// - Compact plate chiller & 3-way thermal valve
    /// - Coolant expansion reservoir
    /// - Color-coded pipeline segments tracking 11 thermal stations
    /// </summary>
    public class CoolingCircuit : MonoBehaviour
    {
        [Header("Physical Components")]
        public Transform pumpImpeller;
        public Transform radiatorFan;
        public GameObject chillerUnit;
        public GameObject threeWayValve;
        public GameObject reservoirTank;
        public GameObject coolingPlateObject;

        [Header("Pipeline Segment Renderers (11 Stations)")]
        public Renderer[] pipelineRenderers; // 11 pipeline nodes

        [Header("Live Pipeline Temperatures (°C)")]
        public float tempReservoirOutlet = 25.0f;
        public float tempPumpOutlet = 25.1f;
        public float tempPlateInlet = 25.2f;
        public float tempChannel1 = 26.5f;
        public float tempChannel2 = 28.0f;
        public float tempChannel3 = 29.5f;
        public float tempPlateOutlet = 30.5f;
        public float tempHxInlet = 30.5f;
        public float tempHxOutlet = 28.0f;
        public float tempRadiatorInlet = 28.0f;
        public float tempRadiatorOutlet = 25.0f;

        private static readonly int PipeColorProp = Shader.PropertyToID("_BaseColor");
        private MaterialPropertyBlock pipePropBlock;

        private void Awake()
        {
            pipePropBlock = new MaterialPropertyBlock();
        }

        public void AnimateActuators(float pumpRPM, float fanRPM, float dt)
        {
            // Spin pump impeller around local Z axis
            if (pumpImpeller != null && pumpRPM > 1.0f)
            {
                float degPerSec = (pumpRPM / 60.0f) * 360.0f;
                pumpImpeller.Rotate(0, 0, degPerSec * dt, Space.Self);
            }

            // Spin radiator fan around local Y axis
            if (radiatorFan != null && fanRPM > 1.0f)
            {
                float degPerSec = (fanRPM / 60.0f) * 360.0f;
                radiatorFan.Rotate(0, degPerSec * dt, 0, Space.Self);
            }
        }

        public void UpdatePipelineStationTemperatures(float[] temperatures)
        {
            if (temperatures == null || temperatures.Length < 11) return;

            tempReservoirOutlet = temperatures[0];
            tempPumpOutlet = temperatures[1];
            tempPlateInlet = temperatures[2];
            tempChannel1 = temperatures[3];
            tempChannel2 = temperatures[4];
            tempChannel3 = temperatures[5];
            tempPlateOutlet = temperatures[6];
            tempHxInlet = temperatures[7];
            tempHxOutlet = temperatures[8];
            tempRadiatorInlet = temperatures[9];
            tempRadiatorOutlet = temperatures[10];

            if (pipelineRenderers != null)
            {
                for (int i = 0; i < Mathf.Min(pipelineRenderers.Length, temperatures.Length); i++)
                {
                    if (pipelineRenderers[i] != null)
                    {
                        Color nodeColor = EvaluateTemperatureColor(temperatures[i]);
                        pipelineRenderers[i].GetPropertyBlock(pipePropBlock);
                        pipePropBlock.SetColor(PipeColorProp, nodeColor);
                        pipelineRenderers[i].SetPropertyBlock(pipePropBlock);
                    }
                }
            }
        }

        private Color EvaluateTemperatureColor(float tempC)
        {
            // Coolant color spectrum: Blue (20C) -> Cyan (25C) -> Green (30C) -> Yellow (35C) -> Orange (40C) -> Red (45C+)
            if (tempC < 25.0f)
            {
                float t = Mathf.InverseLerp(20.0f, 25.0f, tempC);
                return Color.Lerp(new Color(0.12f, 0.40f, 0.75f, 0.65f), new Color(0.10f, 0.70f, 0.65f, 0.65f), t);
            }
            if (tempC < 30.0f)
            {
                float t = Mathf.InverseLerp(25.0f, 30.0f, tempC);
                return Color.Lerp(new Color(0.10f, 0.70f, 0.65f, 0.65f), new Color(0.20f, 0.75f, 0.35f, 0.65f), t);
            }
            if (tempC < 35.0f)
            {
                float t = Mathf.InverseLerp(30.0f, 35.0f, tempC);
                return Color.Lerp(new Color(0.20f, 0.75f, 0.35f, 0.65f), new Color(0.95f, 0.75f, 0.10f, 0.65f), t);
            }
            if (tempC < 40.0f)
            {
                float t = Mathf.InverseLerp(35.0f, 40.0f, tempC);
                return Color.Lerp(new Color(0.95f, 0.75f, 0.10f, 0.65f), new Color(0.92f, 0.45f, 0.15f, 0.65f), t);
            }
            return new Color(0.90f, 0.20f, 0.20f, 0.75f);
        }
    }
}
