from django.urls import path
from . import views

app_name = 'users'

urlpatterns = [
    path('', views.home_view, name='home'),
    path('login/', views.login_view, name='login'),
    path('signup/', views.signup_view, name='signup'),
    path('logout/', views.logout_view, name='logout'),
    path('dashboard/', views.dashboard_view, name='dashboard'),
    path('profile/', views.profile_view, name='profile'),
    path('payment/', views.payment_simulation_view, name='payment'),
    path('process-payment/', views.process_payment_simulation, name='process_payment'),
] 