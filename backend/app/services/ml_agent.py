from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage, HumanMessage
from app.config import settings
import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.linear_model import LogisticRegression, LinearRegression
from sklearn.metrics import (
    accuracy_score, classification_report,
    mean_squared_error, r2_score
)
import warnings
warnings.filterwarnings("ignore")

llm = ChatGroq(
    api_key=settings.groq_api_key,
    model_name="llama-3.3-70b-versatile"
)

def detect_task_type(df: pd.DataFrame, target_col: str) -> str:
    unique_vals = df[target_col].nunique()
    if unique_vals <= 10:
        return "classification"
    return "regression"

def preprocess_for_ml(df: pd.DataFrame, target_col: str):
    df = df.copy()
    df = df.dropna()

    # Encode categorical columns
    le = LabelEncoder()
    for col in df.select_dtypes(include='object').columns:
        df[col] = le.fit_transform(df[col].astype(str))

    X = df.drop(columns=[target_col])
    y = df[target_col]

    return X, y

def run_ml_agent(df: pd.DataFrame) -> dict:
    # Detect target column
    target_col = None
    for col in df.columns:
        if col.lower() in ["survived", "churn", "target", "label", "outcome", "default", "price", "salary"]:
            target_col = col
            break

    if not target_col:
        # Use last column as target
        target_col = df.columns[-1]

    task_type = detect_task_type(df, target_col)

    try:
        X, y = preprocess_for_ml(df, target_col)

        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42
        )

        results = {}

        if task_type == "classification":
            models = {
                "Random Forest": RandomForestClassifier(n_estimators=100, random_state=42),
                "Logistic Regression": LogisticRegression(max_iter=1000, random_state=42)
            }

            for name, model in models.items():
                model.fit(X_train, y_train)
                y_pred = model.predict(X_test)
                acc = round(accuracy_score(y_test, y_pred) * 100, 2)
                results[name] = {"accuracy": acc}

            # Best model feature importance
            best_model = RandomForestClassifier(n_estimators=100, random_state=42)
            best_model.fit(X_train, y_train)
            feature_importance = dict(zip(
                X.columns.tolist(),
                [round(float(x), 4) for x in best_model.feature_importances_]
            ))
            feature_importance = dict(sorted(
                feature_importance.items(),
                key=lambda x: x[1],
                reverse=True
            )[:10])

        else:
            models = {
                "Random Forest": RandomForestRegressor(n_estimators=100, random_state=42),
                "Linear Regression": LinearRegression()
            }

            for name, model in models.items():
                model.fit(X_train, y_train)
                y_pred = model.predict(X_test)
                r2 = round(r2_score(y_test, y_pred) * 100, 2)
                rmse = round(float(np.sqrt(mean_squared_error(y_test, y_pred))), 4)
                results[name] = {"r2_score": r2, "rmse": rmse}

            best_model = RandomForestRegressor(n_estimators=100, random_state=42)
            best_model.fit(X_train, y_train)
            feature_importance = dict(zip(
                X.columns.tolist(),
                [round(float(x), 4) for x in best_model.feature_importances_]
            ))
            feature_importance = dict(sorted(
                feature_importance.items(),
                key=lambda x: x[1],
                reverse=True
            )[:10])

        ml_summary = {
            "target_column": target_col,
            "task_type": task_type,
            "training_samples": len(X_train),
            "test_samples": len(X_test),
            "features_used": len(X.columns),
            "model_results": results,
            "feature_importance": feature_importance
        }

        # LLM interpretation
        messages = [
            SystemMessage(content="You are an ML expert. Interpret these model results concisely."),
            HumanMessage(content=f"""ML Results for {task_type} task on '{target_col}':
Models: {results}
Top Features: {feature_importance}

Write briefly:
**1. Best Model** - Which performed best and why.
**2. Feature Importance** - Top 3 most important features and what they mean.
**3. Model Quality** - Is this good performance? What does it mean practically?
**4. Recommendations** - Next steps to improve the model.""")
        ]

        response = llm.invoke(messages)

        return {
            "agent": "ML Agent",
            "summary": ml_summary,
            "insights": response.content
        }

    except Exception as e:
        return {
            "agent": "ML Agent",
            "summary": {"error": str(e)},
            "insights": f"ML Agent encountered an error: {str(e)}"
        }