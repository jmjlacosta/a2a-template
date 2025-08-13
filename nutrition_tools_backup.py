"""
Nutrition analysis tools for the LLM-based A2A agent.
These tools provide the agent with access to the Nutritionix API and nutrition analysis capabilities.
"""

import os
import json
import httpx
import logging
from typing import Dict, Any, List, Optional
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

class NutritionixClient:
    """Client for interacting with the Nutritionix API."""
    
    def __init__(self):
        self.api_key = os.getenv("NUTRITIONIX_API_KEY")
        self.app_id = os.getenv("NUTRITIONIX_APP_ID", "039db79f")
        self.base_url = "https://trackapi.nutritionix.com/v2"
        self.client = httpx.AsyncClient()
        
        logger.info(f"NutritionixClient initialized with app_id: {self.app_id}")
        
    async def get_nutrition_data(self, query: str) -> Dict[str, Any]:
        """Get nutrition data from Nutritionix API."""
        if not self.api_key:
            logger.warning("No Nutritionix API key available, using mock data")
            return self._get_mock_data(query)
            
        try:
            headers = {
                "x-app-id": self.app_id,
                "x-app-key": self.api_key,
                "Content-Type": "application/json",
            }
            
            payload = {"query": query, "timezone": "US/Eastern"}
            logger.info(f"Making Nutritionix API request for: {query}")
            
            response = await self.client.post(
                f"{self.base_url}/natural/nutrients",
                json=payload,
                headers=headers,
                timeout=10.0,
            )
            
            if response.status_code == 200:
                data = response.json()
                logger.info(f"Successfully retrieved nutrition data for {len(data.get('foods', []))} items")
                return data
            elif response.status_code == 401:
                logger.warning("API authentication failed, falling back to mock data")
                return self._get_mock_data(query)
            else:
                logger.error(f"API request failed with status {response.status_code}")
                return self._get_mock_data(query)
                
        except Exception as e:
            logger.error(f"Exception during API request: {str(e)}")
            return self._get_mock_data(query)
    
    def _get_mock_data(self, query: str) -> Dict[str, Any]:
        """Return mock nutrition data for demonstration."""
        mock_foods = {
            "apple": {
                "food_name": "Apple, raw",
                "serving_qty": 1, "serving_unit": "medium",
                "nf_calories": 95, "nf_total_fat": 0.3, "nf_saturated_fat": 0.1,
                "nf_cholesterol": 0, "nf_sodium": 2, "nf_total_carbohydrate": 25,
                "nf_dietary_fiber": 4, "nf_sugars": 19, "nf_protein": 0.5,
            },
            "rice": {
                "food_name": "Rice, white, cooked",
                "serving_qty": 1, "serving_unit": "cup",
                "nf_calories": 205, "nf_total_fat": 0.4, "nf_saturated_fat": 0.1,
                "nf_cholesterol": 0, "nf_sodium": 2, "nf_total_carbohydrate": 45,
                "nf_dietary_fiber": 0.6, "nf_sugars": 0.1, "nf_protein": 4.3,
            },
            "chicken": {
                "food_name": "Chicken breast, grilled",
                "serving_qty": 100, "serving_unit": "g",
                "nf_calories": 165, "nf_total_fat": 3.6, "nf_saturated_fat": 1.0,
                "nf_cholesterol": 85, "nf_sodium": 74, "nf_total_carbohydrate": 0,
                "nf_dietary_fiber": 0, "nf_sugars": 0, "nf_protein": 31,
            }
        }
        
        query_lower = query.lower()
        for keyword, food_data in mock_foods.items():
            if keyword in query_lower:
                return {"foods": [food_data]}
        
        # Default generic food
        return {
            "foods": [{
                "food_name": f"Food item: {query}",
                "serving_qty": 1, "serving_unit": "serving",
                "nf_calories": 100, "nf_total_fat": 2.0, "nf_saturated_fat": 0.5,
                "nf_cholesterol": 0, "nf_sodium": 50, "nf_total_carbohydrate": 20,
                "nf_dietary_fiber": 2, "nf_sugars": 5, "nf_protein": 3,
            }]
        }

# Global nutritionix client instance
nutritionix_client = NutritionixClient()

async def analyze_nutrition(
    food_query: str,
    serving_size: Optional[str] = None
) -> Dict[str, Any]:
    """
    Analyze the nutritional content of food items.
    
    Args:
        food_query: Natural language description of the food (e.g., "1 cup rice", "large apple")
        serving_size: Optional specific serving size if not included in food_query
        
    Returns:
        Dictionary containing nutritional information including calories, macros, and micronutrients
    """
    logger.info(f"Analyzing nutrition for: {food_query}")
    
    # Combine query with serving size if provided separately
    full_query = food_query
    if serving_size and serving_size not in food_query.lower():
        full_query = f"{serving_size} {food_query}"
    
    try:
        nutrition_data = await nutritionix_client.get_nutrition_data(full_query)
        
        foods = nutrition_data.get("foods", [])
        if not foods:
            return {
                "status": "error",
                "message": f"No nutrition information found for '{food_query}'"
            }
        
        # Format the nutrition data for the LLM
        formatted_results = []
        for food in foods:
            formatted_food = {
                "food_name": food.get("food_name", "Unknown"),
                "serving_qty": food.get("serving_qty", 1),
                "serving_unit": food.get("serving_unit", "serving"),
                "calories": round(food.get("nf_calories", 0), 1),
                "macronutrients": {
                    "protein": round(food.get("nf_protein", 0), 1),
                    "total_carbohydrates": round(food.get("nf_total_carbohydrate", 0), 1),
                    "dietary_fiber": round(food.get("nf_dietary_fiber", 0), 1),
                    "sugars": round(food.get("nf_sugars", 0), 1),
                    "total_fat": round(food.get("nf_total_fat", 0), 1),
                    "saturated_fat": round(food.get("nf_saturated_fat", 0), 1),
                },
                "micronutrients": {
                    "sodium": round(food.get("nf_sodium", 0), 1),
                    "cholesterol": round(food.get("nf_cholesterol", 0), 1),
                    "potassium": round(food.get("nf_potassium", 0), 1),
                }
            }
            formatted_results.append(formatted_food)
        
        return {
            "status": "success",
            "query": full_query,
            "foods": formatted_results,
            "total_items": len(formatted_results)
        }
        
    except Exception as e:
        logger.error(f"Error analyzing nutrition: {str(e)}")
        return {
            "status": "error",
            "message": f"Failed to analyze nutrition for '{food_query}': {str(e)}"
        }

async def calculate_meal_totals(
    food_items: List[str],
    serving_sizes: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    Calculate total nutritional values for a complete meal.
    
    Args:
        food_items: List of food descriptions
        serving_sizes: Optional list of serving sizes corresponding to food_items
        
    Returns:
        Dictionary with total nutritional values for the entire meal
    """
    logger.info(f"Calculating meal totals for {len(food_items)} items")
    
    if serving_sizes and len(serving_sizes) != len(food_items):
        return {
            "status": "error",
            "message": "Number of serving sizes must match number of food items"
        }
    
    meal_totals = {
        "calories": 0,
        "protein": 0,
        "total_carbohydrates": 0,
        "dietary_fiber": 0,
        "sugars": 0,
        "total_fat": 0,
        "saturated_fat": 0,
        "sodium": 0,
        "cholesterol": 0,
        "potassium": 0,
    }
    
    analyzed_foods = []
    
    try:
        for i, food_item in enumerate(food_items):
            serving_size = serving_sizes[i] if serving_sizes else None
            
            result = await analyze_nutrition(food_item, serving_size)
            
            if result["status"] == "success":
                for food in result["foods"]:
                    analyzed_foods.append(food)
                    
                    # Add to totals
                    meal_totals["calories"] += food["calories"]
                    for macro, value in food["macronutrients"].items():
                        if macro in meal_totals:
                            meal_totals[macro] += value
                    for micro, value in food["micronutrients"].items():
                        if micro in meal_totals:
                            meal_totals[micro] += value
        
        # Round all totals
        for key in meal_totals:
            meal_totals[key] = round(meal_totals[key], 1)
        
        return {
            "status": "success",
            "meal_totals": meal_totals,
            "individual_foods": analyzed_foods,
            "total_items": len(analyzed_foods)
        }
        
    except Exception as e:
        logger.error(f"Error calculating meal totals: {str(e)}")
        return {
            "status": "error",
            "message": f"Failed to calculate meal totals: {str(e)}"
        }

async def get_nutrition_recommendations(
    current_nutrition: Dict[str, float],
    user_goals: Optional[str] = None,
    dietary_restrictions: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    Provide nutrition recommendations based on current intake and goals.
    
    Args:
        current_nutrition: Dictionary with current nutritional values
        user_goals: Optional user goals (e.g., "weight loss", "muscle gain", "general health")
        dietary_restrictions: Optional list of dietary restrictions
        
    Returns:
        Dictionary with personalized nutrition recommendations
    """
    logger.info("Generating nutrition recommendations")
    
    try:
        # Basic daily value percentages (approximate for 2000 calorie diet)
        daily_values = {
            "calories": 2000,
            "protein": 50,
            "total_carbohydrates": 300,
            "dietary_fiber": 25,
            "total_fat": 65,
            "saturated_fat": 20,
            "sodium": 2300,
            "cholesterol": 300,
        }
        
        recommendations = []
        percentages = {}
        
        for nutrient, current_value in current_nutrition.items():
            if nutrient in daily_values:
                dv = daily_values[nutrient]
                percentage = (current_value / dv) * 100
                percentages[nutrient] = round(percentage, 1)
                
                # Generate recommendations based on percentage
                if percentage < 25:
                    recommendations.append(f"Consider increasing {nutrient.replace('_', ' ')} intake")
                elif percentage > 100:
                    recommendations.append(f"Consider reducing {nutrient.replace('_', ' ')} intake")
        
        return {
            "status": "success",
            "daily_value_percentages": percentages,
            "recommendations": recommendations,
            "user_goals": user_goals,
            "dietary_restrictions": dietary_restrictions
        }
        
    except Exception as e:
        logger.error(f"Error generating recommendations: {str(e)}")
        return {
            "status": "error",
            "message": f"Failed to generate recommendations: {str(e)}"
        }