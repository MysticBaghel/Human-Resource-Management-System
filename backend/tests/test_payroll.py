"""Payroll: calculations, permissions, generation, revisions, payslips, audit."""

from datetime import date
from decimal import Decimal

import pytest
from django.utils import timezone

from apps.audit.models import AuditLog
from apps.payroll.models import PayrollRecord, SalaryRevision, SalaryStructure

PAYROLL = "/api/v1/payroll"
STRUCTURES = f"{PAYROLL}/salary-structures/"
REVISIONS = f"{PAYROLL}/salary-revisions/"
RECORDS = f"{PAYROLL}/records/"
DASHBOARD = f"{PAYROLL}/dashboard/"


def structure_payload(employee, **overrides) -> dict:
    payload = {
        "employee": employee.pk,
        "basic_salary": "50000.00",
        "hra": "20000.00",
        "conveyance_allowance": "1600.00",
        "medical_allowance": "1250.00",
        "special_allowance": "5000.00",
        "other_allowances": "0.00",
        "provident_fund": "6000.00",
        "professional_tax": "200.00",
        "income_tax": "5000.00",
        "other_deductions": "0.00",
        "effective_date": "2025-01-01",
    }
    payload.update(overrides)
    return payload


def as_decimal(value) -> Decimal:
    return Decimal(str(value))


def generate(write, month: int, year: int, employee=None):
    payload = {"month": month, "year": year}
    if employee is not None:
        payload["employee"] = employee.pk
    return write("post", f"{RECORDS}generate/", payload)


def detail_url(record) -> str:
    return f"{RECORDS}{record.pk}/"


class TestSalaryCalculations:
    def test_gross_deductions_and_net_are_decimal(
        self, make_salary_structure, demo_org
    ):
        structure = make_salary_structure(
            demo_org.esha,
            basic_salary="33333.33",
            hra="11111.11",
            conveyance_allowance="1600.00",
            medical_allowance="1250.00",
            special_allowance="1234.56",
            other_allowances="12.34",
            provident_fund="1800.00",
            professional_tax="200.00",
            income_tax="2500.00",
            other_deductions="100.10",
        )

        assert structure.gross_salary == Decimal("48541.34")
        assert structure.total_deductions == Decimal("4600.10")
        assert structure.net_salary == Decimal("43941.24")
        assert isinstance(structure.net_salary, Decimal)

    def test_deductions_cannot_exceed_gross(self, make_salary_structure, demo_org):
        # The model itself does not reject this, the service/serializer does;
        # this asserts the calculation remains exact if legacy data exists.
        structure = make_salary_structure(
            demo_org.esha,
            basic_salary="1000.00",
            hra="0.00",
            conveyance_allowance="0.00",
            medical_allowance="0.00",
            special_allowance="0.00",
            other_allowances="0.00",
            provident_fund="2000.00",
            professional_tax="0.00",
            income_tax="0.00",
            other_deductions="0.00",
        )
        assert structure.net_salary == Decimal("-1000.00")


class TestSalaryStructureApi:
    def test_hr_creates_a_structure_with_calculated_totals(
        self, auth_client, api_write, demo_org
    ):
        auth_client(demo_org.hr)

        response = api_write("post", STRUCTURES, structure_payload(demo_org.esha))

        assert response.status_code == 201
        assert response.data["employee"] == demo_org.esha.pk
        assert response.data["employee_name"] == "Esha Employee"
        assert response.data["employee_code"] == f"EMP-{demo_org.esha.pk:04d}"
        assert response.data["department"] == "Engineering"
        assert as_decimal(response.data["gross_salary"]) == Decimal("77850.00")
        assert as_decimal(response.data["total_deductions"]) == Decimal("11200.00")
        assert as_decimal(response.data["net_salary"]) == Decimal("66650.00")
        assert response.data["is_active"] is True
        assert response.data["created_by_email"] == demo_org.hr.email

    def test_admin_can_create_and_employee_and_manager_cannot(
        self, auth_client, api_write, demo_org
    ):
        auth_client(demo_org.admin)
        admin_create = api_write("post", STRUCTURES, structure_payload(demo_org.esha))
        assert admin_create.status_code == 201

    @pytest.mark.parametrize("role_attr", ["employee_user", "manager_user"])
    def test_non_hr_cannot_write(self, auth_client, api_write, demo_org, role_attr):
        auth_client(getattr(demo_org, role_attr))

        response = api_write("post", STRUCTURES, structure_payload(demo_org.sam))

        assert response.status_code == 403

    def test_employee_reads_their_own_structure_but_not_change_it(
        self, auth_client, api_client, api_write, demo_org, make_salary_structure
    ):
        structure = make_salary_structure(demo_org.esha)
        auth_client(demo_org.employee_user)

        read = api_client.get(f"{STRUCTURES}{structure.pk}/")
        write = api_write(
            "patch", f"{STRUCTURES}{structure.pk}/", {"basic_salary": "61000.00"}
        )

        assert read.status_code == 200
        assert read.data["employee"] == demo_org.esha.pk
        assert write.status_code == 403

    def test_manager_cannot_change_a_team_members_salary(
        self, auth_client, api_write, demo_org, make_salary_structure
    ):
        structure = make_salary_structure(demo_org.esha)
        auth_client(demo_org.manager_user)

        response = api_write(
            "patch", f"{STRUCTURES}{structure.pk}/", {"basic_salary": "61000.00"}
        )

        assert response.status_code == 403

    def test_duplicate_active_structure_is_rejected(
        self, auth_client, api_write, demo_org, make_salary_structure
    ):
        make_salary_structure(demo_org.esha)
        auth_client(demo_org.hr)

        response = api_write("post", STRUCTURES, structure_payload(demo_org.esha))

        assert response.status_code == 400
        assert "employee" in response.data["fields"]

    def test_negative_net_is_rejected(self, auth_client, api_write, demo_org):
        auth_client(demo_org.hr)
        payload = structure_payload(
            demo_org.esha,
            basic_salary="1000.00",
            hra="0.00",
            conveyance_allowance="0.00",
            medical_allowance="0.00",
            special_allowance="0.00",
            other_allowances="0.00",
            provident_fund="2000.00",
            professional_tax="0.00",
            income_tax="0.00",
            other_deductions="0.00",
        )

        response = api_write("post", STRUCTURES, payload)

        assert response.status_code == 400
        assert "other_deductions" in response.data["fields"]

    def test_list_is_scoped_to_own_employee(
        self, auth_client, api_client, demo_org, make_salary_structure
    ):
        make_salary_structure(demo_org.esha)
        make_salary_structure(demo_org.sam)
        auth_client(demo_org.employee_user)

        response = api_client.get(STRUCTURES)

        assert response.status_code == 200
        assert response.data["count"] == 1
        assert response.data["results"][0]["employee"] == demo_org.esha.pk

    def test_employee_cannot_open_another_structure(
        self, auth_client, api_client, demo_org, make_salary_structure
    ):
        sam_structure = make_salary_structure(demo_org.sam)
        auth_client(demo_org.employee_user)

        response = api_client.get(f"{STRUCTURES}{sam_structure.pk}/")

        assert response.status_code == 404

    def test_manager_reads_only_their_own_structure(
        self, auth_client, api_client, demo_org, make_salary_structure
    ):
        make_salary_structure(demo_org.esha)
        auth_client(demo_org.manager_user)

        response = api_client.get(STRUCTURES)

        assert response.status_code == 200
        assert response.data["count"] == 0

    def test_hr_lists_everyone(
        self, auth_client, api_client, demo_org, make_salary_structure
    ):
        make_salary_structure(demo_org.esha)
        make_salary_structure(demo_org.sam)
        auth_client(demo_org.hr)

        response = api_client.get(STRUCTURES)

        assert response.status_code == 200
        assert response.data["count"] == 2

    def test_filter_by_active_and_employee(
        self, auth_client, api_client, demo_org, make_salary_structure
    ):
        make_salary_structure(demo_org.esha)
        make_salary_structure(demo_org.sam)
        auth_client(demo_org.hr)

        response = api_client.get(
            f"{STRUCTURES}?active=true&employee={demo_org.esha.pk}"
        )

        assert response.status_code == 200
        assert response.data["count"] == 1

    def test_delete_is_not_allowed(
        self, auth_client, api_write, demo_org, make_salary_structure
    ):
        structure = make_salary_structure(demo_org.esha)
        auth_client(demo_org.hr)

        response = api_write("delete", f"{STRUCTURES}{structure.pk}/")

        assert response.status_code == 405


class TestSalaryRevision:
    def test_revision_creates_history_and_replaces_active_structure(
        self, auth_client, api_write, api_client, demo_org
    ):
        auth_client(demo_org.hr)
        created = api_write("post", STRUCTURES, structure_payload(demo_org.esha))
        old_id = created.data["id"]

        response = api_write(
            "patch",
            f"{STRUCTURES}{old_id}/",
            {
                "basic_salary": "60000.00",
                "effective_date": "2026-01-01",
                "reason": "Annual revision",
            },
        )

        assert response.status_code == 200
        new_id = response.data["id"]
        assert new_id != old_id
        assert response.data["is_active"] is True
        assert as_decimal(response.data["net_salary"]) == Decimal("76650.00")

        old = SalaryStructure.objects.get(pk=old_id)
        assert old.is_active is False
        assert old.basic_salary == Decimal("50000.00")

        revision = SalaryRevision.objects.get(employee=demo_org.esha)
        assert revision.previous_structure_id == old_id
        assert revision.new_structure_id == new_id
        assert revision.effective_date == date(2026, 1, 1)
        assert revision.updated_by == demo_org.hr
        assert revision.reason == "Annual revision"
        assert revision.previous_values["basic_salary"] == "50000.00"
        assert revision.new_values["basic_salary"] == "60000.00"
        assert revision.previous_values["net_salary"] == "66650.00"
        assert revision.new_values["net_salary"] == "76650.00"

        history = api_client.get(f"{REVISIONS}?employee={demo_org.esha.pk}")
        assert history.status_code == 200
        assert history.data["count"] == 1
        assert history.data["results"][0]["updated_by_email"] == demo_org.hr.email

    def test_employee_cannot_read_revision_history(
        self, auth_client, api_client, demo_org
    ):
        auth_client(demo_org.employee_user)

        response = api_client.get(REVISIONS)

        assert response.status_code == 403

    def test_effective_date_cannot_move_backwards(
        self, auth_client, api_write, demo_org
    ):
        auth_client(demo_org.hr)
        created = api_write("post", STRUCTURES, structure_payload(demo_org.esha))

        response = api_write(
            "patch",
            f"{STRUCTURES}{created.data['id']}/",
            {"effective_date": "2024-01-01", "basic_salary": "51000.00"},
        )

        assert response.status_code == 400
        assert "effective_date" in response.data["fields"]

    def test_unchanged_update_does_not_create_noise(
        self, auth_client, api_write, demo_org
    ):
        auth_client(demo_org.hr)
        created = api_write("post", STRUCTURES, structure_payload(demo_org.esha))

        response = api_write(
            "patch",
            f"{STRUCTURES}{created.data['id']}/",
            {"basic_salary": "50000.00", "effective_date": "2025-01-01"},
        )

        assert response.status_code == 200
        assert response.data["id"] == created.data["id"]
        assert SalaryRevision.objects.count() == 0


class TestPayrollGeneration:
    def test_generate_individual_snapshots_salary(
        self, auth_client, api_write, demo_org, make_salary_structure
    ):
        structure = make_salary_structure(demo_org.esha)
        auth_client(demo_org.hr)

        response = generate(api_write, 3, 2026, demo_org.esha)

        assert response.status_code == 201
        assert response.data["generated_count"] == 1
        record = response.data["generated"][0]
        assert record["employee"] == demo_org.esha.pk
        assert record["employee_name"] == "Esha Employee"
        assert record["department"] == "Engineering"
        assert record["payroll_month"] == 3
        assert record["payroll_year"] == 2026
        assert record["payslip_number"] == f"PAY-202603-{demo_org.esha.pk:06d}"
        assert record["status"] == "draft"
        assert record["payment_status"] == "pending"
        assert as_decimal(record["gross_salary"]) == structure.gross_salary
        assert as_decimal(record["net_salary"]) == structure.net_salary
        assert record["generated_by_email"] == demo_org.hr.email

    def test_duplicate_individual_generation_is_rejected(
        self, auth_client, api_write, demo_org, make_salary_structure
    ):
        make_salary_structure(demo_org.esha)
        auth_client(demo_org.hr)
        generate(api_write, 3, 2026, demo_org.esha)

        response = generate(api_write, 3, 2026, demo_org.esha)

        assert response.status_code == 400
        assert "already exists" in response.data["detail"]

    def test_bulk_generation_skips_people_without_structures_and_duplicates(
        self, auth_client, api_write, demo_org, make_salary_structure
    ):
        make_salary_structure(demo_org.esha)
        make_salary_structure(demo_org.sam)
        auth_client(demo_org.hr)

        first = generate(api_write, 4, 2026)
        second = generate(api_write, 4, 2026)

        assert first.status_code == 201
        assert first.data["generated_count"] == 2
        assert first.data["skipped_count"] == 1
        assert {row["employee"] for row in first.data["generated"]} == {
            demo_org.esha.pk,
            demo_org.sam.pk,
        }
        assert second.status_code == 200
        assert second.data["generated_count"] == 0
        assert second.data["skipped_count"] == 3
        assert PayrollRecord.objects.count() == 2

    def test_no_applicable_structure_is_reported(
        self, auth_client, api_write, make_employee, demo_org, make_salary_structure
    ):
        later = make_employee(
            first_name="Later",
            last_name="Starter",
            email="later@example.com",
            team=demo_org.engineering,
            start_date=date(2026, 1, 1),
        )
        make_salary_structure(later, effective_date=date(2026, 6, 1))
        auth_client(demo_org.hr)

        response = generate(api_write, 3, 2026, later)

        assert response.status_code == 400
        assert "no salary structure" in response.data["detail"].lower()

    @pytest.mark.parametrize("role_attr", ["employee_user", "manager_user"])
    def test_non_hr_cannot_generate(
        self, auth_client, api_write, demo_org, make_salary_structure, role_attr
    ):
        make_salary_structure(demo_org.esha)
        auth_client(getattr(demo_org, role_attr))

        response = generate(api_write, 3, 2026)

        assert response.status_code == 403

    def test_invalid_period_is_rejected(self, auth_client, api_write, demo_org):
        auth_client(demo_org.hr)

        response = generate(api_write, 13, 2026)

        assert response.status_code == 400
        assert "month" in response.data["fields"]

    def test_admin_can_generate_finalize_and_pay(
        self, auth_client, api_write, demo_org, make_salary_structure
    ):
        make_salary_structure(demo_org.esha)
        auth_client(demo_org.admin)

        generated = generate(api_write, 3, 2026, demo_org.esha)
        assert generated.status_code == 201
        record_id = generated.data["generated"][0]["id"]

        finalized = api_write("post", f"{RECORDS}{record_id}/finalize/")
        paid = api_write(
            "post",
            f"{RECORDS}{record_id}/payment/",
            {
                "payment_status": "paid",
                "payment_date": "2026-04-02",
                "payment_reference": "ADMIN-PAY-1",
            },
        )

        assert finalized.status_code == 200
        assert paid.status_code == 200
        assert paid.data["payment_status"] == "paid"

    def test_structure_revision_does_not_change_generated_record(
        self, auth_client, api_write, api_client, demo_org, make_salary_structure
    ):
        structure = make_salary_structure(demo_org.esha)
        auth_client(demo_org.hr)
        generated = generate(api_write, 3, 2026, demo_org.esha)
        record_id = generated.data["generated"][0]["id"]

        api_write(
            "patch",
            f"{STRUCTURES}{structure.pk}/",
            {
                "basic_salary": "70000.00",
                "effective_date": "2026-04-01",
                "reason": "Promotion",
            },
        )

        record = PayrollRecord.objects.get(pk=record_id)
        assert record.basic_salary == Decimal("50000.00")
        assert record.net_salary == Decimal("66650.00")
        assert record.salary_structure_id == structure.pk


class TestFinalizationAndAdjustments:
    def _record(self, write, employee) -> dict:
        response = generate(write, 3, 2026, employee)
        assert response.status_code == 201, response.data
        return response.data["generated"][0]

    def test_adjustment_changes_net_but_not_snapshot_components(
        self, auth_client, api_write, demo_org, make_salary_structure
    ):
        make_salary_structure(demo_org.esha)
        auth_client(demo_org.hr)
        record = self._record(api_write, demo_org.esha)

        response = api_write(
            "patch",
            f"{RECORDS}{record['id']}/",
            {"adjustment_amount": "1000.50", "adjustment_note": "Festival bonus"},
        )

        assert response.status_code == 200
        assert as_decimal(response.data["adjustment_amount"]) == Decimal("1000.50")
        assert response.data["adjustment_note"] == "Festival bonus"
        assert as_decimal(response.data["gross_salary"]) == Decimal("77850.00")
        assert as_decimal(response.data["net_salary"]) == Decimal("67650.50")

    def test_adjustment_cannot_make_net_negative(
        self, auth_client, api_write, demo_org, make_salary_structure
    ):
        make_salary_structure(demo_org.esha)
        auth_client(demo_org.hr)
        record = self._record(api_write, demo_org.esha)

        response = api_write(
            "patch",
            f"{RECORDS}{record['id']}/",
            {"adjustment_amount": "-100000.00"},
        )

        assert response.status_code == 400
        assert "adjustment_amount" in response.data["fields"]

    def test_finalize_freezes_the_record(
        self, auth_client, api_write, demo_org, make_salary_structure
    ):
        make_salary_structure(demo_org.esha)
        auth_client(demo_org.hr)
        record = self._record(api_write, demo_org.esha)

        finalized = api_write("post", f"{RECORDS}{record['id']}/finalize/")

        assert finalized.status_code == 200
        assert finalized.data["status"] == "finalized"
        assert finalized.data["finalized_by_email"] == demo_org.hr.email
        assert finalized.data["finalized_at"] is not None

        second = api_write("post", f"{RECORDS}{record['id']}/finalize/")
        assert second.status_code == 400

        adjusted = api_write(
            "patch",
            f"{RECORDS}{record['id']}/",
            {"adjustment_amount": "100.00"},
        )
        assert adjusted.status_code == 400

    def test_bulk_finalize_only_touches_drafts(
        self, auth_client, api_write, demo_org, make_salary_structure
    ):
        make_salary_structure(demo_org.esha)
        make_salary_structure(demo_org.sam)
        auth_client(demo_org.hr)
        generate(api_write, 5, 2026, demo_org.esha)
        generate(api_write, 5, 2026, demo_org.sam)
        api_write("post", f"{RECORDS}{PayrollRecord.objects.first().pk}/finalize/")

        response = api_write(
            "post", f"{RECORDS}finalize-period/", {"month": 5, "year": 2026}
        )

        assert response.status_code == 200
        assert response.data["finalized_count"] == 1
        assert PayrollRecord.objects.filter(status="finalized").count() == 2

    def test_payment_requires_finalized_record_and_date(
        self, auth_client, api_write, demo_org, make_salary_structure
    ):
        make_salary_structure(demo_org.esha)
        auth_client(demo_org.hr)
        record = self._record(api_write, demo_org.esha)

        draft_payment = api_write(
            "post",
            f"{RECORDS}{record['id']}/payment/",
            {"payment_status": "paid", "payment_date": "2026-04-01"},
        )
        assert draft_payment.status_code == 400

        api_write("post", f"{RECORDS}{record['id']}/finalize/")
        no_date = api_write(
            "post", f"{RECORDS}{record['id']}/payment/", {"payment_status": "paid"}
        )
        assert no_date.status_code == 400
        assert "payment_date" in no_date.data["fields"]

        paid = api_write(
            "post",
            f"{RECORDS}{record['id']}/payment/",
            {
                "payment_status": "paid",
                "payment_date": "2026-04-02",
                "payment_reference": "UTR-123",
            },
        )
        assert paid.status_code == 200
        assert paid.data["payment_status"] == "paid"
        assert paid.data["payment_date"] == "2026-04-02"
        assert paid.data["payment_reference"] == "UTR-123"

    def test_failed_payment_status_is_recorded(
        self, auth_client, api_write, demo_org, make_salary_structure
    ):
        make_salary_structure(demo_org.esha)
        auth_client(demo_org.hr)
        record = self._record(api_write, demo_org.esha)
        api_write("post", f"{RECORDS}{record['id']}/finalize/")

        response = api_write(
            "post",
            f"{RECORDS}{record['id']}/payment/",
            {
                "payment_status": "failed",
                "payment_reference": "BANK-REJECT-1",
            },
        )

        assert response.status_code == 200
        assert response.data["payment_status"] == "failed"
        assert response.data["payment_reference"] == "BANK-REJECT-1"

    def test_employee_cannot_finalize_or_adjust(
        self, auth_client, api_write, demo_org, make_salary_structure
    ):
        make_salary_structure(demo_org.esha)
        auth_client(demo_org.hr)
        record = self._record(api_write, demo_org.esha)
        auth_client(demo_org.employee_user)

        patch = api_write(
            "patch", f"{RECORDS}{record['id']}/", {"adjustment_amount": "1.00"}
        )
        finalize = api_write("post", f"{RECORDS}{record['id']}/finalize/")
        payment = api_write(
            "post",
            f"{RECORDS}{record['id']}/payment/",
            {"payment_status": "paid", "payment_date": "2026-04-02"},
        )

        assert patch.status_code == 403
        assert finalize.status_code == 403
        assert payment.status_code == 403

    def test_finalized_record_survives_a_later_revision(
        self, auth_client, api_write, demo_org, make_salary_structure
    ):
        structure = make_salary_structure(demo_org.esha)
        auth_client(demo_org.hr)
        record_id = self._record(api_write, demo_org.esha)["id"]
        api_write("post", f"{RECORDS}{record_id}/finalize/")

        api_write(
            "patch",
            f"{STRUCTURES}{structure.pk}/",
            {
                "basic_salary": "90000.00",
                "effective_date": "2026-04-01",
                "reason": "Market correction",
            },
        )

        record = PayrollRecord.objects.get(pk=record_id)
        assert record.status == "finalized"
        assert record.basic_salary == Decimal("50000.00")
        assert record.net_salary == Decimal("66650.00")


class TestEmployeeAccess:
    def _finalized_own(self, auth_client, api_write, demo_org, make_salary_structure):
        make_salary_structure(demo_org.esha)
        auth_client(demo_org.hr)
        generated = generate(api_write, 3, 2026, demo_org.esha)
        record = generated.data["generated"][0]
        api_write("post", f"{RECORDS}{record['id']}/finalize/")
        return record

    def test_employee_sees_only_their_finalized_records(
        self, auth_client, api_client, api_write, demo_org, make_salary_structure
    ):
        own = self._finalized_own(
            auth_client, api_write, demo_org, make_salary_structure
        )
        make_salary_structure(demo_org.sam)
        auth_client(demo_org.hr)
        generate(api_write, 3, 2026, demo_org.sam)

        auth_client(demo_org.employee_user)
        response = api_client.get(RECORDS)

        assert response.status_code == 200
        assert response.data["count"] == 1
        assert response.data["results"][0]["id"] == own["id"]

    def test_employee_cannot_open_another_on_record(
        self, auth_client, api_client, api_write, demo_org, make_salary_structure
    ):
        make_salary_structure(demo_org.sam)
        auth_client(demo_org.hr)
        generated = generate(api_write, 3, 2026, demo_org.sam)
        other_id = generated.data["generated"][0]["id"]
        api_write("post", f"{RECORDS}{other_id}/finalize/")

        auth_client(demo_org.employee_user)
        response = api_client.get(f"{RECORDS}{other_id}/")

        assert response.status_code == 404

    def test_employee_cannot_open_a_draft(
        self, auth_client, api_client, api_write, demo_org, make_salary_structure
    ):
        make_salary_structure(demo_org.esha)
        auth_client(demo_org.hr)
        generated = generate(api_write, 3, 2026, demo_org.esha)
        draft_id = generated.data["generated"][0]["id"]

        auth_client(demo_org.employee_user)
        response = api_client.get(f"{RECORDS}{draft_id}/")

        assert response.status_code == 404

    def test_filters_cannot_escape_employee_scope(
        self, auth_client, api_client, api_write, demo_org, make_salary_structure
    ):
        make_salary_structure(demo_org.esha)
        make_salary_structure(demo_org.sam)
        auth_client(demo_org.hr)
        generated = generate(api_write, 3, 2026, demo_org.sam)
        api_write("post", f"{RECORDS}{generated.data['generated'][0]['id']}/finalize/")

        auth_client(demo_org.employee_user)
        response = api_client.get(f"{RECORDS}?employee={demo_org.sam.pk}")

        assert response.status_code == 200
        assert response.data["count"] == 0

    def test_manager_can_read_only_their_own_payslips(
        self, auth_client, api_client, api_write, demo_org, make_salary_structure
    ):
        make_salary_structure(demo_org.meera)
        auth_client(demo_org.hr)
        generated = generate(api_write, 3, 2026, demo_org.meera)
        api_write("post", f"{RECORDS}{generated.data['generated'][0]['id']}/finalize/")

        auth_client(demo_org.manager_user)
        response = api_client.get(RECORDS)

        assert response.status_code == 200
        assert response.data["count"] == 1
        assert response.data["results"][0]["employee"] == demo_org.meera.pk

    def test_hr_mine_filter_returns_their_own_finalized_only(
        self, auth_client, api_client, api_write, demo_org, make_salary_structure
    ):
        make_salary_structure(demo_org.esha)
        auth_client(demo_org.hr)
        generated = generate(api_write, 3, 2026, demo_org.esha)
        api_write("post", f"{RECORDS}{generated.data['generated'][0]['id']}/finalize/")

        response = api_client.get(f"{RECORDS}?mine=true")

        assert response.status_code == 200
        assert response.data["count"] == 0

    def test_unauthenticated_access_is_rejected(self, api_client):
        assert api_client.get(STRUCTURES).status_code in (401, 403)
        assert api_client.get(RECORDS).status_code in (401, 403)


class TestPayslipPdf:
    def _finalized(self, auth_client, api_write, demo_org, make_salary_structure):
        make_salary_structure(demo_org.esha)
        auth_client(demo_org.hr)
        generated = generate(api_write, 3, 2026, demo_org.esha)
        record_id = generated.data["generated"][0]["id"]
        api_write("post", f"{RECORDS}{record_id}/finalize/")
        return record_id

    def test_hr_downloads_a_pdf(
        self, auth_client, api_client, api_write, demo_org, make_salary_structure
    ):
        record_id = self._finalized(
            auth_client, api_write, demo_org, make_salary_structure
        )

        response = api_client.get(f"{RECORDS}{record_id}/payslip/")

        assert response.status_code == 200
        assert response["Content-Type"] == "application/pdf"
        assert "attachment" in response["Content-Disposition"]
        assert response.content.startswith(b"%PDF")

    def test_employee_downloads_own_finalized_payslip(
        self, auth_client, api_client, api_write, demo_org, make_salary_structure
    ):
        record_id = self._finalized(
            auth_client, api_write, demo_org, make_salary_structure
        )

        auth_client(demo_org.employee_user)
        response = api_client.get(f"{RECORDS}{record_id}/payslip/")

        assert response.status_code == 200
        assert response.content.startswith(b"%PDF")

    def test_employee_cannot_download_a_draft_or_another_payslip(
        self, auth_client, api_client, api_write, demo_org, make_salary_structure
    ):
        make_salary_structure(demo_org.esha)
        make_salary_structure(demo_org.sam)
        auth_client(demo_org.hr)
        esha_draft = generate(api_write, 3, 2026, demo_org.esha).data["generated"][0]
        sam = generate(api_write, 3, 2026, demo_org.sam).data["generated"][0]
        api_write("post", f"{RECORDS}{sam['id']}/finalize/")

        auth_client(demo_org.employee_user)
        draft_response = api_client.get(f"{RECORDS}{esha_draft['id']}/payslip/")
        other_response = api_client.get(f"{RECORDS}{sam['id']}/payslip/")

        assert draft_response.status_code == 404
        assert other_response.status_code == 404

    def test_pdf_uses_company_profile_when_present(
        self, auth_client, api_client, api_write, demo_org, make_salary_structure
    ):
        from apps.organization.models import CompanyProfile
        from apps.payroll.payslip import _company, render_payslip

        profile = CompanyProfile.objects.create(name="Acme Widgets")
        record_id = self._finalized(
            auth_client, api_write, demo_org, make_salary_structure
        )
        record = PayrollRecord.objects.get(pk=record_id)

        pdf = render_payslip(record)

        assert pdf.startswith(b"%PDF")
        assert _company()[0] == profile.name

    def test_pdf_handles_special_characters_in_names(
        self,
        auth_client,
        api_client,
        api_write,
        demo_org,
        make_employee,
        make_salary_structure,
    ):
        employee = make_employee(
            first_name="A&B",
            last_name="<Tester>",
            email="special.person@example.com",
            team=demo_org.engineering,
        )
        make_salary_structure(employee)
        auth_client(demo_org.hr)
        generated = generate(api_write, 3, 2026, employee)
        record_id = generated.data["generated"][0]["id"]
        api_write("post", f"{RECORDS}{record_id}/finalize/")

        response = api_client.get(f"{RECORDS}{record_id}/payslip/")

        assert response.status_code == 200
        assert response.content.startswith(b"%PDF")


class TestPayrollDashboard:
    def test_hr_dashboard_metrics(
        self, auth_client, api_client, api_write, demo_org, make_salary_structure
    ):
        make_salary_structure(demo_org.esha)
        make_salary_structure(demo_org.sam)
        auth_client(demo_org.hr)
        today = timezone.localdate()
        generated = generate(api_write, today.month, today.year)
        first, second = generated.data["generated"]
        api_write("post", f"{RECORDS}{first['id']}/finalize/")
        api_write("post", f"{RECORDS}{second['id']}/finalize/")
        api_write(
            "post",
            f"{RECORDS}{first['id']}/payment/",
            {
                "payment_status": "paid",
                "payment_date": today.isoformat(),
                "payment_reference": "BANK-1",
            },
        )

        response = api_client.get(DASHBOARD)

        assert response.status_code == 200
        assert response.data["employees_with_salary_structures"] == 2
        expected_total = Decimal("66650.00") * 2
        assert (
            as_decimal(response.data["current_month_payroll_total"]) == expected_total
        )
        assert as_decimal(response.data["total_paid_amount"]) == Decimal("66650.00")
        assert response.data["pending_payments_count"] == 1
        assert as_decimal(response.data["pending_payments_amount"]) == Decimal(
            "66650.00"
        )
        assert response.data["finalized_count"] == 2
        assert len(response.data["recent_activity"]) == 2

    @pytest.mark.parametrize("role_attr", ["employee_user", "manager_user"])
    def test_non_hr_cannot_read_dashboard(
        self, auth_client, api_client, demo_org, role_attr
    ):
        auth_client(getattr(demo_org, role_attr))

        response = api_client.get(DASHBOARD)

        assert response.status_code == 403


class TestPayrollAudit:
    def test_structure_and_revision_changes_are_audited(
        self, auth_client, api_write, demo_org
    ):
        auth_client(demo_org.hr)
        created = api_write("post", STRUCTURES, structure_payload(demo_org.esha))
        old_id = created.data["id"]
        api_write(
            "patch",
            f"{STRUCTURES}{old_id}/",
            {
                "basic_salary": "60000.00",
                "effective_date": "2026-01-01",
                "reason": "Revision",
            },
        )

        assert AuditLog.objects.filter(
            model="payroll.salarystructure", object_id=str(old_id)
        ).exists()
        assert AuditLog.objects.filter(model="payroll.salaryrevision").exists()

    def test_finalization_and_payment_are_audited(
        self, auth_client, api_write, demo_org, make_salary_structure
    ):
        make_salary_structure(demo_org.esha)
        auth_client(demo_org.hr)
        generated = generate(api_write, 3, 2026, demo_org.esha)
        record_id = generated.data["generated"][0]["id"]
        api_write("post", f"{RECORDS}{record_id}/finalize/")
        api_write(
            "post",
            f"{RECORDS}{record_id}/payment/",
            {"payment_status": "paid", "payment_date": "2026-04-02"},
        )

        rows = AuditLog.objects.filter(
            model="payroll.payrollrecord", object_id=str(record_id)
        )
        status_changes = [
            row.changes.get("changes", {}).get("status")
            for row in rows
            if row.changes.get("changes", {}).get("status")
        ]
        payment_changes = [
            row.changes.get("changes", {}).get("payment_status")
            for row in rows
            if row.changes.get("changes", {}).get("payment_status")
        ]
        assert {"before": "draft", "after": "finalized"} in status_changes
        assert {"before": "pending", "after": "paid"} in payment_changes
        assert all(row.actor == demo_org.hr for row in rows)
