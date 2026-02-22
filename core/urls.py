# core/urls.py
from django.urls import path
from . import views
from . import views_purchase

app_name = 'core'

urlpatterns = [
    # Party management URLs (Class-Based Views)
    path('parties/', views.PartyListView.as_view(), name='party_list'),
    path('parties/create/', views.PartyCreateView.as_view(), name='party_create'),
    path('parties/<int:pk>/', views.PartyDetailView.as_view(), name='party_detail'),
    path('parties/<int:pk>/edit/', views.PartyUpdateView.as_view(), name='party_edit'),
    path('parties/<int:pk>/delete/', views.PartyDeleteView.as_view(), name='party_delete'),
    path('parties/<int:pk>/statement/', views.party_statement, name='party_statement'),

    # Purchase management URLs
    path('purchases/', views_purchase.purchase_list, name='purchase_list'),
    path('purchases/create/', views_purchase.purchase_create, name='purchase_create'),
    path('purchases/<int:pk>/', views_purchase.purchase_detail, name='purchase_detail'),
    path('purchases/<int:pk>/edit/', views_purchase.purchase_edit, name='purchase_edit'),
    path('purchases/<int:pk>/delete/', views_purchase.purchase_delete, name='purchase_delete'),
    path('purchases/<int:pk>/confirm/', views_purchase.purchase_confirm, name='purchase_confirm'),
    path('purchases/<int:pk>/receive/', views_purchase.purchase_receive, name='purchase_receive'),
]