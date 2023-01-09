import hashlib
import json

from datetime import datetime


class Blockchain:
    def __init__(self, data: dict) -> None:
        self.chain = []
        init_block = self._create_block(index=1, data=data, previous_hash="0")
        self.chain.append(init_block)

    def add_block(self, data: str) -> dict:
        previous_block = self._get_previous_block()
        index = len(self.chain) + 1
        previous_hash = self._hashify(block=previous_block)
        block = self._create_block(index=index, data=data, previous_hash=previous_hash)
        self.chain.append(block)
        return block

    def _hashify(self, block: dict) -> str:
        return hashlib.md5(json.dumps(block).encode()).hexdigest()

    def _get_previous_block(self) -> dict:
        return self.chain[-1]

    def get_last_block(self) -> dict:
        return self.chain[-1]

    def get_init_block(self) -> dict:
        return self.chain[0]

    def _create_block(self, index: int, data: dict, previous_hash: str) -> dict:
        return {
            "index": index,
            "block_created": str(datetime.timestamp(datetime.now())),
            "data": data,
            "previous_hash": previous_hash,
        }


if __name__ == "__main__":
    pass
