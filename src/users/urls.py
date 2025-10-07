from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    # AUTH
    path('login/',  auth_views.LoginView.as_view(template_name='users/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='login'), name='logout'),

    # USERS
    path('', views.users_list, name='users_list'),

    # CREATE USER
    path('new/',    views.user_new,    name='user_new'),
    path('create/', views.user_create, name='user_create'),
    path('check-username/', views.check_username, name='check_username'),

    # EDIT USER
    path('<int:pk>/edit/',   views.user_edit,   name='user_edit'),
    path('<int:pk>/update/', views.user_update, name='user_update'),

    # TOGGLE ACTIVE (Block/Unblock)
    path('<int:pk>/toggle-active/', views.user_toggle_active, name='user_toggle_active'),

    # DELETE USER
    path('<int:pk>/confirm-delete/', views.user_confirm_delete, name='user_confirm_delete'),
    path('<int:pk>/delete/',         views.user_delete,         name='user_delete'),

 
    # DEPARTMENTS
    path('departments/', views.departments_list, name='departments_list'),

    # Create
    path('departments/new/',    views.department_new,    name='department_new'),
    path('departments/create/', views.department_create, name='department_create'),

    # Edit
    path('departments/<int:pk>/edit/',   views.department_edit,   name='department_edit'),
    path('departments/<int:pk>/update/', views.department_update, name='department_update'),

    # Delete
    path('departments/<int:pk>/confirm-delete/', views.department_confirm_delete, name='department_confirm_delete'),
    path('departments/<int:pk>/delete/',         views.department_delete,         name='department_delete'),
]
