"""
Alembic environment configuration — sync migrations.
"""

import os
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from models.base import Base

config = context.config

database_url = os.getenv(
    "DATABASE_URL_SYNC",
    "postgresql://aqar:aqar_dev_password@localhost:5432/aqar_db",
)
config.set_main_option("sqlalchemy.url", database_url)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def include_object(object, name, type_, reflected, compare_to):
    # Comprehensive list of PostGIS/TIGER system tables to ignore
    ignored_tables = {
        "spatial_ref_sys", "topology", "layer", "loader_platform",
        "loader_lookuptables", "loader_variables", "geocode_settings",
        "geocode_settings_default", "zip_lookup", "zip_lookup_base",
        "zip_lookup_all", "zip_state", "zip_state_loc", "state",
        "state_lookup", "direction_lookup", "secondary_unit_lookup",
        "street_type_lookup", "place", "place_lookup", "county",
        "county_lookup", "cousub", "countysub_lookup", "addr",
        "addrfeat", "faces", "edges", "tract", "bg", "tabblock",
        "tabblock20", "zcta5", "featnames", "pagc_rules",
        "pagc_lex", "pagc_gaz"
    }

    if type_ == "table" and (name in ignored_tables or name.startswith("tiger")):
        return False
    return True


# Ensure context.configure includes: include_object=include_object

def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            include_object=include_object, # Ensure this is passed here
            # ... other configs ...
        )
        with context.begin_transaction():
            context.run_migrations()

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()