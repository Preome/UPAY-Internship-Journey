"""
Django Class-Based View Comparison
Reference examples showing each view class with when to choose it.
"""

# ============================================================
# View — Lowest level, full control
# Use when: JSON APIs, custom HTTP responses, complex logic
# ============================================================
from django.views.generic.base import View
from django.http import JsonResponse


class AccountAPIView(View):
    def get(self, request, *args, **kwargs):
        return JsonResponse({"message": "Custom JSON response"})


# ============================================================
# TemplateView — Renders a template with context
# Use when: Simple static pages, dashboards, landing pages
# ============================================================
from django.views.generic.base import TemplateView


class DashboardView(TemplateView):
    template_name = "dashboard.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["stats"] = {"accounts": 10, "transactions": 500}
        return context


# ============================================================
# ListView — Display paginated list of objects
# Use when: Any read-only list with filtering/search
# ============================================================
from django.views.generic.list import ListView


class AccountListView(ListView):
    model = None  # Set to your model, e.g. Account
    template_name = "account_list.html"
    paginate_by = 20

    def get_queryset(self):
        return super().get_queryset().filter(user=self.request.user)


# ============================================================
# CreateView — Form to create a new object
# Use when: Object creation forms with validation
# ============================================================
from django.views.generic.edit import CreateView
from django.urls import reverse_lazy


class AccountCreateView(CreateView):
    model = None  # Set to your model
    fields = ["account_number", "account_type"]
    template_name = "account_form.html"
    success_url = reverse_lazy("account_list")

    def form_valid(self, form):
        form.instance.user = self.request.user
        return super().form_valid(form)


# ============================================================
# UpdateView — Form to edit an existing object
# Use when: Edit forms, profile updates, settings
# ============================================================
from django.views.generic.edit import UpdateView


class AccountUpdateView(UpdateView):
    model = None  # Set to your model
    fields = ["account_number", "account_type"]
    template_name = "account_form.html"
    success_url = reverse_lazy("account_list")


# ============================================================
# DeleteView — Confirmation page to delete an object
# Use when: Single-step deletions with confirmation
# ============================================================
from django.views.generic.edit import DeleteView


class AccountDeleteView(DeleteView):
    model = None  # Set to your model
    template_name = "account_confirm_delete.html"
    success_url = reverse_lazy("account_list")
