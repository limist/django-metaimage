from django import forms

from metaimage.models import MetaImage


# These are the MetaImage (and base-class ImageModel) fields that
# users should generally not edit directly:
model_fields_to_exclude = (
    'admin_notes',
    'creator',
    'is_active',
    'slug',
    'imageset',
    'effect',
    'crop_from')

model_fields_to_include = (
    'image',
    'source_url',
    'title',
    'caption',
    'privacy',
    'source_note',
    'safetylevel',
    'tags')


class OptionalImageField(forms.ImageField):
    def __init__(self, *args, **kwargs):
        super(forms.ImageField, self).__init__(*args, **kwargs)
        self.required = False


class MetaImageUploadForm(forms.ModelForm):
    image = OptionalImageField()

    class Meta:
        model = MetaImage
        exclude = model_fields_to_exclude
        fields = model_fields_to_include

    def __init__(self, user=None, *args, **kwargs):
        self.user = user
        super(forms.ModelForm, self).__init__(*args, **kwargs)

    def clean(self):
        """
        The key inter/multi-fields condition to check is: if a local
        image file is not given, then a source_url must be provided.
        MetaImage.save() will then try to grab that remote image, and
        at that point set the image attribute to a new file with that
        remote image data.
        """
        c_data = self.cleaned_data
        local_image = c_data.get('image')
        remote_image_url = c_data.get('source_url')
        if not local_image and not remote_image_url:
            raise forms.ValidationError(
                'Either a local image, or a remote image URL, must be given.')
        return c_data

    def save(self, *args, **kwargs):
        self.instance.creator = self.user
        self.instance.updater = self.user
        return super(MetaImageUploadForm, self).save(*args, **kwargs)


class MetaImageEditForm(forms.ModelForm):
    class Meta:
        model = MetaImage
        fields = model_fields_to_include = (
            'title',
            'caption',
            'privacy',
            'source_note',
            'safetylevel',
            'tags')

    def __init__(self, user=None, *args, **kwargs):
        self.user = user
        super(forms.ModelForm, self).__init__(*args, **kwargs)

    def save(self, *args, **kwargs):
        self.instance.updater = self.user
        return super(MetaImageEditForm, self).save(*args, **kwargs)
