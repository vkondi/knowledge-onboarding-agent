# SQL and Relational Databases

SQL (Structured Query Language) is the standard language for querying and manipulating relational databases.

## Core Concepts

- **Table**: a structured collection of rows and columns (like a spreadsheet).
- **Row (record/tuple)**: one entry in a table.
- **Column (field/attribute)**: a named property with a specific data type.
- **Primary key**: uniquely identifies each row - cannot be NULL or duplicate.
- **Foreign key**: a column referencing the primary key of another table - enforces referential integrity.
- **Index**: a data structure that speeds up lookups on a column.
- **Schema**: the structure definition of a database - tables, columns, types, constraints.

## Basic Queries

```sql
-- Select all columns
SELECT * FROM users;

-- Select specific columns with a filter
SELECT id, name, email
FROM users
WHERE active = TRUE
ORDER BY name ASC;

-- Limit results
SELECT * FROM orders
ORDER BY created_at DESC
LIMIT 10;

-- Aggregation
SELECT department, COUNT(*) AS headcount, AVG(salary) AS avg_salary
FROM employees
GROUP BY department
HAVING COUNT(*) > 5;
```

## Joins

Joins combine rows from two or more tables based on a related column.

```sql
-- INNER JOIN: only rows with matching keys in both tables
SELECT o.id, u.name, o.total
FROM orders o
INNER JOIN users u ON o.user_id = u.id;

-- LEFT JOIN: all rows from left table, matched rows from right (NULLs if no match)
SELECT u.name, COUNT(o.id) AS order_count
FROM users u
LEFT JOIN orders o ON o.user_id = u.id
GROUP BY u.name;

-- Self join: join a table with itself (e.g., employee–manager hierarchy)
SELECT e.name AS employee, m.name AS manager
FROM employees e
LEFT JOIN employees m ON e.manager_id = m.id;
```

## Modifying Data

```sql
-- Insert a row
INSERT INTO users (name, email, created_at)
VALUES ('Alice', 'alice@example.com', NOW());

-- Insert multiple rows
INSERT INTO tags (name) VALUES ('python'), ('machine-learning'), ('docker');

-- Update rows
UPDATE users
SET active = FALSE, updated_at = NOW()
WHERE last_login < NOW() - INTERVAL '1 year';

-- Delete rows
DELETE FROM sessions
WHERE expires_at < NOW();
```

## Indexes

```sql
-- Create a single-column index
CREATE INDEX idx_users_email ON users(email);

-- Composite index (queries filtering on both columns benefit)
CREATE INDEX idx_orders_user_status ON orders(user_id, status);

-- Unique index (enforces uniqueness + speeds up lookups)
CREATE UNIQUE INDEX idx_users_email_unique ON users(email);
```

When to index: columns used in `WHERE`, `JOIN ON`, `ORDER BY`. Indexes speed up reads but slow down writes - don't over-index.

## Transactions

A transaction is a group of operations that succeed or fail together (ACID guarantee).

```sql
BEGIN;

UPDATE accounts SET balance = balance - 500 WHERE id = 1;
UPDATE accounts SET balance = balance + 500 WHERE id = 2;

COMMIT;   -- apply both changes

-- If something goes wrong:
ROLLBACK; -- undo all changes in the transaction
```

**ACID:**
- **Atomicity** - all or nothing.
- **Consistency** - data remains valid before and after.
- **Isolation** - concurrent transactions don't interfere.
- **Durability** - committed data survives crashes.

## Window Functions

Window functions compute values across rows related to the current row - without collapsing them like `GROUP BY`.

```sql
-- Rank employees by salary within each department
SELECT
    name,
    department,
    salary,
    RANK() OVER (PARTITION BY department ORDER BY salary DESC) AS rank
FROM employees;

-- Running total
SELECT
    date,
    revenue,
    SUM(revenue) OVER (ORDER BY date) AS running_total
FROM daily_sales;
```

## Common Table Expressions (CTEs)

CTEs improve readability by naming subqueries.

```sql
WITH high_value_customers AS (
    SELECT user_id, SUM(total) AS lifetime_value
    FROM orders
    GROUP BY user_id
    HAVING SUM(total) > 1000
),
ranked AS (
    SELECT user_id, lifetime_value,
           RANK() OVER (ORDER BY lifetime_value DESC) AS rank
    FROM high_value_customers
)
SELECT u.name, r.lifetime_value, r.rank
FROM ranked r
JOIN users u ON r.user_id = u.id
WHERE r.rank <= 10;
```

## Performance Tips

1. **Explain plans**: use `EXPLAIN ANALYZE` (PostgreSQL) to see how the query runs and spot full table scans.
2. **Index selectively**: index high-cardinality columns used frequently in filters.
3. **Avoid `SELECT *`**: fetch only the columns you need.
4. **Use parameterised queries**: prevents SQL injection and enables query plan caching.
5. **Paginate large results**: never return all rows of a large table in one query.
6. **Normalise early, denormalise later**: start with 3NF; denormalise only if profiling proves it necessary.
