from django.conf.urls.defaults import patterns, url


urlpatterns = patterns('',
    url(r'^$', 'metaimage.views.show_images', name="show_images"),
    url(r'^details/(?P<id>\d+)/$', 'metaimage.views.image_details', name="image_details"),
    url(r'^edit/(\d+)/$', 'metaimage.views.edit_image', name='edit_image'),
    url(r'^upload/$', 'metaimage.views.upload_image', name="upload_image"),
    url(r'^yours/$', 'metaimage.views.your_images', name='your_images'),
    url(r'^user/(?P<username>[\w]+)/$', 'metaimage.views.show_user_images', name='show_user_images'),
    url(r'^destroy/(\d+)/$', 'metaimage.views.destroy_image', name='destroy_image'),
)
