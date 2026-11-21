using UnityEngine;

namespace BTMS3D.Simulation
{
    /// <summary>
    /// Interactive 3D Camera Controller:
    /// - 360° Orbit rotation (Left mouse drag)
    /// - Pan translation (Right mouse drag)
    /// - Zoom in / out (Scroll wheel)
    /// - Smooth focus to target (Click on cell or component)
    /// - Quick preset buttons (Isometric, Top/Pack, Side/Radiator, Front/Chiller, Exploded)
    /// </summary>
    public class CameraController3D : MonoBehaviour
    {
        [Header("Orbit & Distance")]
        public Transform target;
        public float distance = 1.4f;
        public float minDistance = 0.3f;
        public float maxDistance = 3.5f;

        [Header("Sensitivity Settings")]
        public float orbitSpeedX = 180.0f;
        public float orbitSpeedY = 120.0f;
        public float zoomSpeed = 2.5f;
        public float panSpeed = 0.35f;

        [Header("Rotation Constraints")]
        public float minYAngle = 5.0f;
        public float maxYAngle = 85.0f;

        private float currentX = 45.0f;
        private float currentY = 30.0f;
        private Vector3 targetOffset = Vector3.zero;
        private Vector3 smoothFocusTarget;
        private bool isFocusing = false;

        private void Start()
        {
            if (target == null)
            {
                GameObject dummyTarget = new GameObject("CameraPivot");
                dummyTarget.transform.position = new Vector3(0, 0.05f, 0);
                target = dummyTarget.transform;
            }
            smoothFocusTarget = target.position;
            UpdateCameraTransform();
        }

        private void LateUpdate()
        {
            HandleMouseInput();
            UpdateCameraTransform();
        }

        private void HandleMouseInput()
        {
            // Ignore camera inputs if pointer is over UI elements
            if (UnityEngine.EventSystems.EventSystem.current != null &&
                UnityEngine.EventSystems.EventSystem.current.IsPointerOverGameObject())
            {
                return;
            }

            // Left Mouse: Orbit
            if (Input.GetMouseButton(0) && !Input.GetKey(KeyCode.LeftShift))
            {
                currentX += Input.GetAxis("Mouse X") * orbitSpeedX * Time.deltaTime;
                currentY -= Input.GetAxis("Mouse Y") * orbitSpeedY * Time.deltaTime;
                currentY = Mathf.Clamp(currentY, minYAngle, maxYAngle);
                isFocusing = false;
            }

            // Right Mouse or Shift+Left: Pan
            if (Input.GetMouseButton(1) || (Input.GetMouseButton(0) && Input.GetKey(KeyCode.LeftShift)))
            {
                float panX = -Input.GetAxis("Mouse X") * panSpeed * (distance / 2.0f);
                float panY = -Input.GetAxis("Mouse Y") * panSpeed * (distance / 2.0f);

                Vector3 right = transform.right;
                Vector3 up = transform.up;
                targetOffset += (right * panX) + (up * panY);
                isFocusing = false;
            }

            // Scroll Wheel: Zoom
            float scroll = Input.GetAxis("Mouse ScrollWheel");
            if (Mathf.Abs(scroll) > 0.001f)
            {
                distance -= scroll * zoomSpeed * distance;
                distance = Mathf.Clamp(distance, minDistance, maxDistance);
            }

            // Smooth focus interpolation
            if (isFocusing)
            {
                target.position = Vector3.Lerp(target.position, smoothFocusTarget, Time.deltaTime * 6.0f);
                if (Vector3.Distance(target.position, smoothFocusTarget) < 0.01f)
                {
                    target.position = smoothFocusTarget;
                    isFocusing = false;
                }
            }
        }

        private void UpdateCameraTransform()
        {
            Quaternion rotation = Quaternion.Euler(currentY, currentX, 0);
            Vector3 negDistance = new Vector3(0.0f, 0.0f, -distance);
            Vector3 center = target.position + targetOffset;
            Vector3 position = rotation * negDistance + center;

            transform.rotation = rotation;
            transform.position = position;
        }

        public void FocusOnTarget(Vector3 worldPos, float focusDistance = 0.5f)
        {
            smoothFocusTarget = worldPos;
            targetOffset = Vector3.zero;
            distance = focusDistance;
            isFocusing = true;
        }

        // Camera Preset Angles
        public void SetIsometricView()
        {
            currentX = 45.0f;
            currentY = 32.0f;
            distance = 1.35f;
            targetOffset = Vector3.zero;
        }

        public void SetTopPackView()
        {
            currentX = 0.0f;
            currentY = 88.0f;
            distance = 1.0f;
            targetOffset = Vector3.zero;
        }

        public void SetSideRadiatorView()
        {
            currentX = 90.0f;
            currentY = 15.0f;
            distance = 1.1f;
            targetOffset = new Vector3(0.3f, 0, 0);
        }

        public void SetFrontChillerView()
        {
            currentX = 0.0f;
            currentY = 18.0f;
            distance = 1.1f;
            targetOffset = new Vector3(0, 0, -0.2f);
        }

        public void ResetView()
        {
            SetIsometricView();
        }
    }
}
