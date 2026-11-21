using System.Collections.Generic;
using UnityEngine;

namespace BTMS3D.Simulation
{
    /// <summary>
    /// Visualizes realistic 3D hybrid nanofluid circulation in the BTMS circuit.
    /// Simulates moving Al2O3 (silver) and CuO (copper) nanoparticles flowing through
    /// transparent pipelines and microchannels.
    /// Velocity and particle density scale dynamically with fluid flow rate and volume fraction.
    /// </summary>
    public class NanofluidCirculation : MonoBehaviour
    {
        [Header("Nanoparticle Configuration")]
        public GameObject al2o3ParticlePrefab; // Silver metallic sphere
        public GameObject cuoParticlePrefab;   // Copper metallic sphere
        public Transform particleContainer;

        [Header("Circuit Waypoints (Pipeline Path)")]
        public Transform[] circuitWaypoints;

        [Header("Nanofluid Physical Parameters")]
        [Range(0.0f, 0.05f)] public float phi1_Al2O3 = 0.02f;
        [Range(0.0f, 0.04f)] public float phi2_CuO = 0.01f;
        public float fluidVelocity_m_s = 0.05f;

        [Header("Visual Density Settings")]
        public int maxParticles = 600;
        public float visualSpeedScale = 4.0f; // Multiplier to make physical flow clearly discernible
        public float pipeRadius = 0.012f;

        private struct NanoparticleInstance
        {
            public GameObject gameObject;
            public Transform transform;
            public float pathProgress; // 0.0 to 1.0 along the closed loop
            public float speedMultiplier;
            public Vector3 radialOffset;
            public bool isAl2O3; // True = Silver, False = Copper
        }

        private List<NanoparticleInstance> activeParticles = new List<NanoparticleInstance>();
        private float totalPathLength = 1.0f;
        private float[] waypointDistances;

        private void Start()
        {
            CalculatePathMetrics();
            SpawnNanoparticles();
        }

        private void CalculatePathMetrics()
        {
            if (circuitWaypoints == null || circuitWaypoints.Length < 2) return;

            waypointDistances = new float[circuitWaypoints.Length];
            totalPathLength = 0.0f;

            for (int i = 0; i < circuitWaypoints.Length; i++)
            {
                int next = (i + 1) % circuitWaypoints.Length;
                float d = Vector3.Distance(circuitWaypoints[i].position, circuitWaypoints[next].position);
                waypointDistances[i] = d;
                totalPathLength += d;
            }
        }

        public void SpawnNanoparticles()
        {
            // Clear existing
            for (int i = 0; i < activeParticles.Count; i++)
            {
                if (activeParticles[i].gameObject != null)
                {
                    Destroy(activeParticles[i].gameObject);
                }
            }
            activeParticles.Clear();

            if (circuitWaypoints == null || circuitWaypoints.Length < 2) return;

            float phiTotal = phi1_Al2O3 + phi2_CuO;
            int particleCount = Mathf.Clamp(Mathf.RoundToInt(maxParticles * (phiTotal / 0.05f) * 1.5f), 50, maxParticles);
            float ratioAl2O3 = (phiTotal > 0.0001f) ? (phi1_Al2O3 / phiTotal) : 0.67f;

            for (int i = 0; i < particleCount; i++)
            {
                bool isAl = (Random.value <= ratioAl2O3);
                GameObject prefab = isAl ? al2o3ParticlePrefab : cuoParticlePrefab;

                GameObject obj;
                if (prefab != null)
                {
                    obj = Instantiate(prefab, particleContainer != null ? particleContainer : transform);
                }
                else
                {
                    // Procedural sphere fallback
                    obj = GameObject.CreatePrimitive(PrimitiveType.Sphere);
                    obj.transform.localScale = isAl ? Vector3.one * 0.009f : Vector3.one * 0.012f;
                    Renderer rend = obj.GetComponent<Renderer>();
                    if (rend != null)
                    {
                        Material mat = new Material(Shader.Find("Standard"));
                        if (isAl)
                        {
                            mat.color = new Color(0.85f, 0.88f, 0.92f); // Silver
                            mat.SetFloat("_Metallic", 0.95f);
                            mat.SetFloat("_Glossiness", 0.85f);
                        }
                        else
                        {
                            mat.color = new Color(0.82f, 0.45f, 0.22f); // Copper
                            mat.SetFloat("_Metallic", 0.90f);
                            mat.SetFloat("_Glossiness", 0.75f);
                        }
                        rend.material = mat;
                    }
                    if (particleContainer != null) obj.transform.SetParent(particleContainer);
                }

                Collider col = obj.GetComponent<Collider>();
                if (col != null) col.enabled = false; // Disable physics collisions for performance

                float progress = (float)i / particleCount;
                Vector2 randomCircle = Random.insideUnitCircle * (pipeRadius * 0.75f);
                Vector3 radialOffset = new Vector3(randomCircle.x, randomCircle.y, 0.0f);

                NanoparticleInstance inst = new NanoparticleInstance
                {
                    gameObject = obj,
                    transform = obj.transform,
                    pathProgress = progress,
                    speedMultiplier = Random.Range(0.85f, 1.15f), // Parabolic velocity profile variation
                    radialOffset = radialOffset,
                    isAl2O3 = isAl
                };

                activeParticles.Add(inst);
            }
        }

        private void Update()
        {
            if (activeParticles.Count == 0 || circuitWaypoints == null || circuitWaypoints.Length < 2) return;

            float dt = Time.deltaTime;
            float baseStep = (fluidVelocity_m_s * visualSpeedScale * dt) / Mathf.Max(totalPathLength, 0.001f);

            for (int i = 0; i < activeParticles.Count; i++)
            {
                NanoparticleInstance inst = activeParticles[i];

                inst.pathProgress += baseStep * inst.speedMultiplier;
                if (inst.pathProgress >= 1.0f) inst.pathProgress -= 1.0f;

                Vector3 currentPos = EvaluatePathPosition(inst.pathProgress, out Vector3 tangent);
                Vector3 normal = Vector3.Cross(tangent, Vector3.up).normalized;
                if (normal.sqrMagnitude < 0.001f) normal = Vector3.right;
                Vector3 binormal = Vector3.Cross(tangent, normal).normalized;

                Vector3 offset = (normal * inst.radialOffset.x) + (binormal * inst.radialOffset.y);
                inst.transform.position = currentPos + offset;

                activeParticles[i] = inst;
            }
        }

        private Vector3 EvaluatePathPosition(float progress, out Vector3 tangent)
        {
            float targetDist = progress * totalPathLength;
            float accumulated = 0.0f;

            for (int i = 0; i < circuitWaypoints.Length; i++)
            {
                int next = (i + 1) % circuitWaypoints.Length;
                float segmentLen = waypointDistances[i];

                if (accumulated + segmentLen >= targetDist || i == circuitWaypoints.Length - 1)
                {
                    float localT = Mathf.Clamp01((targetDist - accumulated) / Mathf.Max(segmentLen, 0.0001f));
                    Vector3 p0 = circuitWaypoints[i].position;
                    Vector3 p1 = circuitWaypoints[next].position;
                    tangent = (p1 - p0).normalized;
                    return Vector3.Lerp(p0, p1, localT);
                }
                accumulated += segmentLen;
            }

            tangent = Vector3.forward;
            return circuitWaypoints[0].position;
        }

        public void UpdateFlowParameters(float velocity, float phi1, float phi2)
        {
            bool densityChanged = (Mathf.Abs(phi1_Al2O3 - phi1) > 0.002f || Mathf.Abs(phi2_CuO - phi2) > 0.002f);
            fluidVelocity_m_s = velocity;
            phi1_Al2O3 = phi1;
            phi2_CuO = phi2;

            if (densityChanged)
            {
                SpawnNanoparticles();
            }
        }
    }
}
