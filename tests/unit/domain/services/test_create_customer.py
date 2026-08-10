from conftest import InMemoryDatabase

from domain.entities.customer import Customer
from domain.services.create_customer import create_customer, get_customer


def test_create_customer_reuses_matching_customer(
    customer: Customer,
    database: InMemoryDatabase,
) -> None:
    database.customers.append(customer)

    result = create_customer(
        customer.first_name,
        customer.last_name,
        customer.email,
        customer.preferred_language,
        database,
    )

    assert result is customer
    assert database.saved_customers == []


def test_create_customer_builds_and_saves_new_customer(
    database: InMemoryDatabase,
) -> None:
    result = create_customer("Sam", "Lee", "sam@example.com", "de", database)

    assert result is not None
    assert result.full_name == "Sam Lee"
    assert result.preferred_language == "de"
    assert database.saved_customers == [result]


def test_get_customer_delegates_to_database(
    customer: Customer,
    database: InMemoryDatabase,
) -> None:
    database.customers.append(customer)

    assert get_customer(customer.customer_id, database) is customer


def test_create_customer_rejects_email_owned_by_different_customer(
    customer: Customer,
    database: InMemoryDatabase,
) -> None:
    database.customers.append(customer)

    result = create_customer(
        "Sam",
        "Lee",
        customer.email,
        "de",
        database,
    )

    assert result is None
    assert database.saved_customers == []
