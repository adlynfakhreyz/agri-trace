from datetime import timedelta
from django.utils import timezone

class HarvestPredictionSystem:
    """
    Rule-based system for predicting harvest dates based on crop type,
    planting date, maintenance activities, and environmental conditions.
    """
    
    # Base growing periods in days for different crops
    BASE_GROWING_PERIODS = {
        'corn': 90,      # Corn/Jagung
        'rice': 120,     # Rice/Padi
        'tomato': 80,    # Tomato/Tomat
        'potato': 100,   # Potato/Kentang
        'cabbage': 70,   # Cabbage/Kubis
        'carrot': 75,    # Carrot/Wortel
        'chili': 90,     # Chili/Cabai
        'onion': 100,    # Onion/Bawang
        'soybean': 100,  # Soybean/Kedelai
        'peanut': 120,   # Peanut/Kacang tanah
        'cassava': 300,  # Cassava/Singkong
        'coffee': 270,   # Coffee/Kopi
        'cacao': 180,    # Cacao/Kakao
        'banana': 300,   # Banana/Pisang
        'sugarcane': 300, # Sugarcane/Tebu
    }
    
    # Default growing period for crops not in the list
    DEFAULT_GROWING_PERIOD = 100
    
    @classmethod
    def predict_harvest_date(cls, crop, farm_condition=None):
        """
        Predicts the harvest date for a crop based on its type, planting date,
        maintenance activities, and farm conditions.
        
        Args:
            crop: The Crop model instance
            farm_condition: Optional FarmCondition model instance
            
        Returns:
            Predicted harvest date as a datetime.date object
        """
        if not crop or not crop.planting_date:
            return None
        
        # Start with the base growing period for this crop type
        crop_type_lower = crop.crop_type.lower()
        
        # Find the closest match in our base growing periods
        base_days = cls.DEFAULT_GROWING_PERIOD
        for known_crop, days in cls.BASE_GROWING_PERIODS.items():
            if known_crop in crop_type_lower or crop_type_lower in known_crop:
                base_days = days
                break
        
        # Adjustments based on maintenance activities
        maintenance_modifier = cls._calculate_maintenance_effect(crop)
        
        # Adjustments based on environmental factors
        environment_modifier = cls._calculate_environment_effect(crop, farm_condition)
        
        # Calculate the total growing period with all modifiers
        total_days = base_days + maintenance_modifier + environment_modifier
        
        # Calculate predicted harvest date
        predicted_date = crop.planting_date + timedelta(days=total_days)
        
        return predicted_date
    
    @classmethod
    def _calculate_maintenance_effect(cls, crop):
        """
        Calculate the effect of maintenance activities on growing period.
        Frequent and proper maintenance should reduce growing time.
        
        Returns: Adjustment in days (negative means faster growth)
        """
        days_adjustment = 0
        
        # Get all maintenance activities for this crop
        maintenance_activities = crop.maintenance_activities.all()
        
        if not maintenance_activities.exists():
            # No maintenance might extend growing period
            return 15
        
        # Calculate fertilizer effect
        total_fertilizer = sum(m.fertilizer_applied or 0 for m in maintenance_activities)
        if total_fertilizer > 0:
            fertilizer_per_activity = total_fertilizer / maintenance_activities.count()
            # Good fertilization (neither too little nor too much) speeds up growth
            if 0 < fertilizer_per_activity <= 5:
                days_adjustment -= 5
            elif 5 < fertilizer_per_activity <= 15:
                days_adjustment -= 10
            elif fertilizer_per_activity > 15:
                # Too much fertilizer might slow growth
                days_adjustment += 5
        
        # Calculate irrigation effect
        total_irrigation = sum(m.irrigation_amount or 0 for m in maintenance_activities)
        if total_irrigation > 0:
            irrigation_per_activity = total_irrigation / maintenance_activities.count()
            # Proper irrigation speeds up growth
            if 0 < irrigation_per_activity <= 100:
                days_adjustment -= 3
            elif 100 < irrigation_per_activity <= 500:
                days_adjustment -= 7
            elif irrigation_per_activity > 500:
                # Too much water might slow growth or cause disease
                days_adjustment += 10
        
        # Calculate pesticide effect (prevents disease, can speed up growth)
        total_pesticide = sum(m.pesticide_applied or 0 for m in maintenance_activities)
        if total_pesticide > 0:
            pesticide_per_activity = total_pesticide / maintenance_activities.count()
            if 0 < pesticide_per_activity <= 3:
                days_adjustment -= 3
            # Too much pesticide might stress plants
            elif pesticide_per_activity > 3:
                days_adjustment += 2
        
        # Overall maintenance frequency effect
        days_since_planting = (timezone.now().date() - crop.planting_date).days
        if days_since_planting > 0:
            maintenance_frequency = maintenance_activities.count() / days_since_planting * 30  # activities per month
            
            if maintenance_frequency < 1:
                # Infrequent maintenance extends growing period
                days_adjustment += 10
            elif 1 <= maintenance_frequency < 4:
                # Regular maintenance speeds up growth slightly
                days_adjustment -= 5
            else:
                # Very frequent maintenance leads to optimal growth
                days_adjustment -= 8
        
        return days_adjustment
    
    @classmethod
    def _calculate_environment_effect(cls, crop, farm_condition):
        """
        Calculate the effect of environmental conditions on growing period.
        Optimal conditions speed up growth, poor conditions slow it down.
        
        Returns: Adjustment in days
        """
        if not farm_condition:
            return 0
        
        days_adjustment = 0
        crop_type_lower = crop.crop_type.lower()
        
        # Temperature effects
        if farm_condition.max_daily_temp is not None:
            temp = farm_condition.max_daily_temp
            
            # Different crops have different optimal temperature ranges
            if ('rice' in crop_type_lower) or ('padi' in crop_type_lower):
                # Rice prefers warmer temperatures (25-30°C)
                if 25 <= temp <= 30:
                    days_adjustment -= 10
                elif 20 <= temp < 25 or 30 < temp <= 35:
                    days_adjustment -= 5
                elif temp > 35:
                    days_adjustment += 15  # Too hot slows growth significantly
            
            elif ('corn' in crop_type_lower) or ('jagung' in crop_type_lower):
                # Corn grows well in 20-30°C
                if 20 <= temp <= 30:
                    days_adjustment -= 8
                elif 15 <= temp < 20 or 30 < temp <= 32:
                    days_adjustment -= 3
                elif temp > 32:
                    days_adjustment += 10
            
            # General temperature effects for other crops
            else:
                if 18 <= temp <= 28:  # Optimal temperature range for most crops
                    days_adjustment -= 7
                elif 15 <= temp < 18 or 28 < temp <= 32:
                    days_adjustment -= 3
                elif temp > 32 or temp < 15:
                    days_adjustment += 10
        
        # Soil pH effects
        if farm_condition.soil_ph is not None:
            ph = farm_condition.soil_ph
            
            # Most crops grow best in slightly acidic to neutral soil (6.0-7.0)
            if 6.0 <= ph <= 7.0:
                days_adjustment -= 5
            elif 5.5 <= ph < 6.0 or 7.0 < ph <= 7.5:
                days_adjustment -= 2
            else:
                # Very acidic or alkaline soil slows growth
                days_adjustment += 8
        
        # Soil moisture effects
        if farm_condition.soil_moisture is not None:
            moisture = farm_condition.soil_moisture
            
            # Optimal soil moisture is typically 50-70%
            if 50 <= moisture <= 70:
                days_adjustment -= 7
            elif 40 <= moisture < 50 or 70 < moisture <= 80:
                days_adjustment -= 3
            elif moisture < 20:  # Too dry
                days_adjustment += 15
            elif moisture > 90:  # Waterlogged
                days_adjustment += 20
        
        # Rainfall effects
        if farm_condition.rainfall is not None:
            rainfall = farm_condition.rainfall
            
            # Moderate rainfall is beneficial
            if 100 <= rainfall <= 200:
                days_adjustment -= 5
            elif 50 <= rainfall < 100 or 200 < rainfall <= 300:
                days_adjustment -= 2
            elif rainfall > 400:  # Excessive rain
                days_adjustment += 10
        
        # Day length effects
        if farm_condition.day_length is not None:
            day_length = farm_condition.day_length
            
            # Many crops grow best with 10-14 hours of light
            if 10 <= day_length <= 14:
                days_adjustment -= 5
            elif 8 <= day_length < 10 or 14 < day_length <= 16:
                days_adjustment -= 2
            else:
                days_adjustment += 3
        
        return days_adjustment
    
    @classmethod
    def get_confidence_level(cls, crop, farm_condition=None):
        """
        Calculate a confidence level for the prediction based on data completeness.
        
        Returns: Confidence level as a percentage (0-100)
        """
        confidence = 60  # Base confidence
        
        # Having complete farm condition data increases confidence
        if farm_condition:
            if farm_condition.soil_ph is not None:
                confidence += 5
            if farm_condition.soil_moisture is not None:
                confidence += 5
            if farm_condition.rainfall is not None:
                confidence += 5
            if farm_condition.max_daily_temp is not None:
                confidence += 5
            if farm_condition.day_length is not None:
                confidence += 5
        
        # Having maintenance activities increases confidence
        maintenance_count = crop.maintenance_activities.count()
        if maintenance_count > 0:
            confidence += min(15, maintenance_count * 3)  # Up to 15% for maintenance records
        
        # Check if crop type is in our database
        crop_type_lower = crop.crop_type.lower()
        crop_type_known = any(known_crop in crop_type_lower or crop_type_lower in known_crop 
                            for known_crop in cls.BASE_GROWING_PERIODS.keys())
        if crop_type_known:
            confidence += 10
        
        # Cap at 100%
        return min(confidence, 100)