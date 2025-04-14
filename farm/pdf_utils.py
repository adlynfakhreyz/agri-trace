import io
from datetime import datetime
from django.http import HttpResponse
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, landscape
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image

def generate_farm_report_pdf(farm, fields, crops, active_crops, recent_activities, farm_condition=None):
    """
    Generate a PDF report for a farm with all its details.
    
    Args:
        farm: The Farm model instance
        fields: QuerySet of Field objects
        crops: QuerySet of Crop objects
        active_crops: QuerySet of active Crop objects
        recent_activities: QuerySet of ActivityLog objects
        farm_condition: Optional FarmCondition instance
        
    Returns:
        HttpResponse with PDF attachment
    """
    # Create a buffer for the PDF
    buffer = io.BytesIO()
    
    # Set up the document with letter size paper
    doc = SimpleDocTemplate(buffer, pagesize=letter, 
                        rightMargin=72, leftMargin=72,
                        topMargin=72, bottomMargin=72)
    
    styles = getSampleStyleSheet()

    # Update or add custom styles
    if 'CenterTitle' not in styles:
        styles.add(ParagraphStyle(name='CenterTitle', fontSize=16, alignment=1, spaceAfter=12))

    if 'Heading2' in styles:
        styles['Heading2'].fontSize = 14
        styles['Heading2'].spaceAfter = 10
    else:
        styles.add(ParagraphStyle(name='Heading2', fontSize=14, spaceAfter=10))

    if 'Heading3' in styles:
        styles['Heading3'].fontSize = 12
        styles['Heading3'].spaceAfter = 8
    else:
        styles.add(ParagraphStyle(name='Heading3', fontSize=12, spaceAfter=8))

    if 'Normal' in styles:
        styles['Normal'].fontSize = 10
        styles['Normal'].spaceAfter = 6
    else:
        styles.add(ParagraphStyle(name='Normal', fontSize=10, spaceAfter=6))
    
    # Container for the elements we'll add to the document
    elements = []
    
    # Add logo (placeholder)
    # elements.append(Image("path/to/logo.png", width=2*inch, height=1*inch))
    
    # Title
    title = Paragraph(f"Farm Report: {farm.name}", styles['CenterTitle'])
    elements.append(title)
    elements.append(Spacer(1, 0.25*inch))
    
    # Farm details
    elements.append(Paragraph("FARM DETAILS", styles['Heading2']))
    farm_data = [
        ["Farm Name:", farm.name],
        ["Location:", farm.location],
        ["Size:", f"{farm.size} hectares"],
        ["Created:", farm.created_at.strftime("%B %d, %Y")],
        ["Last Updated:", farm.updated_at.strftime("%B %d, %Y")]
    ]
    
    farm_table = Table(farm_data, colWidths=[2*inch, 4*inch])
    farm_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
        ('TEXTCOLOR', (0, 0), (0, -1), colors.black),
        ('ALIGN', (0, 0), (0, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (0, -1), 10),
        ('BOTTOMPADDING', (0, 0), (0, -1), 12),
        ('BACKGROUND', (1, 0), (1, -1), colors.white),
        ('TEXTCOLOR', (1, 0), (1, -1), colors.black),
        ('ALIGN', (1, 0), (1, -1), 'LEFT'),
        ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
        ('FONTSIZE', (1, 0), (1, -1), 10),
        ('BOTTOMPADDING', (1, 0), (1, -1), 12),
        ('BOX', (0, 0), (-1, -1), 1, colors.black),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
    ]))
    
    elements.append(farm_table)
    elements.append(Spacer(1, 0.2*inch))
    
    # Farm conditions section
    if farm_condition:
        elements.append(Paragraph("FARM CONDITIONS", styles['Heading2']))
        
        conditions_data = [["Metric", "Value"]]
        
        if farm_condition.soil_ph is not None:
            conditions_data.append(["Soil pH", f"{farm_condition.soil_ph:.1f}"])
            
        if farm_condition.soil_moisture is not None:
            conditions_data.append(["Soil Moisture", f"{farm_condition.soil_moisture:.1f}%"])
            
        if farm_condition.rainfall is not None:
            conditions_data.append(["Rainfall", f"{farm_condition.rainfall:.1f} mm"])
            
        if farm_condition.max_daily_temp is not None:
            conditions_data.append(["Max Temperature", f"{farm_condition.max_daily_temp:.1f}°C"])
            
        if farm_condition.day_length is not None:
            conditions_data.append(["Day Length", f"{farm_condition.day_length:.1f} hours"])
        
        if len(conditions_data) > 1:  # Only create table if there's data
            condition_table = Table(conditions_data, colWidths=[3*inch, 3*inch])
            condition_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (1, 0), colors.lightgrey),
                ('TEXTCOLOR', (0, 0), (1, 0), colors.black),
                ('ALIGN', (0, 0), (1, 0), 'CENTER'),
                ('FONTNAME', (0, 0), (1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (1, 0), 10),
                ('BOTTOMPADDING', (0, 0), (1, 0), 12),
                ('BACKGROUND', (0, 1), (1, -1), colors.white),
                ('TEXTCOLOR', (0, 1), (1, -1), colors.black),
                ('ALIGN', (0, 1), (0, -1), 'LEFT'),
                ('ALIGN', (1, 1), (1, -1), 'RIGHT'),
                ('FONTNAME', (0, 1), (1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 1), (1, -1), 10),
                ('BOTTOMPADDING', (0, 1), (1, -1), 6),
                ('BOX', (0, 0), (-1, -1), 1, colors.black),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ]))
            
            elements.append(condition_table)
            elements.append(Spacer(1, 0.2*inch))
    
    # Fields section
    elements.append(Paragraph("FIELDS", styles['Heading2']))
    
    if fields.exists():
        fields_data = [["Field Name", "Size (ha)", "Location", "Active Crops"]]
        
        for field in fields:
            fields_data.append([
                field.name, 
                f"{field.size:.2f}",
                field.location_within_farm or "N/A",
                str(field.get_active_crop_count())
            ])
        
        fields_table = Table(fields_data, colWidths=[2*inch, 1*inch, 2.5*inch, 1*inch])
        fields_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.white),
            ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
            ('ALIGN', (0, 1), (0, -1), 'LEFT'),
            ('ALIGN', (1, 1), (1, -1), 'RIGHT'),
            ('ALIGN', (3, 1), (3, -1), 'CENTER'),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 1), (-1, -1), 6),
            ('BOX', (0, 0), (-1, -1), 1, colors.black),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ]))
        
        elements.append(fields_table)
    else:
        elements.append(Paragraph("No fields have been created for this farm yet.", styles['Normal']))
    
    elements.append(Spacer(1, 0.2*inch))
    
    # Active Crops section
    elements.append(Paragraph("ACTIVE CROPS", styles['Heading2']))
    
    if active_crops.exists():
        crops_data = [["Crop Type", "Field", "Planting Date", "Expected Harvest"]]
        
        for crop in active_crops:
            expected_harvest = crop.expected_harvest_date.strftime("%B %d, %Y") if crop.expected_harvest_date else "Not specified"
            crops_data.append([
                crop.crop_type,
                crop.field.name,
                crop.planting_date.strftime("%B %d, %Y"),
                expected_harvest
            ])
        
        crops_table = Table(crops_data, colWidths=[1.5*inch, 1.5*inch, 1.5*inch, 2*inch])
        crops_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.white),
            ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
            ('ALIGN', (0, 1), (0, -1), 'LEFT'),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 1), (-1, -1), 6),
            ('BOX', (0, 0), (-1, -1), 1, colors.black),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ]))
        
        elements.append(crops_table)
    else:
        elements.append(Paragraph("No active crops on this farm.", styles['Normal']))
    
    elements.append(Spacer(1, 0.2*inch))
    
    # Recent activities section
    elements.append(Paragraph("RECENT ACTIVITIES", styles['Heading2']))
    
    if recent_activities:
        activities_data = [["Date", "Activity Type", "Details"]]
        
        for activity in recent_activities:
            # Generate detail text based on activity type
            detail_text = "Activity recorded"
            try:
                if activity.activity_type == 'preparation':
                    prep = activity.preparationlog
                    detail_text = f"Field: {prep.field.name}, Equipment: {prep.equipment_used}"
                elif activity.activity_type == 'planting':
                    plant = activity.plantinglog
                    detail_text = f"Field: {plant.field.name}, Crop: {plant.crop.crop_type}"
                elif activity.activity_type == 'maintenance':
                    maint = activity.maintenancelog
                    detail_text = f"Crop: {maint.crop.crop_type}"
                elif activity.activity_type == 'harvesting':
                    harv = activity.harvestinglog
                    detail_text = f"Crop: {harv.crop.crop_type}, Yield: {harv.yield_amount} kg"
            except:
                # If any relations don't exist, just use the default text
                pass
            
            activities_data.append([
                activity.timestamp.strftime("%B %d, %Y"),
                activity.get_activity_type_display(),
                detail_text
            ])
        
        activities_table = Table(activities_data, colWidths=[1.5*inch, 1.5*inch, 3.5*inch])
        activities_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.white),
            ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
            ('ALIGN', (0, 1), (0, -1), 'LEFT'),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 1), (-1, -1), 6),
            ('BOX', (0, 0), (-1, -1), 1, colors.black),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ]))
        
        elements.append(activities_table)
    else:
        elements.append(Paragraph("No recent activities recorded.", styles['Normal']))
    
    # Add footer with timestamp
    elements.append(Spacer(1, 0.5*inch))
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    footer_text = f"Report generated: {timestamp}"
    elements.append(Paragraph(footer_text, styles['Normal']))
    
    # Build PDF
    doc.build(elements)
    
    # Get the value of the BytesIO buffer and create response
    pdf = buffer.getvalue()
    buffer.close()
    
    # Create HTTP response with PDF
    filename = f"farm_report_{farm.name.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d')}.pdf"
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    response.write(pdf)
    
    return response