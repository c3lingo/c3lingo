from django.db import models
from django.contrib.auth.models import User
from django.utils.crypto import get_random_string
import hashlib

class Language(models.Model):
    """A language we support, spoken or otherwise."""

    # Language code.
    # For spoken languages, if possible, follow Django's convention of
    # using RFC 3066 (https://docs.djangoproject.com/en/3.0/topics/i18n/).
    # For signed languages, use ISO 639-3.
    code = models.CharField(max_length=8)

    # User-visible language name, in English, for our team's use.
    name_en = models.CharField(max_length=100)

    # User-visible language name, in the form users of that language
    # will most likely recognize (i.e. in the language itself, if it
    # has a written form).
    name_self = models.CharField(max_length=100)

    def __str__(self):
        return self.code

class Conference(models.Model):
    """A public event in which one or more talks will be translated.

    Example: the 36C3.
    """
    shortname = models.CharField(max_length=100)  # e.g. 36c3

    # e.g. "36th Chaos Communication Congress"
    name = models.TextField()

    image_url = models.TextField(blank=True)
    start = models.DateTimeField(null=True)
    end = models.DateTimeField(null=True)

    # The latest version of the Fahrplan JSON we imported.
    fahrplan_version = models.TextField(blank=True)

    def __str__(self):
        return self.shortname

class Room(models.Model):
    """A Room is where Talks are given during a Conference.

    E.g. "Hall Ada"
    """
    conference = models.ForeignKey(Conference, on_delete=models.PROTECT)
    name = models.TextField()

    def __str__(self):
        return '{conf}/{name}'.format(conf=self.conference, name=self.name)

class TalkBaseModel(models.Model):
    """The translatable properties of a talk: title, subtitle, etc.

    In Talk, these are imported untranslated from the Fahrplan."""
    title = models.TextField(blank=True)
    subtitle = models.TextField(blank=True)
    abstract = models.TextField(blank=True)
    description = models.TextField(blank=True)

    class Meta:
        abstract = True

class Talk(TalkBaseModel):
    """A single presentation given at a Conference."""
    conference = models.ForeignKey(Conference, on_delete=models.PROTECT)
    fahrplan_id = models.CharField(max_length=100)
    fahrplan_guid = models.CharField(max_length=100)

    # These fields are untranlsated and imported from the Fahrplan
    logo_url = models.TextField(blank=True)
    talk_type = models.TextField(blank=True)
    speakers = models.TextField(blank=True)  # comma-separated list of speakers from the Fahrplan

    language = models.ForeignKey(Language, on_delete=models.PROTECT)

    room = models.ForeignKey(Room, on_delete=models.PROTECT)

    start = models.DateTimeField()
    end = models.DateTimeField()

    class Meta:
        unique_together = [['conference', 'fahrplan_id']]

    def __str__(self):
        return '{conf}/{title}'.format(conf=self.conference, title=self.title)

    @property
    def slug(self):
        return '{conference_name}-{fahrplan_id}-{name}'.format(
            conference_name=self.conference.acronym,
            fahrplan_id=self.fahrplan_id,
            name=parametrize(self.name),
        )

    @property
    def watch_url(self):
        return 'https://media.ccc.de/v/{slug}'.format(slug=self.slug)

    @property
    def slides_url(self):
        return 'https://speakers.c3lingo.org/talks/{guid}/'.format(self.guid)

class Translation(TalkBaseModel):
    """A translation of the properties of a talk (title, subtitle, etc.)"""
    author = models.ForeignKey(User, null=True, on_delete=models.SET_NULL)
    talk = models.ForeignKey(Talk, on_delete=models.CASCADE)
    language = models.ForeignKey(Language, on_delete=models.PROTECT)

    class Meta:
        unique_together = [['talk', 'language']]

    def __str__(self):
        return '{talk} ({language})'.format(talk=self.talk, language=self.language)

class Translator(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    confirmed = models.BooleanField()
    bio = models.TextField(blank=True)
    contact_info = models.TextField(blank=True)

    # Used to authenticate requests to the iCal URL.
    secret_token = models.CharField(max_length=64, default=lambda: get_random_string(64))

    @property
    def avatar_url(self):
        """Automatically generated Gravatar URL from the email.

        TODO: this leaks the email address (MD5 is rainbowed to death)
        TODO: how does the Chaos community feel about Gravatar?
        """
        return 'https://www.gravatar.com/avatar/{}'.format(
            hashlib.md5(self.user.email.lower()).hexdigest(),
        )

    def __str__(self):
        return str(self.user)

class TranslatorSpeaks(models.Model):
    """Indicates that a translator speaks a given language."""
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    language = models.ForeignKey(Language, on_delete=models.PROTECT)

    def __str__(self):
        return '{translator}: {language}'.format(translator=self.user, language=self.language)

class Booth(models.Model):
    """Represents a translation booth that contains a console."""
    room = models.ForeignKey(Room, on_delete=models.PROTECT)
    name = models.TextField()  # e.g. "Hall A booth 1"
    location = models.TextField() # How to get there (c3nav link, free
                                  # text, ...)
    dect = models.CharField(max_length=30, blank=True)

    # How many translators we want in this booth for a typical talk
    desired_occupancy = models.PositiveIntegerField()

    # How many translators can fit in this booth, max
    maximum_occupancy = models.PositiveIntegerField()

    def __str__(self):
        return '{room}/{name}'.format(room=self.room, name=self.name)

class Shift(models.Model):
    """A shift is an opportunity for a number of Translators to translate
    a given Talk in a given Booth."""
    booth = models.ForeignKey(Booth, on_delete=models.PROTECT)
    talk = models.ForeignKey(Talk, on_delete=models.CASCADE)

    # The language may not be defined, e.g. if we have a booth used
    # for multiple languages based on availability/interest.
    language = models.ForeignKey(Language, blank=True, null=True, on_delete=models.PROTECT)

    @property
    def language_or_any(self):
        if self.language is not None:
            return self.language
        return '*'

    def __str__(self):
        return '{talk} ({src} -> {dst})'.format(
            talk=self.talk,
            src=self.talk.language,
            dst=self.language_or_any
        )

class ShiftAssignment(models.Model):
    """Represents a Translator volunteering for a Shift."""
    shift = models.ForeignKey(Shift, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    waitlisted = models.BooleanField(default=True)
    freeloaded = models.BooleanField(default=False)
    comment = models.TextField(blank=True)

    def __str__(self):
        return '{user} {langfrom} -> {langto} {talk}'.format(
            user=self.user,
            langfrom=self.shift.talk.language,
            langto=self.shift.language,
            talk=self.shift.talk
        )
