# Smart Food Safety Analyzer

A Django-based college mini project that now behaves like a personalized health website: users create an account, update a Self Growth profile, and then analyze packaged foods with ingredient scoring plus body-goal-aware calorie guidance.

## Main sections

- Landing page for a personalized health website experience
- Registration and login system using Django auth
- Self Growth page for height, weight, diet preference, calorie target, BMI, protein target, and meal direction
- Food analysis dashboard for OCR or predefined product selection
- Result page that combines food safety with the user's saved Self Growth profile

## Run the project

```powershell
cd "C:\Users\DELL\Documents\safe food detector\smart_food_safety_analyzer"
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
python manage.py migrate
python manage.py seed_data
python manage.py runserver
```

Open http://127.0.0.1:8000/

## User flow

1. Register or login
2. Open the Self Growth page and save weight, height, and diet preference
3. Go to the dashboard and analyze a food product
4. View food safety score, ingredient watch-outs, calories, BMI context, and protein suggestions together

## Product sources

See `PRODUCT_SOURCES.md` for the public links used to refresh the packaged-food catalog on March 29, 2026.

## Limitation

Calorie and weight suggestions are simple project estimates and are not medical advice.
