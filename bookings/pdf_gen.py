import os
from io import BytesIO
from venv import logger
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.lib.pagesizes import A4
from tours.models import LandTourPage
from django.utils.translation import gettext_lazy as _
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from bookings.models import Booking 
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, 
    Spacer, Table, TableStyle, Image, 
    PageTemplate, Frame, HRFlowable, 
    KeepTogether)

def generate_itinerary_pdf(booking: Booking) -> bytes:
    try:
        buffer = BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            topMargin=15*mm,
            bottomMargin=15*mm,
            leftMargin=15*mm,
            rightMargin=15*mm
        )
        styles = getSampleStyleSheet()

        title_style = ParagraphStyle(
            name='Title',
            parent=styles['Title'],
            fontName='Helvetica-Bold',
            fontSize=20,
            textColor=colors.HexColor('#1a3c6e'),
            spaceAfter=8,
            alignment=1
        )
        title_shadow_style = ParagraphStyle(
            name='TitleShadow',
            parent=title_style,
            textColor=colors.HexColor('#cccccc'),
            spaceAfter=0
        )
        subtitle_style = ParagraphStyle(
            name='Subtitle',
            parent=styles['Title'],
            fontName='Helvetica',
            fontSize=16,
            textColor=colors.HexColor('#1a3c6e'),
            spaceAfter=12,
            alignment=1
        )
        heading_style = ParagraphStyle(
            name='Heading2',
            parent=styles['Heading2'],
            fontName='Helvetica-Bold',
            fontSize=12,
            textColor=colors.HexColor('#333333'),
            spaceBefore=12,
            spaceAfter=8
        )
        normal_style = ParagraphStyle(
            name='Normal',
            parent=styles['Normal'],
            fontName='Helvetica',
            fontSize=10,
            leading=12,
            textColor=colors.HexColor('#333333')
        )
        bullet_style = ParagraphStyle(
            name='Bullet',
            parent=normal_style,
            leftIndent=10,
            bulletIndent=0,
            spaceAfter=4,
            fontSize=10,
            bulletFontName='Helvetica',
            bulletText='●'
        )
        footer_style = ParagraphStyle(
            name='Footer',
            parent=normal_style,
            fontName='Helvetica-Bold',
            fontSize=10,
            alignment=1
        )

        elements = []

        def add_watermark(canvas, doc):
            if canvas.getPageNumber() == 1:
                watermark_path = 'static/images/watermark.jpg'
                logger.info(f"Attempting to load watermark: {watermark_path}")
                if not os.path.exists(watermark_path):
                    logger.warning(f"Watermark file does not exist: {watermark_path}")
                try:
                    canvas.saveState()
                    canvas.setFillAlpha(0.15)
                    watermark = Image(watermark_path, width=doc.width+30*mm, height=doc.height+40*mm)
                    watermark.drawOn(canvas, doc.leftMargin-15*mm, doc.bottomMargin-20*mm)
                    canvas.restoreState()
                except Exception as e:
                    logger.warning(f"Could not load watermark: {e}")
            else:
                logo_path = 'static/images/logo.png'
                logger.info(f"Attempting to load logo watermark: {logo_path}")
                if not os.path.exists(logo_path):
                    logger.warning(f"Logo watermark file does not exist: {logo_path}")
                try:
                    canvas.saveState()
                    canvas.setFillAlpha(0.45)
                    logo = Image(logo_path, width=80*mm, height=40*mm)
                    logo.drawOn(canvas, (doc.width-80*mm)/2, (doc.height-40*mm)/2)
                    canvas.restoreState()
                except Exception as e:
                    logger.warning(f"Could not load logo watermark: {e}")

        doc.addPageTemplates([
            PageTemplate(id='First', frames=[Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height)], onPage=add_watermark),
            PageTemplate(id='Later', frames=[Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height)], onPage=add_watermark),
        ])

        header_bg_path = 'static/images/header_bg.jpg'
        logo_path = 'static/images/logo.png'
        header_row = []
        logo_row = []

        logger.info(f"Attempting to load header background: {header_bg_path}")
        if not os.path.exists(header_bg_path):
            logger.warning(f"Header background file does not exist: {header_bg_path}")
        try:
            header_bg = Image(header_bg_path, width=doc.width+30*mm, height=45*mm)
            header_row.append(header_bg)
        except Exception as e:
            logger.warning(f"Could not load header background: {e}")
            header_row.append(Paragraph(_("Header Image Missing"), normal_style))

        logger.info(f"Attempting to load logo: {logo_path}")
        if not os.path.exists(logo_path):
            logger.warning(f"Logo file does not exist: {logo_path}")
        try:
            logo = Image(logo_path, width=50*mm, height=25*mm)
            logo_row.append(logo)
            logger.info("Successfully loaded logo for header")
        except Exception as e:
            logger.warning(f"Failed to load logo: {e}")
            logo_row.append(Paragraph(_("Logo Missing"), normal_style))

        header_table = Table([header_row, logo_row], colWidths=[doc.width], rowHeights=[45*mm, 25*mm])
        header_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (0, 0), 'CENTER'),
            ('ALIGN', (0, 1), (0, 1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 1), (-1, 1), -30*mm),
            ('LEFTPADDING', (0, 0), (-1, -1), -15*mm),
            ('RIGHTPADDING', (0, 0), (-1, -1), -15*mm),
            ('LEFTPADDING', (0, 1), (0, 1), 15*mm),
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1a3c6e'))
        ]))
        elements.append(header_table)
        elements.append(Spacer(1, 10*mm))

        tour = getattr(booking, 'tour', None)
        tour_name = tour.safe_translation_getter('title', _('Unknown Tour')).upper() if tour else _('Unknown Tour').upper()
        duration = _('CUSTOM')
        if tour:
            if isinstance(tour, (LandTourPage)):
                duration_days = getattr(tour, 'duration_days', 0)
                duration = f"{duration_days} DAYS {duration_days-1} NIGHTS" if duration_days else _("CUSTOM")
            # elif isinstance(tour, DayTour):
            #     duration_hours = getattr(tour, 'duration_hours', 8)
            #     duration = f"{duration_hours} HOURS"
        elements.append(Paragraph(f"{tour_name} FULL PACK", title_shadow_style))
        elements.append(Paragraph(f"{tour_name} FULL PACK", title_style))
        elements.append(Paragraph(duration, subtitle_style))
        elements.append(Spacer(1, 10*mm))

        inclusions = []
        if tour and isinstance(tour, LandTourPage):
            inclusions = [
                _("Alojamiento en hotel seleccionado"),
                _("Desayunos diarios"),
                tour.safe_translation_getter('courtesies', _("Tour guiado")),
            ]      
        # elif tour and isinstance(tour, FullTour):
        #     inclusions = [
        #         _("Boleto aéreo GYE - CTG - GYE via Avianca con artículo personal"),
        #         _("Traslados aeropuerto - hotel - aeropuerto"),
        #         _(f"{getattr(tour, 'duration_days', 3)-1 or 3} noches de alojamiento en hotel a elegir"),
        #         _("Desayunos diarios"),
        #         _("City tour en chiva típica + visita al castillo de San Felipe"),
        #         _("Full Day Isla Barú (Playa Blanca) + almuerzo típico incluido"),
        #         _("Tasas e Impuestos de Ecuador y Colombia"),
        #         ]
        # elif tour and isinstance(tour, DayTour):
        #     inclusions = [
        #         tour.safe_translation_getter('courtesies', _("Botella de agua")),
        #         _("Guía profesional"),
        #     ]
        else:
            inclusions = [_("Servicios según disponibilidad")]

        elements.append(KeepTogether([
            Paragraph(_("INCLUDE"), heading_style),
            *[Paragraph(f"• {item}", bullet_style) for item in inclusions]
        ]))
        elements.append(Spacer(1, 10*mm))

        # if tour and isinstance(tour, FullTour):
        #     elements.append(KeepTogether([
        #         Paragraph(_("ITINERARIO COTIZADO"), heading_style),
        #         Table(
        #             [
        #                 [_("Flight"), _("Date"), _("Route"), _("Departure"), _("Arrival")],
        #                 ["AV8374", "03 Apr", "GYE-BOG", "04:15", "06:10"],
        #                 ["AV9530", "03 Apr", "BOG-CTG", "08:07", "09:39"],
        #                 ["AV9807", "06 Apr", "CTG-BOG", "08:13", "09:45"],
        #                 ["AV8389", "06 Apr", "BOG-GYE", "11:50", "13:40"],
        #             ],
        #             colWidths=[30*mm, 30*mm, 40*mm, 30*mm, 30*mm],
        #             style=TableStyle([
        #                 ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1a3c6e')),
        #                 ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        #                 ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        #                 ('FONTSIZE', (0, 0), (-1, -1), 9),
        #                 ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        #                 ('TOPPADDING', (0, 0), (-1, -1), 8),
        #                 ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#1a3c6e')),
        #                 ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor('#1a3c6e')),
        #                 ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        #                 ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        #                 ('BACKGROUND', (0, 1), (-1, 1), colors.HexColor('#f5f5f5')),
        #                 ('BACKGROUND', (0, 3), (-1, 3), colors.HexColor('#f5f5f5')),
        #             ])
        #         )
        #     ]))
        #     elements.append(Spacer(1, 10*mm))

        total_price = getattr(booking, 'total_price', 0.00) or 0.00
        currency = getattr(tour, 'currency', 'EUR') if tour else 'EUR'
        configuration_details = getattr(booking, 'configuration_details', {}) or {}

        if configuration_details:
            room_data = []
            singles = configuration_details.get('singles', 0)
            doubles = configuration_details.get('doubles', 0)
            triples = configuration_details.get('triples', 0)
            children = configuration_details.get('children', 0)
            infants = configuration_details.get('infants', 0)
            if singles:
                room_data.append([f"Single Room ({singles} adult{'s' if singles > 1 else ''})", f"{currency} {total_price/singles:.2f}"])
            if doubles:
                room_data.append([f"Double Room ({doubles*2} adults)", f"{currency} {total_price/(doubles*2):.2f}"])
            if triples:
                room_data.append([f"Triple Room ({triples*3} adults)", f"{currency} {total_price/(triples*3):.2f}"])
            if children:
                room_data.append([f"Children ({children})", f"{currency} {total_price/children:.2f}"])
            if infants:
                room_data.append([f"Infants ({infants})", f"{currency} 0.00"])
            if room_data:
                elements.append(KeepTogether([
                    Paragraph(_("ROOM CONFIGURATION"), heading_style),
                    Table(
                        room_data,
                        colWidths=[100*mm, 60*mm],
                        style=TableStyle([
                            ('FONTSIZE', (0, 0), (-1, -1), 10),
                            ('TEXTCOLOR', (0, 0), (-1, -1), colors.HexColor('#333333')),
                            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
                            ('TOPPADDING', (0, 0), (-1, -1), 8),
                            ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#1a3c6e')),
                            ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor('#1a3c6e')),
                            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                            ('ALIGN', (0, 0), (0, -1), 'LEFT'),
                            ('ALIGN', (1, 0), (-1, -1), 'RIGHT'),
                            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#f5f5f5')),
                        ])
                    )
                ]))
                elements.append(Spacer(1, 10*mm))

        elements.append(KeepTogether([
            Paragraph(_("TOTAL PRICE"), heading_style),
            Table(
                [[_("Total"), f"{currency} {total_price:.2f}"]],
                colWidths=[100*mm, 60*mm],
                style=TableStyle([
                    ('FONTSIZE', (0, 0), (-1, -1), 10),
                    ('TEXTCOLOR', (0, 0), (-1, -1), colors.HexColor('#333333')),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
                    ('TOPPADDING', (0, 0), (-1, -1), 8),
                    ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#1a3c6e')),
                    ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor('#1a3c6e')),
                    ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                    ('ALIGN', (0, 0), (0, -1), 'LEFT'),
                    ('ALIGN', (1, 0), (-1, -1), 'RIGHT'),
                    ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#f5f5f5')),
                ])
            )
        ]))
        elements.append(Spacer(1, 10*mm))

        not_included = [
            _("Comidas y bebidas no indicadas en el programa"),
            _("Extras personales en hoteles y restaurantes"),
            _("Propinas"),
            _("Tarjeta de asistencia médica"),
        ]
        # if tour and isinstance(tour, DayTour):
        #     not_included = [
        #         _("Transporte al punto de inicio"),
        #         _("Comidas no especificadas"),
        #         _("Propinas"),
        #     ]

        elements.append(KeepTogether([
            Paragraph(_("NO INCLUDE"), heading_style),
            *[Paragraph(f"• {item}", bullet_style) for item in not_included]
        ]))
        elements.append(Spacer(1, 10*mm))

        notes = [
            _("PERÍODO DE COMPRA: COMPRA INMEDIATA"),
            _("Check in a partir de las 15:00 y check out a las 12:00"),
            _("Habitaciones triples cuentan únicamente con 2 camas"),
            _("La asignación de habitaciones se hará con base en disponibilidad"),
            _("PRECIOS SUJETOS A CAMBIO Y DISPONIBILIDAD SIN PREVIO AVISO HASTA CONFIRMAR RESERVA"),
        ]
        # if tour and isinstance(tour, DayTour):
        #     notes = [
        #         _("Confirmación sujeta a disponibilidad"),
        #         _("Mínimo de participantes requerido"),
        #         _("PRECIOS SUJETOS A CAMBIO SIN PREVIO AVISO"),
        #     ]

        elements.append(KeepTogether([
            Paragraph(_("NOTAS IMPORTANTES"), heading_style),
            *[Paragraph(f"• {note}", bullet_style) for note in notes]
        ]))
        elements.append(Spacer(1, 15*mm))

        elements.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor('#1a3c6e')))
        elements.append(Spacer(1, 5*mm))
        elements.append(Paragraph(_("Thank you for choosing Milano Travel!"), footer_style))
        elements.append(Paragraph(_("Contact us at support@milano-travel.com"), normal_style))

        logger.info(f"Building PDF with {len(elements)} elements for booking {booking.id}")
        doc.build(elements)
        pdf = buffer.getvalue()
        buffer.close()
        logger.info(f"Successfully generated PDF for booking {booking.id}")
        return pdf
    except Exception as e:
        logger.error(f"PDF generation failed for booking {booking.id}: {e}")
        raise
