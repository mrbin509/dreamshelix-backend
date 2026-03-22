from django.contrib import admin
from django.urls import path, include
from users.views import home

urlpatterns = [
    path('admin/', admin.site.urls),              # Django admin
    path('api/users/', include('users.urls')),   # All APIs
    path('', home, name='home'),                 # Root check
]