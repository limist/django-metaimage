from django.contrib import admin

from metaimage.models import MetaImage


class BaseModelAdmin(admin.ModelAdmin):
    """
    Because the sage.models relies on the BaseModel abstract class,
    Django's admin UI does not automagically pick up the
    BaseModel.creator and BaseModel.updater fields; in particular, the
    creator field is required.  So create an inheritable save_model()
    method that takes care of that.
    """
    def save_model(self, request, obj, form, change):
        if not change:
            obj.creator = request.user
        else:
            obj.updater = request.user
        obj.save()


class MetaImageAdmin(BaseModelAdmin):
    fieldsets = (
        (None, {
            'fields': ('image', 'crop_from', 'effect', 'title', 'slug', 'caption', 'source_url', 'source_note', 'safetylevel', 'privacy', 'tags', 'imageset', 'admin_notes', 'is_active')
            }),
        )
    list_display = ('title', 'slug', 'caption', 'creator', 'created','is_public','safetylevel','tags',)
    prepopulated_fields = {"slug": ("title",)}

admin.site.register(MetaImage, MetaImageAdmin)
