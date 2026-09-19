"""Concurrent logical retries must share the persisted reservation key."""
import asyncio

from app.services.syroce_b2b import idempotency as target


class RacingCollection:
    def __init__(self):
        self.document = None
        self.readers = 0
        self.both_read = asyncio.Event()
        self.candidates = []

    async def find_one(self, query):
        if self.readers < 2:
            self.readers += 1
            if self.readers == 2:
                self.both_read.set()
            await self.both_read.wait()
            return None  # Both requests observed the initially absent record.
        return dict(self.document) if self.document else None

    async def update_one(self, query, update, *, upsert):
        assert upsert
        self.candidates.append(update["$setOnInsert"]["idempotency_key"])
        if self.document is None:
            self.document = {**query, **update["$setOnInsert"]}


def test_concurrent_requests_return_one_persisted_key(monkeypatch):
    async def scenario():
        collection = RacingCollection()

        async def get_db():
            return {target.COLLECTION: collection}

        monkeypatch.setattr(target, "get_db", get_db)
        keys = await asyncio.gather(*[
            target.resolve_key(provided_key=None, client_request_id="reservation-1")
            for _ in range(2)
        ])
        assert len(set(collection.candidates)) == 2
        assert keys == [collection.document["idempotency_key"]] * 2
        assert await target.resolve_key(
            provided_key=None, client_request_id="reservation-1"
        ) == keys[0]

    asyncio.run(scenario())


def test_explicit_key_without_mapping_is_preserved():
    key = "11111111-1111-4111-8111-111111111111"
    assert asyncio.run(target.resolve_key(provided_key=key, client_request_id=None)) == key


def test_single_shot_requests_still_get_unique_keys():
    first = asyncio.run(target.resolve_key(provided_key=None, client_request_id=None))
    second = asyncio.run(target.resolve_key(provided_key=None, client_request_id=None))
    assert target.is_valid_key(first) and target.is_valid_key(second)
    assert first != second
