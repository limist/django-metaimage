from cStringIO import StringIO
import re
import tempfile
from urlparse import urlparse

from django.db import models
from django.conf import settings
from django.contrib.auth.models import User
from django.core.files import File
from django.utils.safestring import mark_safe
from django.utils.translation import ugettext_lazy as _

from PIL import Image

from autoslug import AutoSlugField
from photologue.models import ImageModel, PHOTOLOGUE_DIR
from taggit.managers import TaggableManager

from utils.openanything import fetch


if getattr(settings, 'METAIMAGE_MAX_REMOTE_IMAGE_SIZE', False):
    MAX_REMOTE_IMAGE_SIZE = settings.METAIMAGE_MAX_REMOTE_IMAGE_SIZE
else:
    MAX_REMOTE_IMAGE_SIZE = 1048576  # 1 MB

# The METAIMAGE_DIR parameter is referenced in tests.py when cleaning
# up after unit-tests, otherwise old test images litter the directory:
#
# Note that PHOTOLOGUE_DIR is the "top-level" directory which holds
# several others: PHOTOLOGUE_PATH is where original-image files are
# stored; temp/ is where uploads are held; samples/, watermarks/ are
# two more.  So to customize, both PHOTOLOGUE_DIR and PHOTOLOGUE_PATH
# (which can be a function) should be in settings.py.
if getattr(settings, 'PHOTOLOGUE_DIR', False):
    METAIMAGE_DIR = settings.PHOTOLOGUE_DIR
else:
    METAIMAGE_DIR = PHOTOLOGUE_DIR


PRIVACY_CHOICES = (
    (1, _('Public')),
    (2, _('Friends')),
    (3, _('Private')),
    )


class MetaImageException(Exception):
    pass


class MetaImageUnableToRetrieveSourceURL(MetaImageException):
    pass


class MetaImageSourceURLNotAnImage(MetaImageException):
    pass


class BaseModel(models.Model):
    """
    An abstract base class that provides standard fields for every
    model.
    """
    admin_notes = models.TextField(blank=True, null=True)
    created = models.DateTimeField(auto_now_add=True, editable=False)
    creator = models.ForeignKey(
        User,
        editable=False,
        related_name='%(class)s_creator')
    updated = models.DateTimeField(auto_now=True, editable=False, null=True)
    updater = models.ForeignKey(
        User,
        editable=False,
        null=True,
        related_name='%(class)s_updater')
    is_active = models.BooleanField(default=True)

    class Meta:
        abstract = True


class ImageSet(BaseModel):
    """
    A set of images, akin to a photo-album.
    """
    name = models.CharField(_('name'), max_length=200)
    description = models.TextField(_('description'))
    privacy = models.IntegerField(
        _('privacy'),
        choices=PRIVACY_CHOICES, default=1)
    tags = TaggableManager()


class MetaImage(ImageModel, BaseModel):
    """
    An image with its useful details.  Parallels photologue's Photo
    class, but with different functionality.

    Note that ImageModel from photologue.models is an abstract model
    too, so there's no one-to-one joining going on here, thankfully.
    As to what the ImageModel base class provides, view the ImageModel
    source at,
    http://code.google.com/p/django-photologue/source/browse/trunk/photologue/models.py

    The key ImageModel attributes include:
    - image, the ImageField
    - date_taken
    - view_count
    - crop_from, default 'center'
    - effect, e.g. WaterMark, PhotoEffect

    Useful methods from ImageModel include:
    - image_filename()
    - get_<photosize>_url(), get_<photosize>_filename() where
      <photosize> is already defined. Note that django-metaimage
      defines some starting PhotoSize instances in
      fixtures/initial_data.json such as square25, square50, etc.
    """
    SAFETY_LEVEL = (
        (1, _('Safe')),
        (2, _('Not Safe')),
    )
    title = models.CharField(_('title'), max_length=200)
    # With AutoSlugField, editable should be set to True to avoid
    # problems with Django's admin form generation - though in
    # practice slugs should not be manually edited:
    slug = AutoSlugField(
        max_length=100, editable=True, populate_from='title', unique=True,
        help_text='In general do NOT edit slugs manually.')
    caption = models.TextField(_('caption'), blank=True)
    # The source of a MetaImage may be from another site; if so,
    # provide URL here.
    source_url = models.URLField(
        _('source URL'),
        blank=True, null=True,
        verify_exists=True,
        help_text='The external URL where the image originated from.')
    source_note = models.CharField(
        _('source note'),
        max_length=500,
        blank=True, null=True,
        help_text='Attribution text, copyright notices, permissions, etc.')
    safetylevel = models.IntegerField(
        _('safetylevel'), choices=SAFETY_LEVEL, default=1)
    privacy = models.IntegerField(
        _('privacy'), choices=PRIVACY_CHOICES, default=1)
    imageset = models.ManyToManyField(
        ImageSet, blank=True, null=True, verbose_name=_('image set'))
    tags = TaggableManager(blank=True)  # taggit has blank=False by default.

    class Meta:
        verbose_name = 'MetaImage'

    def __unicode__(self):
        return self.title

    @models.permalink
    def get_absolute_url(self):
        return ("metaimage_details", [self.pk])

    def is_str_an_image(self, the_string):
        # Verify that the data is, in fact, an image.
        assert isinstance(the_string, str)
        the_image = Image.open(StringIO(the_string))
        try:
            the_image.verify()
            return True
        except Exception:
            return False

    def save(self, *args, **kwargs):
        """
        MetaImage.save transparently fetches remote images to local
        storage - in case the remote image ever changes location or
        disappears, you'll still have it.

        For the other major use-case of server-side generated images,
        pass in the raw image data as a string with
        save(image_data=the_image_as_string).
        """
        raw_image_data = None
        local_img_filename = None
        # There are three cases of how we get image data: 1) uploaded,
        # 2) remote image URL given, or 3) the raw image string is
        # passed in.  Cases 2) and 3) are handled below:
        if getattr(self, 'source_url') and not getattr(self, 'image'):
            # Download remote data, synchronously for now:
            image_data_dct = fetch(
                self.source_url,
                max_size=MAX_REMOTE_IMAGE_SIZE)
            if not image_data_dct:
                raise MetaImageUnableToRetrieveSourceURL
            raw_image_data = image_data_dct['data']
            local_img_filename = self.generate_filename_from_url()
        elif 'image_data' in kwargs and not self.source_url and not self.image:
            # Alternatively, raw image data (as a string) was given:
            raw_image_data = kwargs.pop('image_data')
            local_img_filename = self.generate_filename_from_data(
                raw_image_data)
        # Create and save the remote/given image if needed:
        if raw_image_data and local_img_filename:
            assert self.is_str_an_image(raw_image_data)
            # Django's save() method must receive a Django File
            # object, which in turn, must be wrapped around a real
            # file (not StringIO) to work. Thus use tempfile:
            tmp_file = tempfile.NamedTemporaryFile()
            tmp_file.write(raw_image_data)
            self.image.save(local_img_filename, File(tmp_file))
        if self.creator and not self.updater:
            self.updater = self.creator
        super(MetaImage, self).save(*args, **kwargs)

    def generate_filename_from_url(self, the_url=None):
        """
        When a remote image is fetched, the URL will be unique, and
        that handily provides the basis for a unique filename too.
        """
        if not the_url:
            the_url = self.source_url
        parsed_url = urlparse(the_url)
        non_alphanum_regex = re.compile(r'[^a-zA-Z0-9\-\.]')
        raw_filename = parsed_url.netloc.lower() + parsed_url.path
        the_filename = non_alphanum_regex.sub('_', raw_filename)
        return the_filename

    def generate_filename_from_data(self, the_data):
        # Assume only PNG files for now:
        return '%s.png' % hash(the_data)

    def get_public_status(self):
        """
        Public images can be displayed in default views.
        """
        return bool(self.privacy == 1)

    is_public = property(get_public_status)

    def render(self, the_size='width500', linked=False):
        """
        Returns the HTML to display this MetaImage instance.
        """
        get_url_method_name = 'get_%s_url' % the_size
        mimage_url = getattr(self, get_url_method_name)()
        get_size_method_name = 'get_%s_size' % the_size
        the_width, the_height = getattr(self, get_size_method_name)()
        img_html = mark_safe(
            '<img src="%s" height="%s" width="%s" alt="%s">'
            % (mimage_url, the_height, the_width, str(self.title)))
        if linked:
            return mark_safe(
                '<a href="%s" class="invisible">%s</a>'
                % (self.get_absolute_url(), img_html))
        else:
            return img_html

    def render_linked(self, the_size='width500'):
        return self.render(the_size, linked=True)

    def render_thumbnail_linked(self):
        return self.render_linked(the_size='square25')
