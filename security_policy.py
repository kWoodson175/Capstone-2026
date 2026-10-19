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

#-----------------------------------
# IP Whitelist
#-----------------------------------

ALLOWED_IPS = ["127.0.0.1", # VM IP
               #"192.168.1.101" # IP OF ROBOT

def is_ip_allowed(client_ip):
    """
    Checks if an incoming IP address is in the whitelist.
    """
    if client_ip in ALLOWED_IPS:
        return True
    else:
        return False
#----------------------------------------
# Base Restrictions
#---------------------------------------

MIN_BASE_RADIUS = 0.100
MAX_BASE_RADIUS = 0.800

# 180-Degree Cartesian Working Arc (in Radians)
# This restricts the toolhead to the front half of the robot
MIN_BASE_ANGLE_RAD = -1.5708
MAX_BASE_ANGLE_RAD = 1.5708

def check_motion_limits(x, y, z, v, a):
        # Check velocity and acceleration bounds
    # Using abs() ensures negative velocities/accelerations are also caught
    if abs(v) > MAX_VELOCITY:
        return False, f"Velocity ({v:.4f}) exceeds {MAX_VELOCITY} limit."
    if abs(a) > MAX_ACCELERATION:
        return False, f"Acceleration ({a:.4f}) exceeds {MAX_ACCELERATION} limit."
    # Check Radial Base Limit (Distance)
    radius = math.sqrt(x**2 + y**2)
    if radius < MIN_BASE_RADIUS:
        return False, f"Too close to base! Radius ({radius:.3f}m) violates {MIN_BASE_RADIUS}m minimum"
    if radius > MAX_BASE_RADIUS:
        return False, f"Overextended! Radius ({radius:.3f}m)s exceeds {MAX_BASE_RADIUS}m maximum"

    # Check 180-Degree Base Limit (Angle in Radians)
    # math,.atan2(y, x) returns radians between  -pi and +pi
    cartesian_angle_rad = math.atan2(y, x)
    if not (MIN_BASE_ANGLE_RAD <= cartesian_angle_rad <= MAX_BASE_ANGLE_RAD):
        return False, f"Working angle ({cartesian_angle_rad:.2f} rad) violates the front zone limits"
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
        

        
    return True, "Safe"
