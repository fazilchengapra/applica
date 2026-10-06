-- AlterTable
--
-- dedupe_key is the producer's stable identity for the logical event that caused
-- the notification (a VerificationToken id, say), not something derived from the
-- notification row itself. Nullable: many notifications are not worth
-- deduplicating.
ALTER TABLE "notifications" ADD COLUMN "dedupe_key" VARCHAR(255);

-- CreateIndex
--
-- A plain UNIQUE index treats NULLs as distinct, so this already permits any
-- number of rows per user with a NULL dedupe_key. A partial index
-- ("WHERE dedupe_key IS NOT NULL") would be smaller since most rows have no key,
-- but it is not representable in the Prisma schema, so `prisma migrate` would
-- treat it as drift on the next diff. Expressed here instead, which keeps the
-- constraint one `prisma migrate` understands.
--
-- This is the guard for the two retry paths that could otherwise double-insert:
-- the producer retrying an HTTP request whose response was lost after the insert
-- committed, and BullMQ re-running a job.
CREATE UNIQUE INDEX "uq_notifications_user_dedupe" ON "notifications"("user_id", "dedupe_key");