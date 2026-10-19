"""Generate docs/Phase02.pdf — a report of the Phase 2 work.

Run:  backend\\.venv\\Scripts\\python.exe backend\\build_phase02_pdf.py
"""

from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    PageBreak,
    PageTemplate,
    Paragraph,
    Preformatted,
    Spacer,
    Table,
    TableStyle,
)

OUT = Path(__file__).resolve().parent.parent / "docs" / "Phase02.pdf"

# --- fonts -----------------------------------------------------------------
BODY, BOLD, ITALIC, MONO = "SegoeUI", "SegoeUI-Bold", "SegoeUI-Italic", "Consolas"
FONT_DIR = Path("C:/Windows/Fonts")
pdfmetrics.registerFont(TTFont(BODY, str(FONT_DIR / "segoeui.ttf")))
pdfmetrics.registerFont(TTFont(BOLD, str(FONT_DIR / "seguisb.ttf")))
pdfmetrics.registerFont(TTFont(ITALIC, str(FONT_DIR / "segoeuii.ttf")))
pdfmetrics.registerFont(TTFont(MONO, str(FONT_DIR / "consola.ttf")))
pdfmetrics.registerFontFamily(BODY, normal=BODY, bold=BOLD, italic=ITALIC)

NAVY = colors.HexColor("#1e293b")
SLATE = colors.HexColor("#475569")
MUTED = colors.HexColor("#64748b")
LINE = colors.HexColor("#cbd5e1")
GREEN = colors.HexColor("#047857")
RED = colors.HexColor("#b91c1c")
AMBER = colors.HexColor("#b45309")
BG = colors.HexColor("#f1f5f9")

ss = getSampleStyleSheet()

S = {
    "title": ParagraphStyle("title", fontName=BOLD, fontSize=26, leading=32, textColor=NAVY, spaceAfter=4),
    "subtitle": ParagraphStyle("subtitle", fontName=BODY, fontSize=12.5, leading=18, textColor=SLATE),
    "h1": ParagraphStyle("h1", fontName=BOLD, fontSize=16, leading=21, textColor=NAVY, spaceBefore=16, spaceAfter=7),
    "h2": ParagraphStyle("h2", fontName=BOLD, fontSize=12.5, leading=17, textColor=NAVY, spaceBefore=12, spaceAfter=4),
    "h3": ParagraphStyle("h3", fontName=BOLD, fontSize=10.5, leading=14, textColor=SLATE, spaceBefore=9, spaceAfter=3),
    "body": ParagraphStyle("body", fontName=BODY, fontSize=9.6, leading=14, textColor=colors.HexColor("#0f172a"), alignment=TA_LEFT, spaceAfter=5),
    "small": ParagraphStyle("small", fontName=BODY, fontSize=8.4, leading=12, textColor=MUTED, spaceAfter=4),
    "bullet": ParagraphStyle("bullet", fontName=BODY, fontSize=9.6, leading=14, textColor=colors.HexColor("#0f172a"), leftIndent=11, bulletIndent=2, spaceAfter=2.5),
    "cell": ParagraphStyle("cell", fontName=BODY, fontSize=8.3, leading=11.4, textColor=colors.HexColor("#0f172a")),
    "cellb": ParagraphStyle("cellb", fontName=BOLD, fontSize=8.3, leading=11.4, textColor=colors.HexColor("#0f172a")),
    "code": ParagraphStyle("code", fontName=MONO, fontSize=7.9, leading=10.8, textColor=colors.HexColor("#0f172a")),
}
ss.add(S["body"])


def P(text, style="body"):
    return Paragraph(text, S[style])


def B(text):
    return Paragraph(text, S["bullet"], bulletText="\u2022")


def CODE(text):
    return Preformatted(text, S["code"])


def table(rows, widths, header=True):
    data = []
    for index, row in enumerate(rows):
        style = "cellb" if (header and index == 0) else "cell"
        data.append([Paragraph(str(cell), S[style]) for cell in row])
    t = Table(data, colWidths=widths, repeatRows=1 if header else 0)
    commands = [
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("LINEBELOW", (0, 0), (-1, -2), 0.4, LINE),
        ("BOX", (0, 0), (-1, -1), 0.6, LINE),
    ]
    if header:
        commands += [
            ("BACKGROUND", (0, 0), (-1, 0), BG),
            ("LINEBELOW", (0, 0), (-1, 0), 0.7, SLATE),
        ]
    t.setStyle(TableStyle(commands))
    return t


def callout(title, text, colour=AMBER, background="#fffbeb"):
    inner = [[Paragraph(f"<b>{title}</b>", S["cellb"])], [Paragraph(text, S["cell"])]]
    t = Table(inner, colWidths=[165 * mm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor(background)),
        ("LINEBEFORE", (0, 0), (0, -1), 2.4, colour),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    return t


def defect(title, severity, symptom, cause, fix, verified):
    return [
        P(title, "h2"),
        P(f"<b>Severity.</b> {severity}"),
        P(f"<b>Symptom.</b> {symptom}"),
        P(f"<b>Root cause.</b> {cause}"),
        P(f"<b>Fix.</b> {fix}"),
        P(f"<b>Verified.</b> {verified}"),
    ]


# --- page furniture --------------------------------------------------------
def decorate(canvas, doc):
    canvas.saveState()
    canvas.setStrokeColor(LINE)
    canvas.setLineWidth(0.5)
    canvas.line(20 * mm, 15 * mm, 190 * mm, 15 * mm)
    canvas.setFont(BODY, 7.6)
    canvas.setFillColor(MUTED)
    canvas.drawString(20 * mm, 10.5 * mm, "HRMS \u2014 Phase 2 Report: Teams and Employees")
    canvas.drawRightString(190 * mm, 10.5 * mm, f"Page {doc.page}")
    canvas.restoreState()


doc = BaseDocTemplate(
    str(OUT),
    pagesize=A4,
    leftMargin=20 * mm,
    rightMargin=20 * mm,
    topMargin=18 * mm,
    bottomMargin=20 * mm,
    title="HRMS Phase 2 Report",
    author="DeepSeek Harness agent",
)
frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id="main")
doc.addPageTemplates([PageTemplate(id="all", frames=[frame], onPage=decorate)])

story = []

# ===========================================================================
# Cover / summary
# ===========================================================================
story.append(Spacer(1, 6 * mm))
story.append(P("HRMS \u2014 Phase 2", "title"))
story.append(P("Teams, employees, invites and audit \u2014 development and test report", "subtitle"))
story.append(Spacer(1, 5 * mm))
story.append(table([
    ["Field", "Value"],
    ["Phase", "Phase 2 \u2014 Teams and employees (Phases 0\u20134 are the MVP)"],
    ["Status", "Backend verified by execution. Frontend typechecked and built; browser flow not verified."],
    ["Backend tests", "153 passed, 0 failed (pytest 9.1.1, Django 5.2.18, SQLite)"],
    ["Frontend", "tsc --noEmit exit 0 \u00b7 vite build 455 kB JS / 139 kB gzip"],
    ["Database", "SQLite for development. PostgreSQL not exercised."],
    ["Date", "2026-10-19"],
    ["Handbook basis", "docs/Handbook.pdf, Phase 2 (pages 7\u20138)"],
], [34 * mm, 131 * mm]))

story.append(Spacer(1, 5 * mm))
story.append(P("What this document is", "h2"))
story.append(P(
    "A record of everything done for Phase 2: the models and services that were written, the permissions and "
    "scoping rules, the React pages, the commands that were run with their real output, the defects and "
    "toolchain failures found and fixed, and \u2014 explicitly \u2014 what has <b>not</b> been verified. Where "
    "something was not executed it is labelled as such rather than described as working.",
))

story.append(P("Summary", "h2"))
for item in [
    "<b>Phase 2 is complete against the Handbook's checklist.</b> Teams and employees have role-scoped CRUD, "
    "employee creation sends a one-time invite instead of a password, people are deactivated rather than "
    "deleted, and every change writes one audit row.",
    "<b>The backend test suite grew from 67 to 153 passing tests</b> and now covers the permission matrix, "
    "invite flow, deactivation, filters and the audit rows.",
    "<b>The whole flow was driven over real HTTP against a running server:</b> HR creates a person, the invite "
    "is accepted by that person, an employee sees only their own record, a manager sees only their team, a "
    "deactivated person cannot sign in, and audit rows carry the right actor.",
    "<b>Ten significant problems were found and fixed.</b> The most important were a wrong status code for "
    "hard deletes, audit rows that could miss email/role changes, manager scoping that would have leaked, "
    "missing privilege guards, and a seeded admin that could not actually use the Django admin.",
    "<b>Two things were deliberately left out of Phase 2:</b> no audit API/page (not in the Phase 2 build "
    "list) and no new frontend dependencies (the dialog and select are hand-built on existing primitives).",
    "<b>Not verified:</b> a browser click-through, PostgreSQL, ruff (blocked by the sandbox), and the Django "
    "admin forms beyond opening their list pages.",
]:
    story.append(B(item))

story.append(P("Phase 2 acceptance criteria (from the Handbook)", "h2"))
story.append(table([
    ["Handbook requirement", "Evidence"],
    ["HR creates an employee who logs in through the invite link", "Live HTTP run plus 8 invite tests; the console email contains the one-time link."],
    ["Each role sees only what it should, enforced by the API", "153-test suite includes the full role matrix; out-of-scope records return 404, never 403."],
    ["Audit rows exist for the changes", "Tests assert exactly one row per create/update/deactivate with the actor; live run showed create by HR and updates by HR and by the employee."],
    ["Watch out: employee edits a record or field they should not", "Own record is phone-only (403 on any other field); another record is 404. Tested."],
    ["Watch out: duplicate audit rows", "One save is one row, and a save that changes nothing writes nothing. Tested."],
], [62 * mm, 103 * mm]))

story.append(PageBreak())

# ===========================================================================
# 1. Scope and deliverables
# ===========================================================================
story.append(P("1. Scope and deliverables", "h1"))

story.append(P("Phase 2 goal (from the Handbook)", "h2"))
story.append(P(
    "One place for people data: teams, employees, invites and an audit trail. Deliverables: Team and Employee "
    "models with CRUD and role-scoped querysets; creating an employee also creates a login and an invite link "
    "to set a password; deactivate instead of delete; AuditLog rows written automatically on create, update "
    "and delete; and React pages for the employee list (search, filters, pagination), the employee form, "
    "teams, and accepting an invite.",
))

story.append(P("Delivered", "h2"))
story.append(table([
    ["Item", "Where", "Status"],
    ["Team model, unique name, optional employee lead", "apps/organization", "Done, migrated"],
    ["Employee model (user, names, phone, job title, team, manager, start date, type, status)", "apps/employees/models.py", "Done, migrated"],
    ["One-time EmployeeInvite (UUID token, 7-day expiry)", "apps/employees/models.py", "Done, migrated"],
    ["Role-scoped employee and team viewsets", "apps/core/scoping.py, views.py", "Done, tested"],
    ["Create employee = login + record + invite email", "apps/employees/services.py", "Done, tested"],
    ["Accept-invite endpoint and page that set a password", "employees/views.py, AcceptInvitePage", "Done, tested"],
    ["Deactivate and reactivate instead of delete", "services.py, viewset actions", "Done, tested"],
    ["AuditLog written by signals with request-user middleware", "apps/audit", "Done, tested"],
    ["Employee list with search, team/status/role filters, pagination", "EmployeesPage.tsx", "Done, typechecked"],
    ["Employee detail and create/edit form", "EmployeeDetailPage, EmployeeFormPage", "Done, typechecked"],
    ["Teams page with create/edit dialog", "TeamsPage.tsx", "Done, typechecked"],
    ["Accept-invite React page", "AcceptInvitePage.tsx", "Done, typechecked"],
    ["seed_users extended with teams and employee links", "accounts/management/commands", "Done, idempotent"],
    ["docs/PERMISSIONS.md with the endpoint/role matrix", "docs/PERMISSIONS.md", "Done"],
    ["README updated for Phase 2", "README.md", "Done"],
], [78 * mm, 47 * mm, 40 * mm]))

story.append(P("Explicitly not in Phase 2", "h2"))
for item in [
    "No audit API or audit page. Rows are written and are readable in the Django admin; the Phase 2 build list stops at writing them. This is recorded in docs/PERMISSIONS.md.",
    "No invite resend, no bulk import, no CSV export, no avatars, no employee self-service profile page.",
    "No leave models or endpoints \u2014 Phase 3.",
    "No new npm packages. shadcn/ui components were written by hand on top of the packages that were already installed (Radix dropdown/label/slot, Tailwind, cva). A native select and a small custom dialog cover the new UI needs.",
]:
    story.append(B(item))

story.append(P("Files created and changed", "h2"))
story.append(CODE(
    "backend/apps/organization/\n"
    "  models.py  serializers.py  views.py  urls.py  admin.py  apps.py\n"
    "  migrations/{0001_initial}.py\n"
    "backend/apps/employees/\n"
    "  models.py  serializers.py  services.py  views.py  urls.py  admin.py  apps.py\n"
    "  migrations/{0001_initial,0002_initial}.py\n"
    "backend/apps/audit/\n"
    "  models.py  signals.py  middleware.py  context.py  admin.py  apps.py\n"
    "  migrations/{0001_initial}.py\n"
    "backend/tests/\n"
    "  test_employees.py  test_teams.py  test_invites.py  test_audit.py\n"
    "  test_auth.py (seed/admin tests added)   conftest.py (factories added)\n"
    "backend/\n"
    "  config/settings/base.py  config/urls.py\n"
    "  apps/core/permissions.py  apps/core/scoping.py\n"
    "  apps/accounts/management/commands/seed_users.py\n"
    "  requirements.txt (ruff declared)\n"
    "  build_phase02_pdf.py (this report's generator)\n"
    "frontend/src/\n"
    "  api/{client,queries,employees,teams,types}.ts  lib/{query,format,useDebouncedValue}.ts\n"
    "  components/ui/{table,badge,skeleton,select,dialog}.tsx\n"
    "  components/common/{states,Pagination}.tsx  components/form/Field.tsx\n"
    "  components/employees/StatusBadge.tsx\n"
    "  pages/employees/{EmployeesPage,EmployeeDetailPage,EmployeeFormPage}.tsx\n"
    "  pages/teams/TeamsPage.tsx  pages/auth/AcceptInvitePage.tsx\n"
    "  App.tsx  components/layout/navItems.ts  components/layout/Sidebar.tsx\n"
    "  pages/DashboardPage.tsx\n"
    "docs/PERMISSIONS.md  README.md  .gitignore"
))

story.append(PageBreak())

# ===========================================================================
# 2. Data model and migrations
# ===========================================================================
story.append(P("2. Data model and migrations", "h1"))

story.append(table([
    ["Model", "Fields", "Notes"],
    ["organization.Team", "name (unique), lead (nullable FK to Employee, SET_NULL)", "Lead is a person, not a login, because manager scoping and approvals hang off it."],
    ["employees.Employee", "user (one-to-one), first_name, last_name, phone, job_title, team (FK, SET_NULL), manager (self FK, SET_NULL), start_date, employment_type, status", "One record per person; the login lives on User. Never hard-deleted."],
    ["employees.EmployeeInvite", "user (one-to-one), token (UUID, unique), created_at, expires_at, accepted_at", "One active invite per user. Token is single-use and expires after 7 days."],
    ["audit.AuditLog", "actor (nullable FK), action, model, object_id, changes (JSON), created_at", "Append-only; actor is null for system changes such as the seed."],
], [34 * mm, 73 * mm, 58 * mm]))

story.append(P("The circular foreign key, and how the migrations were split", "h2"))
story.append(P(
    "Team.lead points at Employee, while Employee.team points back at Team. A single migration cannot create "
    "both tables. Django resolved this itself by splitting the work, and the resulting order had to be read "
    "and checked rather than assumed:",
))
story.append(CODE(
    "employees.0001   create Employee (without team/user), EmployeeInvite (without user)\n"
    "organization.0001  create Team (lead FK to employees.employee)\n"
    "employees.0002   add Employee.team, Employee.user, EmployeeInvite.user\n"
    "\n"
    "manage.py migrate output on the dev database:\n"
    "  audit.0001_initial        OK\n"
    "  employees.0001_initial    OK\n"
    "  organization.0001_initial OK\n"
    "  employees.0002_initial    OK\n"
))
story.append(P(
    "The migrations are generated, reviewed and committed; nothing destructive is in them. "
    "makemigrations --check --dry-run reports no pending changes.",
))

story.append(P("Database-level rules in force", "h2"))
for item in [
    "Team.name is unique in the database, and a case-insensitive duplicate is rejected by the serializer (the database's unique index is case-sensitive on both SQLite and PostgreSQL).",
    "User.email is unique (from Phase 1) and the manager lowercases the whole address; Employee.user is one-to-one, so one login cannot own two employee records.",
    "EmployeeInvite.token is unique and generated with uuid4; one invite per user is enforced by the one-to-one.",
    "Deleting a user cascades to the employee record and its invite. Deleting a team sets members' team to NULL; deleting a manager sets their reports' manager to NULL. People are not deleted by any API path.",
    "Status and employment type are constrained to their TextChoices at the application layer; status is read-only on the API so the record and the login cannot disagree.",
    "A person cannot be their own manager: rejected by the serializer. This is application-level rather than a database CHECK, because Django's CHECK API differs across the Django 5.0\u20135.2 range this project allows.",
]:
    story.append(B(item))

story.append(PageBreak())

# ===========================================================================
# 3. Invite flow
# ===========================================================================
story.append(P("3. The invite flow", "h1"))
story.append(P(
    "HR never types a password for someone else. Creating a person creates an inactive login with an unusable "
    "password, an employee record and a one-time invite, all inside one transaction, and emails the link.",
))
story.append(CODE(
    "1. POST /api/v1/employees/            HR or admin, with email, names, start date, team, role\n"
    "2. services.create_employee()          one transaction:\n"
    "     User(email, role, is_active=False, unusable password)\n"
    "     Employee(user, ...)\n"
    "     EmployeeInvite(token=uuid4, expires_at=now+7d)\n"
    "     send_mail(...)                     console backend in development\n"
    "3. Email contains:  <FRONTEND_URL>/accept-invite?token=<uuid>\n"
    "4. The person opens the React page and chooses a password.\n"
    "5. POST /api/v1/auth/accept-invite/   public, CSRF-protected: {token, password}\n"
    "6. Serializer validates token (exists, unused, unexpired), employee still active,\n"
    "   and runs Django's password validators.\n"
    "7. Service sets the password, sets is_active=True, marks the invite accepted, and\n"
    "   the view signs the person in. The React page goes straight to the dashboard.\n"
))

story.append(P("Security properties", "h2"))
for item in [
    "The token is a UUID4 (122 random bits), stored unique, single-use, and expires after seven days.",
    "Unknown, used and expired tokens all return the same message: \u201cThis invite link is invalid or has expired.\u201d The endpoint does not help someone guess tokens or enumerate accounts.",
    "A deactivated employee's outstanding invite is refused, so an old link cannot switch an inactive account back on.",
    "The acceptance endpoint is public but CSRF-protected, exactly like login and password reset, because it changes state.",
    "Passwords go through Django's validators; a weak password is a field error, not a 500.",
    "The audit trail deliberately records no employee change for acceptance: the Employee row did not change, only the login did. Deactivation, which does change the record, is audited.",
]:
    story.append(B(item))

story.append(P("Edge cases covered by tests", "h2"))
story.append(table([
    ["Case", "Expected", "Test"],
    ["Token reused after acceptance", "400, generic message", "test_token_can_only_be_used_once"],
    ["Token expired", "400, generic message", "test_expired_token_is_rejected"],
    ["Token never existed", "400, generic message", "test_unknown_token_is_rejected"],
    ["Employee deactivated before accepting", "400", "test_deactivated_employee_cannot_accept"],
    ["Weak password", "400 with a password field error", "test_weak_password_is_a_field_error"],
    ["No CSRF token", "403", "test_accept_requires_a_csrf_token"],
    ["Accept, then log in normally", "200 as the new employee", "test_accepted_password_works_on_the_login_page"],
], [60 * mm, 55 * mm, 50 * mm]))

story.append(PageBreak())

# ===========================================================================
# 4. Audit trail
# ===========================================================================
story.append(P("4. The audit trail", "h1"))
story.append(P(
    "Audit rows are written by signals and only by signals, so one save is one row. Nothing in a view or "
    "service inserts audit rows by hand, which is what keeps the count predictable.",
))

story.append(P("How a row is produced", "h2"))
for item in [
    "pre_save loads the row currently stored under the instance's primary key and takes a JSON-safe snapshot of every concrete field except the primary key. A new instance has no snapshot.",
    "post_save compares that snapshot with the new values. Create writes {\"after\": {...}}, update writes {\"changes\": {field: {\"before\": ..., \"after\": ...}}}, and a save with no differences writes nothing at all.",
    "The service can attach extra changes that live on the User row (email, role) to the instance; the signal folds them into the same single row instead of creating a second one.",
    "post_delete writes {\"before\": {...}} from the instance that was deleted.",
    "The actor comes from a ContextVar set by CurrentUserMiddleware, which runs after AuthenticationMiddleware. Management commands and other request-less writes leave the actor null rather than guessing.",
]:
    story.append(B(item))

story.append(CODE(
    "create:  {\"after\": {\"first_name\": \"Vera\", \"team\": 2, \"status\": \"active\", ...}}\n"
    "update:  {\"changes\": {\"job_title\": {\"before\": \"QA Engineer\", \"after\": \"Staff QA\"}}}\n"
    "delete:  {\"before\": {\"name\": \"Sales\", \"lead\": null}}\n"
    "\n"
    "actor: the signed-in user, or null for the seed and other system writes.\n"
    "model: the lower-case app label, e.g. \"employees.employee\", \"organization.team\".\n"
))

story.append(P("What is tracked today", "h2"))
story.append(P(
    "Employee and Team. LeaveType and LeaveRequest join the same machinery in Phase 3 by being added to "
    "TRACKED_MODELS; no other change is needed. The audit log itself is not tracked, and User changes made "
    "directly in the Django admin are outside the employee audit trail.",
))

story.append(P("Where to read it", "h2"))
story.append(P(
    "Django admin at /admin/audit/auditlog/, read-only: no add, change or delete permission is granted. Only "
    "the seeded admin account is staff and superuser. There is no API or React page for the audit log yet; "
    "that was outside the Phase 2 build list and is recorded as a gap.",
))

story.append(callout(
    "Why not audit every save?",
    "A no-op PATCH (sending the same job title) should not look like a change. The signal skips it, and a test "
    "asserts that a PATCH with unchanged values creates no row. Bulk queryset .update() calls bypass signals by "
    "design; the application always saves model instances, which keeps the trail accurate.",
))

story.append(PageBreak())

# ===========================================================================
# 5. Permissions and API
# ===========================================================================
story.append(P("5. Permissions and API", "h1"))

story.append(P("Scoping rules", "h2"))
story.append(table([
    ["Role", "Employees", "Teams"],
    ["employee", "own record only", "no access (403)"],
    ["manager", "members of teams they lead, plus their own record", "teams they lead (read-only)"],
    ["hr", "everyone, including inactive people", "every team, read and write"],
    ["admin", "everyone, including inactive people", "every team, read and write"],
], [22 * mm, 80 * mm, 63 * mm]))
story.append(P(
    "Out-of-scope records are removed from the queryset, so a record outside your scope is a 404 rather than a "
    "403. A 403 would confirm that the record exists. The scoping lives in apps/core/scoping.py "
    "(scope_employees, scope_teams) and fails closed for unknown roles.",
))

story.append(P("Endpoints added", "h2"))
story.append(table([
    ["Method", "Path", "Allowed"],
    ["GET", "/employees/ (search, team, status, role, page)", "all roles, scoped"],
    ["GET", "/employees/{id}/", "all roles, scoped"],
    ["POST", "/employees/", "hr, admin"],
    ["PATCH / PUT", "/employees/{id}/", "hr, admin; employee on own record, phone only"],
    ["DELETE", "/employees/{id}/", "nobody \u2014 405 with a deactivate hint"],
    ["POST", "/employees/{id}/deactivate/", "hr, admin (an admin target needs an admin)"],
    ["POST", "/employees/{id}/reactivate/", "hr, admin (an admin target needs an admin)"],
    ["GET", "/teams/ (search)", "manager, hr, admin; manager scoped to led teams"],
    ["POST", "/teams/", "hr, admin"],
    ["GET", "/teams/{id}/", "manager, hr, admin; scoped"],
    ["PATCH / PUT", "/teams/{id}/", "hr, admin"],
    ["DELETE", "/teams/{id}/", "hr, admin"],
    ["POST", "/auth/accept-invite/", "public, CSRF-protected, one-time token"],
], [29 * mm, 86 * mm, 50 * mm]))

story.append(P("Field rules that tests enforce", "h2"))
for item in [
    "An employee PATCHing their own record may send only phone. Any other field, or phone mixed with another field, is a 403 with the message \u201cEmployees may only edit their own phone number.\u201d It is not silently ignored.",
    "status is not writable through the API; deactivation and reactivation are explicit actions. This prevents an HR PATCH from leaving employee.status and user.is_active disagreeing.",
    "Only an admin can grant or remove the admin role. HR may assign employee, manager and hr, so it can still create a manager.",
    "Only an admin can deactivate or reactivate an admin account. Without that guard, HR could switch an admin off or back on.",
    "A manager cannot write employee or team data at all; the manager role can read its own team and nothing else.",
]:
    story.append(B(item))

story.append(P("Error shape", "h2"))
story.append(P(
    "Every response still uses {\"detail\": str, \"code\": str, \"fields\": {}} from the Phase 1 exception "
    "handler. Validation failures populate fields with the field names; permission and 404 responses populate "
    "detail. This is what the React forms map onto inline errors.",
))

story.append(PageBreak())

# ===========================================================================
# 6. Backend services, seed and demo data
# ===========================================================================
story.append(P("6. Services, seed and demo data", "h1"))

story.append(table([
    ["Service", "What it does", "Transaction"],
    ["create_employee(actor, data)", "Checks the role grant, creates the inactive User, the Employee and the invite, then emails the link.", "atomic"],
    ["update_employee(employee, actor, data)", "Applies User email/role changes and Employee fields; hands the User diff to the audit signal.", "atomic"],
    ["deactivate_employee(employee, actor)", "Sets status inactive and the login inactive; refuses an admin target unless the actor is an admin.", "atomic"],
    ["reactivate_employee(employee, actor)", "Restores both, with the same admin guard. Deactivation is not a dead end.", "atomic"],
    ["accept_invite(invite, password)", "Sets the password, activates the login, marks the invite accepted.", "atomic"],
    ["send_invite_email(invite)", "Builds the FRONTEND_URL link and sends it with Django's mail backend.", "inside create"],
], [46 * mm, 96 * mm, 23 * mm]))

story.append(P("Demo company created by seed_users", "h2"))
story.append(table([
    ["Role", "Email", "Team", "Manager"],
    ["admin", "admin@hrms.test", "People Ops", "\u2014"],
    ["hr", "hr@hrms.test", "People Ops (lead)", "\u2014"],
    ["manager", "manager@hrms.test", "Engineering (lead)", "\u2014"],
    ["employee", "employee@hrms.test", "Engineering", "Meera Manager"],
    ["employee", "employee2@hrms.test", "Engineering", "Meera Manager"],
], [22 * mm, 48 * mm, 48 * mm, 47 * mm]))
story.append(P(
    "All five use the password DemoPass123!. The command is idempotent: it creates the teams before the "
    "people, creates the people with their team, then links managers and team leads in a second pass. Re-running "
    "it resets demo passwords, keeps the counts at 5/5/2, and does not duplicate rows.",
))

story.append(P("The admin account, and the error that exposed a real bug", "h2"))
story.append(P(
    "Only admin@hrms.test is staff. The Django admin at /admin/ is not the HRMS application; it is Django's "
    "own admin, and it is deliberately restricted to that account. A manager who visits it is signed in but "
    "not authorized, which is the message the browser shows. That part is correct behaviour.",
))
story.append(P(
    "The error was useful because it led to a real defect: the seed made admin@ staff but not superuser, and a "
    "staff user without model permissions opens an empty admin. The seed now grants both flags, two tests cover "
    "it (admin reaches the audit and employee list pages; a manager is redirected to the admin login), and the "
    "local database was re-seeded. Verified against the dev database: /admin/, /admin/audit/auditlog/, "
    "/admin/employees/employee/ and /admin/organization/team/ all return 200 for admin@hrms.test.",
))

story.append(callout(
    "If you land on the admin as the wrong user",
    "The admin login page offers \u201clog in to a different account\u201d, or open /admin/logout/ and sign in "
    "again. The email field needs the full address (admin@hrms.test), not the word admin. The React app at "
    "http://localhost:5173 is where the manager, HR and employee roles work.",
))

story.append(PageBreak())

# ===========================================================================
# 7. Frontend
# ===========================================================================
story.append(P("7. Frontend implementation", "h1"))

story.append(table([
    ["Page", "Route", "Behaviour"],
    ["Employees", "/employees", "Search (debounced) across name, email and job title; team, status and role filters; 20 per page with a count and page controls; role and status badges; table from 768px up, cards below that."],
    ["Employee detail", "/employees/:id", "Profile, team, manager, start date, employment type and access role; Edit, Deactivate (confirmation dialog) or Reactivate, depending on status and role."],
    ["New employee", "/employees/new", "react-hook-form + zod, inline errors, team and manager selects, role rules, start date; on success goes to the new profile."],
    ["Edit employee", "/employees/:id/edit", "Same form prefilled; role is locked when HR edits an admin, matching the API rule."],
    ["Teams", "/teams", "Search, member counts, lead names, create/edit dialog with an optional lead."],
    ["Accept invite", "/accept-invite?token=...", "Public page: password + confirmation, signs in on success, clear message for an invalid or expired link."],
], [26 * mm, 40 * mm, 99 * mm]))

story.append(P("Data layer", "h2"))
for item in [
    "src/api/employees.ts and src/api/teams.ts hold every query and mutation: useEmployees, useEmployee, useCreateEmployee, useUpdateEmployee, useSetEmployeeStatus, useTeams, useCreateTeam, useUpdateTeam. Components never call fetch.",
    "Query keys are namespaced ([\"employees\", ...], [\"teams\", ...]) so one invalidation refreshes lists and details after a mutation. Pagination uses keepPreviousData so changing pages does not blank the table.",
    "src/api/client.ts gained apiPatch; the existing error parsing turns {detail, code, fields} into ApiError, which forms map onto inline errors.",
]:
    story.append(B(item))

story.append(P("UI primitives added", "h2"))
for item in [
    "table, badge and skeleton follow the shadcn/ui idiom already in the project.",
    "select is a native &lt;select&gt; styled with Tailwind. It keeps the mobile picker, keyboard behaviour and 375px layout correct without another dependency.",
    "dialog is a small hand-written modal: portal, overlay click to close, Escape, body scroll lock, focus moved in and restored on close, and a Tab trap. The close button sits last in the DOM so the form's first field receives focus.",
    "Field, states (ErrorState, EmptyState) and Pagination keep the loading, empty, error and paging patterns identical across pages.",
]:
    story.append(B(item))

story.append(P("Routing and navigation", "h2"))
for item in [
    "Employees and Teams are now real, enabled sidebar items, filtered by role. Time off, Approvals and Audit log remain disabled \u201csoon\u201d entries until their phases.",
    "Routes: /employees and /employees/:id require admin, hr or manager; /employees/new, /employees/:id/edit and /teams require admin or hr; /accept-invite is public. The guards are a UX layer; the API remains the gate.",
    "The dashboard\u2019s \u201ccoming next\u201d card and the sidebar footer now describe Phase 3 rather than Phase 2.",
]:
    story.append(B(item))

story.append(callout(
    "Not verified in a browser",
    "The React code typechecks and the production bundle builds, and every API call behind these pages was "
    "exercised over HTTP. But nobody has rendered the pages, opened a dialog, typed in a filter or looked at "
    "the layout at 375px. This section describes implemented behaviour, not observed behaviour.",
))

story.append(PageBreak())

# ===========================================================================
# 8. Verification performed
# ===========================================================================
story.append(P("8. Verification performed", "h1"))
story.append(P("Every command below was run; the output shown is the real output."))

story.append(P("8.1 Static checks, migrations and seed", "h2"))
story.append(CODE(
    "python manage.py check                        -> System check identified no issues (0 silenced)\n"
    "python manage.py makemigrations --check --dry-run -> No changes detected\n"
    "python manage.py migrate --noinput            -> audit.0001, employees.0001,\n"
    "                                                 organization.0001, employees.0002 applied\n"
    "python manage.py seed_users                   -> 5 users, 5 employees, 2 teams\n"
    "\n"
    "database after the runs:\n"
    "  users 5   employees 5   teams 2   audit rows 22   leftover verify users 0\n"
))

story.append(P("8.2 Test suite", "h2"))
story.append(CODE("pytest -q -p no:cacheprovider   ->  153 passed in 2.76s   (exit 0)\n"
                  "\n"
                  "Phase 1 had 67 tests. Phase 2 adds 86, across four new files.\n"))

story.append(P("8.3 What the tests cover", "h2"))
story.append(table([
    ["Area", "Examples"],
    ["Employee scoping", "hr and admin see all; manager sees own team plus self; employee sees one record; another record is 404 for employee and for a manager outside the team; anonymous is rejected."],
    ["Employee writes", "HR create with invite; HR cannot grant admin; admin can; manager and employee cannot create; duplicate email is a field error; required fields reported."],
    ["Self-edit", "own phone 200; own job title 403 with the exact message; phone mixed with another field 403; another record 404; manager cannot PATCH a team member."],
    ["HR updates", "job title, team and manager changed; email change updates the login; duplicate email rejected; self-manager rejected; role change to manager allowed, to admin refused."],
    ["Deactivation", "login stops; idempotent and audited once; reactivate restores login; manager/employee refused; HR cannot deactivate or reactivate an admin."],
    ["Filters and pagination", "team, status and role filters; search by name and email; unknown status is a 400; the paginated envelope is present."],
    ["Teams", "scoping for every role; create with and without a lead; case-insensitive duplicate rejected; manager read-only; HR rename and delete; members keep their record; member counts; search."],
    ["Invites", "one email with the token; cannot log in before accepting; acceptance activates and signs in; reused, expired, unknown and deactivated cases; weak password; CSRF."],
    ["Audit", "create with actor and new values; update diff only; role change in the same row; no-op writes nothing; deactivation row; team create/update/delete rows; null actor without a request; login and reads write nothing."],
    ["Seed", "roles, teams, employee links, idempotency, admin can use the Django admin, manager is redirected."],
], [40 * mm, 125 * mm]))

story.append(P("8.4 Live end-to-end run over HTTP", "h2"))
story.append(P(
    "A throwaway client (removed afterwards) drove a real runserver on 127.0.0.1:8000 with a cookie jar and "
    "CSRF headers. Confirmed:",
))
story.append(CODE(
    "health 200; csrf 200; HR login 200\n"
    "employees 200 (5 people); teams 200 (2 teams, Engineering lead and member count correct)\n"
    "create employee 201; invite email printed with /accept-invite?token=...\n"
    "search for the new address 200 (1 result)\n"
    "accept invite 200; me 200; own employee list 200 (1 record); own detail 200\n"
    "PATCH own phone 200; PATCH own job_title 403 (\"Employees may only edit their own phone number.\")\n"
    "GET /teams/ as employee 403; DELETE own employee 405\n"
    "logout 204; manager login 200; manager teams 200 (1); manager employees 200 (3, all Engineering)\n"
    "manager GET the new hire (People Ops) 404\n"
    "employee login 200; employees 200 (1 record)\n"
    "HR login; deactivate 200; deactivated login 400; reactivate 200; login 200 again\n"
    "audit: create by hr@, update by the new hire (phone), update by hr (deactivate),\n"
    "       update by hr (reactivate)\n"
))

story.append(P("8.5 Django admin access check", "h2"))
story.append(CODE(
    "admin login: True\n"
    "/admin/                         200\n"
    "/admin/audit/auditlog/          200\n"
    "/admin/employees/employee/      200\n"
    "/admin/organization/team/       200\n"
    "\n"
    "manager login, GET /admin/     302 -> /admin/login/ (expected: not staff)\n"
))

story.append(P("8.6 Frontend", "h2"))
story.append(CODE(
    "tsc --noEmit      -> exit 0\n"
    "npm run build     -> 1733 modules transformed\n"
    "                     dist/assets/index-*.css  20.43 kB (gzip 5.01 kB)\n"
    "                     dist/assets/index-*.js  455.16 kB (gzip 139.05 kB)\n"
    "                     built in 17.31s\n"
))

story.append(PageBreak())

# ===========================================================================
# 9. Defects and errors solved
# ===========================================================================
story.append(P("9. Defects and errors solved", "h1"))
story.append(P(
    "Ten application-level problems and a class of toolchain failures were found and fixed. Severity and how "
    "each was caught are stated, because some were design corrections rather than test failures.",
))

for item in defect(
    "9.1 Hard delete answered 403 instead of 405",
    "Medium \u2014 wrong API contract; a client would read it as a permission problem rather than an unsupported operation.",
    "DELETE /api/v1/employees/{id}/ returned 403 after the permission class was changed to fail closed. The earlier test expected 405.",
    "DRF runs permission checks before it dispatches to the method handler. The fail-closed permission class refused the destroy action before the viewset could report that the method is not allowed.",
    "The permission class now lets destroy through to an explicit destroy() that always raises MethodNotAllowed, and the view has no other delete path. The 405 detail tells the caller to deactivate instead.",
    "test_delete_is_not_allowed passes, and the live run returned 405 with the deactivate message. No code path can hard-delete a person.",
):

    story.append(item)

for item in defect(
    "9.2 Email and role changes were invisible to the audit log",
    "High \u2014 a role grant is one of the most important changes in the system; it must be recorded.",
    "Changing an employee's email or role produced no employee audit row, because both fields live on User, and the audit signal only snapshots Employee.",
    "The snapshot compared model fields only. Saving the User row never touches Employee, so the diff was empty and the signal correctly skipped it.",
    "update_employee computes the User diff itself, attaches it to the employee instance as _audit_extra_changes, and the post_save signal folds it into the same row as any model-field changes. One action still means one row.",
    "test_role_change_lands_in_the_same_row asserts one row containing both job_title and role changes, with before/after values.",
):

    story.append(item)

for item in defect(
    "9.3 Audit rows could duplicate or appear on no-op saves",
    "Medium \u2014 a noisy or missing trail is worse than none; the Handbook explicitly warns about duplicate rows.",
    "Nothing prevented a save with unchanged values from writing an update row, and a second audit hook could have doubled rows for one change.",
    "The first design wrote a row in post_save without comparing against stored values.",
    "pre_save stashes a snapshot; post_save diffs it and returns early when nothing changed. No service writes audit rows by hand, so exactly one path can produce a row.",
    "test_a_save_that_changes_nothing_writes_nothing and the team update test (exactly one row) pass. Raw SQL .update() bypasses signals by design; the app saves instances.",
):

    story.append(item)

for item in defect(
    "9.4 Employees could send edits to fields they may not change",
    "High \u2014 a validation-only approach would either silently ignore the attempt or require every future field to remember the rule.",
    "An employee PATCHing their own record with {\"job_title\": ...} had to be rejected, not accepted and ignored.",
    "Permission checks that consider only the action cannot express \u201conly this field, only on your own row\u201d.",
    "The object-level permission compares the request body's keys with {phone} for the employee role and returns 403 with a specific message; the queryset still limits the reachable rows.",
    "Own phone is 200; own job title is 403; phone mixed with another field is 403; another record is 404. All four are tested.",
):

    story.append(item)

for item in defect(
    "9.5 Manager scoping needed its own implementation",
    "High \u2014 wrong scoping either leaks another team's data or hides a manager's own record.",
    "The Phase 1 helper scope_for_own_team filters on employee__team__lead__user, which works for records that hang off an employee (leave requests), but not for Employee itself, and a manager is also an employee.",
    "One generic strategy was being asked to serve two different shapes of data.",
    "scope_employees filters on Q(team__lead__user=user) | Q(user=user) for managers and user=user for employees; scope_teams filters lead__user for managers. HR and admin get everything; everything else fails closed.",
    "The matrix tests cover all four roles on both resources, and the live run confirmed a manager sees three Engineering people and gets 404 for a People Ops hire.",
):

    story.append(item)

for item in defect(
    "9.6 A seeded admin could not actually use the Django admin",
    "High for operations \u2014 it made the documented way to inspect the audit table unusable, and it is the error the user hit in the browser.",
    "Signing in as manager@hrms.test at /admin/ showed \u201cYou are authenticated as manager@hrms.test, but are not authorized to access this page.\u201d Investigating that surfaced the deeper issue: admin@hrms.test was staff but not superuser.",
    "seed_users set is_staff for the admin role but never is_superuser. A staff user with no model permissions can log in and then sees an empty admin index; the model pages are forbidden.",
    "The seed now sets is_staff and is_superuser for the admin role and clears both for the others, then the local database was re-seeded. Two tests cover admin access and the manager redirect.",
    "admin@ opens /admin/, the audit log, employees and teams (all 200); a manager is redirected to the admin login. The manager message itself is expected behaviour and is now explained in the README.",
):

    story.append(item)

for item in defect(
    "9.7 Privilege escalation through employee administration",
    "High \u2014 HR manages people; it must not be able to create an admin or switch an admin off and on.",
    "HR could otherwise create an employee with role=admin, or deactivate/reactivate an admin account.",
    "Role assignment and deactivation were ordinary serializer/view operations with no rule about who may touch the admin role.",
    "services.assert_can_assign_role refuses to grant or remove admin unless the actor is an admin, and deactivate/reactivate refuse an admin target unless the actor is an admin. HR may still assign employee, manager and hr.",
    "Five tests: HR cannot create an admin, admin can; HR can create a manager; HR cannot change a role to admin; HR cannot deactivate or reactivate an admin.",
):

    story.append(item)

for item in defect(
    "9.8 Invite links had to be safe by construction",
    "High \u2014 an invite is a password-setting credential.",
    "A token could have been reused, accepted after expiry, or used to revive a deactivated account; a weak password could have produced a 500.",
    "Acceptance initially looked only at whether the token existed.",
    "The serializer rejects missing, accepted, expired and deactivated-employee cases with one generic message, runs Django's password validators and converts their errors to a field error; the service applies the change in a transaction and the view signs the person in.",
    "Eight invite tests plus the live accept-and-log-in run; reuse, expiry, unknown token, deactivation, weak password and missing CSRF are all covered.",
):

    story.append(item)

for item in defect(
    "9.9 Circular foreign key across two apps",
    "Medium \u2014 it blocks migrations if handled naively.",
    "Team.lead points at Employee and Employee.team points at Team, so neither app's initial migration could own both tables.",
    "A genuine model-level cycle, not an ordering mistake.",
    "Let Django split it: employees.0001 creates the models without the cross-app fields, organization.0001 adds Team with lead, employees.0002 adds team, user and the invite's user. The order was reviewed and the migrations committed.",
    "migrate applied all four cleanly, and makemigrations --check reports no pending changes.",
):

    story.append(item)

for item in defect(
    "9.10 Toolchain failures in the sandbox",
    "Process \u2014 no application impact, but it limited what could be verified.",
    "(a) npm run build failed with spawn EPERM while esbuild started its helper process. (b) pip install ruff failed with permission denied writing a wheel metadata file in the temp directory, twice, including inside the workspace. (c) The resulting pip temp directories could not be deleted. (d) npm run typecheck printed a PowerShell $LASTEXITCODE error from npm.ps1 even though tsc succeeded.",
    "(a) The Windows sandbox blocks Node child processes that capture output through pipes; esbuild uses one. (b) The same confinement prevented the installer's temp writes. (c) The sandbox's deny entry on DeleteSubdirectoriesAndFiles blocks removing subdirectories, which is the intended confinement, not a fault. (d) A quirk of the npm PowerShell shim under the harness.",
    "(a) The build was rerun once with wider access and succeeded. (b) No lint run was possible; ruff is declared in requirements.txt for the next session. (c) The empty .tmp/pip-* directories are left in place and .tmp/ is gitignored. (d) tsc was invoked directly (node_modules/.bin/tsc.cmd) and reported exit 0.",
    "The production bundle was built and its sizes recorded; the test suite and typecheck are unaffected. The missing lint is listed as a gap, not glossed over.",
):

    story.append(item)

story.append(P("9.11 Bugs in the throwaway verification script", "h2"))
story.append(P(
    "Recorded because it shows the live run was real and iterative, not a transcript: the first pass expected "
    "200 from logout (Django returns 204); the second asserted exactly five employees while a previous partial "
    "run had left a throwaway person behind, so the script now cleans leftovers before it starts; and the third "
    "assumed a \u201cSales\u201d team that exists only in the test fixtures, not in the seeded company (the seed "
    "has People Ops). Each was a defect in the script, fixed and rerun, not in the application.",
))

story.append(PageBreak())

# ===========================================================================
# 10. Not verified, limitations, and reproduction
# ===========================================================================
story.append(P("10. What is not verified", "h1"))
story.append(table([
    ["Item", "Status"],
    ["React pages in a browser", "NOT DONE. Bundle builds, APIs exercised over HTTP, but no page has been rendered or clicked."],
    ["375px layout and dialogs", "NOT DONE. Code-only; responsive classes and the custom dialog are unobserved."],
    ["PostgreSQL", "NOT DONE. Everything ran on SQLite. The models and migrations use no Postgres-specific feature yet, but they have not been applied to a server."],
    ["ruff lint", "NOT RUN. Not installed; installing was blocked by the sandbox. Declared in requirements.txt."],
    ["Frontend lint and tests", "NOT AVAILABLE. npm run lint and npm run test do not exist; ESLint and Vitest were never set up in Phase 1."],
    ["Django admin forms", "PARTIAL. List pages open for the admin; editing through the admin was not exercised."],
    ["Audit API or page", "NOT BUILT. Outside the Phase 2 build list; rows are visible read-only in Django admin."],
    ["Invite resend", "NOT BUILT. A lost invite currently means HR has no UI to reissue one."],
    ["Employee self-service profile page", "NOT BUILT. The API allows an employee to read their own record and edit their phone; there is no page for it yet."],
    ["Phase 3", "NOT STARTED."],
], [55 * mm, 110 * mm]))

story.append(P("Known limitations to carry forward", "h2"))
for item in [
    "The teams page requests up to 100 teams and has no pagination UI; the manager dropdown in the employee form is likewise limited to 100 colleagues.",
    "Manager scoping is defined as \u201cteams you lead\u201d. A manager who is a member of a team they do not lead does not see that team; this matches the approvals model and is documented in PERMISSIONS.md.",
    "User rows edited directly in the Django admin are not part of the employee audit trail.",
    "The audit actor is request-scoped; management-command writes are correctly attributed to nobody.",
    "Employee.status is read-only on the API, so a data fix must go through the actions (or the Django admin, which is deliberately read-only for the status).",
    "docs/HANDBOOK.md is still absent; the Agent instructions in docs/AGENTS.md point at it, but only the PDF exists.",
]:
    story.append(B(item))

story.append(P("11. Reproduce the phase", "h1"))
story.append(CODE(
    "cd D:\\HRMS\\backend\n"
    ".venv\\Scripts\\python.exe manage.py check\n"
    ".venv\\Scripts\\python.exe manage.py migrate\n"
    ".venv\\Scripts\\python.exe manage.py seed_users\n"
    ".venv\\Scripts\\python.exe -m pytest -q\n"
    ".venv\\Scripts\\python.exe manage.py runserver\n"
    "\n"
    "# second terminal\n"
    "cd D:\\HRMS\\frontend\n"
    "npm run typecheck\n"
    "npm run dev\n"
))

story.append(P("Demo script (5 minutes)", "h2"))
for item in [
    "Sign in at http://localhost:5173 as hr@hrms.test / DemoPass123!.",
    "Employees: filter by Engineering, search for a name, then create a person (team People Ops, no manager).",
    "Copy the invite link printed in the Django console and open it; choose a password.",
    "You are now signed in as that person. Their Employees page shows only their own record.",
    "Sign in as manager@hrms.test: Employees shows only Engineering, and Teams is not in the sidebar.",
    "Sign in as hr@, open the new hire, deactivate them; a login attempt now fails. Reactivate.",
    "Sign in at http://127.0.0.1:8000/admin/ as admin@hrms.test / DemoPass123! and open Audit log.",
]:
    story.append(B(item))

story.append(Spacer(1, 5 * mm))
story.append(callout(
    "Bottom line",
    "Phase 2 is complete against the Handbook's checklist and verified by 153 tests plus a real HTTP session: "
    "teams and people with role-scoped access, invites that replace passwords, deactivation instead of deletion, "
    "and an audit trail with exactly one row per action. The defects that mattered most \u2014 a wrong delete "
    "status code, an audit log blind to role changes, manager scoping, missing privilege guards, and an admin "
    "account that could not open the admin \u2014 are fixed and covered. The honest gaps remain the browser, "
    "PostgreSQL and lint.",
    GREEN,
    "#ecfdf5",
))

doc.build(story)
print(f"Wrote {OUT} ({OUT.stat().st_size} bytes)")
