"""Body composition calculation utilities for FitAI.

These are formula-based estimates, not actual DEXA scan results.
"""

import math
from decimal import Decimal, ROUND_HALF_UP


def round_decimal(value, places=2):
    """Round values safely."""
    return Decimal(str(value)).quantize(
        Decimal("1." + ("0" * places)),
        rounding=ROUND_HALF_UP
    )


def is_valid_number(value):
    """Check whether a value is a valid finite number."""

    try:
        return value is not None and math.isfinite(float(value))
    except (ValueError, TypeError):
        return False


def calculate_bmi(weight_kg, height_cm):
    """BMI = weight (kg) / height (m)^2."""

    if not is_valid_number(weight_kg) or not is_valid_number(height_cm):
        return None

    weight_kg = float(weight_kg)
    height_cm = float(height_cm)

    if weight_kg <= 0 or height_cm <= 0:
        return None

    height_m = height_cm / 100

    return weight_kg / (height_m ** 2)


def calculate_body_fat_navy(
    sex,
    height_cm,
    neck_cm,
    waist_cm,
    hip_cm=None
):
    """
    Estimate body-fat percentage using the US Navy circumference method.

    Measurements are in centimeters.

    This is an estimate, NOT a DEXA measurement.
    """

    try:
        if not all(
            is_valid_number(value)
            for value in [height_cm, neck_cm, waist_cm]
        ):
            return None

        height_cm = float(height_cm)
        neck_cm = float(neck_cm)
        waist_cm = float(waist_cm)

        if min(height_cm, neck_cm, waist_cm) <= 0:
            return None

        sex = str(sex).upper()

        if sex == "M":

            measurement = waist_cm - neck_cm

            if measurement <= 0:
                return None

            body_fat = (
                495 / (
                    1.0324
                    - 0.19077 * math.log10(measurement)
                    + 0.15456 * math.log10(height_cm)
                )
            ) - 450

        elif sex == "F":

            if not is_valid_number(hip_cm):
                return None

            hip_cm = float(hip_cm)

            if hip_cm <= 0:
                return None

            measurement = waist_cm + hip_cm - neck_cm

            if measurement <= 0:
                return None

            body_fat = (
                495 / (
                    1.29579
                    - 0.35004 * math.log10(measurement)
                    + 0.22100 * math.log10(height_cm)
                )
            ) - 450

        else:
            return None

        if not math.isfinite(body_fat):
            return None

        if body_fat < 2 or body_fat > 75:
            return None

        return body_fat

    except (ValueError, TypeError, ZeroDivisionError):
        return None


def calculate_fat_mass(weight_kg, body_fat_percent):
    """Estimated fat mass in kilograms."""

    if not is_valid_number(weight_kg):
        return None

    if not is_valid_number(body_fat_percent):
        return None

    weight_kg = float(weight_kg)
    body_fat_percent = float(body_fat_percent)

    if weight_kg <= 0 or not 0 <= body_fat_percent <= 100:
        return None

    return weight_kg * body_fat_percent / 100


def calculate_lean_body_mass(weight_kg, body_fat_percent):
    """Estimated lean body mass in kilograms."""

    fat_mass = calculate_fat_mass(
        weight_kg,
        body_fat_percent
    )

    if fat_mass is None:
        return None

    return float(weight_kg) - fat_mass


def calculate_waist_to_height_ratio(waist_cm, height_cm):
    """Waist-to-height ratio."""

    if not is_valid_number(waist_cm) or not is_valid_number(height_cm):
        return None

    waist_cm = float(waist_cm)
    height_cm = float(height_cm)

    if waist_cm <= 0 or height_cm <= 0:
        return None

    return waist_cm / height_cm


def calculate_bmr_mifflin(
    sex,
    weight_kg,
    height_cm,
    age
):
    """Estimated BMR using the Mifflin-St Jeor equation."""

    if not all(
        is_valid_number(value)
        for value in [weight_kg, height_cm, age]
    ):
        return None

    weight_kg = float(weight_kg)
    height_cm = float(height_cm)
    age = float(age)

    if weight_kg <= 0 or height_cm <= 0 or age <= 0:
        return None

    sex = str(sex).upper()

    if sex == "M":
        return (
            10 * weight_kg
            + 6.25 * height_cm
            - 5 * age
            + 5
        )

    elif sex == "F":
        return (
            10 * weight_kg
            + 6.25 * height_cm
            - 5 * age
            - 161
        )

    return None


def calculate_waist_risk(waist_to_height_ratio):
    """
    General waist-to-height screening indicator.

    This is NOT a measurement of visceral fat.
    """

    if not is_valid_number(waist_to_height_ratio):
        return None

    ratio = float(waist_to_height_ratio)

    if ratio <= 0:
        return None

    if ratio < 0.40:
        return "Low"

    elif ratio < 0.50:
        return "Generally lower risk"

    elif ratio < 0.60:
        return "Increased risk"

    else:
        return "High risk"


def compute_body_composition(record):
    """
    Calculate body composition estimates from a record.

    Missing or invalid information is handled safely.
    """

    height = record.height_cm
    weight = record.weight_kg
    waist = record.waist_cm
    neck = record.neck_cm
    hip = record.hip_cm
    sex = record.sex
    age = record.age

    # BMI
    bmi = calculate_bmi(weight, height)

    # Estimated body-fat percentage
    body_fat = calculate_body_fat_navy(
        sex=sex,
        height_cm=height,
        neck_cm=neck,
        waist_cm=waist,
        hip_cm=hip
    )

    # Estimated fat mass
    fat_mass = calculate_fat_mass(
        weight,
        body_fat
    )

    # Estimated lean body mass
    lean_mass = calculate_lean_body_mass(
        weight,
        body_fat
    )

    # Waist-to-height ratio
    waist_to_height = calculate_waist_to_height_ratio(
        waist,
        height
    )

    # Estimated BMR
    bmr = calculate_bmr_mifflin(
        sex,
        weight,
        height,
        age
    )

    # Waist screening indicator
    waist_risk = calculate_waist_risk(
        waist_to_height
    )

    return {
        "bmi": round(bmi, 2) if bmi is not None else None,

        "body_fat_percent": (
            round(body_fat, 2)
            if body_fat is not None else None
        ),

        "fat_mass_kg": (
            round(fat_mass, 2)
            if fat_mass is not None else None
        ),

        "lean_body_mass_kg": (
            round(lean_mass, 2)
            if lean_mass is not None else None
        ),

        "waist_to_height_ratio": (
            round(waist_to_height, 3)
            if waist_to_height is not None else None
        ),

        "visceral_fat_risk": waist_risk,

        "bmr": (
            round(bmr, 2)
            if bmr is not None else None
        ),
    }