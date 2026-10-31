"""Teams and the company profile used on generated documents."""

from django.db import models
from django.utils.translation import gettext_lazy as _


class Team(models.Model):
    """A team people belong to.

    ``lead`` points at an employee rather than a user: the lead is a person in
    the org chart, and scoping for managers is driven by it.
    """

    name = models.CharField(_("name"), max_length=120, unique=True)
    lead = models.ForeignKey(
        "employees.Employee",
        verbose_name=_("lead"),
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="led_teams",
        help_text=_("The employee who leads this team."),
    )

    class Meta:
        ordering = ["name"]
        verbose_name = _("team")
        verbose_name_plural = _("teams")

    def __str__(self) -> str:
        return self.name


class CompanyProfile(models.Model):
    """Organisation details used on payslips.

    This is a singleton: there is one company. It is managed in the Django
    admin, next to teams, and the payroll PDF falls back to settings when no
    profile has been created yet.
    """

    name = models.CharField(_("company name"), max_length=200, default="HRMS")
    logo = models.ImageField(
        _("logo"),
        upload_to="organization/logos/",
        null=True,
        blank=True,
        help_text=_("Shown on payslips. PNG or JPEG works best."),
    )
    address = models.TextField(_("address"), blank=True)
    email = models.EmailField(_("email"), blank=True)
    phone = models.CharField(_("phone"), max_length=40, blank=True)
    website = models.CharField(_("website"), max_length=200, blank=True)
    updated_at = models.DateTimeField(_("updated at"), auto_now=True)

    class Meta:
        verbose_name = _("company profile")
        verbose_name_plural = _("company profile")

    def __str__(self) -> str:
        return self.name

    def save(self, *args, **kwargs):
        # There can only be one company profile. Pinning the pk makes an
        # accidental second insert update the first row instead of creating a
        # duplicate that the payslip would then have to choose between.
        self.pk = 1
        super().save(*args, **kwargs)

    @classmethod
    def load(cls) -> "CompanyProfile | None":
        return cls.objects.first()
