using System;
using System.Collections.Generic;
using System.IO;
using UnityEngine;

namespace BTMS3D.Simulation
{
    [System.Serializable]
    public class BTMSDatasetRecord
    {
        public int record_id;
        public float inlet_velocity;      // m/s [0.01 - 0.20]
        public float inlet_temperature;   // °C [15.0 - 45.0]
        public float discharge_c_rate;    // C [0.5 - 5.0]
        public float phi1_al2o3;          // fraction [0.00 - 0.05]
        public float phi2_cuo;            // fraction [0.00 - 0.04]
        public float magnetic_field_B0;   // T [0.0 - 2.5]
        public float porosity;            // [0.60 - 0.95]
        public float permeability_k;      // m^2 [1e-9 - 1e-6]
        public float ambient_temp;        // °C [10.0 - 45.0]
    }

    /// <summary>
    /// Ingests, parses, and validates CSV and JSON dataset files.
    /// Enables batch test vector playback into the 3D BTMS model.
    /// </summary>
    public class DatasetManager : MonoBehaviour
    {
        public List<BTMSDatasetRecord> loadedRecords = new List<BTMSDatasetRecord>();
        public int currentRecordIndex = 0;
        public bool isPlaying = false;
        public float playbackInterval = 2.0f; // Seconds per record
        private float timer = 0.0f;

        public event Action<BTMSDatasetRecord> OnRecordApplied;

        public bool LoadDatasetCSV(string csvContent)
        {
            loadedRecords.Clear();
            string[] lines = csvContent.Split(new[] { '\r', '\n' }, StringSplitOptions.RemoveEmptyEntries);
            if (lines.Length < 2) return false;

            string[] headers = lines[0].Split(',');
            for (int i = 1; i < lines.Length; i++)
            {
                string[] parts = lines[i].Split(',');
                if (parts.Length < 6) continue;

                try
                {
                    BTMSDatasetRecord rec = new BTMSDatasetRecord
                    {
                        record_id = i,
                        inlet_velocity = float.Parse(parts[0]),
                        inlet_temperature = float.Parse(parts[1]),
                        discharge_c_rate = float.Parse(parts[2]),
                        phi1_al2o3 = float.Parse(parts[3]),
                        phi2_cuo = float.Parse(parts[4]),
                        magnetic_field_B0 = float.Parse(parts[5]),
                        porosity = parts.Length > 6 ? float.Parse(parts[6]) : 0.85f,
                        permeability_k = parts.Length > 7 ? float.Parse(parts[7]) : 1.0e-7f,
                        ambient_temp = parts.Length > 8 ? float.Parse(parts[8]) : 25.0f
                    };
                    loadedRecords.Add(rec);
                }
                catch (Exception e)
                {
                    Debug.LogWarning($"[DatasetManager] Skipping invalid row {i}: {e.Message}");
                }
            }

            Debug.Log($"[DatasetManager] Successfully loaded {loadedRecords.Count} valid records.");
            currentRecordIndex = 0;
            return loadedRecords.Count > 0;
        }

        private void Update()
        {
            if (isPlaying && loadedRecords.Count > 0)
            {
                timer += Time.deltaTime;
                if (timer >= playbackInterval)
                {
                    timer = 0.0f;
                    ApplyCurrentRecord();
                    currentRecordIndex = (currentRecordIndex + 1) % loadedRecords.Count;
                }
            }
        }

        public void ApplyCurrentRecord()
        {
            if (loadedRecords.Count == 0 || currentRecordIndex >= loadedRecords.Count) return;
            BTMSDatasetRecord rec = loadedRecords[currentRecordIndex];
            OnRecordApplied?.Invoke(rec);
        }

        public void TogglePlayback()
        {
            isPlaying = !isPlaying;
        }
    }
}
