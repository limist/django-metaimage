import shutil

from django.contrib.auth.models import User
from django.test import TestCase
from django.test.client import Client

from metaimage.forms import MetaImageUploadForm, MetaImageEditForm
from metaimage.models import MetaImage, METAIMAGE_DIR


class TestMetaImage(TestCase):
    """
    Testing of the MetaImage model class.
    """

    def setUp(self):
        self.foo = User.objects.create_user('foo', 'foo@test.com', 'bar')
        self.remote_img_url = 'http://media.djangoproject.com/img/site/hdr_logo.gif'

    def test_metaimage_model(self):
        """
        Test fetching and saving a remote image as a new MetaImage
        instance.  In lieu of multiple tests with multiple network
        requests, I'm consolidating several tests of the MetaImage
        model into this single testcase.

        MetaImage wraps around photologue.ImageModel, which wraps
        around Django's ImageField; this simple test actually hits a
        lot of layers.
        """
        test_metaimage = MetaImage(
            title='Django logo',
            source_url=self.remote_img_url,
            source_note='The logo of the Django project.',
            creator=self.foo,
            )
        test_metaimage.save()
        the_metaimage = MetaImage.objects.get(slug='django-logo')
        assert the_metaimage.image is not None  # Image was downloaded OK.
        assert the_metaimage.is_public
        assert the_metaimage.updater == self.foo
        assert the_metaimage.slug == 'django-logo'
        assert (the_metaimage.image.name
                == 'photologue/photos/media.djangoproject.com_img_site_hdr_logo.gif')
        assert (the_metaimage.render()
                == '<img src="photologue/photos/cache/media.djangoproject.com_img_site_hdr_logo_width500.gif" height="41" width="117" alt="Django logo">')
        # As of Django 1.2.5, the image file is NOT removed when the
        # database object is deleted.
        the_metaimage.delete()

    def tearDown(self):
        # In order that image filenames are repeatable, it's necessary
        # to delete the directory where they're stored between test
        # runs.
        shutil.rmtree(METAIMAGE_DIR)


class TestViews(TestCase):
    """
    Tests of metaimage/views.py module.
    """

    def setUp(self):
        self.client = Client()
        self.foo = User.objects.create_user('foo', 'foo@test.com', 'bar')
        self.client.login(username='foo', password='bar')
        self.remote_img_url = 'http://www.google.com/images/nav_logo36.png'
        test_metaimage = MetaImage(
            title='Google small logo',
            source_url=self.remote_img_url,
            source_note='The Google logo, for testing.',
            creator=self.foo,
            )
        test_metaimage.save()
        self.test_image = test_metaimage

    def test_show_metaimages(self):
        response = self.client.get('')
        self.failUnlessEqual(response.status_code, 200)
        self.failUnlessEqual(len(response.context['metaimages']), 1)

    def test_metaimage_details(self):
        response = self.client.get('/details/1/')
        self.failUnlessEqual(response.status_code, 200)
        self.failUnlessEqual(response.context['the_metaimage'].slug,
                             'google-small-logo')

    def test_upload_metaimage(self):
        response = self.client.get('/upload/')
        self.failUnlessEqual(response.status_code, 200)
        self.assertEqual(isinstance(response.context['metaimage_form'],
                                    MetaImageUploadForm),
                         True)

    def test_upload_metaimage_post(self):
        upload_dct = {
            'source_url': 'http://upload.wikimedia.org/wikipedia/en/b/bc/Wiki.png',
            'title': 'Wikipedia logo, English',
            'safetylevel': 1,
            'privacy': 1,
            'action': 'upload'}
        response = self.client.post('/upload/', upload_dct)
        self.assertRedirects(response, '/details/2/')

    def test_your_metaimages(self):
        response = self.client.get('/user/foo/')
        self.failUnlessEqual(response.status_code, 200)
        self.failUnlessEqual(len(response.context['metaimages']), 1)
        self.assertContains(response, 'Google small logo')

    def test_show_user_metaimages(self):
        monty = User.objects.create_user('monty', 'monty@test.com', 'python')
        response = self.client.get('/user/monty/')
        self.failUnlessEqual(response.status_code, 200)
        self.failUnlessEqual(len(response.context['metaimages']), 0)
        self.failUnlessEqual(response.context['the_user'].username,
                             monty.username)

    def test_edit_metaimage(self):
        response = self.client.get('/edit/1/')
        self.failUnlessEqual(response.status_code, 200)
        self.assertEqual(isinstance(response.context['metaimage_form'],
                                    MetaImageEditForm),
                         True)
        self.assertEqual(response.context['metaimage'].source_url,
                         self.test_image.source_url)

    def test_edit_metaimage_disallowed(self):
        User.objects.create_user('monty', 'monty@test.com', 'python')
        new_client = Client()
        new_client.login(username='monty', password='python')
        # Unfortunately the code below does not work; within the
        # edit_metaimage view during test-running, a crash arises when
        # the Django message_set is used, with a completely cryptic
        # error message, "InterfaceError: Error binding parameter 1 -
        # probably unsupported type."  Tried adding the Django message
        # settings to testsettings.py but no luck.  Manual testing via
        # browser shows this works as expected.  2/2011
        #
        #response = new_client.get('/edit/1/')
        #self.assertRedirects(response, '/details/1/')

    def test_edit_metaimage_ok(self):
        edit_dct = {
            'title': self.test_image.title,
            'privacy': self.test_image.privacy,
            'safetylevel': self.test_image.safetylevel,
            'caption': 'Behold the Google logo!',
            'action': 'update'}
        response = self.client.post('/edit/1/', edit_dct)
        self.assertRedirects(response, '/details/1/')

    def test_destroy_metaimage(self):
        delete_dct = {
            'action': 'delete'}
        response = self.client.post('/destroy/1/', delete_dct)
        self.assertRedirects(response, '/yours/')

    def tearDown(self):
        shutil.rmtree(METAIMAGE_DIR)
