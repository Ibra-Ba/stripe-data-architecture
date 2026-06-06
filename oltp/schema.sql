--
-- Stripe OLTP Schema — NeonDB (PostgreSQL)
-- Normalized 3NF · ACID · Indexed


-- Extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ------ Reference tables -------------------------------

CREATE TABLE currencies (
    code        CHAR(3)      PRIMARY KEY,
    name        VARCHAR(50)  NOT NULL
);

CREATE TABLE countries (
    code        CHAR(2)      PRIMARY KEY,
    name        VARCHAR(100) NOT NULL,
    region      VARCHAR(50)
);

CREATE TABLE payment_methods (
    id          SMALLINT     PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    name        VARCHAR(50)  NOT NULL UNIQUE  -- card, bank_transfer, wallet
);

-- -------------Core tables ------------------------------------------------

CREATE TABLE customers (
    id              UUID         PRIMARY KEY DEFAULT uuid_generate_v4(),
    email_hash      VARCHAR(64)  NOT NULL UNIQUE,  -- pseudonymized (GDPR)
    country_code    CHAR(2)      REFERENCES countries(code),
    created_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE TABLE merchants (
    id              UUID         PRIMARY KEY DEFAULT uuid_generate_v4(),
    name            VARCHAR(100) NOT NULL,
    country_code    CHAR(2)      REFERENCES countries(code),
    category        VARCHAR(50),
    created_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE TABLE transactions (
    id                  UUID         PRIMARY KEY DEFAULT uuid_generate_v4(),
    customer_id         UUID         NOT NULL REFERENCES customers(id),
    merchant_id         UUID         NOT NULL REFERENCES merchants(id),
    payment_method_id   SMALLINT     NOT NULL REFERENCES payment_methods(id),
    currency_code       CHAR(3)      NOT NULL REFERENCES currencies(code),
    amount              NUMERIC(12,2) NOT NULL CHECK (amount > 0),
    status              VARCHAR(20)  NOT NULL CHECK (
                            status IN ('success','failed','refunded','pending')
                        ),
    device_type         VARCHAR(20)  CHECK (
                            device_type IN ('mobile','desktop','tablet')
                        ),
    ip_country          CHAR(2)      REFERENCES countries(code),
    fraud_score         NUMERIC(5,4) CHECK (fraud_score BETWEEN 0 AND 1),
    created_at          TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE TABLE refunds (
    id              UUID         PRIMARY KEY DEFAULT uuid_generate_v4(),
    transaction_id  UUID         NOT NULL REFERENCES transactions(id),
    amount          NUMERIC(12,2) NOT NULL CHECK (amount > 0),
    reason          VARCHAR(100),
    created_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE TABLE audit_logs (
    id          BIGINT       PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    table_name  VARCHAR(50)  NOT NULL,
    operation   CHAR(6)      NOT NULL CHECK (operation IN ('INSERT','UPDATE','DELETE')),
    record_id   UUID         NOT NULL,
    changed_by  VARCHAR(50),
    changed_at  TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

-- ------Indexes ---------------------------------

CREATE INDEX idx_transactions_customer   ON transactions(customer_id);
CREATE INDEX idx_transactions_merchant   ON transactions(merchant_id);
CREATE INDEX idx_transactions_created    ON transactions(created_at DESC);
CREATE INDEX idx_transactions_status     ON transactions(status);
CREATE INDEX idx_transactions_fraud      ON transactions(fraud_score DESC)
                                          WHERE fraud_score > 0.7;
CREATE INDEX idx_refunds_transaction     ON refunds(transaction_id);

---------------RBAC ----------------------

CREATE ROLE stripe_reader;
CREATE ROLE stripe_writer;
CREATE ROLE stripe_admin;

GRANT SELECT ON ALL TABLES IN SCHEMA public TO stripe_reader;
GRANT SELECT, INSERT, UPDATE ON transactions, customers, merchants, refunds
    TO stripe_writer;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO stripe_admin;
