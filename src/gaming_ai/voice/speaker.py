import time

from discord import Member, User


class SpeakerInfo:
    def __init__(self, user_id: int, name: str, display_name: str) -> None:
        self.user_id = user_id
        self.name = name
        self.display_name = display_name
        self.first_seen: float = time.time()
        self.last_spoke: float = time.time()
        self.utterance_count: int = 0


class SpeakerTracker:
    def __init__(self) -> None:
        self._speakers: dict[int, SpeakerInfo] = {}

    def get_or_create(self, user: User) -> SpeakerInfo:
        user_id = user.id
        if user_id not in self._speakers:
            self._speakers[user_id] = SpeakerInfo(
                user_id=user_id,
                name=str(user),
                display_name=user.display_name if isinstance(user, Member) else str(user),
            )
        return self._speakers[user_id]

    def record_utterance(self, user_id: int) -> None:
        info = self._speakers.get(user_id)
        if info is not None:
            info.last_spoke = time.time()
            info.utterance_count += 1

    def get(self, user_id: int) -> SpeakerInfo | None:
        return self._speakers.get(user_id)

    def get_all(self) -> dict[int, SpeakerInfo]:
        return dict(self._speakers)

    def remove(self, user_id: int) -> None:
        self._speakers.pop(user_id, None)

    def clear(self) -> None:
        self._speakers.clear()
