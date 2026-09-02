from __future__ import annotations

from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
import xgboost as xgb


PROJECT_ROOT = Path(__file__).resolve().parents[3]

MODEL_PATH = (
    PROJECT_ROOT
    / "backend"
    / "ml"
    / "models"
    / "riskguard_xgboost.joblib"
)

FEATURE_IMPORTANCE_PATH = (
    PROJECT_ROOT
    / "backend"
    / "ml"
    / "models"
    / "xgboost_feature_importance.parquet"
)

THRESHOLD_REPORT_PATH = (
    PROJECT_ROOT
    / "backend"
    / "ml"
    / "models"
    / "risk_threshold_report.json"
)


class RiskGuardPredictor:
    """
    RiskGuard AI inference layer.

    Loads the trained raw XGBoost model and applies the
    exact feature transformations required by the training pipeline.

    Explainability:
        Each prediction is explained using real per-case SHAP
        contributions computed via XGBoost's own native TreeSHAP
        implementation (`Booster.predict(..., pred_contribs=True)`).

        We deliberately do NOT use the `shap` package here: as of
        xgboost>=3.0, `base_score` is serialized as a JSON-encoded
        list (e.g. "[5E-1]"), and shap's TreeExplainer (confirmed on
        shap==0.49.1) still expects a plain float, raising
        `ValueError: could not convert string to float: '[5E-1]'`.
        This is a known, currently-unresolved upstream incompatibility
        (see shap/shap#4288, shap/shap#4202) — not something fixable
        by patching our own model file. XGBoost implements the exact
        TreeSHAP algorithm internally in C++, so `pred_contribs=True`
        gives mathematically identical per-feature Shapley values
        without depending on shap's (currently broken) XGBoost loader
        at all. If a future shap release fixes this, `shap.TreeExplainer`
        could be reintroduced, but there's no benefit to doing so.

        Falls back to the static global feature-importance ranking if
        no usable XGBoost booster can be recovered from the loaded
        model bundle.
    """

    def __init__(
        self,
        model_path: Path = MODEL_PATH,
        feature_importance_path: Path = FEATURE_IMPORTANCE_PATH,
    ) -> None:

        if not model_path.exists():
            raise FileNotFoundError(
                f"RiskGuard model not found: {model_path}"
            )

        if not feature_importance_path.exists():
            raise FileNotFoundError(
                "RiskGuard feature importance file not found: "
                f"{feature_importance_path}"
            )

        bundle = joblib.load(model_path)

        if not isinstance(bundle, dict):
            raise RuntimeError(
                "Invalid RiskGuard model bundle."
            )

        required_keys = {
            "model",
            "feature_columns",
            "target_column",
            "model_type",
        }

        missing = required_keys.difference(bundle.keys())

        if missing:
            raise RuntimeError(
                "Model bundle missing required keys: "
                f"{sorted(missing)}"
            )

        self.model = bundle["model"]
        self.feature_columns = bundle["feature_columns"]
        self.target_column = bundle["target_column"]
        self.model_type = bundle["model_type"]

        if not THRESHOLD_REPORT_PATH.exists():
            raise FileNotFoundError(
                "RiskGuard threshold report not found: "
                f"{THRESHOLD_REPORT_PATH}"
            )

        import json

        with THRESHOLD_REPORT_PATH.open("r", encoding="utf-8") as f:
            threshold_report = json.load(f)

        if "selected_threshold" not in threshold_report:
            raise RuntimeError(
                "Threshold report missing 'selected_threshold'."
            )

        self.threshold = float(
            threshold_report["selected_threshold"]
        )

        print(
            "[RiskGuardPredictor] Locked decision threshold: "
            f"{self.threshold:.2f}"
        )

        self.feature_importance = pd.read_parquet(
            feature_importance_path
        )

        required_importance_columns = {
            "feature",
            "importance",
        }

        missing_importance = (
            required_importance_columns
            - set(self.feature_importance.columns)
        )

        if missing_importance:
            raise RuntimeError(
                "Feature importance file missing columns: "
                f"{sorted(missing_importance)}"
            )

        self.feature_importance = (
            self.feature_importance
            .sort_values(
                "importance",
                ascending=False,
            )
            .reset_index(drop=True)
        )

        # --------------------------------------------------
        # Recover raw XGBoost boosters for native TreeSHAP.
        # --------------------------------------------------

        self._boosters: list[Any] = []
        self._init_explainability()

    # ----------------------------------------------------------
    # Explainability setup
    # ----------------------------------------------------------

    @staticmethod
    def _unwrap_tree_estimator(estimator: Any) -> Any:
        """
        Unwrap a fitted estimator down to something that exposes
        `.get_booster()`. Handles a plain XGBClassifier, or one
        wrapped in a sklearn Pipeline (uses the last step).
        """

        if hasattr(estimator, "steps"):
            # sklearn Pipeline -> take the final step.
            return estimator.steps[-1][1]

        return estimator

    def _extract_tree_estimators(self) -> list[Any]:
        """
        Return a list of fitted XGBoost estimators, regardless of
        whether self.model is:

          - a plain XGBClassifier
          - a fitted sklearn CalibratedClassifierCV wrapping XGBoost
            estimators (one per cross-validation fold)
        """

        model = self.model

        if hasattr(model, "calibrated_classifiers_"):
            estimators = []

            for calibrated_classifier in model.calibrated_classifiers_:
                base = getattr(
                    calibrated_classifier, "estimator", None
                )

                if base is None:
                    base = getattr(
                        calibrated_classifier, "base_estimator", None
                    )

                if base is not None:
                    estimators.append(self._unwrap_tree_estimator(base))

            return estimators

        return [self._unwrap_tree_estimator(model)]

    def _init_explainability(self) -> None:
        """
        Recover raw xgboost.Booster objects for native pred_contribs
        (TreeSHAP) explanations. Falls back to the static global
        feature-importance table if none can be recovered.
        """

        try:
            estimators = self._extract_tree_estimators()

            boosters = []

            for estimator in estimators:
                get_booster = getattr(estimator, "get_booster", None)

                if get_booster is None:
                    # Not an XGBoost sklearn wrapper (e.g. a
                    # RandomForestClassifier from an older bundle).
                    continue

                try:
                    boosters.append(get_booster())
                except Exception as exc:  # noqa: BLE001
                    print(
                        "[RiskGuardPredictor] Could not recover a "
                        f"booster from one estimator: {exc}"
                    )

            self._boosters = boosters

            if self._boosters:
                print(
                    "[RiskGuardPredictor] Native XGBoost per-case "
                    f"explanations enabled ({len(self._boosters)} "
                    "estimator(s))."
                )
            else:
                print(
                    "[RiskGuardPredictor] No usable XGBoost boosters "
                    "found — falling back to static feature importance."
                )

        except Exception as exc:  # noqa: BLE001
            print(
                "[RiskGuardPredictor] Explainability initialization "
                f"failed, falling back to static feature importance: {exc}"
            )
            self._boosters = []

    # ----------------------------------------------------------
    # Feature preparation
    # ----------------------------------------------------------

    def _prepare_input(
        self,
        data: dict[str, Any],
    ) -> pd.DataFrame:
        """
        Convert one return record into the exact feature
        representation expected by the trained model.
        """

        frame = pd.DataFrame([data])

        excluded_columns = {
            self.target_column,
            "user_id",
            "return_id",
            "order_id",
        }

        frame = frame.drop(
            columns=[
                column
                for column in excluded_columns
                if column in frame.columns
            ],
            errors="ignore",
        )

        # ------------------------------------------------------
        # Check required raw input features BEFORE transformation
        # ------------------------------------------------------

        required_raw_features = {
            "order_value",
            "item_value",
            "quantity",
            "time_to_return_request_hours",
            "refund_amount",
            "returned_item_match",
            "item_condition_score",
            "package_weight_delta_pct",
            "vision_confidence_score",
            "account_age_days",
            "lifetime_order_count",
            "lifetime_return_count",
            "total_spent",
            "return_rate",
            "return_velocity_30d",
            "return_velocity_48h",
            "shared_device_count",
            "shared_address_count",
            "shared_payment_fingerprint_count",
            "device_return_velocity_7d",
            "address_return_velocity_7d",
            "payment_return_velocity_7d",
            "cluster_return_velocity_7d",
            "order_category",
            "return_reason",
        }

        missing_features = sorted(
            required_raw_features.difference(
                frame.columns
            )
        )

        if missing_features:
            raise ValueError(
                "Missing required inference features: "
                f"{missing_features}"
            )

        # ------------------------------------------------------
        # Convert datetime columns
        # ------------------------------------------------------

        for column in frame.columns:

            if pd.api.types.is_datetime64_any_dtype(
                frame[column]
            ):
                frame[column] = (
                    pd.to_datetime(
                        frame[column]
                    )
                    .astype("int64")
                    // 10**9
                )

        # ------------------------------------------------------
        # Convert boolean columns
        # ------------------------------------------------------

        for column in frame.columns:

            if pd.api.types.is_bool_dtype(
                frame[column]
            ):
                frame[column] = (
                    frame[column]
                    .astype(int)
                )

        # ------------------------------------------------------
        # Validate numeric raw features
        # ------------------------------------------------------

        numeric_features = required_raw_features - {
            "order_category",
            "return_reason",
        }

        for column in numeric_features:

            if not pd.api.types.is_numeric_dtype(
                frame[column]
            ):
                raise ValueError(
                    f"Inference feature '{column}' "
                    "must be numeric."
                )

        # ------------------------------------------------------
        # One-hot encode categorical features
        # ------------------------------------------------------

        categorical_columns = [
            column
            for column in frame.columns
            if (
                pd.api.types.is_object_dtype(
                    frame[column]
                )
                or isinstance(
                    frame[column].dtype,
                    pd.CategoricalDtype,
                )
            )
        ]

        if categorical_columns:

            frame = pd.get_dummies(
                frame,
                columns=categorical_columns,
                dtype=int,
            )

        # ------------------------------------------------------
        # Align with training feature schema
        # ------------------------------------------------------

        frame = frame.reindex(
            columns=self.feature_columns,
            fill_value=0,
        )

        # ------------------------------------------------------
        # Final numeric validation
        # ------------------------------------------------------

        non_numeric = [
            column
            for column in frame.columns
            if not pd.api.types.is_numeric_dtype(
                frame[column]
            )
        ]

        if non_numeric:
            raise RuntimeError(
                "Non-numeric inference features: "
                f"{non_numeric}"
            )

        if frame.isna().any().any():
            raise RuntimeError(
                "Inference input contains NULL values."
            )

        return frame

    # ----------------------------------------------------------
    # Risk level
    # ----------------------------------------------------------

    @staticmethod
    def _risk_level(
        abuse_probability: float,
    ) -> str:
        """
        Convert abuse probability into a human-readable
        risk level.
        """

        if abuse_probability >= 0.90:
            return "CRITICAL"

        if abuse_probability >= 0.70:
            return "HIGH"

        if abuse_probability >= 0.40:
            return "MEDIUM"

        if abuse_probability >= 0.20:
            return "LOW"

        return "MINIMAL"

    # ----------------------------------------------------------
    # Human-readable feature descriptions
    # ----------------------------------------------------------

    @staticmethod
    def _describe_feature(
        feature: str,
        value: Any,
    ) -> str:
        """
        Convert a model feature into a human-readable
        risk signal.
        """

        if feature == "vision_confidence_score":
            if value is not None and float(value) <= 0:
                return (
                    "No vision assessment was available for this case."
                )
            if value is not None and float(value) < 0.50:
                return (
                    "Low vision confidence may indicate an item mismatch "
                    "or empty package."
                )
            return (
                "Vision assessment confidence is relatively high."
            )

        if feature == "time_to_return_request_hours":
            if value is not None and float(value) <= 48:
                return (
                    "Very rapid return requests can indicate suspicious "
                    "return behavior."
                )
            if value is not None and float(value) <= 168:
                return (
                    "Returns requested within one week can contribute "
                    "to return-abuse risk."
                )
            return (
                "The return request was made after a longer period, "
                "which is less consistent with rapid-return behavior."
            )

        if feature == "order_value":
            return (
                "High-value orders can increase return-abuse exposure."
            )

        if feature == "lifetime_return_count":
            return (
                "High lifetime return activity can indicate repeated "
                "return behavior."
            )

        if feature == "returned_item_match":
            return (
                "Returned item does not match the expected item."
            )

        if feature == "item_condition_score":
            return (
                "Low item condition score may indicate suspicious "
                "item usage."
            )

        if feature == "package_weight_delta_pct":
            return (
                "Large package-weight deviation can indicate an item "
                "swap or empty box."
            )

        if feature == "return_rate":
            return (
                "High historical return rate is a strong abuse signal."
            )

        if feature == "device_return_velocity_7d":
            return (
                "Multiple returns from the same device within seven "
                "days may indicate linked abuse."
            )

        if feature == "payment_return_velocity_7d":
            return (
                "High return activity linked to the same payment "
                "fingerprint may indicate coordinated abuse."
            )

        if feature == "return_velocity_30d":
            return (
                "High return activity over 30 days may indicate "
                "serial returning."
            )

        if feature == "cluster_return_velocity_7d":
            return (
                "High return activity across linked accounts may "
                "indicate an abuse ring."
            )

        if feature == "address_return_velocity_7d":
            return (
                "High return activity associated with the same "
                "address may indicate linked accounts."
            )

        if feature == "account_age_days":
            if value is not None and float(value) < 30:
                return (
                    "Very new accounts with suspicious return behavior "
                    "can indicate account abuse."
                )
            if value is not None and float(value) < 180:
                return (
                    "Relatively new accounts may contribute to "
                    "account-abuse risk."
                )
            return (
                "The account has been active for a longer period, "
                "which is less consistent with a very new account."
            )

        if feature == "shared_address_count":
            return (
                "Multiple accounts sharing an address may indicate "
                "account linkage."
            )

        return f"Feature {feature} contributed to the model decision."

    # ----------------------------------------------------------
    # Explainability — native XGBoost TreeSHAP (preferred)
    # ----------------------------------------------------------

    def _get_native_shap_signals(
        self,
        prepared_features: pd.DataFrame,
        limit: int = 5,
    ) -> list[dict[str, Any]] | None:
        """
        Compute real per-case SHAP contributions for this specific
        return, using XGBoost's own native TreeSHAP implementation
        (`Booster.predict(..., pred_contribs=True)`), averaged across
        estimators when the model is a calibrated ensemble.

        Returns None if no usable booster is available, so the
        caller can fall back to the static global-importance signals.
        """

        if not self._boosters:
            return None

        values = prepared_features.iloc[0]

        try:
            dmatrix = xgb.DMatrix(
                prepared_features,
                feature_names=self.feature_columns,
            )

            contributions = np.zeros(len(self.feature_columns))

            for booster in self._boosters:
                # Shape: (n_samples, n_features + 1). The last column
                # is the base/expected value and is dropped here —
                # we only want the per-feature contributions.
                raw_contribs = booster.predict(
                    dmatrix,
                    pred_contribs=True,
                )
                contributions += np.asarray(raw_contribs)[0, :-1]

            contributions /= len(self._boosters)

        except Exception as exc:  # noqa: BLE001
            print(
                "[RiskGuardPredictor] Native SHAP computation failed "
                f"for this request, falling back to static importance: {exc}"
            )
            return None

        contribution_map = dict(
            zip(self.feature_columns, contributions)
        )

        # Rank by how strongly each feature pushed THIS case toward
        # ABUSIVE (positive contribution in margin space).
        ranked = sorted(
            contribution_map.items(),
            key=lambda item: item[1],
            reverse=True,
        )

        signals: list[dict[str, Any]] = []

        for feature, contribution in ranked:

            if contribution <= 0:
                # Nothing further pushes toward abuse — stop, rather
                # than padding the list with irrelevant negative signals.
                break

            if feature not in values.index:
                continue

            value = values[feature]

            # Ignore inactive one-hot features.
            if feature.startswith("order_category_") or feature.startswith(
                "return_reason_"
            ):
                if float(value) == 0:
                    continue

            signals.append(
                {
                    "feature": feature,
                    "value": (
                        bool(value)
                        if isinstance(value, bool)
                        else float(value)
                        if isinstance(value, (int, float))
                        else str(value)
                    ),
                    "importance": round(float(contribution), 6),
                    "description": self._describe_feature(feature, value),
                }
            )

            if len(signals) >= limit:
                break

        return signals

    # ----------------------------------------------------------
    # Explainability — static global importance (fallback)
    # ----------------------------------------------------------

    def _get_static_signals(
        self,
        prepared_features: pd.DataFrame,
        limit: int = 5,
    ) -> list[dict[str, Any]]:
        """
        Return the most important active model features, ranked by
        the model's global feature importance. Used only when
        per-case native SHAP contributions are unavailable.
        """

        values = prepared_features.iloc[0]

        signals: list[dict[str, Any]] = []

        ranked_features = (
            self.feature_importance
            .head(20)
            .copy()
        )

        for row in ranked_features.itertuples(
            index=False
        ):

            feature = row.feature
            importance = float(row.importance)

            if feature not in values.index:
                continue

            value = values[feature]

            # Ignore inactive one-hot features.
            if feature.startswith(
                "order_category_"
            ) or feature.startswith(
                "return_reason_"
            ):
                if float(value) == 0:
                    continue

            signals.append(
                {
                    "feature": feature,
                    "value": (
                        bool(value)
                        if isinstance(
                            value,
                            bool,
                        )
                        else float(value)
                        if isinstance(
                            value,
                            (int, float),
                        )
                        else str(value)
                    ),
                    "importance": round(
                        importance,
                        6,
                    ),
                    "description":
                        self._describe_feature(
                            feature,
                            value,
                        ),
                }
            )

            if len(signals) >= limit:
                break

        return signals

    def _get_top_risk_signals(
        self,
        prepared_features: pd.DataFrame,
        limit: int = 5,
    ) -> list[dict[str, Any]]:
        """
        Return this case's top risk signals — real per-case native
        XGBoost SHAP contributions when available, otherwise the
        static global feature-importance ranking.
        """

        native_signals = self._get_native_shap_signals(prepared_features, limit)

        if native_signals is not None:
            return native_signals

        return self._get_static_signals(prepared_features, limit)

    # ----------------------------------------------------------
    # Prediction
    # ----------------------------------------------------------

    def predict(
        self,
        data: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Generate a RiskGuard abuse prediction with
        risk score and explainability.
        """

        features = self._prepare_input(data)

        probabilities = self.model.predict_proba(
            features
        )[0]

        classes = list(
            self.model.classes_
        )

        probability_map = {
            int(label): float(probability)
            for label, probability
            in zip(
                classes,
                probabilities,
            )
        }

        legitimate_probability = probability_map.get(
            0,
            0.0,
        )

        abuse_probability = probability_map.get(
            1,
            0.0,
        )

        # Use the cost-tuned threshold instead of a naive 0.5 cutoff.
        prediction = int(abuse_probability >= self.threshold)

        risk_score = round(
            abuse_probability * 100,
            2,
        )

        risk_level = self._risk_level(
            abuse_probability
        )

        risk_signals = (
            self._get_top_risk_signals(
                features
            )
        )

        return {
            "predicted_label": prediction,
            "prediction": (
                "ABUSIVE"
                if prediction == 1
                else "LEGITIMATE"
            ),
            "abuse_probability": round(
                abuse_probability,
                6,
            ),
            "legitimate_probability": round(
                legitimate_probability,
                6,
            ),
            "risk_score": risk_score,
            "risk_level": risk_level,
            "decision_threshold": round(self.threshold, 4),
            "top_risk_signals": risk_signals,
            "model_type": self.model_type,
        }


def load_predictor() -> RiskGuardPredictor:
    """Create and return a RiskGuard predictor."""

    return RiskGuardPredictor()