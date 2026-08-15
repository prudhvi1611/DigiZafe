import asyncio
import json
from app.connectors.registry import CONNECTOR_REGISTRY

async def main():
    await CONNECTOR_REGISTRY.initialize_all()
    statuses = CONNECTOR_REGISTRY.get_all_statuses()
    output = {k: v.dict() for k, v in statuses.items()}
    print(json.dumps(output, indent=2))

if __name__ == "__main__":
    asyncio.run(main())
