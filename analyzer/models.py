from django.conf import settings
from django.db import models


class IngredientReference(models.Model):
    RISK_SAFE = 'safe'
    RISK_MODERATE = 'moderate'
    RISK_HARMFUL = 'harmful'
    RISK_CHOICES = [
        (RISK_SAFE, 'Safe'),
        (RISK_MODERATE, 'Moderate'),
        (RISK_HARMFUL, 'Harmful'),
    ]

    name = models.CharField(max_length=120, unique=True)
    aliases = models.CharField(max_length=255, blank=True, help_text='Comma-separated aliases.')
    risk_level = models.CharField(max_length=20, choices=RISK_CHOICES)
    score_impact = models.IntegerField(default=0)
    description = models.TextField(blank=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class Product(models.Model):
    name = models.CharField(max_length=120, unique=True)
    brand = models.CharField(max_length=120, blank=True)
    ingredient_text = models.TextField()
    category = models.CharField(max_length=120, blank=True)
    image = models.ImageField(upload_to='products/', blank=True, null=True)
    image_url = models.CharField(max_length=255, blank=True)
    short_description = models.TextField(blank=True)
    consumer_watchouts = models.TextField(blank=True)
    healthier_swap = models.CharField(max_length=255, blank=True)
    source_url = models.URLField(blank=True)
    public_health_reference = models.URLField(blank=True)
    calories_per_100g = models.FloatField(default=0)
    sugar_per_100g = models.FloatField(default=0)
    protein_per_100g = models.FloatField(default=0)
    fat_per_100g = models.FloatField(default=0)
    sodium_mg_per_100g = models.FloatField(default=0)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class UserWellnessProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='wellness_profile')
    weight_kg = models.FloatField(null=True, blank=True)
    height_cm = models.FloatField(null=True, blank=True)
    diet_preference = models.CharField(max_length=20, default='balanced')
    bmi = models.FloatField(null=True, blank=True)
    bmi_status = models.CharField(max_length=60, blank=True)
    healthy_weight_min = models.FloatField(null=True, blank=True)
    healthy_weight_max = models.FloatField(null=True, blank=True)
    target_weight = models.FloatField(null=True, blank=True)
    daily_calories = models.PositiveIntegerField(null=True, blank=True)
    protein_target_g = models.PositiveIntegerField(null=True, blank=True)
    wellness_summary = models.TextField(blank=True)
    meal_plan = models.TextField(blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'{self.user.username} wellness profile'


class AnalysisRecord(models.Model):
    STATUS_SAFE = 'Safe'
    STATUS_MODERATE = 'Moderate'
    STATUS_HARMFUL = 'Harmful'

    DIET_BALANCED = 'balanced'
    DIET_VEG = 'vegetarian'
    DIET_NON_VEG = 'non_vegetarian'
    DIET_CHOICES = [
        (DIET_BALANCED, 'Balanced'),
        (DIET_VEG, 'Vegetarian'),
        (DIET_NON_VEG, 'Non-Vegetarian'),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    input_image = models.ImageField(upload_to='uploads/', blank=True, null=True)
    input_source = models.CharField(max_length=20, default='upload')
    selected_product = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True, blank=True)
    extracted_text = models.TextField(blank=True)
    normalized_ingredients = models.TextField(blank=True)
    health_score = models.PositiveIntegerField(default=0)
    classification = models.CharField(max_length=20, default=STATUS_MODERATE)
    harmful_found = models.TextField(blank=True)
    moderate_found = models.TextField(blank=True)
    safe_found = models.TextField(blank=True)
    suggestions = models.TextField(blank=True)
    weight_kg = models.FloatField(null=True, blank=True)
    height_cm = models.FloatField(null=True, blank=True)
    diet_preference = models.CharField(max_length=20, choices=DIET_CHOICES, default=DIET_BALANCED)
    bmi = models.FloatField(null=True, blank=True)
    bmi_status = models.CharField(max_length=60, blank=True)
    healthy_weight_min = models.FloatField(null=True, blank=True)
    healthy_weight_max = models.FloatField(null=True, blank=True)
    target_weight = models.FloatField(null=True, blank=True)
    daily_calories = models.PositiveIntegerField(null=True, blank=True)
    protein_target_g = models.PositiveIntegerField(null=True, blank=True)
    wellness_summary = models.TextField(blank=True)
    meal_plan = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        target = self.selected_product.name if self.selected_product else 'Uploaded label'
        return f'{target} - {self.classification} ({self.health_score})'
