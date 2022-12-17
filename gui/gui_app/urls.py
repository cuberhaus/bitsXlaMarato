from django.urls import path
from gui_app import views

urlpatterns = [
    path('', views.hello_world, name='hello_world'),
]
