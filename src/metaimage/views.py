from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.core.urlresolvers import reverse
from django.db.models import Q
from django.http import Http404
from django.http import HttpResponseRedirect
from django.shortcuts import render_to_response, get_object_or_404
from django.template import RequestContext
from django.utils.translation import ugettext_lazy as _

from metaimage.models import MetaImage
from metaimage.forms import MetaImageUploadForm, MetaImageEditForm


@login_required
def show_metaimages(request, template_name="metaimage/latest.html"):
    """
    For an authenticated user only, show public and private images -
    most recent first.
    """
    metaimages = MetaImage.objects.filter(
        Q(is_public=True)
        | Q(is_public=False, creator=request.user)).order_by("-created")
    return render_to_response(
        template_name,
        {"metaimages": metaimages},
        context_instance=RequestContext(request))


@login_required
def metaimage_details(request, id, template_name="metaimage/details.html"):
    """
    Show details for a MetaImage instance.
    """
    the_metaimage = get_object_or_404(MetaImage, id=id)
    # Private images can only be seen by their creator:
    if not the_metaimage.is_public and the_metaimage.creator != request.user:
        raise Http404
    is_mine = bool(the_metaimage.creator == request.user)
    if is_mine:
        # Could provide extra editing options here for the image's
        # creator, but leaving blank for now.
        pass
    return render_to_response(
        template_name,
        {"the_metaimage": the_metaimage},
        context_instance=RequestContext(request))


@login_required
def upload_metaimage(request, form_class=MetaImageUploadForm, template_name="metaimage/upload.html"):
    """
    Show and process upload form for a MetaImage.
    """
    metaimage_form = form_class()
    if request.method == 'POST' and request.POST.get("action") == "upload":
        metaimage_form = form_class(request.user, request.POST, request.FILES)
        if metaimage_form.is_valid():
            metaimage = metaimage_form.save(commit=False)
            metaimage.creator = request.user
            metaimage.save()
            request.user.message_set.create(
                message=_("Successfully uploaded image '%s'.")
                % metaimage.title)
            return HttpResponseRedirect(
                reverse('metaimage_details', args=(metaimage.id,)))
    return render_to_response(
        template_name,
        {"metaimage_form": metaimage_form},
        context_instance=RequestContext(request))


@login_required
def your_metaimages(request, template_name="metaimage/your_images.html"):
    """
    Show MetaImages belonging to the currently authenticated user.
    """
    metaimages = MetaImage.objects.filter(
        creator=request.user).order_by("-created")
    return render_to_response(
        template_name,
        {"metaimages": metaimages},
        context_instance=RequestContext(request))


@login_required
def show_user_metaimages(request, username, template_name="metaimage/user_images.html"):
    """
    Get a given user's public images, display them.
    """
    the_user = get_object_or_404(User, username=username)
    metaimages = MetaImage.objects.filter(
        creator=the_user, is_public=True).order_by("-created")
    t_dict = {
        "metaimages": metaimages,
        "the_user": the_user}
    return render_to_response(
        template_name,
        t_dict,
        context_instance=RequestContext(request))


@login_required
def edit_metaimage(request, id, form_class=MetaImageEditForm, template_name="metaimage/edit.html"):
    metaimage = get_object_or_404(MetaImage, id=id)
    if metaimage.creator != request.user:
        request.user.message_set.create(
            message=_("You can't edit images that aren't yours."))
        return HttpResponseRedirect(
            reverse('metaimage_details', args=(metaimage.id,)))
    metaimage_form = form_class(instance=metaimage)
    if request.method == "POST" and request.POST["action"] == "update":
        metaimage_form = form_class(
            request.user,
            request.POST,
            instance=metaimage)
        if metaimage_form.is_valid():
            metaimage = metaimage_form.save(commit=False)
            metaimage.save()
            request.user.message_set.create(
                message=_("Successfully updated image '%s'.") % metaimage.title)
            return HttpResponseRedirect(
                reverse('metaimage_details', args=(metaimage.id,)))
    t_dict = {
        "metaimage_form": metaimage_form,
        "metaimage": metaimage}
    return render_to_response(
        template_name,
        t_dict,
        context_instance=RequestContext(request))


@login_required
def destroy_metaimage(request, id):
    metaimage = MetaImage.objects.get(pk=id)
    title = metaimage.title
    if metaimage.creator != request.user:
        request.user.message_set.create(
            message=_("You can't delete images that aren't yours."))
        return HttpResponseRedirect(reverse("your_metaimages"))
    if request.method == "POST" and request.POST["action"] == "delete":
        metaimage.delete()
        request.user.message_set.create(
            message=_("Successfully deleted image '%s'.") % title)
    return HttpResponseRedirect(reverse("your_metaimages"))
