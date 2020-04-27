from django.contrib import admin
from .models import Language, Conference, Room, Talk, Translation, Translator, TranslatorSpeaks, Booth, Shift, ShiftAssignment

admin.site.register(Language)
admin.site.register(Conference)
admin.site.register(Room)
admin.site.register(Talk)
admin.site.register(Translation)
admin.site.register(Translator)
admin.site.register(TranslatorSpeaks)
admin.site.register(Booth)
admin.site.register(Shift)
admin.site.register(ShiftAssignment)
