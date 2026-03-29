from django.contrib import admin
from .models import AnalysisRecord, IngredientReference, Product, UserWellnessProfile

admin.site.register(IngredientReference)
admin.site.register(Product)
admin.site.register(AnalysisRecord)
admin.site.register(UserWellnessProfile)
