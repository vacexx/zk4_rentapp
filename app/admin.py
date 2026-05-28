from django.contrib import admin
from .models import Gig, WorkPhase, Equipment, GigEquipment, Client, UserProfile, CustomInvoiceItem

admin.site.register(Gig)
admin.site.register(WorkPhase)
admin.site.register(Equipment)
admin.site.register(GigEquipment)
admin.site.register(Client)
admin.site.register(UserProfile)
admin.site.register(CustomInvoiceItem)