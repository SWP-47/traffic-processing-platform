from .base import StateStore
from .memory import InMemoryStateStore

# Singleton instance. 
# In the future, read an ENV variable here to decide between InMemoryStateStore, 
# RedisStateStore, or PostgresStateStore.
state_store: StateStore = InMemoryStateStore()