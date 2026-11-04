"""Savings automation engine (DC-014, DC-018, DC-019, DC-020, DC-021).

The engine materialises one execution row per scheduled occurrence before any
effect is applied, so the unique key ``(automation_ref, scheduled_date)`` is the
single source of truth against duplicates. A single missed occurrence is
recovered automatically with its original date; when several occurrences are
missed the user chooses which ones to recover (DC-021).
"""

from __future__ import annotations

import logging
from calendar import monthrange
from datetime import date, datetime, timedelta

from django.conf import settings
from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from .models import (
    Account,
    AutomationExecution,
    Line,
    Notification,
    Profile,
    SavingsAutomation,
    Transaction,
)
from .services import assert_accounts_non_negative

logger = logging.getLogger(__name__)


class MissingAutomationData(Exception):
    """The rule points at an account or savings container that is not usable."""


def next_occurrence(day: date, frequency: str) -> date:
    if frequency == SavingsAutomation.Frequency.DAILY:
        return day + timedelta(days=1)
    if frequency == SavingsAutomation.Frequency.WEEKLY:
        return day + timedelta(days=7)
    months = 12 if frequency == SavingsAutomation.Frequency.YEARLY else 1
    year = day.year + (day.month - 1 + months) // 12
    month = (day.month - 1 + months) % 12 + 1
    last_day = monthrange(year, month)[1]
    return date(year, month, min(day.day, last_day))


def automation_name(automation: SavingsAutomation) -> str:
    savings = automation.savings.name if automation.savings_id else "salvadanaio"
    return f"Versamento automatico su {savings}"


def materialize_occurrences(
    automation: SavingsAutomation, today: date | None = None
) -> list[AutomationExecution]:
    """Create a pending execution for every scheduled date up to ``today``."""
    today = today or timezone.localdate()
    created: list[AutomationExecution] = []
    scheduled = automation.next_run_on
    source_name = (
        automation.source_account.name if automation.source_account_id else ""
    )
    savings_name = automation.savings.name if automation.savings_id else ""
    label = automation_name(automation)

    while scheduled <= today:
        execution, was_created = AutomationExecution.objects.get_or_create(
            automation_ref=automation.pk,
            scheduled_date=scheduled,
            defaults={
                "automation": automation,
                "automation_name": label,
                "profile": automation.profile,
                "amount": automation.amount,
                "source_account": automation.source_account,
                "source_account_name": source_name,
                "savings": automation.savings,
                "savings_name": savings_name,
                "status": AutomationExecution.Status.PENDING,
            },
        )
        if was_created:
            created.append(execution)
        scheduled = next_occurrence(scheduled, automation.frequency)

    if automation.next_run_on != scheduled:
        automation.next_run_on = scheduled
        automation.save(update_fields=("next_run_on", "updated_at"))
    return created


def notify(
    profile: Profile,
    kind: str,
    message: str,
    *,
    automation: SavingsAutomation | None = None,
    execution: AutomationExecution | None = None,
) -> Notification:
    return Notification.objects.create(
        profile=profile,
        automation=automation,
        execution=execution,
        kind=kind,
        message=message[:255],
    )


def notify_pending_choice(
    automation: SavingsAutomation, pending: list[AutomationExecution]
) -> None:
    already = Notification.objects.filter(
        profile=automation.profile,
        automation=automation,
        kind=Notification.Kind.AUTOMATION_PENDING,
        read_at__isnull=True,
    ).exists()
    if already:
        return
    dates = ", ".join(item.scheduled_date.strftime("%d-%m-%Y") for item in pending)
    notify(
        automation.profile,
        Notification.Kind.AUTOMATION_PENDING,
        (
            f"{len(pending)} occorrenze perse per «{automation.savings.name}» "
            f"({dates}): scegli quali recuperare."
        ),
        automation=automation,
    )


def _skip(
    execution: AutomationExecution,
    code: str,
    message: str,
    *,
    notify_user: bool = True,
) -> AutomationExecution:
    execution.status = AutomationExecution.Status.SKIPPED
    execution.failure_code = code
    execution.failure_message = message[:255]
    execution.next_retry_at = None
    execution.save(
        update_fields=(
            "status",
            "attempts",
            "failure_code",
            "failure_message",
            "next_retry_at",
            "updated_at",
        )
    )
    if notify_user:
        notify(
            execution.profile,
            Notification.Kind.AUTOMATION_SKIPPED,
            message,
            automation=execution.automation,
            execution=execution,
        )
    return execution


def _fail_technically(
    execution: AutomationExecution, error: Exception, now: datetime
) -> AutomationExecution:
    execution.attempts += 1
    max_attempts = getattr(settings, "AUTOMATION_MAX_ATTEMPTS", 3)
    delays = getattr(settings, "AUTOMATION_RETRY_DELAYS", [60, 300, 900])
    message = str(error)[:255] or "Errore tecnico."
    execution.failure_code = AutomationExecution.FailureCode.TECHNICAL_ERROR
    execution.failure_message = message

    if execution.attempts >= max_attempts:
        execution.status = AutomationExecution.Status.FAILED
        execution.next_retry_at = None
        automation = execution.automation
        if automation is not None:
            automation.status = SavingsAutomation.Status.SUSPENDED
            automation.save(update_fields=("status", "updated_at"))
            notify(
                execution.profile,
                Notification.Kind.AUTOMATION_SUSPENDED,
                (
                    f"Automazione su «{execution.savings_name}» sospesa dopo "
                    f"{execution.attempts} tentativi: {message}"
                ),
                automation=automation,
                execution=execution,
            )
    else:
        delay_index = min(execution.attempts - 1, len(delays) - 1)
        delay = delays[delay_index] if delays else 60
        execution.status = AutomationExecution.Status.FAILED
        execution.next_retry_at = now + timedelta(seconds=delay)

    execution.save(
        update_fields=(
            "status",
            "attempts",
            "failure_code",
            "failure_message",
            "next_retry_at",
            "updated_at",
        )
    )
    return execution


def _apply_transfer(
    automation: SavingsAutomation, execution: AutomationExecution
) -> Transaction:
    source: Account | None = execution.source_account
    savings = execution.savings
    if source is None or savings is None:
        raise MissingAutomationData(
            "Il conto di partenza o il salvadanaio non esistono più."
        )
    if source.archived:
        raise MissingAutomationData("Il conto di partenza è archiviato.")

    amount = execution.amount
    assert_accounts_non_negative([(source, -amount, execution.scheduled_date)])

    operation = Transaction.objects.create(
        profile=execution.profile,
        automation=automation,
        kind=Transaction.Kind.TRANSFER,
        date=execution.scheduled_date,
        description=f"Versamento automatico · {savings.name}",
        amount=amount,
    )
    Line.objects.create(
        transaction=operation,
        account=source,
        amount=-amount,
        role=Line.Role.TRANSFER_OUT,
    )
    Line.objects.create(
        transaction=operation,
        savings=savings,
        amount=amount,
        role=Line.Role.TRANSFER_IN,
    )
    return operation


def _validation_message(error: ValidationError) -> tuple[str, str]:
    detail = error.detail
    if isinstance(detail, dict):
        code = detail.get("code")
        if isinstance(code, (list, tuple)):
            code = code[0] if code else ""
        message = detail.get("amount") or detail.get("detail") or detail
        if isinstance(message, (list, tuple)):
            message = message[0] if message else ""
        return str(code or ""), str(message)
    if isinstance(detail, (list, tuple)):
        return "", str(detail[0]) if detail else ""
    return "", str(detail)


def execute_occurrence(
    execution: AutomationExecution, now: datetime | None = None
) -> AutomationExecution:
    """Apply one occurrence exactly once and persist its outcome."""
    now = now or timezone.now()
    execution_id = execution.pk
    try:
        with transaction.atomic():
            automation = (
                SavingsAutomation.objects.select_for_update()
                .filter(pk=execution.automation_ref)
                .first()
            )
            execution = AutomationExecution.objects.select_for_update().get(
                pk=execution_id
            )
            if execution.status not in {
                AutomationExecution.Status.PENDING,
                AutomationExecution.Status.FAILED,
            }:
                return execution
            if automation is None:
                return _skip(
                    execution,
                    AutomationExecution.FailureCode.RULE_DELETED,
                    "La regola dell'automazione non esiste più.",
                )
            if automation.status != SavingsAutomation.Status.ACTIVE:
                return execution
            if (
                execution.status == AutomationExecution.Status.FAILED
                and execution.next_retry_at is not None
                and execution.next_retry_at > now
            ):
                return execution

            execution.status = AutomationExecution.Status.RUNNING
            execution.save(update_fields=("status", "updated_at"))
            operation = _apply_transfer(automation, execution)
            execution.attempts += 1
            execution.status = AutomationExecution.Status.SUCCEEDED
            execution.transaction = operation
            execution.failure_code = ""
            execution.failure_message = ""
            execution.next_retry_at = None
            execution.save(
                update_fields=(
                    "status",
                    "attempts",
                    "transaction",
                    "failure_code",
                    "failure_message",
                    "next_retry_at",
                    "updated_at",
                )
            )
            return execution
    except MissingAutomationData as error:
        with transaction.atomic():
            execution = AutomationExecution.objects.select_for_update().get(
                pk=execution_id
            )
            execution.attempts += 1
            return _skip(
                execution,
                AutomationExecution.FailureCode.MISSING_DATA,
                str(error),
            )
    except ValidationError as error:
        code, message = _validation_message(error)
        with transaction.atomic():
            execution = AutomationExecution.objects.select_for_update().get(
                pk=execution_id
            )
            execution.attempts += 1
            if code == "insufficient_account_balance":
                return _skip(
                    execution,
                    AutomationExecution.FailureCode.INSUFFICIENT_BALANCE,
                    message or "Saldo insufficiente sul conto di partenza.",
                )
            return _fail_technically(execution, error, now)
    except Exception as error:  # noqa: BLE001 - technical failures are recorded
        with transaction.atomic():
            execution = AutomationExecution.objects.select_for_update().get(
                pk=execution_id
            )
            return _fail_technically(execution, error, now)


def process_automation(
    automation: SavingsAutomation,
    *,
    today: date | None = None,
    now: datetime | None = None,
) -> dict[str, int]:
    """Materialise due occurrences and apply what the policy allows."""
    today = today or timezone.localdate()
    now = now or timezone.now()
    result = {"created": 0, "executed": 0, "pending_choice": 0, "retried": 0}

    automation_id = automation.pk
    with transaction.atomic():
        automation = (
            SavingsAutomation.objects.select_for_update()
            .filter(pk=automation_id)
            .first()
        )
        if automation is None or automation.status != SavingsAutomation.Status.ACTIVE:
            return result
        created = materialize_occurrences(automation, today)
    result["created"] = len(created)

    retries = list(
        automation.executions.filter(
            status=AutomationExecution.Status.FAILED,
            next_retry_at__lte=now,
        ).order_by("scheduled_date", "id")
    )
    for execution in retries:
        automation.refresh_from_db()
        if automation.status != SavingsAutomation.Status.ACTIVE:
            break
        executed = execute_occurrence(execution, now=now)
        if executed.status == AutomationExecution.Status.SUCCEEDED:
            result["retried"] += 1

    automation.refresh_from_db()
    if automation.status != SavingsAutomation.Status.ACTIVE:
        return result

    pending = list(
        automation.executions.filter(
            status=AutomationExecution.Status.PENDING
        ).order_by("scheduled_date", "id")
    )
    if len(pending) > 1:
        notify_pending_choice(automation, pending)
        result["pending_choice"] = len(pending)
        return result

    if len(pending) == 1:
        execution = execute_occurrence(pending[0], now=now)
        if execution.status == AutomationExecution.Status.SUCCEEDED:
            result["executed"] += 1
    return result


def run_for_profile(
    profile: Profile,
    *,
    today: date | None = None,
    now: datetime | None = None,
) -> dict[str, int]:
    totals = {"rules": 0, "created": 0, "executed": 0, "pending_choice": 0, "retried": 0}
    automations = SavingsAutomation.objects.filter(
        profile=profile, status=SavingsAutomation.Status.ACTIVE
    ).select_related("savings", "source_account")
    for automation in automations:
        totals["rules"] += 1
        try:
            outcome = process_automation(automation, today=today, now=now)
        except Exception:  # noqa: BLE001 - one broken rule must not stop the rest
            logger.exception("Automazione %s non elaborata", automation.pk)
            continue
        for key in ("created", "executed", "pending_choice", "retried"):
            totals[key] += outcome[key]
    return totals


def run_all(
    *, today: date | None = None, now: datetime | None = None
) -> dict[str, int]:
    totals = {"rules": 0, "created": 0, "executed": 0, "pending_choice": 0, "retried": 0}
    automations = SavingsAutomation.objects.filter(
        status=SavingsAutomation.Status.ACTIVE
    ).select_related("savings", "source_account")
    for automation in automations:
        totals["rules"] += 1
        try:
            outcome = process_automation(automation, today=today, now=now)
        except Exception:  # noqa: BLE001 - one broken rule must not stop the rest
            logger.exception("Automazione %s non elaborata", automation.pk)
            continue
        for key in ("created", "executed", "pending_choice", "retried"):
            totals[key] += outcome[key]
    return totals


def resolve_pending(
    automation: SavingsAutomation,
    recover_ids: set[int],
    *,
    now: datetime | None = None,
) -> dict[str, int]:
    """Recover the selected occurrences and skip all the other pending ones.

    Calling this method is the explicit choice required by DC-021. The
    unselected occurrences are marked as skipped and are not executed later.
    """
    now = now or timezone.now()
    outcome = {"recovered": 0, "skipped": 0}
    pending = list(
        automation.executions.filter(
            status=AutomationExecution.Status.PENDING
        ).order_by("scheduled_date", "id")
    )
    for execution in pending:
        if execution.pk in recover_ids:
            automation.refresh_from_db()
            result = execute_occurrence(execution, now=now)
            if result.status == AutomationExecution.Status.SUCCEEDED:
                outcome["recovered"] += 1
            else:
                outcome["skipped"] += 1
        else:
            execution.attempts += 1
            _skip(
                execution,
                AutomationExecution.FailureCode.NOT_SELECTED,
                (
                    f"Occorrenza del {execution.scheduled_date:%d-%m-%Y} "
                    "non selezionata per il recupero."
                ),
                notify_user=False,
            )
            outcome["skipped"] += 1

    Notification.objects.filter(
        profile=automation.profile,
        automation=automation,
        kind=Notification.Kind.AUTOMATION_PENDING,
        read_at__isnull=True,
    ).update(read_at=timezone.now())
    return outcome


def cancel_open_executions(
    automation: SavingsAutomation, code: str
) -> int:
    return automation.executions.filter(
        status__in=(
            AutomationExecution.Status.PENDING,
            AutomationExecution.Status.FAILED,
        )
    ).update(
        status=AutomationExecution.Status.CANCELLED,
        failure_code=code,
        next_retry_at=None,
        updated_at=timezone.now(),
    )
