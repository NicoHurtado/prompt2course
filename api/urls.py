from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

# Configurar router para ViewSets
router = DefaultRouter()
router.register(r'courses', views.CourseViewSet, basename='course')
router.register(r'modules', views.ModuleViewSet, basename='module')
router.register(r'progress', views.UserProgressViewSet, basename='progress')

app_name = 'api'

urlpatterns = [
    # API REST endpoints
    path('', include(router.urls)),
] 