import io
import uuid

import qrcode
from django.core.files.base import ContentFile



# [NEW:QR_HELPER]
def ensure_booking_qr(booking, public_url: str) -> None:
    """
    Create + save booking.qr_image only if it doesn't exist.
    QR encodes the shareable public_url.
    """
    if booking.qr_image:
        return

    qr = qrcode.QRCode(version=None, box_size=10, border=2)
    qr.add_data(public_url)
    qr.make(fit=True)

    img = qr.make_image(fill_color="#080808", back_color="white")

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)

    filename = f"qr_{booking.booking_ref}.png"
    booking.qr_image.save(filename, ContentFile(buf.getvalue()), save=True)
# [/NEW:QR_HELPER]