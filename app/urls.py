from django.urls import path
from . import views

urlpatterns = [
    path('', views.gig_list, name='gig_list'),
    path('prehled/', views.financial_overview, name='financial_overview'),
    path('akce/<int:gig_id>/tisk/', views.gig_print, name='gig_print'),
    path('akce/nova/', views.gig_create, name='gig_create'),
    path('akce/<int:gig_id>/', views.gig_detail, name='gig_detail'),
    path('akce/<int:gig_id>/upravit/', views.gig_update, name='gig_update'),
    path('akce/<int:gig_id>/smazat/', views.gig_delete, name='gig_delete'),
    
    # Fáze (Práce)
    path('akce/<int:gig_id>/pridat-fazi/', views.workphase_create, name='workphase_create'),
    path('faze/<int:phase_id>/upravit/', views.workphase_update, name='workphase_update'),
    path('faze/<int:phase_id>/smazat/', views.workphase_delete, name='workphase_delete'),
    
    # Technika
    path('akce/<int:gig_id>/pridat-techniku/', views.gigequipment_create, name='gigequipment_create'),
    path('technika/<int:eq_id>/smazat/', views.gigequipment_delete, name='gigequipment_delete'),

    # Vlastní položky na faktuře
    path('akce/<int:gig_id>/pridat-polozku/', views.custom_invoice_item_create, name='custom_invoice_item_create'),
    path('polozka/<int:item_id>/upravit/', views.custom_invoice_item_update, name='custom_invoice_item_update'),
    path('polozka/<int:item_id>/smazat/', views.custom_invoice_item_delete, name='custom_invoice_item_delete'),

    # Klienti
    path('klient/novy/', views.client_create, name='client_create'),
]