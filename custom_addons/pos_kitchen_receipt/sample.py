import os
from datetime import datetime, timedelta


class MockObj:
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)


def _line(qty, name, category, note="", state="pending"):
    return MockObj(
        qty_total=qty,
        full_product_name=name,
        note=note,
        product_category=category,
        state=state,
    )


def _order_line(qty, name, category, note=""):
    return MockObj(
        qty=qty,
        full_product_name=name,
        note=note,
        product_id=MockObj(
            name=name,
            pos_categ_ids=[MockObj(name=category)],
        ),
    )


def build_ticket(sequence="KT-0042", batch="A", ticket_type="new",
                 table_number=None, partner_name=None,
                 partner_street=None, partner_street2=None,
                 payment_status="not_paid", lines=None,
                 customer_note=None, minutes_ago=5):
    partner = None
    if partner_name:
        partner = MockObj(
            name=partner_name,
            street=partner_street or "",
            street2=partner_street2 or "",
        )
    table = None
    if table_number:
        table = MockObj(table_number=table_number)

    create_date = datetime.now() - timedelta(minutes=minutes_ago)
    requested_time = create_date + timedelta(minutes=20)

    ticket = MockObj(
        sequence=sequence,
        batch_letter=batch,
        partner_id=partner,
        table_id=table,
        ticket_type=ticket_type,
        payment_status=payment_status,
        requested_time=requested_time,
        create_date=create_date,
        line_ids=lines or [],
        origin_pos_order_id=None,
        pos_config_id=MockObj(id=1),
    )

    if customer_note:
        mock_lines = [
            _order_line(ln.qty_total, ln.full_product_name, ln.product_category, ln.note)
            for ln in (lines or [])
        ]
        ticket.origin_pos_order_id = MockObj(
            general_customer_note=customer_note,
            lines=mock_lines,
            amount_total=0,
        )
    else:
        total = sum(ln.qty_total * 100 for ln in (lines or []))
        ticket.origin_pos_order_id = MockObj(
            amount_total=total,
        )

    return ticket


SAMPLE_TICKETS = {
    "01_mesa_muzzarella": build_ticket(
        sequence="KT-0042", batch="A", ticket_type="new",
        table_number=5,
        lines=[
            _line(2, "Muzzarella Grande", "Pizza", note="sin ajo"),
            _line(1, "Napolitana Chica", "Pizza"),
            _line(1, "Fugazzeta Rellena Grande", "Pizza", note="bien cocida"),
            _line(2, "Empanada de Carne Suave", "Empanada"),
            _line(1, "Empanada JyQ", "Empanada"),
            _line(2, "Coca-Cola 500ml", "Bebida"),
            _line(1, "Agua sin Gas 500ml", "Bebida"),
        ],
    ),
    "02_delivery_juan": build_ticket(
        sequence="KT-0043", batch="A", ticket_type="new",
        partner_name="Juan Perez",
        partner_street="Av. Corrientes 1234",
        partner_street2="Piso 3 Dto. B",
        lines=[
            _line(3, "Muzzarella Grande", "Pizza"),
            _line(1, "Calabresa Chica", "Pizza", note="sin cebolla"),
            _line(1, "Cerveza Pinta", "Bebida"),
        ],
        customer_note="Tocar timbre Piso 3\nDejar en la puerta si no atienden",
    ),
    "03_pickup_maria": build_ticket(
        sequence="KT-0044", batch="A", ticket_type="new",
        partner_name="Maria Gomez",
        payment_status="paid",
        lines=[
            _line(1, "Jamon y Morrones Grande", "Pizza"),
            _line(6, "Empanada de Pollo", "Empanada"),
            _line(6, "Empanada de Carne Picante", "Empanada"),
        ],
    ),
    "04_adicion_mesa5": build_ticket(
        sequence="KT-0042", batch="B", ticket_type="addition",
        table_number=5,
        lines=[
            _line(1, "Fugazzeta Chica", "Pizza"),
            _line(1, "Cerveza Pinta", "Bebida"),
        ],
        minutes_ago=15,
    ),
    "05_cancelacion_mesa5": build_ticket(
        sequence="KT-0042", batch="C", ticket_type="cancellation",
        table_number=5,
        lines=[
            _line(1, "Empanada JyQ", "Empanada", state="cancelled"),
        ],
        minutes_ago=25,
    ),
}


DEFAULT_OUTPUT_DIR = "/tmp/kitchen_samples"


def build_ticket_data(printer_model, ticket, with_logo=True):
    """Return full ESC/POS bytes: format_ticket_escpos + logo + cut.

    Logo sits between the ticket text and the auto-cut.
    """
    text = printer_model.format_ticket_escpos(ticket, with_cut=False)
    data = text.encode("utf-8", errors="replace")
    if with_logo:
        try:
            from odoo.addons.pos_kitchen_receipt.models._logo import get_logo_escpos_bytes
            logo_bytes = get_logo_escpos_bytes()
            if logo_bytes:
                data = data + logo_bytes + b"\x1bd\x08"
        except Exception:
            pass
    data = data + b"\x1bi"
    return data


def generate_all(printer_model, output_dir=None, with_logo=True):
    """Generate all sample .bin files. `printer_model` is env['kitchen.ticket.printer']."""
    if output_dir is None:
        output_dir = DEFAULT_OUTPUT_DIR
    os.makedirs(output_dir, exist_ok=True)
    for i, (name, ticket) in enumerate(SAMPLE_TICKETS.items(), 1):
        data = build_ticket_data(printer_model, ticket, with_logo=with_logo)
        path = os.path.join(output_dir, f"{name}.bin")
        with open(path, "wb") as f:
            f.write(data)
        print(f"  [{i}/{len(SAMPLE_TICKETS)}] {name}.bin ({len(data)} bytes)")
    return output_dir
