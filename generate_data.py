import psycopg2
from faker import Faker
import random

# -------------------------------
# CONFIG (EDIT THIS)
# -------------------------------
DB_NAME = "ecommerce"
DB_USER = "postgres"
DB_PASSWORD = "Kjayavishal"
DB_HOST = "localhost"
DB_PORT = "5432"

# -------------------------------
# INIT
# -------------------------------
fake = Faker()

conn = psycopg2.connect(
    dbname=DB_NAME,
    user=DB_USER,
    password=DB_PASSWORD,
    host=DB_HOST,
    port=DB_PORT
)

cursor = conn.cursor()

BATCH_SIZE = 1000


# -------------------------------
# INSERT PRODUCTS (10K)
# -------------------------------
def insert_products():
    print("Inserting products...")
    products = []

    for _ in range(10000):
        products.append((
            fake.word(),
            round(random.uniform(10, 1000), 2)
        ))

    cursor.executemany(
        "INSERT INTO products (name, price) VALUES (%s, %s)",
        products
    )

    conn.commit()
    print("✅ Products inserted")


# -------------------------------
# INSERT USERS (500K)
# -------------------------------
def insert_users():
    print("Inserting users...")

    total_batches = 500  # 500 * 1000 = 500K

    for i in range(total_batches):
        users = []

        for _ in range(BATCH_SIZE):
            users.append((
                fake.name(),
                fake.email(),
                fake.date_time_this_decade()
            ))

        cursor.executemany(
            "INSERT INTO users (name, email, created_at) VALUES (%s, %s, %s)",
            users
        )

        conn.commit()

        if i % 10 == 0:
            print(f"Inserted {i * BATCH_SIZE} users")

    print("✅ Users inserted")


# -------------------------------
# INSERT ORDERS (1M)
# -------------------------------
def insert_orders():
    print("Inserting orders...")

    statuses = ["pending", "shipped", "delivered", "cancelled"]
    total_batches = 1000  # 1M rows

    for i in range(total_batches):
        orders = []

        for _ in range(BATCH_SIZE):
            orders.append((
                random.randint(1, 500000),  # user_id
                random.choice(statuses),
                fake.date_time_this_decade()
            ))

        cursor.executemany(
            "INSERT INTO orders (user_id, order_status, created_at) VALUES (%s, %s, %s)",
            orders
        )

        conn.commit()

        if i % 20 == 0:
            print(f"Inserted {i * BATCH_SIZE} orders")

    print("✅ Orders inserted")


# -------------------------------
# INSERT ORDER ITEMS (2M)
# -------------------------------
def insert_order_items():
    print("Inserting order_items...")

    total_batches = 2000  # 2M rows

    for i in range(total_batches):
        items = []

        for _ in range(BATCH_SIZE):
            items.append((
                random.randint(1, 1000000),  # order_id
                random.randint(1, 10000),    # product_id
                random.randint(1, 5)
            ))

        cursor.executemany(
            "INSERT INTO order_items (order_id, product_id, quantity) VALUES (%s, %s, %s)",
            items
        )

        conn.commit()

        if i % 50 == 0:
            print(f"Inserted {i * BATCH_SIZE} order_items")

    print("✅ Order items inserted")


# -------------------------------
# MAIN EXECUTION
# -------------------------------
if __name__ == "__main__":
    # insert_products()
    # insert_users()
    # insert_orders()
    insert_order_items()

    cursor.close()
    conn.close()

    print("\n🎉 Data generation completed!")