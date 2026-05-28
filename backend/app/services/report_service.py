from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.colors import HexColor
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
from reportlab.lib.enums import TA_LEFT, TA_CENTER
import io
from datetime import datetime

# NEXUS Colors
PRIMARY = HexColor("#7c3aed")
SECONDARY = HexColor("#4edea3")
BACKGROUND = HexColor("#12121d")
SURFACE = HexColor("#1f1e2a")
TEXT = HexColor("#e3e0f1")
TEXT_MUTED = HexColor("#ccc3d8")
ERROR = HexColor("#ffb4ab")

def generate_analysis_report(
    filename: str,
    eda_result: dict,
    stats_result: dict,
    insight_result: dict,
    ml_result: dict = None
) -> bytes:

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=0.75*inch,
        leftMargin=0.75*inch,
        topMargin=0.75*inch,
        bottomMargin=0.75*inch
    )

    styles = getSampleStyleSheet()

    # Custom styles
    title_style = ParagraphStyle(
        "NexusTitle",
        parent=styles["Title"],
        fontSize=28,
        textColor=PRIMARY,
        spaceAfter=4,
        fontName="Helvetica-Bold"
    )

    subtitle_style = ParagraphStyle(
        "NexusSubtitle",
        parent=styles["Normal"],
        fontSize=12,
        textColor=TEXT_MUTED,
        spaceAfter=20,
        fontName="Helvetica"
    )

    section_style = ParagraphStyle(
        "NexusSection",
        parent=styles["Heading1"],
        fontSize=16,
        textColor=PRIMARY,
        spaceBefore=20,
        spaceAfter=8,
        fontName="Helvetica-Bold"
    )

    body_style = ParagraphStyle(
        "NexusBody",
        parent=styles["Normal"],
        fontSize=10,
        textColor=HexColor("#333333"),
        spaceAfter=6,
        leading=16,
        fontName="Helvetica"
    )

    bold_style = ParagraphStyle(
        "NexusBold",
        parent=body_style,
        fontName="Helvetica-Bold",
        textColor=HexColor("#1a1a2e")
    )

    elements = []

    # Header
    elements.append(Paragraph("NEXUS", title_style))
    elements.append(Paragraph("Multi-Agent Data Analysis Report", subtitle_style))
    elements.append(Paragraph(f"Dataset: {filename}", bold_style))
    elements.append(Paragraph(f"Generated: {datetime.now().strftime('%B %d, %Y at %H:%M')}", body_style))
    elements.append(HRFlowable(width="100%", thickness=2, color=PRIMARY, spaceAfter=20))

    # EDA Section
    elements.append(Paragraph("1. Exploratory Data Analysis", section_style))
    summary = eda_result.get("summary", {})

    # Dataset stats table
    shape = summary.get("shape", [0, 0])
    missing = sum(summary.get("missing", {}).values())
    numeric_cols = len(summary.get("numeric_cols", []))
    cat_cols = len(summary.get("categorical_cols", []))

    eda_table_data = [
        ["Metric", "Value"],
        ["Total Rows", str(shape[0]) if len(shape) > 0 else "N/A"],
        ["Total Columns", str(shape[1]) if len(shape) > 1 else "N/A"],
        ["Numeric Columns", str(numeric_cols)],
        ["Categorical Columns", str(cat_cols)],
        ["Total Missing Values", str(missing)],
    ]

    eda_table = Table(eda_table_data, colWidths=[3*inch, 3*inch])
    eda_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), PRIMARY),
        ("TEXTCOLOR", (0, 0), (-1, 0), HexColor("#ffffff")),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 11),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 1), (-1, -1), 10),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [HexColor("#f5f5f5"), HexColor("#ffffff")]),
        ("GRID", (0, 0), (-1, -1), 0.5, HexColor("#cccccc")),
        ("ROUNDEDCORNERS", [4, 4, 4, 4]),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
    ]))
    elements.append(eda_table)
    elements.append(Spacer(1, 12))

    # Predictor Importance table
    feature_importance = summary.get("feature_importance", [])
    if feature_importance:
        elements.append(Paragraph("Top Mathematically Important Predictors:", bold_style))
        fi_data = [["Rank", "Feature Name", "Predictive Weight"]]
        for idx, item in enumerate(feature_importance[:5]):
            fi_data.append([
                f"#{idx+1}",
                item.get("feature", "N/A"),
                f"{round(item.get('importance', 0.0) * 100, 1)}%"
            ])
            
        fi_table = Table(fi_data, colWidths=[1.0*inch, 3.0*inch, 2.0*inch])
        fi_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), SECONDARY),
            ("TEXTCOLOR", (0, 0), (-1, 0), HexColor("#003824")),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
            ("FONTSIZE", (0, 0), (-1, -1), 10),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [HexColor("#f5f5f5"), HexColor("#ffffff")]),
            ("GRID", (0, 0), (-1, -1), 0.5, HexColor("#cccccc")),
            ("ROUNDEDCORNERS", [4, 4, 4, 4]),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ]))
        elements.append(fi_table)
        elements.append(Spacer(1, 12))

    # EDA Insights
    elements.append(Paragraph("EDA Agent Insights:", bold_style))
    insights_text = eda_result.get("insights", "No insights available.")
    # Clean markdown formatting
    insights_text = insights_text.replace("**", "").replace("*", "").replace("#", "")
    for line in insights_text.split("\n"):
        if line.strip():
            elements.append(Paragraph(line.strip(), body_style))
    elements.append(Spacer(1, 12))

    # Stats Section
    elements.append(HRFlowable(width="100%", thickness=1, color=HexColor("#cccccc"), spaceAfter=8))
    elements.append(Paragraph("2. Statistical Analysis", section_style))

    stats = stats_result.get("stats", {})
    skewness = stats.get("skewness", {})
    kurtosis = stats.get("kurtosis", {})

    if skewness:
        skew_data = [["Column", "Skewness", "Kurtosis"]]
        for col in list(skewness.keys())[:10]:
            skew_data.append([
                col,
                str(round(skewness.get(col, 0), 3)),
                str(round(kurtosis.get(col, 0), 3))
            ])

        skew_table = Table(skew_data, colWidths=[2.5*inch, 1.75*inch, 1.75*inch])
        skew_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), SECONDARY),
            ("TEXTCOLOR", (0, 0), (-1, 0), HexColor("#003824")),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
            ("FONTSIZE", (0, 0), (-1, -1), 10),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [HexColor("#f5f5f5"), HexColor("#ffffff")]),
            ("GRID", (0, 0), (-1, -1), 0.5, HexColor("#cccccc")),
            ("ROUNDEDCORNERS", [4, 4, 4, 4]),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ]))
        elements.append(skew_table)
        elements.append(Spacer(1, 12))

    # Strongest Correlations Table
    correlations = stats.get("correlations", [])
    if correlations:
        elements.append(Paragraph("Strongest Linear Correlations:", bold_style))
        corr_data = [["Feature A", "Feature B", "Coefficient (r)"]]
        for item in correlations[:6]:
            corr_data.append([
                item.get("feat1", "N/A"),
                item.get("feat2", "N/A"),
                str(item.get("coefficient", 0.0))
            ])
        
        corr_table = Table(corr_data, colWidths=[2.5*inch, 2.5*inch, 1.0*inch])
        corr_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), PRIMARY),
            ("TEXTCOLOR", (0, 0), (-1, 0), HexColor("#ffffff")),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
            ("FONTSIZE", (0, 0), (-1, -1), 10),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [HexColor("#f5f5f5"), HexColor("#ffffff")]),
            ("GRID", (0, 0), (-1, -1), 0.5, HexColor("#cccccc")),
            ("ROUNDEDCORNERS", [4, 4, 4, 4]),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ]))
        elements.append(corr_table)
        elements.append(Spacer(1, 12))

    elements.append(Paragraph("Stats Agent Insights:", bold_style))
    stats_insights = stats_result.get("insights", "No insights available.")
    stats_insights = stats_insights.replace("**", "").replace("*", "").replace("#", "")
    for line in stats_insights.split("\n"):
        if line.strip():
            elements.append(Paragraph(line.strip(), body_style))
    elements.append(Spacer(1, 12))

    # Insight Section
    elements.append(HRFlowable(width="100%", thickness=1, color=HexColor("#cccccc"), spaceAfter=8))
    elements.append(Paragraph("3. Executive Insights", section_style))
    final_insights = insight_result.get("final_insights", "No insights available.")
    final_insights = final_insights.replace("**", "").replace("*", "").replace("#", "")
    for line in final_insights.split("\n"):
        if line.strip():
            elements.append(Paragraph(line.strip(), body_style))
    elements.append(Spacer(1, 12))

    # ML Section
    if ml_result and "summary" in ml_result:
        elements.append(HRFlowable(width="100%", thickness=1, color=HexColor("#cccccc"), spaceAfter=8))
        elements.append(Paragraph("4. Machine Learning Results", section_style))

        ml_summary = ml_result.get("summary", {})
        if "error" not in ml_summary:
            ml_table_data = [
                ["Metric", "Value"],
                ["Target Column", str(ml_summary.get("target_column", "N/A"))],
                ["Task Type", str(ml_summary.get("task_type", "N/A")).capitalize()],
                ["Training Samples", str(ml_summary.get("training_samples", "N/A"))],
                ["Test Samples", str(ml_summary.get("test_samples", "N/A"))],
                ["Features Used", str(ml_summary.get("features_used", "N/A"))],
            ]

            model_results = ml_summary.get("model_results", {})
            for model_name, metrics in model_results.items():
                for metric, value in metrics.items():
                    ml_table_data.append([f"{model_name} - {metric}", str(value)])

            ml_table = Table(ml_table_data, colWidths=[3*inch, 3*inch])
            ml_table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), PRIMARY),
                ("TEXTCOLOR", (0, 0), (-1, 0), HexColor("#ffffff")),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
                ("FONTSIZE", (0, 0), (-1, -1), 10),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [HexColor("#f5f5f5"), HexColor("#ffffff")]),
                ("GRID", (0, 0), (-1, -1), 0.5, HexColor("#cccccc")),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]))
            elements.append(ml_table)
            elements.append(Spacer(1, 12))

            # Feature importance
            feature_importance = ml_summary.get("feature_importance", {})
            if feature_importance:
                elements.append(Paragraph("Top Feature Importance:", bold_style))
                fi_data = [["Feature", "Importance Score"]]
                for feat, score in list(feature_importance.items())[:10]:
                    fi_data.append([feat, str(score)])

                fi_table = Table(fi_data, colWidths=[3*inch, 3*inch])
                fi_table.setStyle(TableStyle([
                    ("BACKGROUND", (0, 0), (-1, 0), SECONDARY),
                    ("TEXTCOLOR", (0, 0), (-1, 0), HexColor("#003824")),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                    ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
                    ("FONTSIZE", (0, 0), (-1, -1), 10),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [HexColor("#f5f5f5"), HexColor("#ffffff")]),
                    ("GRID", (0, 0), (-1, -1), 0.5, HexColor("#cccccc")),
                    ("TOPPADDING", (0, 0), (-1, -1), 6),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ]))
                elements.append(fi_table)
                elements.append(Spacer(1, 12))

        ml_insights = ml_result.get("insights", "")
        if ml_insights:
            elements.append(Paragraph("ML Agent Insights:", bold_style))
            ml_insights = ml_insights.replace("**", "").replace("*", "").replace("#", "")
            for line in ml_insights.split("\n"):
                if line.strip():
                    elements.append(Paragraph(line.strip(), body_style))

    # Footer
    elements.append(Spacer(1, 20))
    elements.append(HRFlowable(width="100%", thickness=2, color=PRIMARY, spaceAfter=8))
    elements.append(Paragraph(
        "Generated by NEXUS Multi-Agent Data Analysis System",
        ParagraphStyle("Footer", parent=body_style, textColor=TEXT_MUTED, alignment=TA_CENTER)
    ))

    doc.build(elements)
    buffer.seek(0)
    return buffer.read()