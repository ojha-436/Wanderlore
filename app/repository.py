"""Firestore data access for profiles and saved trips.

Layout:
  users/{uid}                → profile document
  users/{uid}/trips/{tripId} → saved trip (destination, label, payload, createdAt)

The Firestore client is created lazily; importing this module needs no credentials.
Tests substitute an in-memory fake via dependency override.
"""
from typing import List, Optional

from .schemas import UserProfile


class Repository:
    def __init__(self, db=None):
        self._db = db

    @property
    def db(self):
        if self._db is None:
            from firebase_admin import firestore

            from .firebase_app import ensure_firebase_app

            ensure_firebase_app()
            self._db = firestore.client()
        return self._db

    # ---- profile ----
    def get_profile(self, uid: str) -> Optional[dict]:
        snap = self.db.collection("users").document(uid).get()
        return snap.to_dict() if snap.exists else None

    def upsert_profile(self, profile: UserProfile) -> None:
        self.db.collection("users").document(profile.uid).set(
            profile.model_dump(), merge=True
        )

    # ---- trips ----
    def save_trip(self, uid: str, destination: str, label: str, payload: dict) -> str:
        from firebase_admin import firestore

        doc = self.db.collection("users").document(uid).collection("trips").document()
        doc.set(
            {
                "destination": destination,
                "label": label or destination,
                "payload": payload,
                "createdAt": firestore.SERVER_TIMESTAMP,
            }
        )
        return doc.id

    def list_trips(self, uid: str, limit: int = 20) -> List[dict]:
        from firebase_admin import firestore

        query = (
            self.db.collection("users")
            .document(uid)
            .collection("trips")
            .order_by("createdAt", direction=firestore.Query.DESCENDING)
            .limit(limit)
        )
        out = []
        for d in query.stream():
            row = d.to_dict()
            row["id"] = d.id
            out.append(row)
        return out
