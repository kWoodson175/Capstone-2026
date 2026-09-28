# security_policy.py

# -----------------------------
# Spatial Safety Bounds (Meters)
# -----------------------------
X_MIN = 0.000
X_MAX = 0.750
Y_MIN = -0.500
Y_MAX = 0.420
Z_MIN = 0.020  
Z_MAX = 0.500

# -----------------------------
#  Safety Bounds
# -----------------------------
MAX_VELOCITY = 0.5 # 500 mm/s       
MAX_ACCELERATION = 2.0 #2000 mm/s^2

def check_motion_limits(x, y, z, v, a):
    """
    Validates whether a requested motion is within safe operational limits.
    Returns (True, "Safe") if allowed, or (False, "Reason") if blocked.
    """
    # Check Spatial Bounds (X, Y, Z)
    if not (X_MIN <= x <= X_MAX):
        return False, f"X coordinate ({x:.4f}) is out of bounds."
    if not (Y_MIN <= y <= Y_MAX):
        return False, f"Y coordinate ({y:.4f}) is out of bounds."
    if not (Z_MIN <= z <= Z_MAX):
        return False, f"Z coordinate ({z:.4f}) is out of bounds."
        
    # Check velocity and acceleration bounds
    # Using abs() ensures negative velocities/accelerations are also caught
    if abs(v) > MAX_VELOCITY:
        return False, f"Velocity ({v:.4f}) exceeds {MAX_VELOCITY} limit."
    if abs(a) > MAX_ACCELERATION:
        return False, f"Acceleration ({a:.4f}) exceeds {MAX_ACCELERATION} limit."
        
    return True, "Safe"