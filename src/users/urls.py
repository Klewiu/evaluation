# users/urls.py
from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    path('login/',  auth_views.LoginView.as_view(template_name='users/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='login'), name='logout'),

    path('', views.users_list, name='users_list'),

    # CREATE
    path('new/',    views.user_new,    name='user_new'),
    path('create/', views.user_create, name='user_create'),
    path('check-username/', views.check_username, name='check_username'),  # ← NEW

    # EDIT
    path('<int:pk>/edit/',   views.user_edit,   name='user_edit'),
    path('<int:pk>/update/', views.user_update, name='user_update'),

    # DELETE
    path('<int:pk>/confirm-delete/', views.user_confirm_delete, name='user_confirm_delete'),
    path('<int:pk>/delete/',         views.user_delete,         name='user_delete'),
]
