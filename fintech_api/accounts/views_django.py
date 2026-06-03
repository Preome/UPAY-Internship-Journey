from django.views.generic import View, TemplateView, ListView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from django.shortcuts import render
from django.http import JsonResponse, HttpResponse
from django.db.models import Sum
from .models import Account
from django.contrib.auth.mixins import LoginRequiredMixin

"""
COMPARISON TABLE - When to choose which view class:

┌─────────────────┬─────────────────────────────────────────────────────────────┐
│ View Class      │ Best Use Case                                               │
├─────────────────┼─────────────────────────────────────────────────────────────┤
│ View            │ JSON APIs, custom HTTP responses, file downloads,           │
│                 │ complex logic not fitting CRUD patterns                     │
├─────────────────┼─────────────────────────────────────────────────────────────┤
│ TemplateView    │ Simple static pages, dashboards, about pages,               │
│                 │ landing pages with minimal context data                     │
├─────────────────┼─────────────────────────────────────────────────────────────┤
│ ListView        │ Displaying lists of objects, paginated results,             │
│                 │ search/filtered lists (80% of read-only list pages)         │
├─────────────────┼─────────────────────────────────────────────────────────────┤
│ CreateView      │ Object creation forms, user registration,                   │
│                 │ any "new resource" form with validation                     │
├─────────────────┼─────────────────────────────────────────────────────────────┤
│ UpdateView      │ Edit forms, profile updates, settings pages,                │
│                 │ any object modification with validation                     │
├─────────────────┼─────────────────────────────────────────────────────────────┤
│ DeleteView      │ Single-step deletions (with confirmation),                  │
│                 │ quick delete operations (not for cascading deletes)         │
└─────────────────┴─────────────────────────────────────────────────────────────┘

"""


class AccountAPIView(View):
    
    def get(self, request, *args, **kwargs):
        accounts = list(Account.objects.filter(user=request.user).values('id', 'account_number', 'balance'))
        return JsonResponse(accounts, safe=False)
    
    def post(self, request, *args, **kwargs):
        # Custom POST handling logic
        import json
        data = json.loads(request.body)
        account = Account.objects.create(
            user=request.user,
            account_number=data.get('account_number'),
            balance=data.get('balance', 0)
        )
        return JsonResponse({'id': account.id, 'message': 'Created'})


class DashboardView(TemplateView):
    template_name = 'dashboard.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Bank Dashboard'
        context['account_count'] = Account.objects.filter(user=self.request.user).count()
        return context


class AccountListView(ListView):
    model = Account
    template_name = 'accounts_list.html'
    context_object_name = 'accounts'
    paginate_by = 20
    
    def get_queryset(self):
        return Account.objects.filter(user=self.request.user).order_by('-created_at')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['total_balance'] = self.get_queryset().aggregate(total=Sum('balance'))['total']
        return context


class AccountCreateView(CreateView):
    model = Account
    fields = ['account_number', 'balance', 'account_type']
    template_name = 'account_form.html'
    success_url = reverse_lazy('django_account_list')
    
    def form_valid(self, form):
        form.instance.user = self.request.user
        return super().form_valid(form)


class AccountUpdateView(UpdateView):
    model = Account
    fields = ['account_number', 'account_type']
    template_name = 'account_form.html'
    success_url = reverse_lazy('django_account_list')
    
    def get_queryset(self):
        return Account.objects.filter(user=self.request.user)


class AccountDeleteView(DeleteView):
    model = Account
    template_name = 'account_confirm_delete.html'
    success_url = reverse_lazy('django_account_list')
    
    def get_queryset(self):
        return Account.objects.filter(user=self.request.user)