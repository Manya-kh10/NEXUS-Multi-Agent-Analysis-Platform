from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage, HumanMessage
from app.config import settings
import pandas as pd
import numpy as np

def convert_to_python(obj):
    """Convert numpy and pandas types to native Python types for JSON serialization."""
    if hasattr(obj, 'item'):
        return obj.item()
    if isinstance(obj, np.integer):
        return int(obj)
    if isinstance(obj, np.floating):
        return float(obj)
    if isinstance(obj, np.ndarray):
        return [convert_to_python(x) for x in obj]
    if isinstance(obj, dict):
        return {str(k): convert_to_python(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [convert_to_python(i) for i in obj]
    return obj

llm = ChatGroq(
    api_key=settings.groq_api_key,
    model_name="llama-3.3-70b-versatile"
)

def calculate_advanced_stats(df: pd.DataFrame) -> dict:
    """Calculate advanced data correlations, predictors, outliers, and segment relationships."""
    # 1. Detect target column
    target_col = None
    for col in df.columns:
        if col.lower() in ["survived", "churn", "target", "label", "outcome", "default", "price", "salary"]:
            target_col = col
            break
    if not target_col and len(df.columns) > 0:
        target_col = df.columns[-1]

    # 2. Top Correlations
    numeric_df = df.select_dtypes(include='number')
    correlations = []
    if len(numeric_df.columns) > 1:
        corr_matrix = numeric_df.corr()
        cols = corr_matrix.columns
        for i in range(len(cols)):
            for j in range(i+1, len(cols)):
                val = corr_matrix.iloc[i, j]
                if not pd.isna(val):
                    correlations.append({
                        "feat1": cols[i],
                        "feat2": cols[j],
                        "coefficient": round(float(val), 3)
                    })
        # Sort by absolute correlation coefficient
        correlations = sorted(correlations, key=lambda x: abs(x["coefficient"]), reverse=True)[:6]

    # 3. Outliers Detection (Z-score > 3)
    outliers = {}
    for col in numeric_df.columns:
        mean_val = df[col].mean()
        std_val = df[col].std()
        if std_val > 0:
            count = int(((df[col] - mean_val).abs() > 3 * std_val).sum())
            if count > 0:
                outliers[col] = {
                    "count": count,
                    "percentage": round((count / len(df)) * 100, 2)
                }

    # 4. Feature Importance
    feature_importance = []
    if target_col and len(df.columns) > 1:
        try:
            # Sample for performance if large
            df_slice = df.sample(min(2000, len(df)), random_state=42).copy()
            df_slice = df_slice.dropna(subset=[target_col])
            
            # Fill missing numeric with median, object with mode
            for col in df_slice.columns:
                if df_slice[col].dtype.kind in 'iufc':
                    median_val = df_slice[col].median()
                    df_slice[col] = df_slice[col].fillna(median_val if not pd.isna(median_val) else 0)
                else:
                    mode_vals = df_slice[col].mode()
                    df_slice[col] = df_slice[col].fillna(mode_vals[0] if not mode_vals.empty else 'Missing')
            
            from sklearn.preprocessing import LabelEncoder
            le = LabelEncoder()
            for col in df_slice.select_dtypes(include='object').columns:
                df_slice[col] = le.fit_transform(df_slice[col].astype(str))
            
            X = df_slice.drop(columns=[target_col])
            y = df_slice[target_col]
            
            # Label encode target if it is categorical
            if y.dtype.kind not in 'iufc' or y.nunique() <= 10:
                y = le.fit_transform(y.astype(str))
                from sklearn.ensemble import RandomForestClassifier
                model = RandomForestClassifier(n_estimators=50, max_depth=6, random_state=42)
            else:
                from sklearn.ensemble import RandomForestRegressor
                model = RandomForestRegressor(n_estimators=50, max_depth=6, random_state=42)
                
            model.fit(X, y)
            for col, imp in zip(X.columns, model.feature_importances_):
                feature_importance.append({
                    "feature": col,
                    "importance": round(float(imp), 4)
                })
            feature_importance = sorted(feature_importance, key=lambda x: x["importance"], reverse=True)[:6]
        except Exception as e:
            print(f"Error calculating feature importance: {e}")

    # 5. Target-Segment Relationship profiling
    relationships = []
    if target_col and len(feature_importance) > 0:
        top_feats = [item["feature"] for item in feature_importance[:3]]
        unique_targets = df[target_col].nunique()
        is_classification = unique_targets <= 10 or df[target_col].dtype.kind not in 'iufc'
        
        for feat in top_feats:
            try:
                # Drop nulls for relationship analysis
                df_clean = df.dropna(subset=[feat, target_col])
                if df_clean[feat].dtype.kind in 'iufc':
                    # Numeric feature: divide into 3 quantiles for clear trend analysis
                    bins = pd.qcut(df_clean[feat], q=3, duplicates='drop')
                    if is_classification:
                        agg = df_clean.groupby(bins)[target_col].value_counts(normalize=True).unstack().fillna(0).round(3).to_dict()
                    else:
                        agg = df_clean.groupby(bins)[target_col].mean().round(3).to_dict()
                    relationships.append({
                        "feature": feat,
                        "type": "numeric_binned",
                        "aggregation": {str(k): v for k, v in agg.items()}
                    })
                else:
                    # Categorical feature: group by top 5 categories
                    top_cats = df_clean[feat].value_counts().index[:5]
                    df_filtered = df_clean[df_clean[feat].isin(top_cats)]
                    if is_classification:
                        agg = df_filtered.groupby(feat)[target_col].value_counts(normalize=True).unstack().fillna(0).round(3).to_dict()
                    else:
                        agg = df_filtered.groupby(feat)[target_col].mean().round(3).to_dict()
                    relationships.append({
                        "feature": feat,
                        "type": "categorical",
                        "aggregation": agg
                    })
            except Exception as e:
                print(f"Error profiling relationship for {feat}: {e}")

    return {
        "correlations": convert_to_python(correlations),
        "outliers": convert_to_python(outliers),
        "feature_importance": convert_to_python(feature_importance),
        "relationships": convert_to_python(relationships),
        "target_col": target_col
    }

def run_eda_agent(df: pd.DataFrame) -> dict:
    numeric_cols = df.select_dtypes(include='number').columns.tolist()
    categorical_cols = df.select_dtypes(include='object').columns.tolist()

    # Base value counts
    value_counts = {}
    for col in categorical_cols[:3]:
        value_counts[col] = df[col].value_counts().head(5).to_dict()

    # Numeric summaries
    numeric_summary = {}
    for col in numeric_cols[:6]:
        numeric_summary[col] = {
            "mean": round(df[col].mean(), 2),
            "std": round(df[col].std(), 2),
            "min": round(df[col].min(), 2),
            "max": round(df[col].max(), 2),
        }

    # Calculate advanced segment relationships and correlations
    advanced = calculate_advanced_stats(df)
    target_col = advanced.get("target_col")
    
    target_breakdown = {}
    if target_col:
        target_breakdown["overall"] = df[target_col].value_counts().to_dict()
        for col in categorical_cols[:2]:
            try:
                target_breakdown[f"by_{col}"] = df.groupby(col)[target_col].mean().round(3).to_dict()
            except Exception:
                pass

    value_counts = convert_to_python(value_counts)
    numeric_summary = convert_to_python(numeric_summary)
    target_breakdown = convert_to_python(target_breakdown)
    
    summary = {
        "shape": list(df.shape),
        "columns": list(df.columns),
        "dtypes": df.dtypes.astype(str).to_dict(),
        "missing": df.isnull().sum().to_dict(),
        "numeric_cols": numeric_cols,
        "categorical_cols": categorical_cols,
        "value_counts": value_counts,
        "numeric_summary": numeric_summary,
        "target_col": target_col,
        "target_breakdown": target_breakdown,
        "correlations": advanced.get("correlations"),
        "feature_importance": advanced.get("feature_importance"),
        "relationships": advanced.get("relationships")
    }

    # Advanced prompt feeding the LLM mathematical segment statistics
    messages = [
        SystemMessage(content="""You are a senior data scientist and business intelligence expert. 
Your goal is to write a highly compelling, domain-specific executive synthesis that explains the hidden stories in the data.
Avoid generic descriptions (like 'this column contains numeric values'). Instead, identify the likely business domain of the dataset 
(e.g., if it has Survived/Sex/Pclass, it is Titanic passenger demographics; if it has runs/balls, it is cricket; if it has price/sqft, it is real estate) 
and use proper terminology. Always use numbers and percentages to support your findings."""),
        HumanMessage(content=f"""Analyze this dataset profile:
Dataset Shape: {summary['shape'][0]} rows x {summary['shape'][1]} columns
Missing Values: {summary['missing']}
Target Column: '{target_col}'
Overall Target Distribution: {target_breakdown.get('overall', {})}

Top Mathematically Important Predictors:
{advanced.get('feature_importance')}

Top Numeric & Categorical Target Relationships:
{advanced.get('relationships')}

Top Feature-to-Feature Correlations:
{advanced.get('correlations')}

Write a detailed, beautifully structured report with:
**1. Dataset Domain & Semantic Identity** - Explain what this dataset is, what business/scientific context it represents, and who the records represent.
**2. Data Quality & Usability Rating** - Rate 1-10 with direct analytical reasons (outliers, missing ratios).
**3. Top 3 Hidden Findings** - Elaborate on specific, deep data relationships and segment trends from the statistics above (e.g. 'Class A survived at a 75% rate, whereas Class C survived at only 24%...'). Reference specific variables, weights, and counts.
**4. Critical Vulnerabilities & Red Flags** - Outliers, structural issues, or heavily skewed predictors.
**5. High-Impact Strategic Next Steps** - Top 3 actions to extract more value or run downstream operations based on these segment trends.""")
    ]

    response = llm.invoke(messages)
    return {"agent": "EDA Agent", "summary": summary, "insights": response.content}

def run_stats_agent(df: pd.DataFrame) -> dict:
    numeric_df = df.select_dtypes(include='number')
    skewness = numeric_df.skew().round(3).to_dict() if not numeric_df.empty else {}
    kurtosis = numeric_df.kurtosis().round(3).to_dict() if not numeric_df.empty else {}
    
    advanced = calculate_advanced_stats(df)
    
    stats = {
        "skewness": skewness,
        "kurtosis": kurtosis,
        "correlations": advanced.get("correlations"),
        "outliers": advanced.get("outliers"),
        "feature_importance": advanced.get("feature_importance")
    }

    # Enhanced stats agent prompt focusing on mathematical proof and relationships
    messages = [
        SystemMessage(content="""You are a senior statistical modeler. Write a mathematically rigorous but highly practical statistical analysis.
Do not talk about basic definitions of skewness or kurtosis. Instead, interpret the specific columns, correlations, and outliers of the actual dataset.
Explain the practical modeling and decision-making impact of these metrics using exact column names."""),
        HumanMessage(content=f"""Interpret these calculated statistical metrics:
Skewness: {skewness}
Kurtosis: {kurtosis}
Strongest Linear Correlations: {advanced.get('correlations')}
Anomalous Outlier Columns: {advanced.get('outliers')}
Top Predictor Features: {advanced.get('feature_importance')}

Write:
**1. Distribution & Density Summary** - Which columns show severe skewness or kurtosis? Use the exact numbers and explain what this says about the population distribution.
**2. Strongest Mathematical Relationships** - Interpret the top linear correlations. Which features move together, which move in opposite directions, and what are the coefficient strengths?
**3. Outlier Profile & Risk Analysis** - Identify the exact columns containing extreme outliers and discuss whether these represent noise, rare high-impact events, or data entry errors.
**4. Feature Engineering & ML Pipeline Recommendations** - Which variables require transformations (log, box-cox, robust scaling) or encoding adjustments prior to predictive modeling, and why?""")
    ]

    response = llm.invoke(messages)
    return {"agent": "Stats Agent", "stats": stats, "insights": response.content}

def run_insight_agent(eda_result: dict, stats_result: dict) -> dict:
    messages = [
        SystemMessage(content="""You are a Chief Data Officer writing an Executive brief. 
Synthesize raw agent reports into a high-level strategic roadmap. 
Focus entirely on the business implications, hidden trends, and strategic actions. Use a sharp, professional executive tone. Avoid generic statements."""),
        HumanMessage(content=f"""Synthesize these detailed reports:

EDA Agent Findings:
{eda_result['insights']}

Statistical Agent Findings:
{stats_result['insights']}

Write:
**EXECUTIVE SUMMARY** - A 2-sentence high-level summary of the dataset's core finding and domain.
**Top 3 Core Strategic Insights** - Deep business/domain findings discovered from the segment profiling and correlations, ranked by commercial or operational importance. Use specific numbers.
**Immediate High-Priority Actions** - What specific operations or cleanup actions must be executed immediately.
**High-Value Business Use Cases** - 3 specific ways this dataset's trends can be leveraged to drive revenue, mitigate risk, or optimize operations.
**Risk & Exposure Assessment** - The ultimate operational risk if data limitations or outliers are ignored.""")
    ]

    response = llm.invoke(messages)
    return {"agent": "Insight Agent", "final_insights": response.content}