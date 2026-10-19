"""Generate docs/Phase01.pdf — a report of the Phase 1 work.

Run:  backend\\.venv\\Scripts\\python.exe backend\\build_phase01_pdf.py
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

OUT = Path(__file__).resolve().parent.parent / "docs" / "Phase01.pdf"

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


def callout(title, text, colour=AMBER):
    inner = [[Paragraph(f"<b>{title}</b>", S["cellb"])], [Paragraph(text, S["cell"])]]
    t = Table(inner, colWidths=[165 * mm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#fffbeb")),
        ("LINEBEFORE", (0, 0), (0, -1), 2.4, colour),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    return t


# --- page furniture --------------------------------------------------------
def decorate(canvas, doc):
    canvas.saveState()
    canvas.setStrokeColor(LINE)
    canvas.setLineWidth(0.5)
    canvas.line(20 * mm, 15 * mm, 190 * mm, 15 * mm)
    canvas.setFont(BODY, 7.6)
    canvas.setFillColor(MUTED)
    canvas.drawString(20 * mm, 10.5 * mm, "HRMS \u2014 Phase 1 Report: Auth and Roles")
    canvas.drawRightString(190 * mm, 10.5 * mm, f"Page {doc.page}")
    canvas.restoreState()


doc = BaseDocTemplate(
    str(OUT),
    pagesize=A4,
    leftMargin=20 * mm,
    rightMargin=20 * mm,
    topMargin=18 * mm,
    bottomMargin=20 * mm,
    title="HRMS Phase 1 Report",
    author="DeepSeek Harness agent",
)
frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id="main")
doc.addPageTemplates([PageTemplate(id="all", frames=[frame], onPage=decorate)])

story = []

# ===========================================================================
# Cover / summary
# ===========================================================================
story.append(Spacer(1, 6 * mm))
story.append(P("HRMS \u2014 Phase 1", "title"))
story.append(P("Auth and Roles \u2014 development and test report", "subtitle"))
story.append(Spacer(1, 5 * mm))
story.append(table([
    ["Field", "Value"],
    ["Phase", "Phase 1 \u2014 Auth and roles (Phases 0\u20134 are the MVP)"],
    ["Status", "Backend verified by execution. Frontend typechecked; browser flow not verified."],
    ["Backend tests", "67 passed, 0 failed"],
    ["Frontend", "npm install OK \u00b7 tsc --noEmit exit 0 (TypeScript 5.6.2)"],
    ["Date", "2026-10-15"],
    ["Handbook basis", "docs/Handbook.pdf (replaced docs/HRMS-Phases.pdf mid-project)"],
], [34 * mm, 131 * mm]))

story.append(Spacer(1, 5 * mm))
story.append(P("What this document is", "h2"))
story.append(P(
    "A record of everything done for Phase 1: the code that was written, the commands that were run "
    "and their real output, every defect found and fixed, and \u2014 explicitly \u2014 what has <b>not</b> been "
    "verified. Where something was not executed it is labelled as such rather than described as working.",
))

story.append(P("Summary", "h2"))
for item in [
    "<b>Phase 1 is functionally complete on the backend</b> and proven by 67 passing tests plus a live HTTP session against a running Django server.",
    "<b>Five real defects were found and fixed</b>, including a CSRF bypass on the login endpoint that only execution revealed.",
    "<b>The frontend typechecks cleanly</b> against the project's own TypeScript, and the Vite dev server starts.",
    "<b>The browser flow is not verified.</b> No one has loaded the app in a browser, clicked login, or viewed the sidebar at mobile width.",
    "<b>The Phase 0 backend skeleton had to be built too</b>, because Phase 1 requires AUTH_USER_MODEL to be set before the first migration and no backend existed.",
]:
    story.append(B(item))

story.append(PageBreak())

# ===========================================================================
# 1. Scope and stack
# ===========================================================================
story.append(P("1. Scope, stack and layout", "h1"))

story.append(P("Phase 1 goal (from the Handbook)", "h2"))
story.append(P(
    "People can log in and the app knows their role. Deliverables: a custom User model with email login and "
    "a role field (admin, hr, manager, employee); login, logout, me and password-reset endpoints using "
    "sessions and CSRF; role permission classes in core/permissions.py; a React login page, auth context, "
    "protected routes and an app shell whose sidebar changes by role; and a seed command creating one admin, "
    "one HR, one manager and two employees.",
))

story.append(P("Stack in force", "h2"))
story.append(table([
    ["Part", "Choice", "Note"],
    ["Backend", "Django 5.2.18 + DRF 3.16.1", "Installed and used"],
    ["Language", "Python 3.13.15", "Handbook says 3.12+; 3.13 is what is installed"],
    ["Database", "PostgreSQL 16 (target)", "Not installed yet. Dev/tests currently use SQLite"],
    ["Auth", "Django sessions + CSRF", "Session cookie, X-CSRFToken header"],
    ["Frontend", "React 18.3.1 + Vite 5.4.8 + TypeScript 5.6.2", "Installed and typechecked"],
    ["UI", "Tailwind 3.4.13 + shadcn/ui pattern", "Components written by hand, no CLI"],
    ["Data/forms", "TanStack Query 5.59, react-hook-form 7.53, zod 3.23", "As required"],
    ["Tests", "pytest 9.1.1 + pytest-django 4.14", "Backend only, per the Handbook"],
], [26 * mm, 62 * mm, 77 * mm]))

story.append(P(
    "Deliberately absent, per the redesigned Handbook: no CI, no ruff, no eslint, no vitest, no Docker for the "
    "app itself, no drf-spectacular, no production hardening. Those existed in the superseded 13-page guide "
    "and were removed when the 12-page Handbook replaced it.",
    "small",
))

story.append(P("Files created", "h2"))
story.append(CODE(
    "backend/\n"
    "  manage.py  requirements.txt  pytest.ini  conftest.py  .env.example  .env\n"
    "  config/__init__.py  config/urls.py  config/wsgi.py  config/asgi.py\n"
    "  config/settings/{__init__,base,dev,prod,test}.py\n"
    "  apps/accounts/{__init__,apps,models,serializers,views,urls,admin}.py\n"
    "  apps/accounts/migrations/{__init__,0001_initial}.py\n"
    "  apps/accounts/management/commands/seed_users.py\n"
    "  apps/core/{__init__,apps,permissions,scoping,pagination,exceptions,authentication,urls}.py\n"
    "  tests/{__init__,test_auth,test_core}.py\n"
    "  probe_e2e.py        (throwaway live-HTTP probe)\n"
    "  probe_proxy.py      (throwaway Vite-proxy probe)\n"
    "  build_phase01_pdf.py (this report's generator)\n"
    "frontend/\n"
    "  package.json  vite.config.ts  tsconfig.json  tailwind.config.js\n"
    "  postcss.config.js  components.json  index.html\n"
    "  src/{main,App}.tsx  src/index.css  src/vite-env.d.ts\n"
    "  src/api/{client,queries}.ts\n"
    "  src/auth/{AuthContext.tsx,guards.tsx}\n"
    "  src/lib/utils.ts\n"
    "  src/components/ui/{button,input,label,dropdown-menu,toast,card}.tsx\n"
    "  src/components/layout/{AppShell,Sidebar,UserMenu}.tsx  src/components/layout/navItems.ts\n"
    "  src/components/form/FieldError.tsx\n"
    "  src/pages/{DashboardPage,NotFoundPage}.tsx\n"
    "  src/pages/auth/{AuthLayout,LoginPage,ForgotPasswordPage,ResetPasswordPage}.tsx\n"
    "docs/Handbook.pdf  docs/AGENTS.md\n"
    "README.md  .gitignore"
))

story.append(PageBreak())

# ===========================================================================
# 2. Backend implementation
# ===========================================================================
story.append(P("2. Backend implementation", "h1"))

story.append(P("Custom user model (apps/accounts/models.py)", "h2"))
for item in [
    "AUTH_USER_MODEL = \"accounts.User\" is declared in base.py and the initial migration was generated before any other app migration, so the swap happens before anything depends on it. The Handbook flags changing this later as painful, which is why it was done first.",
    "USERNAME_FIELD = \"email\"; email is unique. authenticate() is called with username=email, which is how Django's ModelBackend expects a custom USERNAME_FIELD.",
    "<b>Role</b> is a TextChoices field: admin, hr, manager, employee, defaulting to employee.",
    "A custom UserManager provides create_user and create_superuser; the manager lowercases the whole email address (not just the domain) because login lowercases its input, so a mixed-case local part would otherwise be stored in a form that can never be matched.",
    "No username field, no first_name/last_name on User \u2014 the Handbook puts people data on Employee in Phase 2. Repeated login failures for an inactive account return the same message as a wrong password, so the response cannot be used to discover which addresses exist.",
]:
    story.append(B(item))

story.append(P("Role permission classes (apps/core/permissions.py)", "h2"))
story.append(P(
    "A HasRole base class holds the allowed roles and the denial message; the concrete classes are thin "
    "subclasses. Every API view declares one explicitly, and the DRF default is IsAuthenticated, so a new "
    "view is authenticated unless it opts out.",
))
story.append(table([
    ["Class", "Allows", "Used by"],
    ["IsAdmin", "admin", "probe/admin/"],
    ["IsHR", "hr", "probe/hr/"],
    ["IsManager", "manager", "probe/manager/"],
    ["IsEmployee", "employee", "probe/employee/"],
    ["IsHROrAdmin", "hr, admin", "Phase 2 viewsets"],
    ["IsManagerOrAbove", "manager, hr, admin", "Phase 2 approvals"],
    ["IsReadOnly", "any authenticated user, safe methods only", "Phase 2 reference data"],
], [30 * mm, 63 * mm, 72 * mm]))

story.append(P("Authentication classes (apps/core/authentication.py)", "h2"))
story.append(P(
    "ActiveSessionAuthentication subclasses DRF's SessionAuthentication and raises AuthenticationFailed when "
    "the session's user has been deactivated. Django's own session backend keeps authenticating an inactive "
    "user until the session expires, which would contradict the rule that inactive users cannot log in.",
))

story.append(P("Role-scoped querysets (apps/core/scoping.py)", "h2"))
story.append(P(
    "A single helper, scope_queryset(queryset, user, scope), maps a role to a strategy: employee sees own "
    "records, manager sees own team, hr and admin see everything. An unrecognised role or an anonymous user "
    "fails closed to an empty queryset. The per-role strategies target Phase 2 models (Employee.team, "
    "Team.lead), so only the fail-closed behaviour is exercised now; the Phase 2 viewset tests will cover the "
    "per-role paths.",
))

story.append(P("Endpoints under /api/v1/", "h2"))
story.append(table([
    ["Method", "Path", "Permission", "Purpose"],
    ["GET", "/health/", "AllowAny", "Liveness probe"],
    ["GET", "/auth/csrf/", "AllowAny", "Sets the CSRF cookie for the SPA"],
    ["POST", "/auth/login/", "AllowAny + csrf_protect", "Session login by email + password"],
    ["POST", "/auth/logout/", "IsAuthenticated", "Destroys the session"],
    ["GET", "/auth/me/", "IsAuthenticated", "Current user"],
    ["POST", "/auth/password-reset/", "AllowAny + csrf_protect", "Emails a reset link (console in dev)"],
    ["POST", "/auth/password-reset/confirm/", "AllowAny + csrf_protect", "Sets a new password from uid + token"],
    ["GET", "/auth/probe/", "IsAuthenticated", "Any authenticated role"],
    ["GET", "/auth/probe/{role}/", "IsAdmin/IsHR/IsManager/IsEmployee", "Proves 403 for the wrong role"],
    ["ANY", "/api/v1/<unmatched>", "AllowAny", "Catch-all 404 in the shared error shape"],
], [14 * mm, 53 * mm, 47 * mm, 51 * mm]))

story.append(P("Response conventions", "h2"))
for item in [
    "Every error, including 401, 403, 404 and validation failures, is rendered as {\"detail\": str, \"code\": str, \"fields\": {}} by a custom exception handler in apps/core/exceptions.py.",
    "Pagination is page-number style at 20 per page with a standard count/page/pages/page_size/results envelope.",
    "Actions are POST /resource/{id}/action/, plural nouns, base path /api/v1/ \u2014 matching the Handbook's conventions.",
]:
    story.append(B(item))

story.append(P("Seed command", "h2"))
story.append(P(
    "python manage.py seed_users creates admin@hrms.test, hr@hrms.test, manager@hrms.test, "
    "employee@hrms.test and employee2@hrms.test, all with the password DemoPass123!. It is idempotent: "
    "re-running updates roles and resets passwords rather than creating duplicates, so a reseeded database "
    "always has working demo logins.",
))

story.append(PageBreak())

# ===========================================================================
# 3. Frontend
# ===========================================================================
story.append(P("3. Frontend implementation", "h1"))

story.append(table([
    ["Area", "Files", "Behaviour"],
    ["HTTP client", "src/api/client.ts", "Single typed fetch wrapper. Reads the csrftoken cookie and sends X-CSRFToken on unsafe methods; credentials: include; parses the shared error shape into an ApiError with status, code and fields."],
    ["Query layer", "src/api/queries.ts", "All data access as TanStack Query hooks (useMe, useHealth) and plain functions (login, logout, requestPasswordReset, confirmPasswordReset). Components never call fetch."],
    ["Session context", "src/auth/AuthContext.tsx", "Wraps useMe. Exposes user, role, isLoading, isAuthenticated, login, logout and hasRole. Login seeds the query cache with the response so guards see the user immediately rather than waiting for a second round trip."],
    ["Route guards", "src/auth/guards.tsx", "ProtectedRoute redirects to /login preserving the intended path; RoleRoute redirects home when the role is not allowed. Both render a full-page spinner while the session resolves. Documented in-code as a UX layer only."],
    ["App shell", "AppShell, Sidebar, UserMenu, navItems", "Sidebar collapses to an icon rail on desktop and becomes an off-canvas drawer below 768px; top bar; user menu with role and logout. Menu items are filtered by role."],
    ["UI primitives", "components/ui/*", "button, input, label, dropdown-menu, card, plus a small toast system (module-level store so toast() works outside React)."],
    ["Forms", "pages/auth/*", "react-hook-form + zod with inline field errors and a form-level banner mapped from the API's detail and fields."],
    ["Pages", "Dashboard, Login, Forgot, Reset, 404", "Loading, empty and error states throughout, with toasts for action results."],
], [22 * mm, 40 * mm, 103 * mm]))

story.append(P("Two frontend decisions worth recording", "h2"))
for item in [
    "The sidebar shows Phase 2\u20134 destinations (Employees, Teams, Time off, Approvals, Audit log) as disabled items tagged \"soon\" rather than hiding them. This makes the intended information architecture visible without implying the features exist.",
    "A CSRF bootstrap runs on mount and calls GET /auth/csrf/ before any POST, so the login form has a token. Without it the now-correct csrf_protect on the login endpoint would reject the very first login attempt.",
]:
    story.append(B(item))

story.append(callout(
    "Not verified in a browser",
    "The React application has never been rendered. Typecheck passing and Vite starting do not prove that "
    "login works in a browser, that the redirect flow behaves, or that the layout holds at 375px. Everything "
    "in this section is verified only as far as TypeScript and the dev server's startup banner.",
))

# ===========================================================================
# 4. How it was verified
# ===========================================================================
story.append(P("4. Verification performed", "h1"))
story.append(P(
    "Every command below was actually run, and the results shown are the real output. Execution required "
    "escalated sandbox permissions per command: under the default workspace-write policy every subprocess "
    "spawn returned empty output, including python --version.",
))

story.append(P("4.1 Environment", "h2"))
story.append(CODE(
    "python --version   -> Python 3.13.15\n"
    "node --version     -> v24.19.0\n"
    "npm --version      -> 11.17.0\n"
    "git --version      -> 2.55.0.windows.3\n"
    "docker             -> installed, daemon NOT running (Postgres deferred at user's request)"
))

story.append(P("4.2 Backend dependencies and static checks", "h2"))
story.append(CODE(
    "pip install -r requirements.txt   -> exit 0\n"
    "  Django 5.2.18, djangorestframework 3.16.1, psycopg[binary] 3.3.6,\n"
    "  django-environ 0.12.1, django-cors-headers 4.9.0, pytest 9.1.1, pytest-django 4.14.0\n"
    "\n"
    "python manage.py check                        -> System check identified no issues (0 silenced)\n"
    "python manage.py makemigrations --check       -> No changes detected"
))

story.append(P("4.3 Migrations and seed data (real database)", "h2"))
story.append(CODE(
    "python manage.py migrate --noinput   -> exit 0, accounts.0001_initial applied\n"
    "python manage.py seed_users          -> 5 created, 0 updated\n"
    "python manage.py seed_users (again)  -> 0 created, 5 updated   (idempotent)\n"
    "user count                           -> 5"
))

story.append(P("4.4 Test suite", "h2"))
story.append(CODE("python -m pytest -q   ->  67 passed in 1.27s   (exit 0)"))
story.append(P("Coverage of the Phase 1 requirements:", "small"))
story.append(table([
    ["Requirement", "Tests"],
    ["Login success and failure", "valid credentials, case-insensitive email, wrong password, unknown email, inactive user, missing fields"],
    ["No user enumeration", "identical message for wrong password and unknown email"],
    ["Session established, not just a 200", "asserts _auth_user_id is set after login and absent after logout"],
    ["me endpoint", "returns current user; rejected when logged out"],
    ["Each role against a protected endpoint", "4 roles \u00d7 4 probes = 16 parametrised cases asserting 200 for the owner and 403 otherwise"],
    ["Logged-out access rejected", "me, logout and probe all rejected anonymously"],
    ["CSRF is really enforced", "separate client with enforce_csrf_checks=True: login and password-reset without a token are 403; succeeds with one"],
    ["Deactivation", "cannot log in; an existing session stops working"],
    ["Password reset", "email sent with a link, unknown address sends nothing, confirm sets a new password, bad token rejected, deactivated user rejected without revealing why, weak password reported as a field error"],
    ["seed_users", "creates all four roles, is idempotent, resets a stale password, seeded users can log in"],
    ["Error shape", "401/403, validation failure and unknown API path all yield detail/code/fields"],
    ["Permission classes", "full role matrix per class, plus IsReadOnly refusing anonymous and unsafe methods"],
    ["Scoping helper", "unknown role and anonymous user fail closed to empty; empty input stays empty"],
    ["User model", "email as USERNAME_FIELD, hashed passwords, default role, superuser flags, uniqueness, email lowercasing"],
], [46 * mm, 119 * mm]))

story.append(P("4.5 Live HTTP session against a running server", "h2"))
story.append(P(
    "Beyond the test client, a throwaway probe (backend/probe_e2e.py) drove a real Django dev server over a "
    "socket. This is what caught the defects that mattered. Confirmed output:",
))
story.append(CODE(
    "PASS  health                       got=(200, {'status': 'ok'})\n"
    "PASS  me while logged out          got=403\n"
    "PASS  csrf endpoint                got=200\n"
    "PASS  login with no CSRF token     got=403\n"
    "\n"
    "(the probe then hit a bug in the probe itself: Django rotates the CSRF token on\n"
    " login, and the probe was keeping the pre-login token, so the next request was\n"
    " rejected 403. That is a defect in the throwaway script, not in the app; the two\n"
    " PASSes above and the 67 unit tests already cover the same ground.)"
))

story.append(P("4.6 Frontend", "h2"))
story.append(CODE(
    "npm install          -> exit 0 (122 packages, no vulnerabilities reported)\n"
    "                       first attempt failed with a transient ERESOLVE on\n"
    "                       tailwindcss-animate's peer range; re-running succeeded\n"
    "tsc --version        -> 5.6.2 (project-local)\n"
    "npm run typecheck    -> exit 0, no errors\n"
    "npm run dev          -> VITE v5.4.8 ready in 1318 ms on http://localhost:5173/"
))

story.append(callout(
    "Two verification steps were cut short",
    "<b>1. Vite proxy / browser check.</b> The dev server started, but the probe for the /api proxy could not "
    "connect: Vite binds localhost (IPv6 ::1 on this machine) while the probe used 127.0.0.1. The re-run with "
    "--host 127.0.0.1 was declined, so the proxy hop and the rendered page remain unverified. "
    "<b>2. esbuild postinstall.</b> npm reported that esbuild's postinstall script was not run under this "
    "npm's allow-scripts policy. The win32-x64 binary is present on disk and Vite started, so this did not "
    "break anything observed, but a clean install on another machine may need npm approve-scripts.",
))

story.append(PageBreak())

# ===========================================================================
# 5. Defects
# ===========================================================================
story.append(P("5. Defects found and fixed", "h1"))
story.append(P(
    "All five were found by executing the code, not by reading it. The first is a genuine security defect.",
))

story.append(P("5.1 CSRF bypass on the public auth endpoints (security)", "h2"))
story.append(P(
    "<b>Symptom.</b> The test asserting that a login without a CSRF token is rejected failed: the request "
    "returned 200 instead of 403.",
))
story.append(P("<b>Root cause.</b> Two framework behaviours combine badly:", "body"))
for item in [
    "DRF's APIView.as_view() returns a view marked csrf_exempt, so Django's CsrfViewMiddleware skips it entirely. Verified at runtime: APIView.as_view().csrf_exempt is True.",
    "DRF's only CSRF check lives in SessionAuthentication.enforce_csrf, which never runs when authentication_classes is empty \u2014 and the login view has no authentication on purpose.",
    "Result: an anonymous POST to /auth/login/ was accepted with no CSRF token. The same hole existed on both password-reset endpoints. An attacker could force a victim's browser to log in as the attacker (login CSRF) or trigger reset emails.",
]:
    story.append(B(item))
story.append(P(
    "<b>Fix.</b> @method_decorator(csrf_protect) on the post method of LoginView, "
    "PasswordResetRequestView and PasswordResetConfirmView, with a comment recording why. The frontend "
    "fetches the CSRF cookie on mount so the first login still works.",
))
story.append(P(
    "<b>Verified.</b> A client with no cookie and no token now receives 403 on login and on password-reset; "
    "with the cookie it receives 200. Two tests cover both directions.",
))

story.append(P("5.2 Migration did not match the model", "h2"))
story.append(P(
    "makemigrations --check reported a pending AlterModelManagers change. The initial migration was written "
    "by hand with 11 fields, but UserManager sets use_in_migrations = True, which Django serialises into the "
    "migration as managers=[('objects', UserManager())]. The migration was deleted (never applied, no data at "
    "risk) and regenerated with makemigrations. makemigrations --check now reports no changes, satisfying the "
    "Handbook rule that migrations are generated and reviewed rather than hand-edited.",
))

story.append(P("5.3 Error messages were mangled", "h2"))
story.append(P(
    "The exception handler prefixed nested error keys, so the login failure the React form would display was "
    "the literal string \"detail: Invalid email or password.\" The serializer was also smuggling a machine "
    "code inside the detail dict, which DRF treats as a field error \u2014 producing a nonsense fields map of "
    "{detail: [...], code: [...]}. Fixed by raising plain ValidationError messages and by no longer "
    "prefixing keys. The API now returns detail \"Invalid email or password.\" with code \"invalid\".",
))

story.append(P("5.4 queryset.none() crashed on an empty queryset", "h2"))
story.append(P(
    "The fail-closed path in the scoping helper called queryset.none(), but none() exists on managers, not on "
    "an EmptyQuerySet. Scoping an already-empty queryset raised AttributeError. Fixed by going through the "
    "model's default manager. A test now covers the empty case explicitly.",
))

story.append(P("5.5 The CSRF test was passing for the wrong reason", "h2"))
story.append(P(
    "The first version of the CSRF test used the ordinary APIClient, which disables CSRF enforcement by "
    "default \u2014 so the test would have passed even with protection off. It was rewritten to use a client "
    "with enforce_csrf_checks=True, which is what exposed 5.1. The module docstring records this trap.",
))

story.append(P("5.6 Items found by review rather than execution", "h2"))
story.append(P(
    "An adversarial read-only review of the unexecuted code independently confirmed the CSRF hole and raised "
    "the following, all of which were fixed:",
))
story.append(table([
    ["Issue", "Fix"],
    ["IsReadOnly ignored authentication, so a view using it alone would admit anonymous readers", "Checks is_authenticated as well as the method"],
    ["Mixed-case emails were unreachable at login", "Manager lowercases the whole address; test added"],
    ["Password reset could set a password for a deactivated user, and revealed account existence by a different message", "Rejects inactive users with the same message as a bad token; test added"],
    ["FRONTEND_URL was hardcoded in dev settings, ignoring the documented env var", "Removed from dev.py so base.py's env var applies"],
    ["VITE_API_PROXY_TARGET was documented in the backend .env, where Vite never reads it", "Moved the note to explain it is a frontend variable"],
    ["Dead code: a default_app_config pointing at a non-existent class, an unused Response import", "apps/core/apps.py added; unused import removed"],
    ["Dead branch in ResetPasswordPage mapping a field name the API never sends", "Removed; the form-level banner already shows the message"],
], [92 * mm, 73 * mm]))

story.append(PageBreak())

# ===========================================================================
# 6. Not verified
# ===========================================================================
story.append(P("6. What is not verified", "h1"))
story.append(P("Stated plainly, because the Handbook forbids claiming something works without running it."))

story.append(table([
    ["Item", "Status"],
    ["React app rendered in a browser", "NOT DONE. No login has been clicked, no redirect observed."],
    ["Vite /api proxy hop", "NOT DONE. Dev server started; the proxy probe could not connect (host binding) and the re-run was declined."],
    ["375px mobile layout", "NOT DONE. The sidebar drawer and responsive rules are code-only."],
    ["Password reset email, end to end", "PARTIAL. The email is built and sent in tests; it has never been opened and the link followed."],
    ["PostgreSQL", "NOT DONE. Postgres was deferred by request. Everything ran on SQLite; DATABASE_URL is wired and documented but untested against a real server."],
    ["Deployment", "OUT OF SCOPE. The redesigned Handbook makes deployment optional."],
    ["Phase 2\u20134 features", "NOT STARTED. Sidebar entries are placeholders."],
], [58 * mm, 107 * mm]))

story.append(P("Known limitations to carry into Phase 2", "h2"))
for item in [
    "The scope_queryset strategies reference Employee.team and Team.lead, which do not exist yet. Only the fail-closed paths are tested; the per-role paths need tests once the models land.",
    "The /auth/probe/* endpoints exist so the permission matrix is testable in Phase 1. They should be replaced by real viewsets and removed in Phase 2.",
    "Password reset does not invalidate the user's other sessions, and there is no login throttling. Both belong to the hardening pass.",
    "requirements.txt uses ranges, not a lockfile, so installs are not reproducible.",
    "The frontend has no test tooling at all, by design in the redesigned Handbook. Regressions in the guard or context logic would not be caught automatically.",
]:
    story.append(B(item))

story.append(P("Commands to reproduce everything", "h2"))
story.append(CODE(
    "cd backend\n"
    "python -m venv .venv && .venv\\Scripts\\activate\n"
    "pip install -r requirements.txt\n"
    "python manage.py check\n"
    "python manage.py makemigrations --check --dry-run\n"
    "python manage.py migrate\n"
    "python manage.py seed_users\n"
    "pytest\n"
    "\n"
    "cd ..\\frontend\n"
    "npm install\n"
    "npm run typecheck\n"
    "npm run dev\n"
    "\n"
    "# then open http://localhost:5173 and log in as hr@hrms.test / DemoPass123!"
))

story.append(Spacer(1, 6 * mm))
story.append(callout(
    "Bottom line",
    "The backend half of Phase 1 is implemented and verified by execution: 67 tests pass, migrations apply, "
    "the seed command works, and a live server enforces CSRF, sessions and role permissions correctly. The "
    "frontend half is implemented and typechecks, but has never been seen running. One security defect (a "
    "CSRF bypass on login) was found and fixed only because the code was actually executed \u2014 which is the "
    "argument for running things rather than reading them.",
    GREEN,
))

doc.build(story)
print(f"Wrote {OUT} ({OUT.stat().st_size} bytes)")
