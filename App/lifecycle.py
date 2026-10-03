"""Transfer startup resources to the backend only after a successful build."""
from contextlib import AsyncExitStack


async def build_with_resources(factory):
    async with AsyncExitStack() as resources:
        backend = await factory(resources)
        backend.register_resource(resources.pop_all())
        return backend
