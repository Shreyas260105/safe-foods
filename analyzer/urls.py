from django.urls import path
from . import views

app_name = 'analyzer'

urlpatterns = [
    path('', views.landing, name='landing'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('self-growth/', views.self_growth, name='self_growth'),
    path('login/', views.login_view, name='login'),
    path('register/', views.register_view, name='register'),
    path('logout/', views.logout_view, name='logout'),
    path('analyze/', views.analyze_food, name='analyze_food'),
    path('result/<int:record_id>/', views.analysis_result, name='analysis_result'),
]
