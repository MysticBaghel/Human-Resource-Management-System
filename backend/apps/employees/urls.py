"""Employee routes, including the public invite-acceptance endpoint."""

from django.urls import path
from rest_framework.routers import SimpleRouter

from .views import AcceptInviteView, EmployeeViewSet

router = SimpleRouter()
router.register("employees", EmployeeViewSet, basename="employee")

urlpatterns = [
    # Lives under /auth/ because it is part of the sign-in story, but the view
    # and the invite model belong to the employees app.
    path("auth/accept-invite/", AcceptInviteView.as_view(), name="auth-accept-invite"),
    *router.urls,
]
