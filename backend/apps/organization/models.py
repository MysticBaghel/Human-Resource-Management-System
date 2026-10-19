"""Teams: the company's org units, each with an optional employee lead."""

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
