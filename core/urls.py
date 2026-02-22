# core/urls.py
from django.urls import path
from . import views

app_name = 'core'

urlpatterns = [
    # Party management URLs (Class-Based Views)
    path('parties/', views.PartyListView.as_view(), name='party_list'),
    path('parties/create/', views.PartyCreateView.as_view(), name='party_create'),
    path('parties/<int:pk>/', views.PartyDetailView.as_view(), name='party_detail'),
    path('parties/<int:pk>/edit/', views.PartyUpdateView.as_view(), name='party_edit'),
    path('parties/<int:pk>/delete/', views.PartyDeleteView.as_view(), name='party_delete'),
    path('parties/<int:pk>/statement/', views.party_statement, name='party_statement'),
]