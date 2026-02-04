import ssl
import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from .config import settings

# 1. Locate the ca.pem file
# We look for it in the root directory (one level up from 'common' folder)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CA_PATH = os.path.join(BASE_DIR, "ca.pem")

# 2. Create the SSL Context
# We create a default context and load the CA cert provided by Aiven
ssl_context = ssl.create_default_context(cafile=CA_PATH)
# Some environments require check_hostname to be False for self-signed or internal CA certs
ssl_context.check_hostname = False 

# --- DATABASE ENGINE CONFIGURATION ---
engine = create_async_engine(
    settings.MYSQL_URL,
    echo=False,
    pool_pre_ping=True,
    connect_args={
        "ssl": ssl_context  # Pass the full SSL context with the CA file
    }
)

# --- SESSION FACTORY ---
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False
)

# --- BASE MODEL ---
class Base(DeclarativeBase):
    pass

# --- DEPENDENCY ---
async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()