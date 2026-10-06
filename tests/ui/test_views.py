"""Deadlines computed on read from accepted fields (US-00-007 AC-3, TC-0120, TC-0121)."""

import dataclasses
from datetime import date

from app.ui.views import deadlines_from
from tests.ui.fakes import LEASE_01, LEASE_01_FIELDS, field

TODAY = date(2026, 10, 5)
VENDOR_07 = dataclasses.replace(
    LEASE_01, title="Supply Agreement 07", id=LEASE_01.id.__class__(int=7)
)
VENDOR_07_FIELDS = [
    field(VENDOR_07, "effective_date", "1 September 2025", "2.1"),
    field(VENDOR_07, "term", "two (2) years", "2.2"),
    field(VENDOR_07, "notice_period", "three (3) months", "2.3"),
]


# TC-0120
def test_tc0120_deadlines_are_soonest_first_with_contract_and_clause() -> None:
    rows = deadlines_from([*VENDOR_07_FIELDS, *LEASE_01_FIELDS], TODAY)

    assert [(r.contract_title, r.kind, r.due, r.clause) for r in rows] == [
        ("Lease Agreement 01", "notice_deadline", date(2026, 12, 1), "7"),
        ("Lease Agreement 01", "expiry", date(2026, 12, 31), "2.2"),
        ("Supply Agreement 07", "notice_deadline", date(2027, 5, 31), "2.3"),
        ("Supply Agreement 07", "expiry", date(2027, 8, 31), "2.2"),
    ]
    assert rows[0].days_left == 57


# TC-0121
def test_tc0121_without_a_usable_notice_period_only_expiry_is_listed() -> None:
    usable = [f for f in LEASE_01_FIELDS if f.field_name != "notice_period"]

    rows = deadlines_from(usable, TODAY)

    assert [r.kind for r in rows] == ["expiry"]
