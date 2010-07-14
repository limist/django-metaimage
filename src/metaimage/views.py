from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.core.urlresolvers import reverse
from django.db.models import Q
from django.http import Http404
from django.http import HttpResponseRedirect, get_host
from django.shortcuts import render_to_response, get_object_or_404
from django.template import RequestContext
from django.utils.translation import ugettext_lazy as _

from photologue.models import *

from metaimage.models import MetaImage
from metaimage.forms import MetaImageUploadForm, MetaImageEditForm



@login_required
def show_images(request, template_name="metaimage/latest.html"):
    """Show public images, most recent first, but only to
    authenticated users.
    """
    images = MetaImage.objects.filter(
        Q(is_public=True) |
        Q(is_public=False, user=request.user)
    ).order_by("-created")
    return render_to_response(template_name, {"images": images,}, context_instance=RequestContext(request))



@login_required
def image_details(request, id, template_name="metaimage/details.html"):
    """Show the image details.
    """
    image = get_object_or_404(MetaImage, id=id)
    if not image.is_public and request.user != image.user:
        raise Http404
    title = image.title
    host = "http://%s" % get_host(request)
    is_me = bool(image.creator == request.user)
    if is_me:
        # Note that the "if" sections below I decided to leave from
        # the old Pinax social_project photo app as a placeholder for
        # how they used it, but the code was poorly organized, so
        # what's below already went through some clean-up from me.  KW
        # 7/24/2009
        if request.POST and request.POST["action"] == "add_to_project":
            projectid = request.POST["project"]
            myproject = Project.objects.get(pk=projectid)
            if not myproject.images.filter(image=image).count():
                myproject.images.create(image=image)
                request.user.message_set.create(message=_("Successfully added image '%s' to project") % title)
            else:
                # TODO: this applies to pinax in general. don't use
                # ugettext_lazy here. its usage is fragile.
                request.user.message_set.create(message=_("Did not add image '%s' to project because it already exists.") % title)

            return HttpResponseRedirect(reverse('image_details', args=(image.id,)))
        elif request.POST and request.POST["action"] == "removefromproject":
            projectid = request.POST["project"]
            myproject = Project.objects.get(pk=projectid)
            if myproject.images.filter(image=image).count():
                myproject.images.filter(image=image).delete()
                request.user.message_set.create(message=_("Successfully removed image '%s' from project") % title)
            else:
                request.user.message_set.create(message=_("Did not remove image '%s' from project.") % title)

            return HttpResponseRedirect(reverse('image_details', args=(image.id,)))
    t_dict = {
        "host": host, 
        "image": image,
        "is_me": is_me,
        }
    return render_to_response(template_name, t_dict, context_instance=RequestContext(request))



@login_required
def upload_image(request, form_class=MetaImageUploadForm, template_name="metaimage/upload.html"):
    """Upload form for images.
    """
    image_form = form_class()
    if request.method == 'POST' and request.POST.get("action") == "upload":
        image_form = form_class(request.user, request.POST, request.FILES)
        if image_form.is_valid():
            image = image_form.save(commit=False)
            image.user = request.user
            image.save()
            request.user.message_set.create(message=_("Successfully uploaded image '%s'") % image.title)
            return HttpResponseRedirect(reverse('image_details', args=(image.id,)))
    t_dict = {
        "image_form": image_form,
        }
    return render_to_response(template_name, t_dict, context_instance=RequestContext(request))



@login_required
def your_images(request, template_name="metaimage/your_images.html"):
    """Show MetaImages belonging to the currently authenticated user.
    """
    images = MetaImage.objects.filter(user=request.user).order_by("-created")
    return render_to_response(template_name, {"images": images,}, context_instance=RequestContext(request))



@login_required
def show_user_images(request, username, template_name="metaimage/user_images.html"):
    """Get a given user's public images, display them.
    """
    user = get_object_or_404(User, username=username)
    images = MetaImage.objects.filter(user__username=username, is_public=True).order_by("-created")
    return render_to_response(template_name, {"images": images,}, context_instance=RequestContext(request))



@login_required
def edit_image(request, id, form_class=MetaImageEditForm, template_name="metaimage/edit.html"):
    image = get_object_or_404(MetaImage, id=id)
    if image.user != request.user:
        request.user.message_set.create(message="You can't edit images that aren't yours")
        return HttpResponseRedirect(reverse('image_details', args=(image.id,)))
    image_form = form_class(instance=image)
    image_url = image.get_display_url()
    if request.method == "POST" and request.POST["action"] == "update":
        image_form = form_class(request.user, request.POST, instance=image)
        if image_form.is_valid():
            imageobj = image_form.save(commit=False)
            imageobj.save()
            request.user.message_set.create(message=_("Successfully updated image '%s'") % image.title)
            return HttpResponseRedirect(reverse('image_details', args=(image.id,)))
    t_dict = {
        "image_form": image_form,
        "image": image,
        "image_url": image_url,
        }
    return render_to_response(template_name, t_dict, context_instance=RequestContext(request))



@login_required
def destroy_image(request, id):
    image = MetaImage.objects.get(pk=id)
    title = image.title
    if image.user != request.user:
        request.user.message_set.create(message="You can't delete images that aren't yours")
        return HttpResponseRedirect(reverse("your_images"))
    if request.method == "POST" and request.POST["action"] == "delete":
        image.delete()
        request.user.message_set.create(message=_("Successfully deleted image '%s'") % title)
    return HttpResponseRedirect(reverse("your_images"))
