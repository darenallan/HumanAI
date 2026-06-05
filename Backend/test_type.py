import asyncio
import json
from sqlalchemy import create_engine, select, text, Column
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

# Import SafeArray to test it
from app.core.database import SafeArray, Base
from sqlalchemy import Text

class TestModel(Base):
    __tablename__ = 'test_table'
    id = Column(Text, primary_key=True)
    tags = Column(SafeArray(Text))

async def main():
    engine = create_async_engine('sqlite+aiosqlite:///:memory:', echo=True)
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        
    async_session = async_sessionmaker(engine, expire_on_commit=False)
    
    async with async_session() as session:
        obj = TestModel(id='1', tags=['a', 'b', 'c'])
        session.add(obj)
        try:
            await session.commit()
            print("COMMIT SUCCESSFUL")
        except Exception as e:
            print("COMMIT FAILED:", e)
            import traceback
            traceback.print_exc()

if __name__ == '__main__':
    asyncio.run(main())
