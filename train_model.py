import os
import pickle
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import LabelEncoder
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix

def main():
    data_path = "data/samples.csv"
    model_dir = "models"
    model_path = os.path.join(model_dir, "gesture_model.pkl")

    if not os.path.exists(data_path):
        print(f"ERROR: Dataset not found at {data_path}. Collect data first.")
        return

    df = pd.read_csv(data_path)
    if "label" not in df.columns:
        print("ERROR: 'label' column missing.")
        return

    df = df.dropna(subset=["label"])
    feature_cols = [c for c in df.columns if c not in ["timestamp", "label"]]
    df[feature_cols] = df[feature_cols].apply(pd.to_numeric, errors="coerce").fillna(0)

    X = df[feature_cols].values
    y = df["label"].astype(str).values

    enc = LabelEncoder()
    y_enc = enc.fit_transform(y)

    print(f"Classes: {list(enc.classes_)}")
    if len(enc.classes_) < 2:
        print("ERROR: Need at least 2 classes.")
        return

    X_train, X_test, y_train, y_test = train_test_split(
        X, y_enc, test_size=0.2, random_state=42, stratify=y_enc
    )

    model = RandomForestClassifier(n_estimators=100, random_state=42)
    model.fit(X_train, y_train)

    pred = model.predict(X_test)
    acc = accuracy_score(y_test, pred)

    print(f"\nAccuracy: {acc*100:.2f}%")
    print("\nConfusion Matrix:")
    print(confusion_matrix(y_test, pred))
    print("\nReport:")
    print(classification_report(y_test, pred, target_names=enc.classes_))

    os.makedirs(model_dir, exist_ok=True)
    with open(model_path, "wb") as f:
        pickle.dump({"model": model, "label_encoder": enc}, f)

    print(f"\n✅ Saved: {model_path}")

if __name__ == "__main__":
    main()
