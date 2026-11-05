"""Bounded, tenant-scoped and idempotent historical sales imports."""

import csv
import hashlib
import io
import json
from collections import defaultdict
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy import select, func, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_manager, get_current_user
from app.database import get_db
from app.models import Customer, MenuItem, PaymentMethod, Sale, SaleItem, User
from app.models.imported_order import ImportedOrder

router = APIRouter(prefix="/data", tags=["Data Import"])
MAX_BYTES = 5 * 1024 * 1024
MAX_ROWS = 10_000


def parse_date(value):
    if value:
        for fmt in (
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%d",
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%dT%H:%M:%S.%f",
            "%d-%m-%Y",
            "%m/%d/%Y",
            "%d/%m/%Y",
            "%Y/%m/%d",
        ):
            try:
                return datetime.strptime(value.strip(), fmt).replace(
                    tzinfo=timezone.utc
                )
            except ValueError:
                continue
    return None


def money(value, allow_zero=False):
    amount = Decimal(value)
    if (
        not amount.is_finite()
        or amount < 0
        or (amount == 0 and not allow_zero)
        or amount > Decimal("99999999.99")
    ):
        raise ValueError("Amount outside supported range")
    if amount != amount.quantize(Decimal("0.01")):
        raise ValueError("Amounts require at most two decimal places")
    return amount.quantize(Decimal("0.01"))


@router.post(
    "/upload-sales", status_code=201, dependencies=[Depends(get_current_manager)]
)
async def upload_sales(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Each row requires order_id, payment_method, tax_amount and pre-tax total_amount.

    Offset-free dates mean UTC. Reject any order with an invalid row. Exact
    retries skip existing orders; changed content under an old ID is rejected.
    """
    if not (file.filename or "").lower().endswith(".csv"):
        raise HTTPException(400, "Uploaded file must be a CSV")
    content = await file.read(MAX_BYTES + 1)
    if len(content) > MAX_BYTES:
        raise HTTPException(413, "CSV must not exceed 5 MB")
    try:
        decoded = content.decode("utf-8-sig")
        if "\x00" in decoded:
            raise ValueError("Binary content")
        reader = csv.DictReader(io.StringIO(decoded), strict=True)
        headers = [h.strip().lower() for h in (reader.fieldnames or [])]
        required = {
            "order_id",
            "date",
            "item_name",
            "quantity",
            "unit_price",
            "total_amount",
            "payment_method",
            "tax_amount",
        }
        if len(set(headers)) != len(headers) or not required.issubset(headers):
            raise HTTPException(
                400, "CSV requires unique headers: " + ", ".join(sorted(required))
            )
        rows = []
        for raw in reader:
            if len(rows) >= MAX_ROWS:
                raise HTTPException(413, "CSV must not exceed 10,000 rows")
            if None in raw or any(v is None for v in raw.values()):
                raise ValueError("Malformed row")
            rows.append({k.strip().lower(): v.strip() for k, v in raw.items()})
        if not rows:
            raise HTTPException(400, "CSV contains no data rows")
    except (UnicodeError, csv.Error, ValueError):
        raise HTTPException(400, "Invalid UTF-8 CSV content") from None

    if db.bind.dialect.name == "sqlite":
        # Legacy SQLite transaction control does not BEGIN for SELECT. Without
        # an explicit transaction, releasing the first SAVEPOINT commits it.
        connection = await db.connection()
        active = await connection.run_sync(
            lambda sync: sync.connection.driver_connection.in_transaction
        )
        if not active:
            await connection.exec_driver_sql("BEGIN IMMEDIATE")

    names = {row["item_name"].lower() for row in rows}
    menus = (
        (
            await db.execute(
                select(MenuItem).where(
                    MenuItem.tenant_id == current_user.tenant_id,
                    func.lower(MenuItem.name).in_(names),
                )
            )
        )
        .scalars()
        .all()
    )
    menu_map = {item.name.strip().lower(): item.id for item in menus}
    ids = set()
    for row in rows:
        try:
            customer_id = int(row.get("customer_id", ""))
            if 0 < customer_id <= 2147483647:
                ids.add(customer_id)
        except ValueError:
            pass
    customers = set(
        (
            await db.execute(
                select(Customer.id).where(
                    Customer.tenant_id == current_user.tenant_id, Customer.id.in_(ids)
                )
            )
        )
        .scalars()
        .all()
    )
    groups, rejected, errors = defaultdict(list), set(), []

    def reject(index, order_id, message):
        rejected.add(order_id)
        errors.append({"row": index, "errors": [message]})

    for index, row in enumerate(rows, 1):
        order_id = row["order_id"]
        try:
            customer = int(row["customer_id"]) if row.get("customer_id") else None
            if customer is not None and customer not in customers:
                reject(index, order_id, "Customer ID is invalid or unavailable")
                continue
            date, menu_id, qty = (
                parse_date(row["date"]),
                menu_map.get(row["item_name"].lower()),
                int(row["quantity"]),
            )
            if (
                not order_id
                or len(order_id) > 128
                or date is None
                or menu_id is None
                or not 1 <= qty <= 1000
            ):
                raise ValueError("Invalid order")
            groups[order_id].append(
                {
                    "row": index,
                    "timestamp": date,
                    "customer_id": customer,
                    "menu_item_id": menu_id,
                    "quantity": qty,
                    "unit_price": money(row["unit_price"]),
                    "total_amount": money(row["total_amount"]),
                    "tax_amount": money(row["tax_amount"], True),
                    "payment_method": PaymentMethod(row["payment_method"]).value,
                }
            )
        except (ValueError, InvalidOperation, OverflowError):
            reject(
                index,
                order_id,
                "Invalid order row: check date, menu item, quantity, amounts and payment method",
            )
    inserted = matched = skipped = 0
    try:
        for order_id, items in groups.items():
            if order_id in rejected:
                continue
            first = items[0]
            fields = (
                "timestamp",
                "customer_id",
                "total_amount",
                "tax_amount",
                "payment_method",
            )
            if (
                len(items) > 100
                or any(any(i[k] != first[k] for k in fields) for i in items)
                or sum((i["unit_price"] * i["quantity"] for i in items), Decimal(0))
                != first["total_amount"]
                or first["tax_amount"] > first["total_amount"]
            ):
                reject(
                    first["row"],
                    order_id,
                    "Inconsistent order totals, metadata or item count",
                )
                continue
            canonical = [
                json.dumps(
                    {k: str(v) for k, v in i.items() if k != "row"}, sort_keys=True
                )
                for i in items
            ]
            digest = hashlib.sha256(json.dumps(sorted(canonical)).encode()).hexdigest()
            query = select(ImportedOrder).where(
                ImportedOrder.tenant_id == current_user.tenant_id,
                ImportedOrder.order_id == order_id,
            )
            receipt = (await db.execute(query)).scalar_one_or_none()
            if receipt:
                if receipt.content_hash == digest:
                    skipped += 1
                else:
                    reject(
                        first["row"],
                        order_id,
                        "order_id was already imported with different content",
                    )
                continue
            try:
                async with db.begin_nested():
                    sale = Sale(
                        tenant_id=current_user.tenant_id,
                        **{k: first[k] for k in fields},
                    )
                    db.add(sale)
                    await db.flush()
                    db.add(
                        ImportedOrder(
                            tenant_id=current_user.tenant_id,
                            order_id=order_id,
                            content_hash=digest,
                            sale_id=sale.id,
                        )
                    )
                    for item in items:
                        db.add(
                            SaleItem(
                                tenant_id=current_user.tenant_id,
                                sale_id=sale.id,
                                menu_item_id=item["menu_item_id"],
                                quantity=item["quantity"],
                                unit_price_at_sale=item["unit_price"],
                            )
                        )
                    if first["customer_id"] is not None:
                        updated = await db.execute(
                            update(Customer)
                            .where(
                                Customer.id == first["customer_id"],
                                Customer.tenant_id == current_user.tenant_id,
                            )
                            .values(
                                visit_count=Customer.visit_count + 1,
                                total_spent_inr=Customer.total_spent_inr
                                + first["total_amount"]
                                + first["tax_amount"],
                            )
                        )
                        if updated.rowcount != 1:
                            raise HTTPException(409, "Customer is no longer available")
                    await db.flush()
            except IntegrityError:
                receipt = (await db.execute(query)).scalar_one_or_none()
                if receipt is None:
                    raise
                if receipt.content_hash == digest:
                    skipped += 1
                else:
                    reject(
                        first["row"],
                        order_id,
                        "order_id was already imported with different content",
                    )
                continue
            inserted += 1
            matched += len(items)
        await db.commit()
    except Exception:
        await db.rollback()
        raise
    return {
        "status": "success",
        "rows_inserted": inserted,
        "items_matched": matched,
        "orders_skipped": skipped,
        "validation_errors": errors,
        "message": f"{inserted} sales imported. Retrain your forecast model to incorporate new data.",
    }
