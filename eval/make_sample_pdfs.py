"""Create the sample PDFs used by the evaluation.

All three documents are fictional and were written for this project, so they
can be shared freely. The generated PDFs are committed in eval/docs/, so you
only need this script if you change the text.

    pip install -r eval/requirements.txt
    python eval/make_sample_pdfs.py

Turkish letters (ç, ğ, ı, İ, ö, ş, ü) need a Unicode TrueType font. The script
uses Arial on Windows or DejaVu Sans on Linux; pass --font to use another.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from fpdf import FPDF

DOCS_DIR = Path(__file__).parent / "docs"
FONT_CANDIDATES = [
    Path("C:/Windows/Fonts/arial.ttf"),
    Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
    Path("/Library/Fonts/Arial Unicode.ttf"),
]

# Each document is a list of pages; each page is a list of (heading, text).
DOCUMENTS: dict[str, tuple[str, list[list[tuple[str, str]]]]] = {
    "acme_employee_handbook.pdf": (
        "Acme Analytics Ltd. - Employee Handbook (fictional sample)",
        [
            [
                ("About Acme Analytics",
                 "Acme Analytics Ltd. is a data consulting company founded in 2012 in "
                 "Manchester, United Kingdom. We help retailers and logistics firms turn "
                 "their sales data into forecasts. Today the company employs around 140 "
                 "people across two offices, Manchester and Leeds."),
                ("How to use this handbook",
                 "This handbook explains the everyday rules of working at Acme. It does not "
                 "replace your employment contract. If the handbook and your contract "
                 "disagree, your contract wins. Questions about any policy should go to the "
                 "People Team at people@acme-analytics.example."),
            ],
            [
                ("Working hours",
                 "The standard working week is 37.5 hours. Core hours are 10:00 to 16:00, "
                 "when everyone is expected to be available. Outside core hours you may "
                 "start and finish when it suits you, as long as your team agrees."),
                ("Remote work",
                 "Employees may work from home up to two days per week. Remote days must be "
                 "recorded in the shared team calendar by Friday of the previous week. "
                 "Working from another country requires written approval from your manager "
                 "and the People Team, and is limited to 20 working days per year."),
            ],
            [
                ("Annual leave",
                 "Full-time employees receive 25 days of paid annual leave per year, plus UK "
                 "public holidays. Up to 5 unused days can be carried over to the next year; "
                 "they must be used before 31 March. Leave requests should be made at least "
                 "two weeks in advance through the HR portal."),
                ("Sick leave",
                 "If you are ill, tell your manager by 09:30 on the first day of absence. For "
                 "absences longer than 7 calendar days a doctor's fit note is required. Acme "
                 "pays full salary for the first 10 sick days in any 12-month period."),
            ],
            [
                ("Expenses",
                 "Business expenses must be submitted in the expenses app within 30 days of "
                 "the purchase, with a photo of the receipt. Claims without a receipt are "
                 "not reimbursed. Approved expenses are paid with the next monthly salary."),
                ("Travel and meals",
                 "Train travel should be booked in standard class. Flights need approval "
                 "from a director before booking. When travelling for work, meals are "
                 "covered up to 25 pounds per day. Hotel stays are covered up to 120 pounds "
                 "per night in London and 90 pounds per night elsewhere."),
            ],
            [
                ("IT and security",
                 "Passwords must be at least 12 characters long and must never be shared. "
                 "Multi-factor authentication is required on all company accounts. "
                 "Suspicious emails must be reported to security@acme-analytics.example "
                 "without clicking any links."),
                ("Leaving the company",
                 "Employees must give one month of notice in writing. Your laptop, badge "
                 "and any other company equipment must be returned within 5 working days "
                 "of your last day. Your final salary includes payment for any unused "
                 "annual leave."),
            ],
        ],
    ),
    "nova_hizmet_sozlesmesi.pdf": (
        "Nova Yazılım A.Ş. - Bulut Muhasebe Hizmet Sözleşmesi (kurgusal örnek)",
        [
            [
                ("Taraflar ve konu",
                 "Bu sözleşme, merkezi İzmir'de bulunan Nova Yazılım A.Ş. (Hizmet Sağlayıcı) "
                 "ile hizmeti satın alan şirket (Müşteri) arasında yapılmıştır. Sözleşmenin "
                 "konusu, Nova Bulut Muhasebe yazılımının internet üzerinden kullanıma "
                 "sunulmasıdır. Hizmet; fatura kesme, gider takibi ve aylık raporları kapsar."),
                ("Süre",
                 "Sözleşme imza tarihinde yürürlüğe girer ve bir yıl süreyle geçerlidir. "
                 "Taraflardan biri feshetmediği sürece sözleşme her yıl aynı koşullarla "
                 "otomatik olarak yenilenir."),
            ],
            [
                ("Ücret",
                 "Hizmetin aylık ücreti 4.500 TL + KDV'dir. Ücret, her yıl Ocak ayında bir "
                 "önceki yılın enflasyon oranı kadar güncellenebilir. Yeni kullanıcı eklemek "
                 "için kullanıcı başına aylık 350 TL + KDV ek ücret alınır."),
                ("Ödeme koşulları",
                 "Fatura her ayın 5'inde düzenlenir. Müşteri, faturayı düzenlenme tarihinden "
                 "itibaren 10 gün içinde banka havalesi ile öder. Geciken ödemeler için aylık "
                 "yüzde 2 gecikme faizi uygulanır. Ödeme 30 günden fazla gecikirse Hizmet "
                 "Sağlayıcı hizmeti geçici olarak durdurabilir."),
            ],
            [
                ("Hizmet seviyesi",
                 "Hizmet Sağlayıcı, sistemin aylık en az yüzde 99,5 oranında erişilebilir "
                 "olmasını taahhüt eder. Planlı bakım çalışmaları en az 48 saat önceden "
                 "e-posta ile duyurulur ve gece 02:00 ile 05:00 arasında yapılır."),
                ("Teknik destek",
                 "Teknik destek hafta içi 09:00 ile 18:00 arasında telefon ve e-posta ile "
                 "verilir. Kritik arızalara en geç 4 saat içinde, diğer taleplere ise en geç "
                 "bir iş günü içinde yanıt verilir."),
            ],
            [
                ("Fesih",
                 "Taraflar, sözleşmeyi 30 gün önceden yazılı bildirimde bulunarak "
                 "feshedebilir. Fesih durumunda, peşin ödenmiş ancak kullanılmamış aylara ait "
                 "ücretler Müşteri'ye iade edilir."),
                ("Verilerin saklanması ve gizlilik",
                 "Sözleşme sona erdikten sonra Müşteri'nin verileri 60 gün boyunca saklanır; "
                 "bu süre içinde Müşteri verilerini dışa aktarabilir. 60 günün sonunda tüm "
                 "veriler kalıcı olarak silinir. Kişisel veriler KVKK'ya uygun olarak "
                 "işlenir ve üçüncü kişilerle paylaşılmaz."),
            ],
        ],
    ),
    "solaris_x2_user_manual.pdf": (
        "Solaris X2 Portable Speaker - User Manual (fictional sample)",
        [
            [
                ("In the box",
                 "The box contains the Solaris X2 speaker, a USB-C charging cable, a carrying "
                 "strap and this manual. A wall charger is not included; any USB-C charger "
                 "of at least 10 watts can be used."),
                ("Before first use",
                 "Charge the speaker fully before using it for the first time. A full charge "
                 "takes about 3 hours. While charging, the LED ring glows orange; it turns "
                 "solid blue when the battery is full."),
            ],
            [
                ("Pairing with Bluetooth",
                 "Hold the power button for 3 seconds to switch the speaker on. Press the "
                 "Bluetooth button once; the LED ring flashes blue. Select Solaris X2 in the "
                 "Bluetooth settings of your phone. The speaker remembers up to 8 devices."),
                ("Battery and water resistance",
                 "A full battery plays music for up to 8 hours at medium volume. The speaker "
                 "is rated IPX5, which means it is protected against splashing water, but it "
                 "must not be put under water."),
            ],
            [
                ("Troubleshooting",
                 "If the speaker stops responding, hold the power button for 10 seconds to "
                 "restart it. To restore factory settings, hold the power and volume-down "
                 "buttons together for 5 seconds; this also removes all paired devices."),
                ("Warranty",
                 "Solaris X2 comes with a 2-year limited warranty from the date of purchase. "
                 "The warranty does not cover damage caused by submerging the speaker in "
                 "water, drops, or opening the case. Keep your receipt as proof of purchase."),
            ],
        ],
    ),
}


def find_font(explicit: str | None) -> Path:
    if explicit:
        return Path(explicit)
    for candidate in FONT_CANDIDATES:
        if candidate.exists():
            return candidate
    raise SystemExit("No Unicode font found. Pass one with --font path/to/font.ttf")


def build(filename: str, title: str, pages: list[list[tuple[str, str]]], font: Path) -> None:
    pdf = FPDF(format="A4")
    pdf.set_margins(20, 20, 20)
    pdf.add_font("Body", "", str(font))
    for number, sections in enumerate(pages, start=1):
        pdf.add_page()
        pdf.set_font("Body", size=10)
        pdf.set_text_color(110, 110, 110)
        pdf.cell(0, 6, title, new_x="LMARGIN", new_y="NEXT")
        pdf.ln(4)
        for heading, text in sections:
            pdf.set_text_color(20, 20, 20)
            pdf.set_font("Body", size=14)
            pdf.cell(0, 8, heading, new_x="LMARGIN", new_y="NEXT")
            pdf.set_font("Body", size=11)
            pdf.multi_cell(0, 6, text, new_x="LMARGIN", new_y="NEXT")
            pdf.ln(4)
        # Page number in the bottom margin. Auto page break is switched off
        # while writing it, otherwise it would start a new, almost empty page.
        pdf.set_auto_page_break(False)
        pdf.set_y(-15)
        pdf.set_font("Body", size=9)
        pdf.set_text_color(110, 110, 110)
        pdf.cell(0, 6, f"{number}", align="C")
        pdf.set_auto_page_break(True, margin=20)
    pdf.output(str(DOCS_DIR / filename))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--font", help="Path to a Unicode .ttf font")
    args = parser.parse_args()
    font = find_font(args.font)
    DOCS_DIR.mkdir(exist_ok=True)
    for filename, (title, pages) in DOCUMENTS.items():
        build(filename, title, pages, font)
        print(f"wrote eval/docs/{filename} ({len(pages)} pages)")


if __name__ == "__main__":
    main()
