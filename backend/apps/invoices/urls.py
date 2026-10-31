"""Invoice routes under /api/v1/.

Static paths are declared before the router so ``/invoices/dashboard/`` is not
mistaken for an invoice detail lookup.
"""

from django.urls import path
from rest_framework.routers import SimpleRouter

from .views import (
    ClientViewSet,
    InvoiceDashboardView,
    InvoiceReminderListView,
    InvoiceReminderQueueView,
    InvoiceViewSet,
)

router = SimpleRouter()
router.register("clients", ClientViewSet, basename="client")
router.register("invoices", InvoiceViewSet, basename="invoice")

urlpatterns = [
    path(
        "invoices/dashboard/",
        InvoiceDashboardView.as_view(),
        name="invoice-dashboard",
    ),
    path(
        "invoices/reminder-queue/",
        InvoiceReminderQueueView.as_view(),
        name="invoice-reminder-queue",
    ),
    path(
        "invoices/reminders/",
        InvoiceReminderListView.as_view(),
        name="invoice-reminder-list",
    ),
    *router.urls,
]
