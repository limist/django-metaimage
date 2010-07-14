from datetime import datetime

from django import forms
from django.utils.translation import ugettext_lazy as _

from metaimage.models import MetaImage



class MetaImageUploadForm(forms.ModelForm):
    
    class Meta:
        model = MetaImage
        exclude = ('user','photoset','slug','effect','crop_from')
        
    def __init__(self, user=None, *args, **kwargs):
        self.user = user
        super(MetaImageUploadForm, self).__init__(*args, **kwargs)



class MetaImageEditForm(forms.ModelForm):
    
    class Meta:
        model = MetaImage
        exclude = ('user','photoset','slug','effect','crop_from','image')
        
    def __init__(self, user=None, *args, **kwargs):
        self.user = user
        super(MetaImageEditForm, self).__init__(*args, **kwargs)
