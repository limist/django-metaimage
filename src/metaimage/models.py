from cStringIO import StringIO
import re
import tempfile
from urlparse import urlparse

from django.db import models
from django.conf import settings
from django.contrib.auth.models import User
from django.core.files import File
from django.template.defaultfilters import slugify
from django.utils.safestring import mark_safe
from django.utils.translation import ugettext_lazy as _

from PIL import Image

from photologue.models import ImageModel, PHOTOLOGUE_DIR
from tagging.fields import TagField

from utils.openanything import fetch


if getattr(settings, 'METAIMAGE_MAX_REMOTE_IMAGE_SIZE', False):
    MAX_REMOTE_IMAGE_SIZE = settings.METAIMAGE_MAX_REMOTE_IMAGE_SIZE
else:
    MAX_REMOTE_IMAGE_SIZE = 1048576  # 1 MB

PRIVACY_CHOICES = (
    (1, _('Public')),
    (2, _('Friends')),
    (3, _('Private')),
    )

# This parameter is needed when cleaning up after unit-tests,
# otherwise old test images litter the directory:
METAIMAGE_DIR = PHOTOLOGUE_DIR


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
    tags = TagField()


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
    slug = models.SlugField(_('slug'))
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
    tags = TagField()

    class Meta:
        verbose_name = 'MetaImage'

    def __unicode__(self):
        return self.title

    @models.permalink
    def get_absolute_url(self):
        return ("metaimage_details", [self.pk])

    def save(self, *args, **kwargs):
        """
        MetaImage.save transparently fetches remote images to local
        storage - in case the remote image ever changes location or
        disappears, you'll still have it.
        """
        # If the MetaImage.source_url is defined, but not the
        # ImageModel.image attribute, then we need to download the
        # remote image file, and set that file as the ImageModel.image
        # attribute.
        if getattr(self, 'source_url') and not getattr(self, 'image'):
            image_data_dct = fetch(self.source_url,
                                   max_size=MAX_REMOTE_IMAGE_SIZE)
            if image_data_dct:
                # Verify that the data is, in fact, an image.
                image_data = image_data_dct['data']
                the_image = Image.open(StringIO(image_data))
                try:
                    the_image.verify()
                except Exception, e:
                    raise MetaImageSourceURLNotAnImage(e)
                # Django's save() method must receive a Django File
                # object, which in turn, must be wrapped around a real
                # file (not StringIO) to work; thus, use tempfile.
                tmp_file = tempfile.NamedTemporaryFile()
                tmp_file.write(image_data)
                tmp_image_file = File(tmp_file)
                filename = self.generate_filename_from_url()
                self.image.save(filename, tmp_image_file)
            else:
                raise MetaImageUnableToRetrieveSourceURL
        # Handle slug; note that this solution is not very robust
        # currently, may use django-autoslug next.
        if not self.slug:
            self.slug = slugify(self.title)
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
