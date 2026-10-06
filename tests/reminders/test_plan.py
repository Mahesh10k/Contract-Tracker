"""Reminder planning, choice, email text and today (US-00-006, TC-0161 to 0172)."""

import uuid
from datetime import date

from app.reminders.plan import (
    DueReminder,
    PlannedReminder,
    choose,
    diff_obligations,
    plan_reminders,
    render_email,
    resolve_today,
)

TODAY = date(2026, 10, 5)


def due(
    lead: int, due_on: date, obligation: uuid.UUID, kind: str = "notice_deadline"
) -> DueReminder:
    return DueReminder(
        id=uuid.uuid4(),
        obligation_id=obligation,
        lead_days=lead,
        due_on=due_on,
        kind=kind,
        contract_title="Lease Agreement 01",
        clause="7",
    )


def test_tc0161_a_2028_11_30_deadline_is_reminded_at_60_30_and_7_days() -> None:
    plans = plan_reminders(date(2028, 11, 30))

    assert plans == [
        PlannedReminder(60, date(2028, 10, 1)),
        PlannedReminder(30, date(2028, 10, 31)),
        PlannedReminder(7, date(2028, 11, 23)),
    ]


def test_tc0162_planning_across_a_month_and_year_end() -> None:
    plans = plan_reminders(date(2027, 1, 5))

    assert [(p.lead_days, p.send_on) for p in plans] == [
        (60, date(2026, 11, 6)),
        (30, date(2026, 12, 6)),
        (7, date(2026, 12, 29)),
    ]
    assert all(p.send_on < date(2027, 1, 5) for p in plans)


def test_tc0163_a_deadline_three_days_away_sends_only_the_seven_day_reminder() -> None:
    obligation = uuid.uuid4()
    reminders = [due(lead, date(2026, 10, 8), obligation) for lead in (60, 30, 7)]

    choice = choose(reminders, TODAY)

    assert [r.lead_days for r in choice.send] == [7]
    assert sorted(r.lead_days for r in choice.skip) == [30, 60]


def test_tc0164_a_deadline_that_has_already_passed_is_skipped_not_emailed() -> None:
    obligation = uuid.uuid4()
    reminders = [due(lead, date(2026, 10, 1), obligation) for lead in (30, 7)]

    choice = choose(reminders, TODAY)

    assert choice.send == []
    assert len(choice.skip) == 2


def test_a_deadline_falling_today_is_still_sent() -> None:
    choice = choose([due(7, TODAY, uuid.uuid4())], TODAY)

    assert len(choice.send) == 1
    assert choice.skip == []


def test_two_obligations_are_chosen_independently() -> None:
    notice, expiry = uuid.uuid4(), uuid.uuid4()
    reminders = [
        due(30, date(2026, 11, 1), notice),
        due(7, date(2026, 11, 1), notice),
        due(30, date(2026, 12, 31), expiry, "expiry"),
    ]

    choice = choose(reminders, TODAY)

    assert sorted((r.obligation_id == notice, r.lead_days) for r in choice.send) == [
        (False, 30),
        (True, 7),
    ]
    assert [r.lead_days for r in choice.skip] == [30]


def test_tc0169_the_email_names_the_contract_the_obligation_the_date_and_the_clause() -> None:
    reminder = due(60, date(2026, 12, 1), uuid.uuid4())

    message = render_email(reminder, TODAY, "owner@x.test", "reminders@x.test")

    body = message.get_content()
    assert message["To"] == "owner@x.test"
    assert message["From"] == "reminders@x.test"
    assert "Lease Agreement 01" in message["Subject"]
    assert "Notice deadline" in message["Subject"]
    assert "2026-12-01" in body
    assert "clause 7" in body
    assert "57 days" in body


def test_an_email_for_a_field_with_no_clause_does_not_print_an_empty_clause_line() -> None:
    reminder = DueReminder(
        uuid.uuid4(), uuid.uuid4(), 7, date(2026, 12, 1), "expiry", "Lease", None
    )

    body = render_email(reminder, TODAY, "a@b.test", "c@d.test").get_content()

    assert "clause" not in body.lower()
    assert "Contract expires" in body


def test_tc0170_an_explicit_date_beats_pretend_today_which_beats_the_real_clock() -> None:
    real = date(2026, 10, 5)

    assert resolve_today(date(2028, 10, 31), date(2028, 10, 1), real) == date(2028, 10, 31)
    assert resolve_today(None, date(2028, 10, 1), real) == date(2028, 10, 1)
    assert resolve_today(None, None, real) == real


def test_tc0172_a_changed_due_date_replaces_the_obligation_and_unchanged_ones_stay() -> None:
    existing = {("expiry", date(2026, 12, 31)), ("notice_deadline", date(2026, 12, 1))}
    desired = {("expiry", date(2027, 12, 31)), ("notice_deadline", date(2026, 12, 1))}

    delete, insert = diff_obligations(existing, desired)

    assert delete == [("expiry", date(2026, 12, 31))]
    assert insert == [("expiry", date(2027, 12, 31))]
