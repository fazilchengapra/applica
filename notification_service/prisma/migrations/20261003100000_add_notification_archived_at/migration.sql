-- AlterTable
--
-- archived_at is when the user dismissed a notification, which is not the same
-- fact as read_at: read means seen, archived means no longer in the inbox. Keeping
-- them apart means dismissing does not overwrite when it was read, and the
-- retention job can prune dismissed rows while leaving unread ones alone.
ALTER TABLE "notifications" ADD COLUMN "archived_at" TIMESTAMPTZ(6);

-- DropIndex
--
-- Replaced by the two indexes below. It could serve the default list only by
-- leaving read_at unconstrained between user_id and created_at, which forces a
-- sort, and it could not express the archived filter at all.
DROP INDEX "idx_user_read_created";

-- CreateIndex
--
-- The default list: user_id + archived_at IS NULL, with created_at/id DESC
-- matching the newest-first ordering. It narrows the query to one user's live rows
-- instead of scanning the table. The sort is not eliminated -- `archived_at IS NULL`
-- is applied as a filter, not an equality scan key -- but it then sorts only that
-- user's rows.
CREATE INDEX "idx_user_archived_created" ON "notifications"("user_id", "archived_at", "created_at" DESC, "id" DESC);

-- CreateIndex
--
-- The unread list and the unread count are user_id + read_at IS NULL +
-- archived_at IS NULL. Unread is a small subset of a user's rows, so this scan is
-- correspondingly tighter than the default list's.
CREATE INDEX "idx_user_read_archived_created" ON "notifications"("user_id", "read_at", "archived_at", "created_at" DESC, "id" DESC);

-- CreateIndex
--
-- The retention sweep. read_at IS NOT NULL narrows to rows eligible for
-- deletion and created_at then gives the cutoff range, so the daily prune only
-- touches rows it is about to remove.
CREATE INDEX "idx_read_created" ON "notifications"("read_at", "created_at");