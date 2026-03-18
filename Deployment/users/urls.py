from django.urls import path

from . import views

urlpatterns = [
    
    
    path('',views.model,name='model'),
    path('fetch_firebase_data/', views.fetch_firebase_data, name='fetch_firebase_data'),
    
   
    
    
    
    
    
    ]


 