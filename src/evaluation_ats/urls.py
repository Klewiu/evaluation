from django.contrib import admin
from django.urls import path, include
from django.views.generic import RedirectView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('users/', include('users.urls')),         # logowanie i logout
    path('', include('evaluations.urls')),         # główna aplikacja
    path('surveys/', include('surveys.urls')),     # ankiety (HR i admin)
]
