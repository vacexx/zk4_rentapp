from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('ucty/', include('django.contrib.auth.urls')), # Autentizace
    path('', include('app.urls')), # Zde napojujeme tvůj nový soubor app/urls.py
]