"""
URL configuration for config project.
"""
from django.contrib import admin
from django.urls import path, include
from rest_framework_simplejwt.views import TokenRefreshView
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView, SpectacularRedocView
from config.db import views

urlpatterns = [
    # ---- Admin ----
    path('admin/', admin.site.urls),
    
    # ---- Documentación API ----
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
    
    # ---- Autenticación ----
    path('api/auth/register/', views.RegisterView.as_view(), name='register'),
    path('api/auth/login/', views.LoginView.as_view(), name='login'),
    path('api/auth/logout/', views.LogoutView.as_view(), name='logout'),
    path('api/auth/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('api/auth/profile/', views.UserProfileView.as_view(), name='profile'),
    path('api/auth/change-password/', views.ChangePasswordView.as_view(), name='change_password'),
    
    # ---- Personas ----
    path('api/persons/', views.PersonViewSet.as_view(), name='person_list'),
    path('api/persons/<int:pk>/', views.PersonDetailView.as_view(), name='person_detail'),
    path('api/persons/<int:person_id>/sessions/', views.person_sessions, name='person_sessions'),
    path('api/persons/<int:person_id>/alerts/', views.person_alerts, name='person_alerts'),
    path('api/persons/<int:person_id>/report/', views.behavior_report, name='behavior_report'),
    
    # ---- Sesiones ----
    path('api/sessions/', views.SessionListView.as_view(), name='session_list'),
    path('api/sessions/<int:session_id>/', views.session_detail, name='session_detail'),
    
    # ---- Alertas ----
    path('api/alerts/', views.AlertListView.as_view(), name='alert_list'),
    path('api/alerts/<int:alert_id>/review/', views.mark_alert_reviewed, name='mark_alert_reviewed'),
    
    # ---- Dashboard ----
    path('api/dashboard/', views.dashboard_stats, name='dashboard'),
    
    # ---- Análisis de imagen (REST) ----
    path('api/analyze/', views.analyze_image, name='analyze_image'),
]
