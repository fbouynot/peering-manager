import platform
import sys

from cacheops import CacheMiss, cache
from django.conf import settings
from django.shortcuts import render
from django.urls import reverse
from django.views.generic import View
from packaging import version

from devices.models import Configuration
from extras.models import ObjectChange
from messaging.models import Contact, Email
from peering.models import (
    AutonomousSystem,
    BGPGroup,
    Community,
    DirectPeeringSession,
    InternetExchange,
    InternetExchangePeeringSession,
    Router,
    RoutingPolicy,
)
from peering_manager.constants import SEARCH_MAX_RESULTS, SEARCH_TYPES
from peering_manager.forms import SearchForm
from peeringdb.models import Synchronisation


def handle_500(request):
    """
    Custom 500 error handler.
    """
    type, error, traceback = sys.exc_info()
    del traceback
    return render(
        request,
        "500.html",
        {
            "python_version": platform.python_version(),
            "peering_manager_version": settings.VERSION,
            "exception": str(type),
            "error": error,
        },
        status=500,
    )


def trigger_500(request):
    """
    Method to fake trigger a server error for test reporting.
    """
    raise Exception("Manually triggered error.")


class Home(View):
    def get(self, request):
        statistics = {
            "autonomous_systems_count": AutonomousSystem.objects.count(),
            "bgp_groups_count": BGPGroup.objects.count(),
            "communities_count": Community.objects.count(),
            "direct_peering_sessions_count": DirectPeeringSession.objects.count(),
            "internet_exchanges_count": InternetExchange.objects.count(),
            "internet_exchange_peering_sessions_count": InternetExchangePeeringSession.objects.count(),
            "routers_count": Router.objects.count(),
            "routing_policies_count": RoutingPolicy.objects.count(),
            # Devices
            "configurations_count": Configuration.objects.count(),
            # Messaging
            "contacts_count": Contact.objects.count(),
            "emails_count": Email.objects.count(),
        }

        # Check whether a new release is available (staff and superusers only)
        new_release = None
        if request.user.is_staff or request.user.is_superuser:
            try:
                latest_release = cache.get("latest_release")
            except CacheMiss:
                latest_release = None
            if latest_release:
                release_version, release_url = latest_release
                if release_version > version.parse(settings.VERSION):
                    new_release = {"version": str(release_version), "url": release_url}

        context = {
            "statistics": statistics,
            "changelog": ObjectChange.objects.select_related(
                "user", "changed_object_type"
            )[:15],
            "synchronisations": Synchronisation.objects.all()[:5],
            "new_release": new_release,
        }
        return render(request, "home.html", context)


class SearchView(View):
    def get(self, request):
        form = SearchForm(request.GET)
        results = []

        if form.is_valid():
            for obj_type in SEARCH_TYPES.keys():
                queryset = SEARCH_TYPES[obj_type]["queryset"]
                filterset = SEARCH_TYPES[obj_type]["filterset"]
                table = SEARCH_TYPES[obj_type]["table"]
                url = SEARCH_TYPES[obj_type]["url"]

                # Construct the results table for this object type
                filtered_queryset = filterset(
                    {"q": form.cleaned_data["q"]}, queryset=queryset
                ).qs
                table = table(filtered_queryset, orderable=False, no_actions=True)
                table.paginate(per_page=SEARCH_MAX_RESULTS)

                if table.page:
                    results.append(
                        {
                            "name": queryset.model._meta.verbose_name_plural,
                            "table": table,
                            "url": f"{reverse(url)}?q={form.cleaned_data.get('q')}",
                        }
                    )

        return render(request, "search.html", {"form": form, "results": results})
