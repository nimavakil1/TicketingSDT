-- Migration: Add unique constraints to order_number and purchase_order_number
-- Date: 2025-10-23
-- Reason: Prevent race condition where two emails for same order create duplicate tickets

-- Step 1: Check for existing duplicates (run this first)
-- If any duplicates exist, you'll need to manually resolve them before applying constraints

SELECT 'Duplicate order_numbers found:' as message;
SELECT order_number, COUNT(*) as count
FROM ticket_states
WHERE order_number IS NOT NULL
GROUP BY order_number
HAVING COUNT(*) > 1;

SELECT 'Duplicate purchase_order_numbers found:' as message;
SELECT purchase_order_number, COUNT(*) as count
FROM ticket_states
WHERE purchase_order_number IS NOT NULL
GROUP BY purchase_order_number
HAVING COUNT(*) > 1;

-- Step 2: If no duplicates were found above, apply the unique constraints
-- NOTE: SQLite doesn't support adding constraints to existing tables directly
-- We need to recreate the table. This is handled by the application's init_database()
-- which will create the new schema. For existing databases:

-- OPTION A: If starting fresh (no important data):
--   Just let the app recreate the tables with new constraints

-- OPTION B: If you have existing data without duplicates:
--   1. Back up your database
--   2. Let the app handle the migration by recreating the table
--   3. SQLAlchemy will copy data to the new table structure

-- For manual migration (if needed), you would:
-- 1. Rename old table
-- 2. Create new table with constraints
-- 3. Copy data from old table
-- 4. Drop old table

-- This migration is safe to run multiple times (idempotent)
