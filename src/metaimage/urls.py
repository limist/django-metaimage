from django.conf.urls.defaults import patterns, url, handler404, handler500


urlpatterns = patterns('',
    url(r'^$', 'metaimage.views.show_metaimages',
        name="show_metaimages"),
    url(r'^details/(?P<id>\d+)/$', 'metaimage.views.metaimage_details',
        name="metaimage_details"),
    url(r'^edit/(?P<id>\d+)/$', 'metaimage.views.edit_metaimage',
        name='edit_metaimage'),
    url(r'^upload/$', 'metaimage.views.upload_metaimage',
        name="upload_metaimage"),
    url(r'^yours/$', 'metaimage.views.your_metaimages',
        name='your_metaimages'),
    url(r'^user/(?P<username>[\w]+)/$', 'metaimage.views.show_user_metaimages',
        name='show_user_metaimages'),
    url(r'^destroy/(?P<id>\d+)/$', 'metaimage.views.destroy_metaimage',
        name='destroy_metaimage'),
)
