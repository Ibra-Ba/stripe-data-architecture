-- ─────────────────────────────────────────
-- Stripe OLTP — Requêtes clés
-- ─────────────────────────────────────────

-- 1. Transactions suspectes (fraud_score > 0.7)
SELECT
    t.id,
    t.amount,
    t.currency_code,
    t.fraud_score,
    t.status,
    t.created_at,
    m.name   AS merchant,
    m.category
FROM transactions t
JOIN merchants m ON t.merchant_id = m.id
WHERE t.fraud_score > 0.7
ORDER BY t.fraud_score DESC
LIMIT 50;

-- 2. Volume journalier par statut (7 derniers jours)
SELECT
    DATE(created_at)  AS day,
    status,
    COUNT(*)          AS nb_transactions,
    SUM(amount)       AS total_amount
FROM transactions
WHERE created_at >= NOW() - INTERVAL '7 days'
GROUP BY day, status
ORDER BY day DESC, status;

-- 3. Top 10 marchands par volume
SELECT
    m.name,
    m.category,
    COUNT(t.id)   AS nb_transactions,
    SUM(t.amount) AS total_volume
FROM transactions t
JOIN merchants m ON t.merchant_id = m.id
WHERE t.status = 'success'
GROUP BY m.id, m.name, m.category
ORDER BY total_volume DESC
LIMIT 10;

-- 4. Taux de fraude par pays client
SELECT
    c.country_code,
    COUNT(*)                                        AS total,
    SUM(CASE WHEN t.fraud_score > 0.7 THEN 1 END)  AS suspected_fraud,
    ROUND(
        100.0 * SUM(CASE WHEN t.fraud_score > 0.7 THEN 1 END) / COUNT(*), 2
    )                                               AS fraud_rate_pct
FROM transactions t
JOIN customers c ON t.customer_id = c.id
GROUP BY c.country_code
ORDER BY fraud_rate_pct DESC;

-- 5. Remboursements en attente de réconciliation
SELECT
    r.id        AS refund_id,
    r.amount    AS refund_amount,
    t.amount    AS original_amount,
    t.status,
    t.created_at AS transaction_date,
    r.created_at AS refund_date,
    r.reason
FROM refunds r
JOIN transactions t ON r.transaction_id = t.id
WHERE t.status != 'refunded'
ORDER BY r.created_at DESC;
