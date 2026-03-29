import re
from dataclasses import dataclass
from typing import Dict, List, Optional

from django.conf import settings
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage

from .models import IngredientReference, Product

try:
    import pytesseract
except ImportError:  # pragma: no cover
    pytesseract = None

try:
    from PIL import Image
except ImportError:  # pragma: no cover
    Image = None


VEG_PROTEIN_SOURCES = [
    {'name': 'Paneer', 'protein': '18g per 100g', 'benefit': 'Rich vegetarian protein with calcium.'},
    {'name': 'Tofu', 'protein': '10g per 100g', 'benefit': 'Lean soy protein for bowls, wraps, and stir-fries.'},
    {'name': 'Lentils', 'protein': '9g per 100g cooked', 'benefit': 'Budget-friendly protein with fiber.'},
    {'name': 'Chickpeas', 'protein': '8.5g per 100g cooked', 'benefit': 'Works well in salads, chaat, and curries.'},
    {'name': 'Greek yogurt or curd', 'protein': '8 to 10g per 100g', 'benefit': 'Helpful for satiety and gut-friendly meals.'},
    {'name': 'Peanuts', 'protein': '25g per 100g', 'benefit': 'Good snack option when portion-controlled.'},
]

NON_VEG_PROTEIN_SOURCES = [
    {'name': 'Eggs', 'protein': '6g per egg', 'benefit': 'Easy high-quality protein for breakfast or snacks.'},
    {'name': 'Chicken breast', 'protein': '27g per 100g', 'benefit': 'Lean protein with low carbs.'},
    {'name': 'Fish', 'protein': '20 to 24g per 100g', 'benefit': 'Adds protein and healthy fats depending on the variety.'},
    {'name': 'Prawns', 'protein': '20g per 100g', 'benefit': 'High protein and relatively low calorie.'},
    {'name': 'Turkey', 'protein': '29g per 100g', 'benefit': 'Lean protein if available locally.'},
    {'name': 'Lean mutton cuts', 'protein': '25g per 100g', 'benefit': 'Good protein but best eaten in moderate portions.'},
]


@dataclass
class AnalysisResult:
    extracted_text: str
    ingredients: List[str]
    score: int
    classification: str
    harmful_found: List[Dict]
    moderate_found: List[Dict]
    safe_found: List[Dict]
    suggestions: List[str]
    nutrition_flags: List[str]


@dataclass
class WellnessPlan:
    weight_kg: float
    height_cm: float
    bmi: float
    bmi_status: str
    healthy_weight_min: float
    healthy_weight_max: float
    target_weight: float
    daily_calories: int
    protein_target_g: int
    summary: str
    meals: List[str]


class OCRService:
    @staticmethod
    def upload_to_cloud(image_file):
        provider = settings.CLOUD_STORAGE_PROVIDER.lower()
        file_name = default_storage.save(f'uploads/{image_file.name}', ContentFile(image_file.read()))
        image_file.seek(0)
        url = default_storage.url(file_name) if hasattr(default_storage, 'url') else file_name
        return {
            'provider': provider,
            'stored_path': file_name,
            'url': url,
        }

    @staticmethod
    def extract_text(image_path):
        provider = settings.OCR_PROVIDER.lower()
        if provider == 'google_vision':
            return OCRService._extract_with_google_vision(image_path)
        return OCRService._extract_with_tesseract(image_path)

    @staticmethod
    def _extract_with_tesseract(image_path):
        if not pytesseract or not Image:
            return ''
        try:
            return pytesseract.image_to_string(Image.open(image_path))
        except Exception:
            return ''

    @staticmethod
    def _extract_with_google_vision(image_path):
        try:
            from google.cloud import vision
        except ImportError:
            return OCRService._extract_with_tesseract(image_path)

        try:
            client = vision.ImageAnnotatorClient()
            with open(image_path, 'rb') as image_file:
                content = image_file.read()
            image = vision.Image(content=content)
            response = client.text_detection(image=image)
            if response.text_annotations:
                return response.text_annotations[0].description
        except Exception:
            return OCRService._extract_with_tesseract(image_path)
        return ''


class IngredientAnalyzer:
    DEFAULT_SUGGESTIONS = {
        'Safe': 'This product looks relatively safer than most packaged options in the current catalog. Keep an eye on portions and total daily calories.',
        'Moderate': 'This product is usable occasionally, but it would be smarter to balance it with higher-protein and less-processed meals during the rest of the day.',
        'Harmful': 'This product is heavily processed or nutritionally weak. It is better treated as an occasional food, not a daily staple.',
    }

    @staticmethod
    def normalize_ingredients(text):
        normalized = re.sub(r'ingredients?[:\-]', '', text, flags=re.IGNORECASE)
        normalized = re.sub(r'\([^)]*\)', '', normalized)
        raw_parts = re.split(r',|\n|;|\.|\u2022', normalized)
        cleaned = []
        for part in raw_parts:
            token = re.sub(r'[^a-zA-Z0-9\s]', ' ', part).strip().lower()
            token = re.sub(r'\s+', ' ', token)
            if token:
                cleaned.append(token)
        return cleaned

    @staticmethod
    def _reference_map():
        references = list(IngredientReference.objects.all())
        reference_map = {}
        for reference in references:
            keys = [reference.name.lower()]
            if reference.aliases:
                keys.extend([alias.strip().lower() for alias in reference.aliases.split(',') if alias.strip()])
            for key in keys:
                reference_map[key] = reference
        return reference_map

    @staticmethod
    def analyze(ingredient_text: str, product: Optional[Product] = None):
        ingredients = IngredientAnalyzer.normalize_ingredients(ingredient_text)
        reference_map = IngredientAnalyzer._reference_map()

        harmful_found = []
        moderate_found = []
        safe_found = []
        nutrition_flags = []
        score = 100

        for ingredient in ingredients:
            matched_reference = None
            for key, reference in reference_map.items():
                if key in ingredient:
                    matched_reference = reference
                    break
            if not matched_reference:
                continue

            item = {
                'name': matched_reference.name,
                'impact': matched_reference.score_impact,
                'description': matched_reference.description,
                'matched_text': ingredient,
            }
            score += matched_reference.score_impact
            if matched_reference.risk_level == IngredientReference.RISK_HARMFUL:
                harmful_found.append(item)
            elif matched_reference.risk_level == IngredientReference.RISK_MODERATE:
                moderate_found.append(item)
            else:
                safe_found.append(item)

        if product:
            if product.sugar_per_100g >= 20:
                score -= 10
                nutrition_flags.append(f'High sugar: {product.sugar_per_100g}g per 100g')
            elif product.sugar_per_100g >= 10:
                score -= 5
                nutrition_flags.append(f'Moderate sugar: {product.sugar_per_100g}g per 100g')

            if product.sodium_mg_per_100g >= 500:
                score -= 8
                nutrition_flags.append(f'High sodium: {product.sodium_mg_per_100g}mg per 100g')
            elif product.sodium_mg_per_100g >= 250:
                score -= 4
                nutrition_flags.append(f'Moderate sodium: {product.sodium_mg_per_100g}mg per 100g')

            if product.protein_per_100g >= 8:
                score += 4
                nutrition_flags.append(f'Helpful protein: {product.protein_per_100g}g per 100g')
            if product.fat_per_100g >= 20:
                score -= 6
                nutrition_flags.append(f'High fat: {product.fat_per_100g}g per 100g')

        score = max(0, min(100, score))
        if score >= 80:
            classification = 'Safe'
        elif score >= 50:
            classification = 'Moderate'
        else:
            classification = 'Harmful'

        suggestions = [IngredientAnalyzer.DEFAULT_SUGGESTIONS[classification]]
        if harmful_found:
            harmful_names = ', '.join(sorted({item['name'] for item in harmful_found}))
            suggestions.append(f'Watch out for: {harmful_names}.')
        if moderate_found and classification != 'Harmful':
            moderate_names = ', '.join(sorted({item['name'] for item in moderate_found}))
            suggestions.append(f'Moderate-risk ingredients detected: {moderate_names}.')
        if product and product.healthier_swap:
            suggestions.append(f'Better swap idea: {product.healthier_swap}.')

        return AnalysisResult(
            extracted_text=ingredient_text.strip(),
            ingredients=ingredients,
            score=score,
            classification=classification,
            harmful_found=harmful_found,
            moderate_found=moderate_found,
            safe_found=safe_found,
            suggestions=suggestions,
            nutrition_flags=nutrition_flags,
        )


class WellnessAdvisor:
    @staticmethod
    def build_plan(weight_kg: Optional[float], height_cm: Optional[float], diet_preference: str):
        if not weight_kg or not height_cm:
            return None

        height_m = height_cm / 100
        bmi = round(weight_kg / (height_m * height_m), 1)
        healthy_weight_min = round(18.5 * height_m * height_m, 1)
        healthy_weight_max = round(24.9 * height_m * height_m, 1)
        target_weight = round((healthy_weight_min + healthy_weight_max) / 2, 1)

        if bmi < 18.5:
            bmi_status = 'Underweight'
            calorie_base = target_weight * 33
            summary = 'You are below the healthy BMI range, so the plan favors steady nourishment with protein-rich meals and slightly higher calories.'
        elif bmi <= 24.9:
            bmi_status = 'Healthy range'
            calorie_base = weight_kg * 30
            summary = 'Your BMI is in the healthy range, so the plan focuses on maintenance calories, steady protein, and better food quality.'
        elif bmi <= 29.9:
            bmi_status = 'Overweight'
            calorie_base = target_weight * 28
            summary = 'You are above the healthy BMI range, so the plan recommends moderate calorie control and higher satiety foods.'
        else:
            bmi_status = 'Obesity range'
            calorie_base = target_weight * 26
            summary = 'You are well above the healthy BMI range, so the plan aims for structured calories, higher protein, and less ultra-processed food.'

        daily_calories = int(round(calorie_base / 50.0) * 50)
        protein_target_g = int(round(target_weight * 1.2))
        meals = WellnessAdvisor._meal_plan(daily_calories, diet_preference)

        return WellnessPlan(
            weight_kg=weight_kg,
            height_cm=height_cm,
            bmi=bmi,
            bmi_status=bmi_status,
            healthy_weight_min=healthy_weight_min,
            healthy_weight_max=healthy_weight_max,
            target_weight=target_weight,
            daily_calories=daily_calories,
            protein_target_g=protein_target_g,
            summary=summary,
            meals=meals,
        )

    @staticmethod
    def _meal_plan(calories: int, diet_preference: str):
        if calories <= 1700:
            breakfast = 'Breakfast: oats or vegetable poha with curd, plus one fruit.'
            lunch = 'Lunch: 2 chapatis, dal, sabzi, salad, and curd.'
            dinner = 'Dinner: paneer bhurji or grilled chicken with vegetables and one chapati.'
            snack = 'Snack: roasted chana, buttermilk, or boiled eggs.'
        elif calories <= 2200:
            breakfast = 'Breakfast: oats with milk and seeds, or omelette with toast and fruit.'
            lunch = 'Lunch: 2 to 3 chapatis, dal, sabzi, rice, and a protein side.'
            dinner = 'Dinner: paneer/tofu bowl or fish/chicken with vegetables and rice.'
            snack = 'Snack: sprouts chaat, nuts, yogurt, or peanut chikki in controlled portions.'
        else:
            breakfast = 'Breakfast: paneer sandwich or egg bhurji with toast, milk, and fruit.'
            lunch = 'Lunch: rice, chapati, dal, sabzi, and a strong protein serving.'
            dinner = 'Dinner: chicken/fish curry or soy/paneer curry with vegetables and carbs.'
            snack = 'Snack: banana with peanut butter, lassi, trail mix, or boiled chana.'

        if diet_preference == 'vegetarian':
            dinner = dinner.replace('fish/chicken', 'soy chunks').replace('chicken/fish curry', 'rajma or paneer curry')
            snack = 'Snack: sprouts chaat, yogurt, peanuts, roasted makhana, or boiled chana.'
        elif diet_preference == 'non_vegetarian':
            breakfast = breakfast.replace('oats with milk and seeds, or omelette with toast and fruit', 'omelette with toast and fruit, or oats plus boiled eggs')
            lunch = lunch.replace('a protein side', 'eggs, chicken, or fish')

        return [breakfast, lunch, dinner, snack]


def protein_sources():
    return {
        'veg': VEG_PROTEIN_SOURCES,
        'non_veg': NON_VEG_PROTEIN_SOURCES,
    }


def cloud_summary():
    provider = settings.CLOUD_STORAGE_PROVIDER.lower()
    ocr_provider = settings.OCR_PROVIDER.lower()
    storage_label = {
        'firebase': 'Firebase Storage',
        'aws_s3': 'AWS S3',
        'local': 'Local media storage',
    }.get(provider, provider.title())
    ocr_label = {
        'google_vision': 'Google Vision API',
        'tesseract': 'Tesseract OCR',
    }.get(ocr_provider, ocr_provider.title())
    return {
        'storage': storage_label,
        'ocr': ocr_label,
        'storage_provider': provider,
        'ocr_provider': ocr_provider,
    }
