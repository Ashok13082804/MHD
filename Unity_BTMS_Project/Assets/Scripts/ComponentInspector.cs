using System.Collections.Generic;
using UnityEngine;
using UnityEngine.UI;

namespace BTMS3D.Simulation
{
    /// <summary>
    /// 3D Raycast Inspector:
    /// Handles user clicks on individual battery cells (B01-B50) and cooling circuit components.
    /// Surfaces all 10 cell parameters, component thermophysical properties, and applicable governing equations.
    /// </summary>
    public class ComponentInspector : MonoBehaviour
    {
        [Header("Camera & Raycast")]
        public Camera mainCamera;
        public CameraController3D cameraController;
        public LayerMask inspectableLayerMask = ~0;

        [Header("UI Inspection HUD References")]
        public GameObject inspectionPanel;
        public Text titleText;
        public Text param1Text;
        public Text param2Text;
        public Text param3Text;
        public Text param4Text;
        public Text param5Text;
        public Text param6Text;
        public Text param7Text;
        public Text param8Text;
        public Text param9Text;
        public Text param10Text;
        public Text equationDisplayText;

        [Header("Selected State")]
        public BatteryCell selectedCell;
        public GameObject selectedComponent;

        private void Start()
        {
            if (mainCamera == null) mainCamera = Camera.main;
            if (cameraController == null && mainCamera != null)
            {
                cameraController = mainCamera.GetComponent<CameraController3D>();
            }
        }

        private void Update()
        {
            // Left click to select object
            if (Input.GetMouseButtonDown(0))
            {
                if (UnityEngine.EventSystems.EventSystem.current != null &&
                    UnityEngine.EventSystems.EventSystem.current.IsPointerOverGameObject())
                {
                    return;
                }

                Ray ray = mainCamera.ScreenPointToRay(Input.mousePosition);
                if (Physics.Raycast(ray, out RaycastHit hit, 10.0f, inspectableLayerMask))
                {
                    InspectObject(hit.collider.gameObject);
                }
            }

            // Live refresh of inspection HUD if a cell is selected
            if (selectedCell != null && inspectionPanel != null && inspectionPanel.activeSelf)
            {
                RefreshCellTelemetry();
            }
        }

        public void InspectObject(GameObject obj)
        {
            selectedComponent = obj;
            selectedCell = obj.GetComponentInParent<BatteryCell>();

            if (cameraController != null)
            {
                cameraController.FocusOnTarget(obj.transform.position, 0.45f);
            }

            if (inspectionPanel != null)
            {
                inspectionPanel.SetActive(true);
            }

            if (selectedCell != null)
            {
                RefreshCellTelemetry();
            }
            else
            {
                DisplayGenericComponentInfo(obj.name);
            }
        }

        private void RefreshCellTelemetry()
        {
            if (selectedCell == null) return;

            if (titleText != null) titleText.text = $"BATTERY CELL: {selectedCell.cellName}";

            // 10 Detailed Inspection Parameters
            if (param1Text != null) param1Text.text = $"1. Cell Identifier: {selectedCell.cellName} (Row {selectedCell.row + 1}, Col {selectedCell.col + 1})";
            if (param2Text != null) param2Text.text = $"2. Current Temp: {selectedCell.currentTemperatureC:F2} °C ({selectedCell.temperatureK:F2} K)";
            if (param3Text != null) param3Text.text = $"3. Initial Temp: {selectedCell.initialTemperatureC:F2} °C";
            if (param4Text != null) param4Text.text = $"4. Heat Generation Rate: {selectedCell.heatGenerationWatts:F3} W";
            if (param5Text != null) param5Text.text = $"5. Discharge C-Rate: {selectedCell.cRate:F2} C";
            if (param6Text != null) param6Text.text = $"6. Operating Current: {selectedCell.currentA:F2} A";
            if (param7Text != null) param7Text.text = $"7. Operating Voltage: {selectedCell.operatingVoltageVop:F3} V (Voc: {selectedCell.openCircuitVoltageVoc:F2} V)";
            if (param8Text != null) param8Text.text = $"8. Heat Transfer Rate: {selectedCell.heatTransferWatts:F3} W";
            if (param9Text != null) param9Text.text = $"9. Cooling Status: {(selectedCell.heatTransferWatts > 0.5f ? "ACTIVE FORCED NANOFLUID" : "PASSIVE STANDBY")}";
            if (param10Text != null)
            {
                int sampleCount = selectedCell.temperatureHistory.Count;
                float firstT = sampleCount > 0 ? selectedCell.temperatureHistory[0] : selectedCell.currentTemperatureC;
                param10Text.text = $"10. Temp Variation: Delta {selectedCell.currentTemperatureC - firstT:+0.00;-0.00;0.00} °C over {sampleCount} steps";
            }

            if (equationDisplayText != null)
            {
                var eq2 = GoverningEquations.Eq2_BernardiHeat(
                    selectedCell.currentA,
                    selectedCell.openCircuitVoltageVoc,
                    selectedCell.operatingVoltageVop,
                    selectedCell.temperatureK,
                    selectedCell.entropicCoeff_dU_dT
                );
                equationDisplayText.text = $"GOVERNING FORMULATION (Eq 2):\n{eq2.name}\n{eq2.latex}\n{eq2.substitution} = {eq2.result:F2} {eq2.unit}";
            }
        }

        private void DisplayGenericComponentInfo(string compName)
        {
            if (titleText != null) titleText.text = $"COMPONENT: {compName.ToUpper()}";

            if (param1Text != null) param1Text.text = $"Component Name: {compName}";
            if (param2Text != null) param2Text.text = "Material: Aerospace Grade Brazed Al-3003 Alloy";
            if (param3Text != null) param3Text.text = "Thermal Conductivity: 190.0 W/(m·K)";
            if (param4Text != null) param4Text.text = "Specific Heat: 890.0 J/(kg·K)";
            if (param5Text != null) param5Text.text = "Density: 2730 kg/m³";
            if (param6Text != null) param6Text.text = "Coolant Fluid: Al2O3-CuO/Water Hybrid Nanofluid";
            if (param7Text != null) param7Text.text = "Flow Regime: Laminar Darcy-Brinkman";
            if (param8Text != null) param8Text.text = "MHD Field: Transverse B0 Applied";
            if (param9Text != null) param9Text.text = "Operating Status: Nominal Online";
            if (param10Text != null) param10Text.text = "Hydraulic Seal: Hermetic EPDM / Viton";

            if (equationDisplayText != null)
            {
                var eq21 = GoverningEquations.Eq21_NusseltNumber(450.0f, 5.37f, 0.008f, 0.75f, 0.03f);
                equationDisplayText.text = $"GOVERNING FORMULATION (Eq 21):\n{eq21.name}\n{eq21.latex}\n{eq21.substitution} = {eq21.result:F2}";
            }
        }

        public void CloseInspectionPanel()
        {
            selectedCell = null;
            selectedComponent = null;
            if (inspectionPanel != null)
            {
                inspectionPanel.SetActive(false);
            }
        }
    }
}
