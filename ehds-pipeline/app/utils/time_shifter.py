import random
from datetime import timedelta, datetime

class TimeShifter:
    """Utility class for Pillar 2 Temporal Shifting.
    Applies a consistent random time shift to all dates for a given patient seed.
    """
    def __init__(self, patient_seed: str | None):
        self.seed_str = patient_seed or "unknown"
        # Generate deterministic random offset between -30 and +30 days
        rng = random.Random(self.seed_str)
        self.offset_days = rng.randint(-30, 30)

    def shift_datetime(self, dt: datetime | None) -> datetime | None:
        if not dt:
            return None
        return dt + timedelta(days=self.offset_days)
