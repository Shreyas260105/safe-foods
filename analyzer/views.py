from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from .forms import FoodAnalysisForm, LoginForm, RegistrationForm, SelfGrowthForm
from .models import AnalysisRecord, Product, UserWellnessProfile
from .services import IngredientAnalyzer, OCRService, WellnessAdvisor, cloud_summary, protein_sources


PRODUCT_LIMIT = 12


def landing(request):
    if request.user.is_authenticated:
        return redirect('analyzer:dashboard')
    return render(request, 'analyzer/landing.html', {'cloud': cloud_summary()})



def register_view(request):
    if request.user.is_authenticated:
        return redirect('analyzer:dashboard')

    form = RegistrationForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        user = form.save(commit=False)
        user.first_name = form.cleaned_data['first_name']
        user.email = form.cleaned_data['email']
        user.save()
        UserWellnessProfile.objects.get_or_create(user=user)
        login(request, user)
        messages.success(request, 'Your account is ready. Start by filling your Self Growth details.')
        return redirect('analyzer:self_growth')

    return render(request, 'analyzer/register.html', {'form': form, 'cloud': cloud_summary()})



def login_view(request):
    if request.user.is_authenticated:
        return redirect('analyzer:dashboard')

    form = LoginForm(request, data=request.POST or None)
    if request.method == 'POST' and form.is_valid():
        login(request, form.get_user())
        return redirect('analyzer:dashboard')
    return render(request, 'analyzer/login.html', {'form': form, 'cloud': cloud_summary()})


@login_required
def logout_view(request):
    logout(request)
    return redirect('analyzer:landing')


@login_required
def dashboard(request):
    form = FoodAnalysisForm()
    recent_analyses = AnalysisRecord.objects.select_related('selected_product').filter(user=request.user)[:5]
    products = Product.objects.all()[:PRODUCT_LIMIT]
    profile, _ = UserWellnessProfile.objects.get_or_create(user=request.user)
    context = {
        'form': form,
        'products': products,
        'featured_product': products[0] if products else None,
        'recent_analyses': recent_analyses,
        'cloud': cloud_summary(),
        'protein_data': protein_sources(),
        'profile': profile,
    }
    return render(request, 'analyzer/dashboard.html', context)


@login_required
def self_growth(request):
    profile, _ = UserWellnessProfile.objects.get_or_create(user=request.user)
    form = SelfGrowthForm(request.POST or None, instance=profile)

    if request.method == 'POST' and form.is_valid():
        profile = form.save(commit=False)
        profile.user = request.user
        wellness = WellnessAdvisor.build_plan(profile.weight_kg, profile.height_cm, profile.diet_preference)
        if wellness:
            profile.bmi = wellness.bmi
            profile.bmi_status = wellness.bmi_status
            profile.healthy_weight_min = wellness.healthy_weight_min
            profile.healthy_weight_max = wellness.healthy_weight_max
            profile.target_weight = wellness.target_weight
            profile.daily_calories = wellness.daily_calories
            profile.protein_target_g = wellness.protein_target_g
            profile.wellness_summary = wellness.summary
            profile.meal_plan = ' || '.join(wellness.meals)
        profile.save()
        messages.success(request, 'Your Self Growth profile has been updated.')
        return redirect('analyzer:self_growth')

    context = {
        'form': form,
        'profile': profile,
        'meal_plan_items': [item.strip() for item in profile.meal_plan.split('||') if item.strip()],
        'protein_data': protein_sources(),
        'cloud': cloud_summary(),
    }
    return render(request, 'analyzer/self_growth.html', context)


@login_required
def analyze_food(request):
    if request.method != 'POST':
        return redirect('analyzer:dashboard')

    form = FoodAnalysisForm(request.POST, request.FILES)
    products = Product.objects.all()[:PRODUCT_LIMIT]
    profile, _ = UserWellnessProfile.objects.get_or_create(user=request.user)
    if not form.is_valid():
        for _, errors in form.errors.items():
            for error in errors:
                messages.error(request, error)
        return render(request, 'analyzer/dashboard.html', {
            'form': form,
            'products': products,
            'featured_product': products[0] if products else None,
            'recent_analyses': AnalysisRecord.objects.select_related('selected_product').filter(user=request.user)[:5],
            'cloud': cloud_summary(),
            'protein_data': protein_sources(),
            'profile': profile,
        })

    product = form.cleaned_data.get('product')
    ingredient_image = form.cleaned_data.get('ingredient_image')

    if product:
        ingredient_text = product.ingredient_text
        record = AnalysisRecord.objects.create(
            user=request.user,
            input_source='database',
            selected_product=product,
            extracted_text=ingredient_text,
            weight_kg=profile.weight_kg,
            height_cm=profile.height_cm,
            diet_preference=profile.diet_preference,
        )
    else:
        record = AnalysisRecord.objects.create(
            user=request.user,
            input_source='upload',
            input_image=ingredient_image,
            weight_kg=profile.weight_kg,
            height_cm=profile.height_cm,
            diet_preference=profile.diet_preference,
        )
        OCRService.upload_to_cloud(ingredient_image)
        ingredient_text = OCRService.extract_text(record.input_image.path)
        if not ingredient_text.strip():
            messages.warning(request, 'OCR could not confidently read the image. A sample fallback analysis is shown if text is weak.')
            ingredient_text = 'Ingredients: sugar, palm oil, salt, artificial color, preservative, wheat flour'
        record.extracted_text = ingredient_text

    analysis = IngredientAnalyzer.analyze(ingredient_text, product=product)
    record.normalized_ingredients = ', '.join(analysis.ingredients)
    record.health_score = analysis.score
    record.classification = analysis.classification
    record.harmful_found = ', '.join(item['name'] for item in analysis.harmful_found)
    record.moderate_found = ', '.join(item['name'] for item in analysis.moderate_found)
    record.safe_found = ', '.join(item['name'] for item in analysis.safe_found)
    record.suggestions = ' '.join(analysis.suggestions + analysis.nutrition_flags)

    wellness = WellnessAdvisor.build_plan(profile.weight_kg, profile.height_cm, profile.diet_preference)
    if wellness:
        record.bmi = wellness.bmi
        record.bmi_status = wellness.bmi_status
        record.healthy_weight_min = wellness.healthy_weight_min
        record.healthy_weight_max = wellness.healthy_weight_max
        record.target_weight = wellness.target_weight
        record.daily_calories = wellness.daily_calories
        record.protein_target_g = wellness.protein_target_g
        record.wellness_summary = wellness.summary
        record.meal_plan = ' || '.join(wellness.meals)

    record.save()
    return redirect('analyzer:analysis_result', record_id=record.id)


@login_required
def analysis_result(request, record_id):
    record = get_object_or_404(AnalysisRecord.objects.select_related('selected_product'), id=record_id, user=request.user)
    context = {
        'record': record,
        'harmful_items': [item.strip() for item in record.harmful_found.split(',') if item.strip()],
        'moderate_items': [item.strip() for item in record.moderate_found.split(',') if item.strip()],
        'safe_items': [item.strip() for item in record.safe_found.split(',') if item.strip()],
        'normalized_ingredients': [item.strip() for item in record.normalized_ingredients.split(',') if item.strip()],
        'meal_plan_items': [item.strip() for item in record.meal_plan.split('||') if item.strip()],
        'cloud': cloud_summary(),
        'protein_data': protein_sources(),
    }
    return render(request, 'analyzer/result.html', context)
