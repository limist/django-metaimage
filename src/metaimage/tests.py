from django.contrib.auth.models import User
from django.test import TestCase

from metaimage.models import MetaImage


class TestMetaImage(TestCase):

    def setUp(self):
        self.foo = User.objects.create_user('foo', 'foo@test.com', 'bar')
        self.remote_img_url = 'http://media.djangoproject.com/img/site/hdr_logo.gif'

    def test_metaimage_save(self):
        """
        MetaImage wraps around photologue.ImageModel, which wraps
        around Django's ImageField.  So this simple test hits a lot of
        layers.
        """
        test_metaimage = MetaImage(
            title='Django logo',
            slug='django-logo',
            source_url=self.remote_img_url,
            source_note='The logo of the Django project, for testing.',
            creator=self.foo,
            )
        test_metaimage.save()
        the_metaimage = MetaImage.objects.get(slug='django-logo')
        assert the_metaimage.image is not None  # Image was downloaded
        assert the_metaimage.is_public
        the_metaimage.delete()  # Removes image file too

    def tearDown(self):
        pass
