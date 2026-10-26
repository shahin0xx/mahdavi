from modeltranslation.translator import translator, TranslationOptions
from .models import Station, Badge, PrayerTime

class StationTranslationOptions(TranslationOptions):
    fields = ('name', 'description')

class BadgeTranslationOptions(TranslationOptions):
    fields = ('name', 'description')

class PrayerTimeTranslationOptions(TranslationOptions):
    fields = ('name', 'description')

translator.register(Station, StationTranslationOptions)
translator.register(Badge, BadgeTranslationOptions)
translator.register(PrayerTime, PrayerTimeTranslationOptions)