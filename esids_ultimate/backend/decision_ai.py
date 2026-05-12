"""
ESIDS Decision AI — Multi-signal decision engine with avoidance planning
"""
import math
import numpy as np


def evaluate_scenario(delay, congestion, risk_high, anomaly_pct, oti, blackout=False):
    """
    Evaluate current system state and recommend actions
    
    Args:
        delay: Current Mars delay (minutes)
        congestion: LEO congestion percentage
        risk_high: Number of high-risk conjunctions
        anomaly_pct: Percentage of anomalies detected
        oti: Operational Threat Index
        blackout: Whether in communication blackout
    
    Returns:
        dict with severity, confidence, rationale, recommendations
    """
    
    # Severity scoring
    severity_score = 0
    factors = []
    
    # 1. Delay assessment (blackout is warning, not critical)
    if blackout:
        severity_score += 30
        factors.append("Communication blackout detected")
    elif delay > 22:
        severity_score += 25
        factors.append(f"High delay: {delay:.2f} min")
    elif delay > 15:
        severity_score += 15
        factors.append(f"Elevated delay: {delay:.2f} min")
    
    # 2. Congestion assessment
    if congestion > 60:
        severity_score += 30
        factors.append(f"Severe congestion: {congestion:.1f}%")
    elif congestion > 40:
        severity_score += 20
        factors.append(f"High congestion: {congestion:.1f}%")
    
    # 3. Risk assessment
    if risk_high > 50:
        severity_score += 35
        factors.append(f"Critical conjunctions: {risk_high}")
    elif risk_high > 20:
        severity_score += 25
        factors.append(f"High-risk events: {risk_high}")
    elif risk_high > 5:
        severity_score += 10
        factors.append(f"Elevated risk: {risk_high} events")
    
    # 4. Anomaly assessment
    if anomaly_pct > 0.05:
        severity_score += 20
        factors.append(f"Anomaly rate: {anomaly_pct*100:.1f}%")
    elif anomaly_pct > 0.02:
        severity_score += 10
        factors.append(f"Minor anomalies: {anomaly_pct*100:.1f}%")
    
    # 5. OTI assessment
    if oti > 75:
        severity_score += 20
        factors.append(f"OTI critical: {oti:.1f}")
    elif oti > 60:
        severity_score += 10
        factors.append(f"OTI elevated: {oti:.1f}")
    
    # Determine severity level
    if severity_score >= 80:
        severity = "CRITICAL"
        confidence = 0.90
    elif severity_score >= 50:
        severity = "WARNING"
        confidence = 0.85
    elif severity_score >= 25:
        severity = "ADVISORY"
        confidence = 0.80
    else:
        severity = "NOMINAL"
        confidence = 0.95
    
    # Adjust confidence based on data quality
    confidence *= (1 - anomaly_pct * 2)  # Anomalies reduce confidence
    confidence = max(0.5, min(0.95, confidence))
    
    # Generate recommendations
    recommendations = []
    
    if severity == "CRITICAL":
        recommendations.extend([
            "Activate emergency protocols",
            "Alert mission control immediately",
            "Prepare collision avoidance maneuvers",
            "Increase monitoring frequency to real-time",
        ])
    elif severity == "WARNING":
        recommendations.extend([
            "Increase monitoring frequency",
            "Review high-risk conjunction forecasts",
            "Prepare contingency plans",
            "Alert relevant stakeholders",
        ])
    elif severity == "ADVISORY":
        recommendations.extend([
            "Continue standard monitoring",
            "Review trajectory predictions",
            "Monitor developing situations",
        ])
    else:
        recommendations.extend([
            "Maintain nominal operations",
            "Continue routine monitoring",
        ])
    
    # Specific recommendations based on factors
    if blackout:
        recommendations.append("Switch to alternative communication channels")
    
    if risk_high > 20:
        recommendations.append("Execute collision avoidance maneuvers for top-risk events")
    
    if congestion > 50:
        recommendations.append("Consider orbital slot de-confliction")
    
    # Build rationale
    rationale = " | ".join(factors) if factors else "All systems nominal"
    
    return {
        "severity": severity,
        "confidence": round(confidence, 3),
        "severity_score": severity_score,
        "rationale": rationale,
        "recommendations": recommendations[:5],  # Max 5 recommendations
        "factors": factors,
    }


def plan_hohmann_transfer(current_alt_km, target_alt_km, mass_kg=1000):
    """
    Plan Hohmann transfer orbit for collision avoidance
    
    Args:
        current_alt_km: Current orbital altitude (km)
        target_alt_km: Target altitude for avoidance (km)
        mass_kg: Satellite mass (kg)
    
    Returns:
        dict with delta-v requirements, burn times, transfer duration
    """
    GM = 398600.4418  # km³/s²
    RE = 6371.0  # km
    
    # Orbital radii
    r1 = RE + current_alt_km
    r2 = RE + target_alt_km
    
    # Current circular velocity
    v_circular = math.sqrt(GM / r1)
    
    # Transfer orbit semi-major axis
    a_transfer = (r1 + r2) / 2
    
    # Delta-v calculations
    # First burn (raise apogee)
    v_transfer_perigee = math.sqrt(GM * (2/r1 - 1/a_transfer))
    delta_v1 = abs(v_transfer_perigee - v_circular)
    
    # Second burn (circularize at apogee)
    v_transfer_apogee = math.sqrt(GM * (2/r2 - 1/a_transfer))
    v_circular_target = math.sqrt(GM / r2)
    delta_v2 = abs(v_circular_target - v_transfer_apogee)
    
    # Total delta-v
    total_delta_v = delta_v1 + delta_v2
    
    # Transfer time (half orbital period of transfer orbit)
    transfer_period = 2 * math.pi * math.sqrt(a_transfer**3 / GM)
    transfer_time_sec = transfer_period / 2
    
    # Propellant requirements (Tsiolkovsky rocket equation)
    # Assuming Isp = 300s (typical for electric propulsion)
    g0 = 9.81 / 1000  # km/s²
    Isp = 300  # seconds
    ve = Isp * g0  # Exhaust velocity
    
    # Delta-m = m * (1 - exp(-delta_v / ve))
    propellant_mass_kg = mass_kg * (1 - math.exp(-total_delta_v / ve))
    
    return {
        "current_altitude_km": current_alt_km,
        "target_altitude_km": target_alt_km,
        "delta_v_burn1_kms": round(delta_v1, 4),
        "delta_v_burn2_kms": round(delta_v2, 4),
        "total_delta_v_kms": round(total_delta_v, 4),
        "transfer_time_sec": int(transfer_time_sec),
        "transfer_time_min": round(transfer_time_sec / 60, 2),
        "propellant_required_kg": round(propellant_mass_kg, 2),
        "propellant_percent": round(100 * propellant_mass_kg / mass_kg, 2),
    }


def compute_predicted_miss_distance(current_miss_km, delta_v_kms, time_to_ca_sec):
    """
    Estimate new miss distance after avoidance maneuver
    
    Args:
        current_miss_km: Current predicted miss distance
        delta_v_kms: Delta-v of avoidance maneuver
        time_to_ca_sec: Time to closest approach
    
    Returns:
        Predicted new miss distance (km)
    """
    # Simplified: miss distance increases proportional to delta-v and time
    # More accurate models would use full orbital mechanics
    
    # Assume delta-v applied perpendicular to relative velocity vector
    # Position change ≈ delta_v * time
    delta_position = delta_v_kms * time_to_ca_sec
    
    # New miss distance (Pythagorean sum)
    new_miss_km = math.sqrt(current_miss_km**2 + delta_position**2)
    
    return round(new_miss_km, 3)
