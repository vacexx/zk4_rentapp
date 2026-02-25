from django.contrib import admin
from .models import Gig, WorkPhase, Equipment, GigEquipment

admin.site.register(Gig)
admin.site.register(WorkPhase)
admin.site.register(Equipment)
admin.site.register(GigEquipment)