import os

import pytest

from heraclis.models import Base, get_engine

TEST_DB_FILENAME = "test.db"


def pytest_configure(config):
    temp_db_url = f"sqlite:///{TEST_DB_FILENAME}"
    os.environ["DB_URL"] = temp_db_url
    print(f"Testing DB URL: {temp_db_url}")


@pytest.fixture(autouse=True, scope="session")
def init_db():
    engine = get_engine()
    Base.metadata.create_all(engine)
    # don't remove file to allow inspection after tests
    # os.remove(TEST_DB_FILENAME)
    # print(f"Removed DB file: {TEST_DB_FILENAME}")


if __name__ == "__main__":
    pytest.main()
