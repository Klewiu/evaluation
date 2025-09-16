from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    path('login/',  auth_views.LoginView.as_view(template_name='users/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='login'), name='logout'),
    path('', views.users_list, name='users_list'),
    path('<int:pk>/confirm-delete/', views.user_confirm_delete, name='user_confirm_delete'),
    path('<int:pk>/delete/',         views.user_delete,         name='user_delete'),
]
