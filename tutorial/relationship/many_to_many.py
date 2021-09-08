import uvicorn
from fastapi import FastAPI
from sqlalchemy.orm import declarative_base, sessionmaker

from fastapi_quickcrud import CrudMethods
from fastapi_quickcrud import crud_router_builder
from fastapi_quickcrud import sqlalchemy_table_to_pydantic
from fastapi_quickcrud import sqlalchemy_to_pydantic

app = FastAPI()

Base = declarative_base()
metadata = Base.metadata

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession

engine = create_async_engine('postgresql+asyncpg://postgres:1234@127.0.0.1:5432/postgres', future=True, echo=True,
                             pool_use_lifo=True, pool_pre_ping=True, pool_recycle=7200)
async_session = sessionmaker(bind=engine, class_=AsyncSession)


async def get_transaction_session() -> AsyncSession:
    async with async_session() as session:
        async with session.begin():
            yield session


from sqlalchemy import CHAR, Column, ForeignKey, Integer, Table
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()
metadata = Base.metadata
association_table = Table('association', Base.metadata,
                          Column('left_id', ForeignKey('left.id')),
                          Column('right_id', ForeignKey('right.id'))
                          )


class Parent(Base):
    __tablename__ = 'left'
    id = Column(Integer, primary_key=True)
    children = relationship("Child",
                            secondary=association_table)


class Child(Base):
    __tablename__ = 'right'
    id = Column(Integer, primary_key=True)
    name = Column(CHAR, nullable=True)


@app.on_event("startup")
async def startup_event():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


user_model_m2m = sqlalchemy_table_to_pydantic(db_model=association_table,
                                              crud_methods=[
                                                  CrudMethods.FIND_MANY,
                                                  CrudMethods.UPSERT_ONE,
                                                  CrudMethods.UPDATE_MANY,
                                                  CrudMethods.DELETE_MANY,
                                                  CrudMethods.PATCH_MANY,

                                              ],
                                              exclude_columns=[])

user_model_set = sqlalchemy_to_pydantic(db_model=Parent,
                                        crud_methods=[
                                            CrudMethods.FIND_MANY,
                                            CrudMethods.FIND_ONE,
                                            CrudMethods.UPSERT_ONE,
                                            CrudMethods.UPDATE_MANY,
                                            CrudMethods.UPDATE_ONE,
                                            CrudMethods.DELETE_ONE,
                                            CrudMethods.DELETE_MANY,
                                            CrudMethods.PATCH_MANY,

                                        ],
                                        exclude_columns=[])

friend_model_set = sqlalchemy_to_pydantic(db_model=Child,
                                          crud_methods=[
                                              CrudMethods.FIND_MANY,
                                              CrudMethods.UPSERT_MANY,
                                              CrudMethods.UPDATE_MANY,
                                              CrudMethods.DELETE_MANY,
                                              CrudMethods.PATCH_MANY,

                                          ],
                                          exclude_columns=[])

crud_route_1 = crud_router_builder(db_session=get_transaction_session,
                                   crud_models=user_model_set,
                                   db_model=Parent,
                                   prefix="/Parent",
                                   dependencies=[],
                                   async_mode=True,
                                   tags=["Parent"]
                                   )
crud_route_3 = crud_router_builder(db_session=get_transaction_session,
                                   crud_models=user_model_m2m,
                                   db_model=association_table,
                                   prefix="/Parent2child",
                                   dependencies=[],
                                   async_mode=True,
                                   tags=["m2m"]
                                   )
crud_route_2 = crud_router_builder(db_session=get_transaction_session,
                                   crud_models=friend_model_set,
                                   db_model=Child,
                                   async_mode=True,
                                   prefix="/Child",
                                   dependencies=[],
                                   tags=["Child"]
                                   )

app.include_router(crud_route_1)
app.include_router(crud_route_2)
app.include_router(crud_route_3)
uvicorn.run(app, host="0.0.0.0", port=8000, debug=False)